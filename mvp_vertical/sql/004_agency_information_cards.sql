CREATE TABLE IF NOT EXISTS agency_information_cards (
    information_id TEXT PRIMARY KEY,
    series_id TEXT NOT NULL,
    project_id TEXT NOT NULL REFERENCES agency_projects(project_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT,
    source_note TEXT,
    source_version TEXT,
    index_label TEXT NOT NULL,
    information_date DATE,
    summary TEXT NOT NULL DEFAULT '',
    details TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('draft', 'in_progress', 'acted', 'superseded')),
    limits JSONB NOT NULL DEFAULT '[]'::jsonb,
    type_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    subject_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    author TEXT,
    base_acted_id TEXT REFERENCES agency_information_cards(information_id) ON DELETE RESTRICT,
    previous_source_id TEXT REFERENCES agency_information_cards(information_id) ON DELETE RESTRICT,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision >= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acted_at TIMESTAMPTZ,
    CHECK (source_ref IS NOT NULL OR source_note IS NOT NULL),
    CHECK ((status = 'acted' AND acted_at IS NOT NULL) OR status <> 'acted')
);

CREATE INDEX IF NOT EXISTS agency_information_project_lookup
    ON agency_information_cards (project_id, series_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS agency_information_one_working_version
    ON agency_information_cards (series_id)
    WHERE status IN ('draft', 'in_progress');

CREATE UNIQUE INDEX IF NOT EXISTS agency_information_one_current_acted
    ON agency_information_cards (series_id)
    WHERE status = 'acted';
