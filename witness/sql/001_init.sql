BEGIN;
CREATE TABLE IF NOT EXISTS witness_events (
 event_id uuid PRIMARY KEY,
 source text NOT NULL,
 received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 body jsonb NOT NULL,
 body_sha256 text NOT NULL CHECK (body_sha256 ~ '^[0-9a-f]{64}$')
);
CREATE TABLE IF NOT EXISTS witness_ledger (
 seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 kind text NOT NULL CHECK (kind IN ('COLLECTED','VERIFIED','REJECTED')),
 event_id uuid NOT NULL REFERENCES witness_events(event_id),
 payload jsonb NOT NULL,
 previous_hash text NOT NULL,
 entry_hash text NOT NULL UNIQUE,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX IF NOT EXISTS witness_one_collection ON witness_ledger(event_id) WHERE kind='COLLECTED';
CREATE UNIQUE INDEX IF NOT EXISTS witness_one_verdict ON witness_ledger(event_id) WHERE kind IN ('VERIFIED','REJECTED');
CREATE OR REPLACE FUNCTION witness_reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'witness audit records are append-only'; END $$;
DROP TRIGGER IF EXISTS witness_events_immutable ON witness_events;
CREATE TRIGGER witness_events_immutable BEFORE UPDATE OR DELETE ON witness_events FOR EACH ROW EXECUTE FUNCTION witness_reject_mutation();
DROP TRIGGER IF EXISTS witness_ledger_immutable ON witness_ledger;
CREATE TRIGGER witness_ledger_immutable BEFORE UPDATE OR DELETE ON witness_ledger FOR EACH ROW EXECUTE FUNCTION witness_reject_mutation();
COMMIT;
