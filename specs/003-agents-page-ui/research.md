# Research: Agents Page UI Improvements

## Decision 1: Fix the modal viewport issue by changing only the overlay alignment
- **Decision**: Change the outer Add Agent modal overlay from `items-center` to `items-start` and keep the inner dialog's existing `my-auto` class.
- **Rationale**: The bug is caused by flex centering on an overflowable overlay. Using `items-start` allows tall content to begin at the top of the scroll container while `my-auto` preserves centering for shorter dialog content.
- **Alternatives considered**:
  - Add custom viewport height calculations in JavaScript — rejected as unnecessary complexity for a class-level layout issue.
  - Remove `my-auto` from the inner dialog — rejected because it would worsen the short-content centering behavior the spec wants to keep.

## Decision 2: Remove Featured Agents entirely instead of hiding it
- **Decision**: Delete the Featured Agents section, its memoized spotlight calculation, and every import/derived value used only by that section.
- **Rationale**: The specification explicitly requires the entire section to disappear and calls for dead-code cleanup. Removing the logic is smaller and safer than leaving dormant code paths behind.
- **Alternatives considered**:
  - Hide the section behind a feature flag or condition — rejected because the spec requires complete removal.
  - Keep the spotlight calculation for future reuse — rejected because no remaining consumer exists in scope.

## Decision 3: Add collapsible behavior with local component state and shared visual cues
- **Decision**: Add three local booleans in `AgentsPanel.tsx` (`pendingCollapsed`, `catalogCollapsed`, `awesomeCatalogCollapsed`) and render a clickable `ChevronDown` in each section header.
- **Rationale**: This matches the explicit product decision in the spec and the existing `SettingsSection` interaction pattern: local state, no persistence, and a rotated chevron to communicate state.
- **Alternatives considered**:
  - Introduce a reusable collapsible section component — rejected because the scope is small and the spec explicitly prefers inline state.
  - Persist collapse state in local storage — rejected because persistence is out of scope.

## Decision 4: Treat this as a frontend-only change with a no-op API contract
- **Decision**: Record an empty OpenAPI artifact for this feature with an explicit note that no backend endpoints, payloads, or schemas change.
- **Rationale**: The requested work is entirely presentation/state behavior in existing frontend components. Capturing that explicitly prevents downstream agents from inventing unnecessary backend work.
- **Alternatives considered**:
  - Skip the contract artifact entirely — rejected because `/speckit.plan` Phase 1 expects a contracts output.
  - Create synthetic API endpoints for UI toggles — rejected because collapse state is local-only and not persisted.

## Decision 5: Verify with existing frontend commands and focused agent tests
- **Decision**: Use the existing frontend commands `npm run type-check`, `npm run build`, and the focused AgentsPanel/AddAgentModal Vitest files for validation.
- **Rationale**: The repository already has agent-specific tests covering these components, and the feature specification explicitly calls for build/type-check plus agent-related regression coverage.
- **Alternatives considered**:
  - Run the entire frontend suite only — rejected as broader than necessary for a small localized UI change.
  - Add new test infrastructure — rejected because existing Vitest coverage is sufficient.
