-- Run as PostgreSQL schema owner, never as OWL worker or judge role.
CREATE TABLE IF NOT EXISTS owl_evaluation_events (
  event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  request_id text NOT NULL UNIQUE,
  request_hash char(64) NOT NULL,
  dataset_id text NOT NULL,
  candidate_id text NOT NULL,
  baseline_id text NOT NULL,
  verdict jsonb NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT verdict_cannot_promote CHECK (verdict->>'promotion_authorized' = 'false')
);
CREATE OR REPLACE FUNCTION owl_deny_evaluation_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'owl_evaluation_events is append-only';
END $$;
DROP TRIGGER IF EXISTS owl_no_evaluation_mutation ON owl_evaluation_events;
CREATE TRIGGER owl_no_evaluation_mutation
BEFORE UPDATE OR DELETE OR TRUNCATE ON owl_evaluation_events
FOR EACH STATEMENT EXECUTE FUNCTION owl_deny_evaluation_mutation();
-- Provision separate LOGIN roles out-of-band; change role name as appropriate.
-- REVOKE ALL ON owl_evaluation_events FROM PUBLIC;
-- GRANT SELECT, INSERT ON owl_evaluation_events TO owl_judge;
-- Do not give owl_judge ownership, ALTER, TRUNCATE, or bypass privileges.
-- PostgreSQL table owners/superusers can still rewrite the database:
-- operational immutability also requires backups/WAL/archive and external anchoring.
