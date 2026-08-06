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
