# OWL Witness v1 — collector → PostgreSQL → verifier → immutable ledger
Prototype only. No production deployment, external provider proof, or fault-injection proof is implied.
Install Node.js 22+, run `npm install pg`, then execute `psql "$DATABASE_URL" -f witness/sql/001_init.sql`.
Start collector: `DATABASE_URL=... WITNESS_INGEST_SECRET=... node witness/collector.mjs`.
Run independent verifier process: `DATABASE_URL=... node witness/verifier.mjs`.
Ingestion: POST /events, JSON `{"event_id":"<uuid>","source":"source-id","payload":{...}}`.
Header `x-witness-signature` is lowercase hex HMAC-SHA256 over the exact UTF-8 request body using WITNESS_INGEST_SECRET.
All inserts are transactional. Replays of identical event_id+source+payload are idempotent; mismatched repeats return 409.
An advisory transaction lock serializes writers; event + ledger entry commit atomically.
DB triggers forbid UPDATE/DELETE on evidence and audit rows. Enforce database least-privilege: application role without DDL, ownership, TRUNCATE, or trigger privileges; only privileged migration role creates schema.
Threat model: privileged DB owners/superusers can rewrite data or disable triggers; cryptographic chaining by itself does not provide external immutability. Anchor signed ledger heads to an independent store and independently reconcile provider delivery receipts before asserting end-to-end proof.
Missing acceptance gates: fresh isolated Postgres integration tests, concurrent collectors, SIGKILL between external HTTP side effect and receipt, lease expiry/recovery, provider-ledger reconciliation, externally authored hidden tests, real Vercel deployment.
