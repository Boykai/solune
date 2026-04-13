"""Chat API sub-package.

Splits the monolithic chat.py into focused modules:
- messages.py: Conversation and message CRUD endpoints
- streaming.py: SSE streaming endpoint
- proposals.py: Proposal confirmation and cancellation
- plans.py: Plan mode endpoints
- uploads.py: File upload endpoint
- persistence.py: SQLite persistence helpers
- constants.py: Shared types, constants, and config
"""
