# Dashboard

The dashboard route (`/`) is now Solune's full-screen chat workspace. Instead of a welcome hero or quick-access cards, `AppPage` renders `ChatPanelManager` so you can work in one or more conversations side by side.

## What You See

### Desktop layout

- **Chat panels** — each panel is an independent conversation backed by its own `conversation_id`
- **Resizable split view** — drag the divider between panels to rebalance width (minimum 320 px per panel)
- **Add chat button** — open another conversation without leaving the page
- **Editable titles** — rename each conversation from the panel header
- **Close button** — remove a panel when more than one conversation is open

### Mobile layout

- **Tabbed conversations** — panels switch to a one-at-a-time tab strip below 768 px
- **Add Chat action** — create another conversation from the tab bar or footer action

## How to Use It

1. Start on `/` after signing in.
2. Use the first panel for your main conversation.
3. Click **Add Chat** to open another conversation for a different task or app.
4. Resize desktop panels or switch tabs on mobile as needed.
5. Rename a panel when you want a clearer conversation title.

## Conversation Behavior

- Panel layout is persisted in `localStorage` under `solune:chat-panels`.
- Each panel keeps its own message history and plan-mode state.
- Deleting a panel removes its conversation after the UI closes it.
- The floating chat popup on other pages remains available, but it is separate from the dashboard's multi-panel conversations.
