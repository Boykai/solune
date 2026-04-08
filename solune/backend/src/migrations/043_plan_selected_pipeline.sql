-- Migration 043: Persist selected pipeline choice for chat plans
ALTER TABLE chat_plans ADD COLUMN selected_pipeline_id TEXT;