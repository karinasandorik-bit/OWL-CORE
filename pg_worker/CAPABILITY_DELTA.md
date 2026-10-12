# OWL Capability Delta — 2026-10-12

Baseline: SQLite-only bounded worker; no PostgreSQL fencing proof.

External evidence: GitHub Actions run 38220945008, job 114716786704,
PostgreSQL 17.11 container, six pytest cases PASSED in 1.67 seconds.
Independent baseline worker checks: run 38220944907 SUCCESS.
Commit under test: 027f64da0f14394573d96217b9bb5638aebf71eb.

Observed capabilities:
- PostgreSQL row-lock claim + monotonic fencing, stale completion rejected.
- Separate database connections compete for one task.
- SIGKILL of worker process, expiry, takeover by another worker.
- Simulated provider durable SQLite commit followed by SIGKILL,
  independent receipt readback and single-effect assertion.
- Fail-closed UNKNOWN / NOT_FOUND reconciliation semantics.

Important limitations:
- Provider oracle is SQLite, not an HTTP server; no real HTTP commit boundary.
- No database role least-privilege tests or production connectivity.
- No multi-host/network partition or PostgreSQL crash injection.
- No durable transactional outbox dispatcher; effect_outbox remains blocked.
- No real-world exactly-once guarantee. Provider-side atomic idempotency and
  independently verified receipts remain mandatory.
- Test suite uses a disposable CI database and privileged setup user.
- This evidence does not authorize production merge, deployment, credentials,
  HTTP effects, payments, or signing.

Next falsification targets:
1. External HTTP test provider with durable independent ledger and deliberate
   crash immediately after 200/commit but before local receipt.
2. 2+ worker processes across hosts, forced lease expiry, delayed stale worker.
3. PostgreSQL failover/restart and connection loss at commit boundary.
4. Least-privilege roles (worker cannot DDL, DELETE, bypass RLS, or grant itself
   actuator authority), schema migration rollback and negative tests.
5. Independently checked CI artifacts with commit SHA and oracle hashes.

Verdict: LOCALLY_AND_CI_VERIFIED_FOR_SYNTHETIC_SCOPE / KEEP_TESTING.
