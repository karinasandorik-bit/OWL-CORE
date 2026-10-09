# OWL-CORE
Owned evidence contracts and bounded authority policy. No private keys or payment execution code.

## Security invariants
- Deny arbitrary message signing, transaction signing and broadcast.
- Capability grants must be scoped, time-bounded, revocable and audited.
- Evidence, decisions, actions, outcomes and lineage are distinct typed records.
- Never claim revenue or successful settlement without independent confirmation.
- Do not deploy signing functions from this repository without security review.
