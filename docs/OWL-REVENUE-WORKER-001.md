# OWL-REVENUE-WORKER-001 integration contract

Status: STAGED / DENY BY DEFAULT. No production authorization implied.

Runtime: Railway SWE-REPLAY-LAB / owl-worker, source karinasandorik-bit/OWL-CORE main, mounted /data.
Authority DB: Supabase OWL PostgreSQL, public.owl_capability_grants and public.owl_action_ledger.
Actuator: github_draft_artifact only, target repository karinasandorik-bit/OWL-CORE.

## Required before activation
1. Use a dedicated scoped database identity; never expose service-role or database admin credentials to a model or untrusted task.
2. Worker must check grant from PostgreSQL before each GitHub call and fail closed on network/database errors.
3. Enforce repository and branch prefix owl/revenue/ in code AND DB; reject protected branches and existing files.
4. Enforce max_actions=1 transactionally in PostgreSQL. Current SQL does NOT enforce this yet.
5. Bind request_hash to canonical action payload, reject hash collisions, and verify existing action status before retries.
6. Use independent GitHub readback (branch/file SHA) before marking outcome verified.
7. Record commit SHA, deployment ID, timestamps and immutable evidence; separate actor permissions from verifier.
8. Revocation must stop future GitHub calls; demonstrate rejection and crash/retry idempotency.
9. Test in isolated branch, open draft PR, obtain green CI, then explicitly approve rollout.
10. No money movement, signing, trading, external client messages or automatic merges.

Acceptance: one authorized new artifact, exactly one GitHub commit, independently verified ledger outcome, no duplicate on replay; disabled/revoked grants denied.

The database grant OWL-REVENUE-WORKER-001 was inserted disabled on 2026-10-09.
