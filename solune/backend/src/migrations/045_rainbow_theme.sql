-- Add rainbow_theme toggle to user_preferences and global_settings.
-- Stores whether the rainbow colour scheme is enabled (1) or disabled (0).

ALTER TABLE user_preferences ADD COLUMN rainbow_theme INTEGER DEFAULT 0;

ALTER TABLE global_settings ADD COLUMN rainbow_theme INTEGER DEFAULT 0;
