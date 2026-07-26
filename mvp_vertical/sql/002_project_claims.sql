-- Agency Data seam: a project_claim is a typed, status-qualified value shown on
-- a Project Card that CITES its backing card. It conforms to the vendored
-- governance schema mvp_vertical/vendor/pantheon/project_claim.schema.yaml
-- (upstream schemas/project_claim.schema.yaml). This is bounded internal
-- persistence, not an approval, Evidence admission or system-of-record mutation
-- engine: the status vocabulary has no "approved" value by construction, and
-- nothing here promotes a claim to an opposable value.
--
-- Per AGENCY_DATA_SYSTEM_OF_RECORD.md §15 the native records live under the
-- agency.* semantic schema. Physical co-location grants no cross-schema
-- authority.

CREATE SCHEMA IF NOT EXISTS agency;

CREATE TABLE IF NOT EXISTS agency.project_claim (
    claim_id TEXT PRIMARY KEY CHECK (claim_id ~ '^[a-z0-9._-]+$'),
    project_id TEXT NOT NULL CHECK (length(project_id) >= 1),
    claim_type TEXT NOT NULL CHECK (length(claim_type) >= 1),
    -- value is scalar-polymorphic in the schema (string | number | boolean |
    -- null); JSONB preserves the scalar type faithfully on round-trip.
    value JSONB,
    unit TEXT,
    -- backing_card_ref (object): the card that backs the claim.
    card_family TEXT NOT NULL CHECK (
        card_family IN (
            'document', 'evidence', 'knowledge', 'decision',
            'surface_fact', 'jalon', 'participation'
        )
    ),
    card_id TEXT NOT NULL CHECK (length(card_id) >= 1),
    card_status TEXT,
    -- provenance (object).
    source_kind TEXT NOT NULL CHECK (
        source_kind IN ('document', 'human_assertion', 'derived', 'external_projection')
    ),
    source_ref TEXT,
    asserted_by TEXT,
    derivation_note TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('asserted', 'source_backed', 'verified', 'contested', 'retired')
    ),
    observed_at TIMESTAMPTZ NOT NULL,
    -- optimistic-concurrency marker, aligned with the Agency Data doctrine.
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    supersedes TEXT,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS project_claim_by_project
    ON agency.project_claim (project_id, claim_type, observed_at DESC);
