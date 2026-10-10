# OWL Core P0 Reference

Local stdlib-only runtime with versioned skill registry, deny-by-default time-bound grants, action ledger, event journal, idempotent submits, independent verifier callback and persisted terminal-state recovery. This reference adapter has no external write permissions.

Run the companion downloaded ZIP to execute 55 tests (30 control, 20 deterministic separately seeded synthetic holdouts, 5 negative/recovery). These are smoke tests, **not** independent or secret real-world holdouts.

Known gaps: no hosted worker, production PostgreSQL implementation, leased queue, external idempotency receipts, immutable audit proofs, audiovisual adapters or live PWA. Do not use for financial transactions or high-impact operations.
