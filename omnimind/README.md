# OWL OMNIMIND — Network Workspace
Status: EXPERIMENTAL / NOT DEPLOYED

This is a new non-destructive workspace branch for model collaboration work.

## Goals
- Coordinate independent Claude, Gemini, and OpenRouter responses via official APIs, only with configured credentials.
- Preserve immutable-ish local provenance and explicitly mark test fixtures.
- Add provider budgets, external evaluation, and permission-gated tools before production deployment.
- Do not claim another LLM was contacted without actual response metadata.

## Interfaces
ProviderAdapter: (task, role) -> {provider, model, response, usage, evidence}
ExecutionLedger: task_created -> provider_response/error -> evaluation -> final
Safety: no outbound writes or purchases without scoped authorization.
Browser actions and app connectors remain user-authorized and logged.

## Stage gates
1. LOCAL: fixtures, unit tests, schema contract
2. LIVE: one authorized provider response with usage metadata
3. COUNCIL: two independent providers + contradiction detection
4. RELIABLE: independent adversarial tests, cost and recovery gates
5. DEPLOYED: authenticated HTTPS entrypoint and multi-worker durability

This branch is not equivalent to persistent connectivity with this ChatGPT session.
