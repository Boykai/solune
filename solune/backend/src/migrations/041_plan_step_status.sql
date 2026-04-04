-- Migration 041: Per-step approval status
ALTER TABLE chat_plan_steps ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (approval_status IN ('pending', 'approved', 'rejected'));
