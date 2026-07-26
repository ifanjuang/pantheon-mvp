-- Simplify project contacts: one project-owned JSON snapshot, no participation relation.
-- This is an Agency Data storage simplification, not a new governance authority.

ALTER TABLE agency_projects
    ADD COLUMN IF NOT EXISTS contacts JSONB NOT NULL DEFAULT '[]'::jsonb;

-- ProjectParticipation is intentionally retired. People and Organizations remain
-- available as optional directory sources; projects no longer relate to them here.
DROP TABLE IF EXISTS agency_project_participations;
