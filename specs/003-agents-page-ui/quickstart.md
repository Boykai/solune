# Quickstart: Agents Page UI Improvements

## Prerequisites
- Repository checked out at `/home/runner/work/solune/solune`
- Frontend dependencies installed in `/home/runner/work/solune/solune/solune/frontend`

## Focused validation commands

```bash
cd /home/runner/work/solune/solune/solune/frontend
npm run type-check
npm run build
npm run test -- src/components/agents/__tests__/AgentsPanel.test.tsx src/components/agents/__tests__/AddAgentModal.test.tsx
```

## Manual verification flow

1. Start the frontend app from `/home/runner/work/solune/solune/solune/frontend` with `npm run dev`.
2. Open the Agents page for a project with at least one configured agent.
3. Confirm the visible section order is:
   - Quick Actions
   - Save Banner (only when present)
   - Pending Changes (only when present)
   - Catalog Controls
   - Awesome Catalog
4. Verify there is no Featured Agents section anywhere on the page.
5. Click each chevron in Pending Changes, Catalog Controls, and Awesome Catalog:
   - the section body collapses/expands
   - the chevron visually reflects the state
   - toggling one section does not change the others
6. Click `+ Add Agent`:
   - with short content, the modal remains centered
   - with tall content / smaller viewport, the overlay scroll position exposes the top of the modal instead of clipping it above the fold
7. Capture an updated screenshot of the Agents page after the UI changes are implemented.
