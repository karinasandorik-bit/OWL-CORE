# OWL P0 PostgreSQL recovery adapter
Reference PostgreSQL worker design, fail-closed reconciliation and fault-injection tests.

The worker requires a **strongly consistent external idempotency-key lookup** and an endpoint that atomically deduplicates requests by the same key. PostgreSQL leases prevent simultaneous claims but do not by themselves guarantee exactly-once external effects.

Run the Python fault-injection tests in the downloadable archive. The live Supabase migration and hosted worker have NOT been deployed or verified. Current result: 5 simulated recovery tests passed.

The proposed schema lives in pg_recovery/schema_patch.sql. Follow security reviews before applying.
