-- Migration 036: Add template_id column to apps table
-- Feature: Autonomous App Builder (v0.5.0)
-- Links app records to their originating template for display and re-scaffolding.

ALTER TABLE apps ADD COLUMN template_id TEXT;
