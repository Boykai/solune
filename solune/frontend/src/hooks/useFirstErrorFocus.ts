import { useCallback, type RefObject } from 'react';

/**
 * Returns a `focusFirstError` function that, when called, focuses the first
 * field whose key has a truthy entry in `errors`.
 *
 * `fieldRefs` keys determine the priority order (first key = highest priority).
 *
 * Usage:
 *   const nameRef = useRef<HTMLInputElement>(null);
 *   const promptRef = useRef<HTMLTextAreaElement>(null);
 *   const focusFirstError = useFirstErrorFocus(
 *     { name: nameRef, prompt: promptRef },
 *     { name: nameError, prompt: promptError },
 *   );
 *   // In submit handler after validation:
 *   if (!valid) { focusFirstError(); return; }
 */
export function useFirstErrorFocus(
  fieldRefs: Record<string, RefObject<HTMLElement | null>>,
  errors: Record<string, string | null | undefined>,
) {
  return useCallback(() => {
    for (const key of Object.keys(fieldRefs)) {
      if (errors[key]) {
        fieldRefs[key]?.current?.focus();
        return;
      }
    }
  }, [fieldRefs, errors]);
}
