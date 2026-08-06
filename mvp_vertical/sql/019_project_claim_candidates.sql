-- Tranche F: qualify ProjectClaims and preserve exact Execution Result provenance.
--
-- Existing Claims remain valid but acquire certainty E0 because no stronger
-- certainty was recorded. The migration creates no Claim and promotes no result.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'agency_project_claims' AND column_name = 'certainty'
    ) THEN
        ALTER TABLE agency_project_claims
            ADD COLUMN certainty TEXT NOT NULL DEFAULT 'E0';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'agency_project_claims' AND column_name = 'effective_at'
    ) THEN
        ALTER TABLE agency_project_claims ADD COLUMN effective_at TIMESTAMPTZ;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'agency_project_claims' AND column_name = 'candidate_execution_id'
    ) THEN
        ALTER TABLE agency_project_claims ADD COLUMN candidate_execution_id TEXT;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'agency_project_claims' AND column_name = 'candidate_result_id'
    ) THEN
        ALTER TABLE agency_project_claims ADD COLUMN candidate_result_id TEXT;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'agency_project_claims' AND column_name = 'candidate_review_disposition_id'
    ) THEN
        ALTER TABLE agency_project_claims ADD COLUMN candidate_review_disposition_id TEXT;
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'agency_project_claims'::regclass
           AND conname = 'agency_project_claims_certainty_check'
    ) THEN
        ALTER TABLE agency_project_claims
            ADD CONSTRAINT agency_project_claims_certainty_check
            CHECK (certainty IN ('E0', 'E1', 'E2', 'E3', 'E4')) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'agency_project_claims'::regclass
           AND pg_get_constraintdef(oid) LIKE '%execution_result%'
           AND pg_get_constraintdef(oid) LIKE '%source_kind%'
    ) THEN
        ALTER TABLE agency_project_claims
            DROP CONSTRAINT IF EXISTS agency_project_claims_source_kind_check;
        ALTER TABLE agency_project_claims
            ADD CONSTRAINT agency_project_claims_source_kind_check
            CHECK (source_kind IN (
                'information', 'document', 'human_assertion', 'derived',
                'execution_result', 'external_projection'
            )) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'agency_project_claims'::regclass
           AND conname = 'agency_project_claims_candidate_identity_check'
    ) THEN
        ALTER TABLE agency_project_claims
            ADD CONSTRAINT agency_project_claims_candidate_identity_check
            CHECK (
                (candidate_execution_id IS NULL AND candidate_result_id IS NULL
                 AND candidate_review_disposition_id IS NULL)
                OR
                (candidate_execution_id IS NOT NULL AND candidate_result_id IS NOT NULL)
            ) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'agency_project_claims'::regclass
           AND conname = 'agency_project_claims_execution_source_check'
    ) THEN
        ALTER TABLE agency_project_claims
            ADD CONSTRAINT agency_project_claims_execution_source_check
            CHECK (
                source_kind <> 'execution_result'
                OR (candidate_execution_id IS NOT NULL AND candidate_result_id IS NOT NULL)
            ) NOT VALID;
    END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS agency_project_claims_one_claim_per_candidate
    ON agency_project_claims (candidate_execution_id, candidate_result_id)
    WHERE candidate_execution_id IS NOT NULL AND candidate_result_id IS NOT NULL;

-- These references are installed only when the execution-result owner is present.
-- Standalone Agency Data initialization remains valid; composed startup replays
-- this migration after execution_results and installs the references.
DO $$
BEGIN
    IF to_regclass('execution_results') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM pg_constraint
            WHERE conrelid = 'agency_project_claims'::regclass
              AND conname = 'agency_project_claims_candidate_execution_fk'
       ) THEN
        ALTER TABLE agency_project_claims
            ADD CONSTRAINT agency_project_claims_candidate_execution_fk
            FOREIGN KEY (candidate_execution_id)
            REFERENCES execution_results(execution_result_id) ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF to_regclass('execution_result_items') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM pg_constraint
            WHERE conrelid = 'agency_project_claims'::regclass
              AND conname = 'agency_project_claims_candidate_result_fk'
       ) THEN
        ALTER TABLE agency_project_claims
            ADD CONSTRAINT agency_project_claims_candidate_result_fk
            FOREIGN KEY (candidate_result_id)
            REFERENCES execution_result_items(result_id) ON DELETE RESTRICT
            NOT VALID;
    END IF;

    IF to_regclass('execution_result_review_dispositions') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM pg_constraint
            WHERE conrelid = 'agency_project_claims'::regclass
              AND conname = 'agency_project_claims_candidate_disposition_fk'
       ) THEN
        ALTER TABLE agency_project_claims
            ADD CONSTRAINT agency_project_claims_candidate_disposition_fk
            FOREIGN KEY (candidate_review_disposition_id)
            REFERENCES execution_result_review_dispositions(disposition_id)
            ON DELETE RESTRICT NOT VALID;
    END IF;
