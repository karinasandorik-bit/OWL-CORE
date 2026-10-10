# OWL SOVEREIGN — executable architecture contract (v0.1)

## Mission
Produce independently verifiable useful outcomes and legitimate earned revenue while minimizing spend, risk, and user intervention. An agent count is not a capability metric.

## Loop
1. SCOUT: discover opportunities and constraints with timestamps and source URLs.
2. CRITIC: reject stale, unverified, unsafe, duplicate, or uneconomic candidates.
3. PLANNER: choose one bounded action by expected verified utility / cost.
4. WORKER: execute with idempotency key, scoped authority, and durable outbox.
5. VERIFIER: independently inspect external outcome; do not trust worker self-report.
6. LEDGER: append evidence, action, outcome, failure, and next cheapest test.
7. EVOLVE: compare with baseline, perform ablation; promote only measured gains.

## Invariants
- Evidence statuses: HYPOTHESIS, DERIVED, EXECUTED, VERIFIED, BLOCKED, TAINTED.
- VERIFIED requires independent external observation, not an agent assertion.
- Revenue requires third-party acceptance AND settlement evidence; a bounty listing is not revenue.
- Every side effect has operation_id, payload digest, authorization scope, and recovery policy.
- External mutations must be idempotent or require explicit human approval if not safely replayable.
- A source retraction taints dependent decisions and outcomes until reverified.
- No live trading, transfers, arbitrary signing, paid spend, deployment, merge, or contractual commitments without scoped approval.
- No credentials in repository, logs, or model-visible reports.
- Fewer components are preferred when equivalent on held-out outcomes.

## Priority order
P0: validate real GitHub Actions SIGKILL -> durable pending -> 2 workers -> 1 external effect -> independently verified result.
P0: verify Augora PR #141 review, acceptance, and actual settlement, if any.
P1: validate OWL revenue scout and deliver one buyer-approved paid task.
P1: run KISA prospective market-data -> decision -> immutable shadow outcome; no live orders.
P2: test frontier capabilities against simple baselines.

## Evidence record schema
```json
{
  "operation_id": "string",
  "created_at": "RFC3339",
  "source_urls": ["https://..."],
  "authority_scope": "read|branch_write|explicit_approval",
  "claim": "string",
  "status": "HYPOTHESIS|DERIVED|EXECUTED|VERIFIED|BLOCKED|TAINTED",
  "action_digest": "sha256:...",
  "external_observation": null,
  "dependencies": [],
  "next_cheapest_test": "string"
}
```

## Promotion gates
A capability is PROMOTED only after: (1) deterministic local tests, (2) external end-to-end proof where applicable, (3) negative/adversarial test, (4) baseline comparison, (5) rollback procedure. Otherwise remain EXPERIMENTAL.

## Current epistemic state
This document is a policy contract, not proof of a running autonomous server, successful CI, deployed service, or earned payment.
