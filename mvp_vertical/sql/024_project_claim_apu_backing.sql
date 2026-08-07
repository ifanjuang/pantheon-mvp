-- H3: let ProjectClaims cite an existing APU object as governed backing.
--
-- The APU object remains support/context only. This migration does not canonize
-- an object claim, admit Evidence, validate professional truth or mutate APU.

CREATE OR REPLACE FUNCTION validate_agency_project_claim_apu_backing()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    backing_project_id TEXT;
BEGIN
    IF NEW.backing_entity_type <> 'apu_object' THEN
        RETURN NEW;
    END IF;

    IF to_regclass('agency_apu_objects') IS NULL THEN
        RAISE EXCEPTION 'APU owner is unavailable for ProjectClaim backing';
    END IF;

    EXECUTE 'SELECT project_id FROM agency_apu_objects WHERE object_id = $1'
       INTO backing_project_id USING NEW.backing_entity_id;

    IF backing_project_id IS NULL THEN
        RAISE EXCEPTION 'unknown apu_object ProjectClaim backing: %', NEW.backing_entity_id;
    END IF;
    IF backing_project_id <> NEW.project_id THEN
        RAISE EXCEPTION 'ProjectClaim APU backing must belong to the Claim Project';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS agency_project_claims_validate_apu_backing
    ON agency_project_claims;
CREATE TRIGGER agency_project_claims_validate_apu_backing
BEFORE INSERT ON agency_project_claims
FOR EACH ROW
EXECUTE FUNCTION validate_agency_project_claim_apu_backing();

-- Extend the existing execution-candidate gate without introducing another
-- ProjectClaim candidate path. Exact candidate/result/review provenance remains
-- unchanged; only the already-open basis_ref type `apu_object` gains an executable
-- same-Project resolver.
CREATE OR REPLACE FUNCTION validate_agency_project_claim_candidate_ref()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    actual_execution_id TEXT;
    candidate_kind TEXT;
    candidate_payload JSONB;
    execution_project_ref TEXT;
    review_result_ref TEXT;
    review_disposition TEXT;
    review_kind TEXT;
    latest_disposition_id TEXT;
    matching_basis JSONB;
    backing_project_id TEXT;