END;
$$;

-- Refresh the existing Project read cache with the qualified Claim shape. The
-- cache remains derived and never becomes a second Claim authority.
CREATE OR REPLACE FUNCTION refresh_agency_project_claim_projection(target_project_id TEXT)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    scalar_values JSONB := '{}'::jsonb;
    scalar_refs JSONB := '{}'::jsonb;
    parcel_values JSONB := '[]'::jsonb;
    parcel_refs JSONB := '[]'::jsonb;
BEGIN
    WITH active_scalar AS (
        SELECT DISTINCT ON (c.claim_type) c.*
          FROM agency_project_claims c
         WHERE c.project_id = target_project_id
           AND c.claim_type <> 'parcelle'
           AND c.status <> 'retired'
           AND NOT EXISTS (
               SELECT 1 FROM agency_project_claims newer
                WHERE newer.supersedes = c.claim_id
           )
         ORDER BY c.claim_type, c.observed_at DESC, c.created_at DESC, c.claim_id DESC
    ), projected AS (
        SELECT claim_type,
               value,
               jsonb_build_object(
                   'claim_id', claim_id,
                   'status', status,
                   'certainty', certainty,
                   'unit', unit,
                   'backing_ref', CASE
                       WHEN backing_entity_type IS NULL THEN NULL
                       ELSE jsonb_build_object(
                           'entity_type', backing_entity_type,
                           'entity_id', backing_entity_id,
                           'observed_status', backing_observed_status
                       )
                   END,
                   'provenance', jsonb_build_object(
                       'source_kind', source_kind,
                       'source_ref', source_ref,
                       'candidate_ref', CASE
                           WHEN candidate_execution_id IS NULL THEN NULL
                           ELSE jsonb_build_object(
                               'execution_id', candidate_execution_id,
                               'result_id', candidate_result_id,
                               'review_disposition_id', candidate_review_disposition_id
                           )
                       END,
                       'asserted_by', asserted_by,
                       'derivation_note', derivation_note
                   ),
                   'observed_at', observed_at,
                   'effective_at', effective_at
               ) AS ref
          FROM active_scalar
    )
    SELECT COALESCE(jsonb_object_agg(claim_type, value), '{}'::jsonb),
           COALESCE(jsonb_object_agg(claim_type, ref), '{}'::jsonb)
      INTO scalar_values, scalar_refs
      FROM projected;

    WITH active_parcels AS (
        SELECT c.*
          FROM agency_project_claims c
         WHERE c.project_id = target_project_id
           AND c.claim_type = 'parcelle'
           AND c.status <> 'retired'
           AND NOT EXISTS (
               SELECT 1 FROM agency_project_claims newer
                WHERE newer.supersedes = c.claim_id
           )
         ORDER BY c.observed_at DESC, c.created_at DESC, c.claim_id DESC
    )
    SELECT COALESCE(jsonb_agg(value), '[]'::jsonb),
           COALESCE(jsonb_agg(jsonb_build_object(
               'claim_id', claim_id,
               'status', status,
               'certainty', certainty,
               'backing_ref', CASE
                   WHEN backing_entity_type IS NULL THEN NULL
                   ELSE jsonb_build_object(
                       'entity_type', backing_entity_type,
                       'entity_id', backing_entity_id,
                       'observed_status', backing_observed_status
                   )
               END,
               'provenance', jsonb_build_object(
                   'source_kind', source_kind,
                   'source_ref', source_ref,
                   'candidate_ref', CASE
                       WHEN candidate_execution_id IS NULL THEN NULL
                       ELSE jsonb_build_object(
                           'execution_id', candidate_execution_id,
                           'result_id', candidate_result_id,
                           'review_disposition_id', candidate_review_disposition_id
                       )
                   END,
                   'asserted_by', asserted_by,
                   'derivation_note', derivation_note
               ),
               'observed_at', observed_at,
               'effective_at', effective_at
           )), '[]'::jsonb)
      INTO parcel_values, parcel_refs
      FROM active_parcels;

    IF jsonb_array_length(parcel_values) > 0 THEN
        scalar_values := scalar_values || jsonb_build_object('parcelle', parcel_values);
        scalar_refs := scalar_refs || jsonb_build_object('parcelle', parcel_refs);
    END IF;

    UPDATE agency_projects
       SET claim_values = scalar_values,
           claim_refs = scalar_refs
     WHERE project_id = target_project_id;
END;
$$;
