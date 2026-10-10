# OWL MINIMAL-KERNEL-001 — limited prototype

Four offline tests demonstrate local SQLite crash recovery, deduplication, and hash mismatch detection. The external event is a **fixture** based on a real GitHub issue, not a live webhook. The action is a **local placeholder**, not an externally executed operation. The verifier uses hashes in the **same mutable database** and therefore is not independent, tamper-proof, or secure against a privileged database writer.

Run: `cd experiments/minimal_kernel && python -m unittest -v`.

## Not proven / release blockers
- Authenticated GitHub webhook ingestion with signature validation and replay protection.
- Real bounded actuator and independently observed world outcome.
- Durable append-only event log with separate trust domain, signatures or external witness.
- Transactional outbox, leases, concurrent workers, idempotency across remote side effects.
- Recovery after process kill at every state transition and post-side-effect pre-ack failure.
- Taint propagation across dependencies, external evidence retraction, rollback and reconciliation.
- Production CI, deployed watchdog, monitoring, real payment validation.

Do **not** freeze production architecture based on these tests.
