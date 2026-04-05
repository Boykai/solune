import { useCallback, useLayoutEffect, useRef, type RefObject } from 'react';

/**
 * Returns a `focusFirstError` function that, when called, focuses the first
 * field whose key has a truthy entry in `errors`.
 *
 * `fieldRefs` keys determine the priority order (first key = highest priority).
 *
 * Both `fieldRefs` and `errors` are mirrored into refs so the returned
 * callback always reads the *latest* values even when invoked from a stale
 * closure (e.g. inside `requestAnimationFrame`).
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
  // Mirror both arguments into refs via useLayoutEffect so the callback is
  // always up-to-date regardless of which render's closure it was captured in.
  // useLayoutEffect runs synchronously after every render, before the browser
  // paints — so by the time requestAnimationFrame fires the refs are current.
  const fieldRefsRef = useRef(fieldRefs);
  const errorsRef = useRef(errors);
  useLayoutEffect(() => {
    fieldRefsRef.current = fieldRefs;
    errorsRef.current = errors;
  });

  return useCallback(() => {
    const latestRefs = fieldRefsRef.current;
    const latestErrors = errorsRef.current;
    for (const key of Object.keys(latestRefs)) {
      if (latestErrors[key]) {
        latestRefs[key]?.current?.focus();
        return;
      }
    }
  }, []); // stable – reads from refs at call time
}
