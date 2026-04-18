# Tag Convention Contract

**Feature**: 002-reduce-broad-except
**Owners**: All Python source files in `solune/backend/src/` containing Tagged broad-except handlers.
**Consumers**: `uv run ruff check` (linter), code reviewers, new contributors.

This contract specifies the format, placement, and usage rules for the `# noqa: BLE001` justification tag applied to intentionally broad exception handlers.

---

## T1 — Tag format

### Canonical form

```python
except Exception as exc:  # noqa: BLE001 — reason: <one-line human-readable justification>
```

### Regex for machine validation

```regex
# noqa: BLE001\s*[—-]\s*reason:\s*.+
```

### Components

| Component | Required | Description |
|---|---|---|
| `# noqa: BLE001` | Yes | Ruff suppression directive. Must be on the same line as the `except` keyword. |
| `—` (em-dash) or `-` (hyphen) | Yes | Separator between the rule code and the reason. Em-dash is preferred; hyphen is accepted. |
| `reason:` | Yes | Keyword prefix for the human-readable justification. |
| `<justification text>` | Yes | One-line explanation of why this broad handler is intentional. Must be non-empty. |

### Valid examples

```python
# Third-party callback with unknown exception surface
except Exception:  # noqa: BLE001 — reason: plugin hook may raise any exception; caller logs and continues

# asyncio.TaskGroup drain where child exceptions are unbounded
except Exception as exc:  # noqa: BLE001 — reason: TaskGroup.gather collects arbitrary child exceptions

# Best-effort helper (canonical wrapper)
except Exception as exc:  # noqa: BLE001 — reason: canonical best-effort wrapper; callers pass context

# Startup resilience (app must boot even if optional setup fails)
except Exception as exc:  # noqa: BLE001 — reason: non-blocking startup step; failure logged, app continues
```

### Invalid examples (rejected in code review)

```python
# Missing reason text
except Exception:  # noqa: BLE001

# Empty reason
except Exception:  # noqa: BLE001 — reason:

# Missing reason: prefix
except Exception:  # noqa: BLE001 — because it might fail

# Global suppression (file-level)
# ruff: noqa: BLE001  ← FORBIDDEN at file level
```

---

## T2 — Placement rules

1. The `# noqa: BLE001 — reason:` tag MUST appear on the same line as the `except Exception` keyword. Ruff requires inline `# noqa` directives on the line that triggers the diagnostic.

2. The tag MUST NOT be placed on a separate line or as a block comment above the `except` clause — Ruff will not recognise it.

3. If the `except` line would exceed the line-length limit (88 characters by default in Ruff's formatter), the tag may still be placed on the same line — `E501` is already ignored in this project's configuration, so long lines are accepted.

---

## T3 — When to use the tag

The tag is appropriate ONLY when the exception handler meets ALL of the following criteria:

1. **The wrapped call has a genuinely unbounded exception surface** — the caller cannot predict which exception types the callee may raise (e.g., third-party callbacks, plugin hooks, dynamic dispatch).

2. **Silent failure is the correct behaviour** — the caller has explicitly decided that this operation is non-critical and a fallback value is acceptable.

3. **The failure is logged** — the handler logs the exception at an appropriate severity level (`error`, `warning`, or `debug`).

4. **No narrower exception type exists** — if the call only raises a known set of exceptions, the handler should be narrowed instead of tagged.

### Decision flowchart

```text
Is the call's exception surface bounded?
├── Yes → Narrow the except clause to specific types
└── No  → Is silent failure acceptable?
          ├── No  → Promote (remove handler; let caller handle)
          └── Yes → Is the failure logged?
                    ├── No  → Add logging, then Tag
                    └── Yes → Tag with # noqa: BLE001 — reason: ...
```

---

## T4 — Documentation requirement (FR-005)

The tag convention MUST be documented in `solune/backend/README.md` with:

1. **Format specification**: The canonical `# noqa: BLE001 — reason:` format.
2. **When to use it**: The decision flowchart from T3.
3. **Examples**: At least 3 examples covering the most common Tagged scenarios.
4. **Cross-reference**: Link to this contract for full details.

A new contributor should be able to find and understand the convention within 2 minutes (SC-005).