BEGIN
    IF NEW.source_kind <> 'execution_result' THEN
        RETURN NEW;
    END IF;

    IF to_regclass('execution_result_items') IS NULL
       OR to_regclass('execution_result_review_dispositions') IS NULL THEN
        RAISE EXCEPTION 'execution result authorities are unavailable for ProjectClaim creation';
    END IF;

    SELECT i.execution_result_id, i.result_kind, i.payload, e.project_ref
      INTO actual_execution_id, candidate_kind, candidate_payload, execution_project_ref
      FROM execution_result_items i
      JOIN execution_results e
        ON e.execution_result_id = i.execution_result_id
     WHERE i.result_id = NEW.candidate_result_id
     FOR UPDATE OF i;

    IF actual_execution_id IS NULL OR actual_execution_id <> NEW.candidate_execution_id THEN
        RAISE EXCEPTION 'ProjectClaim candidate result does not belong to the declared execution';
    END IF;
    IF candidate_kind <> 'project_claim_candidate' THEN
        RAISE EXCEPTION 'ProjectClaim creation requires a project_claim_candidate result';
    END IF;
    IF execution_project_ref IS DISTINCT FROM NEW.project_id
       OR candidate_payload->>'project_ref' IS DISTINCT FROM NEW.project_id THEN
        RAISE EXCEPTION 'ProjectClaim candidate and execution must belong to the Claim Project';
    END IF;
    IF candidate_payload->>'claim_type' IS DISTINCT FROM NEW.claim_type THEN
        RAISE EXCEPTION 'ProjectClaim claim_type must match the reviewed candidate';
    END IF;
    IF candidate_payload->'proposed_value' IS DISTINCT FROM NEW.value THEN
        RAISE EXCEPTION 'ProjectClaim value must match the reviewed candidate';
    END IF;
    IF candidate_payload->>'unit' IS DISTINCT FROM NEW.unit THEN
        RAISE EXCEPTION 'ProjectClaim unit must match the reviewed candidate';
    END IF;
    IF (candidate_payload->>'observed_at')::timestamptz IS DISTINCT FROM NEW.observed_at THEN
        RAISE EXCEPTION 'ProjectClaim observed_at must match the reviewed candidate';
    END IF;
    IF (candidate_payload->>'effective_at')::timestamptz IS DISTINCT FROM NEW.effective_at THEN
        RAISE EXCEPTION 'ProjectClaim effective_at must match the reviewed candidate';
    END IF;

    SELECT result_ref, disposition, reviewer_kind
      INTO review_result_ref, review_disposition, review_kind
      FROM execution_result_review_dispositions
     WHERE disposition_id = NEW.candidate_review_disposition_id;

    IF review_result_ref IS NULL OR review_result_ref <> NEW.candidate_result_id THEN
        RAISE EXCEPTION 'ProjectClaim review disposition does not belong to the candidate result';
    END IF;
    IF review_disposition <> 'accepted_for_claim' OR review_kind <> 'human' THEN
        RAISE EXCEPTION 'ProjectClaim creation requires a human accepted_for_claim disposition';
    END IF;

    SELECT disposition_id
      INTO latest_disposition_id
      FROM execution_result_review_dispositions
     WHERE result_ref = NEW.candidate_result_id
     ORDER BY occurred_at DESC, disposition_id DESC
     LIMIT 1;

    IF latest_disposition_id <> NEW.candidate_review_disposition_id THEN
        RAISE EXCEPTION 'ProjectClaim creation requires the latest candidate disposition';
    END IF;

    IF NEW.backing_entity_type IS NOT NULL THEN
        IF NEW.backing_entity_type NOT IN ('project', 'information', 'apu_object') THEN
            RAISE EXCEPTION 'candidate-backed Claim admits project, information or apu_object backing';
        END IF;

        SELECT basis
          INTO matching_basis
          FROM jsonb_array_elements(COALESCE(candidate_payload->'basis_refs', '[]'::jsonb)) basis
         WHERE basis->>'entity_type' = NEW.backing_entity_type
           AND basis->>'entity_id' = NEW.backing_entity_id
         LIMIT 1;

        IF matching_basis IS NULL THEN
            RAISE EXCEPTION 'ProjectClaim backing_ref must be one of the candidate basis_refs';
        END IF;
        IF matching_basis->>'observed_status' IS DISTINCT FROM NEW.backing_observed_status THEN
            RAISE EXCEPTION 'ProjectClaim backing observed_status must match the candidate basis_ref';
        END IF;

        IF NEW.backing_entity_type = 'project' THEN
            IF NEW.backing_entity_id <> NEW.project_id THEN
                RAISE EXCEPTION 'ProjectClaim project backing must identify the Claim Project';
            END IF;
        ELSIF NEW.backing_entity_type = 'information' THEN
            SELECT project_id
              INTO backing_project_id
              FROM agency_information_cards
             WHERE information_id = NEW.backing_entity_id;
            IF backing_project_id IS NULL OR backing_project_id <> NEW.project_id THEN
                RAISE EXCEPTION 'ProjectClaim information backing must belong to the Claim Project';
            END IF;
        ELSE
            IF to_regclass('agency_apu_objects') IS NULL THEN
                RAISE EXCEPTION 'APU owner is unavailable for ProjectClaim backing';
            END IF;
            EXECUTE 'SELECT project_id FROM agency_apu_objects WHERE object_id = $1'
               INTO backing_project_id USING NEW.backing_entity_id;
            IF backing_project_id IS NULL OR backing_project_id <> NEW.project_id THEN
                RAISE EXCEPTION 'ProjectClaim APU backing must belong to the Claim Project';
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;
