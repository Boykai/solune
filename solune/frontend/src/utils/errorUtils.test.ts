import { describe, expect, it } from 'vitest';
import { ApiError } from '@/services/api';
import { getErrorMessage, isApiError } from './errorUtils';

describe('errorUtils', () => {
  it('identifies ApiError instances', () => {
    expect(isApiError(new ApiError(400, { error: 'Bad request' }))).toBe(true);
    expect(isApiError(new Error('oops'))).toBe(false);
  });

  it('extracts messages from ApiError and Error instances', () => {
    expect(getErrorMessage(new ApiError(400, { error: 'Bad request' }), 'fallback')).toBe(
      'Bad request'
    );
    expect(getErrorMessage(new Error('oops'), 'fallback')).toBe('oops');
  });

  it('falls back for unknown or empty error payloads', () => {
    expect(getErrorMessage(new ApiError(500, { error: '' }), 'fallback')).toBe('fallback');
    expect(getErrorMessage(42, 'fallback')).toBe('fallback');
    expect(getErrorMessage(undefined, 'fallback')).toBe('fallback');
  });
});
