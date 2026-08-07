-- H3: immutable APU scope references owned by Decision Requests.
--
-- These rows project one existing Decision Request into an APU-object context.
-- They are not semantic Entity Relations, APU domain relations, task
-- authorization, Evidence or professional validation.

CREATE TABLE IF NOT EXISTS agency_decision_request_scope_refs (
    request_id TEXT NOT NULL
        REFERENCES agency_decision_requests(request_id) ON DELETE RESTRICT,
    entity_type TEXT NOT NULL CHECK (entity_type = 'apu_object'),
    entity_id TEXT NOT NULL CHECK (entity_id ~ '^[a-z0-9][a-z0-9._-]*$'),
    PRIMARY KEY (request_id, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS decision_request_scope_entity_lookup
    ON agency_decision_request_scope_refs (entity_type, entity_id, request_id);

CREATE OR REPLACE FUNCTION validate_decision_request_apu_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    request_project_id TEXT;
    object_project_id TEXT;
BEGIN
    SELECT project_id
      INTO request_project_id
      FROM agency_decision_requests
     WHERE request_id = NEW.request_id;

    IF request_project_id IS NULL THEN
        RAISE EXCEPTION 'APU-scoped Decision Request requires Project classification';
    END IF;

    IF to_regclass('agency_apu_objects') IS NULL THEN
        RAISE EXCEPTION 'Decision Request APU scope owner is not implemented';
    END IF;

    EXECUTE 'SELECT project_id FROM agency_apu_objects WHERE object_id = $1'
       INTO object_project_id USING NEW.entity_id;

    IF object_project_id IS NULL THEN
        RAISE EXCEPTION 'unknown apu_object Decision Request scope: %', NEW.entity_id;
    END IF;
    IF object_project_id <> request_project_id THEN
        RAISE EXCEPTION 'Decision Request APU scope belongs to another Project';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION reject_decision_request_scope_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Decision Request scope references are immutable and retained';
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'decision_request_apu_scope_guard'
          AND tgrelid = 'agency_decision_request_scope_refs'::regclass
    ) THEN
        CREATE TRIGGER decision_request_apu_scope_guard
        BEFORE INSERT ON agency_decision_request_scope_refs
        FOR EACH ROW EXECUTE FUNCTION validate_decision_request_apu_scope();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'decision_request_scope_no_mutation'
          AND tgrelid = 'agency_decision_request_scope_refs'::regclass
    ) THEN
        CREATE TRIGGER decision_request_scope_no_mutation
        BEFORE UPDATE OR DELETE ON agency_decision_request_scope_refs
        FOR EACH ROW EXECUTE FUNCTION reject_decision_request_scope_mutation();
    END IF;
END;
$$;
