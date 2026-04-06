import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';

import { useFirstErrorFocus } from './useFirstErrorFocus';

type ErrorMap = {
  name: string | null;
  prompt: string | null;
};

type FieldRefs = Record<string, { current: HTMLElement | null }>;

describe('useFirstErrorFocus', () => {
  it('focuses the first field with an error using field key order', () => {
    const nameFocus = vi.fn();
    const promptFocus = vi.fn();
    const fieldRefs = {
      name: { current: { focus: nameFocus } as unknown as HTMLElement },
      prompt: { current: { focus: promptFocus } as unknown as HTMLElement },
    };
    const errors = { name: null, prompt: 'Required' };
    const { result } = renderHook(() => useFirstErrorFocus(fieldRefs, errors));

    act(() => {
      result.current();
    });

    expect(nameFocus).not.toHaveBeenCalled();
    expect(promptFocus).toHaveBeenCalledOnce();
  });

  it('uses the latest refs and errors after rerender', () => {
    const nameFocus = vi.fn();
    const promptFocus = vi.fn();
    const initialProps: { refs: FieldRefs; errors: ErrorMap } = {
      refs: {
        name: { current: { focus: nameFocus } as unknown as HTMLElement },
        prompt: { current: null as HTMLElement | null },
      },
      errors: { name: 'Missing', prompt: null },
    };
    const { result, rerender } = renderHook(
      ({ refs, errors }: { refs: FieldRefs; errors: ErrorMap }) => useFirstErrorFocus(refs, errors),
      { initialProps },
    );

    rerender({
      refs: {
        name: { current: { focus: nameFocus } as unknown as HTMLElement },
        prompt: { current: { focus: promptFocus } as unknown as HTMLElement },
      },
      errors: { name: null, prompt: 'Still missing' },
    });

    act(() => {
      result.current();
    });

    expect(nameFocus).not.toHaveBeenCalled();
    expect(promptFocus).toHaveBeenCalledOnce();
  });

  it('is a no-op when refs are null or there are no errors', () => {
    const focus = vi.fn();
    const fieldRefs = {
      name: { current: null as HTMLElement | null },
      prompt: { current: { focus } as unknown as HTMLElement },
    };
    const initialProps: { errors: ErrorMap } = {
      errors: { name: 'Missing', prompt: null },
    };
    const { result, rerender } = renderHook(
      ({ errors }: { errors: ErrorMap }) => useFirstErrorFocus(fieldRefs, errors),
      { initialProps },
    );

    act(() => {
      result.current();
    });
    expect(focus).not.toHaveBeenCalled();

    rerender({ errors: { name: null, prompt: null } });
    act(() => {
      result.current();
    });
    expect(focus).not.toHaveBeenCalled();
  });
});
