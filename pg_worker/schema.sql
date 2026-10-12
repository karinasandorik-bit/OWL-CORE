CREATE SCHEMA IF NOT EXISTS owl_worker;
CREATE TABLE IF NOT EXISTS owl_worker.jobs (
 id text PRIMARY KEY, kind text NOT NULL CHECK (kind IN ('healthcheck','evaluate_candidate')),
 payload jsonb NOT NULL, status text NOT NULL DEFAULT 'queued'
 CHECK (status IN ('queued','leased','done')),
 lease_owner text, lease_until timestamptz,
 fencing_token bigint NOT NULL DEFAULT 0 CHECK (fencing_token >= 0),
 result jsonb, updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS owl_worker.effect_outbox (
 effect_id text PRIMARY KEY, job_id text NOT NULL REFERENCES owl_worker.jobs(id),
 idempotency_key text NOT NULL UNIQUE, request jsonb NOT NULL,
 state text NOT NULL DEFAULT 'blocked' CHECK (state IN ('blocked','ready','inflight','confirmed','unknown')),
 provider_receipt jsonb, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
-- No actuator grant or HTTP sender is installed by this migration.
