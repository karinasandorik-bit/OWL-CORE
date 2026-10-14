# OWL Bounty Radar — External sample audit 001

Date: 2026-10-14. Operator: OWL LAB. Status: **UNCOMMISSIONED DEMONSTRATION**, not a paid delivery, not a live chain attestation.

## Method / frozen decision priority
1. STOP when explicit quarantine, terminal paid/settled, or permission exclusion appears.
2. HOLD if already claimed or in progress, or eligibility cannot be established.
3. VERIFY LIVE only if no exclusions and funding is claimed. GitHub issue body never proves actual escrow.
4. Before any real claim, read canonical contract events, live claimability and eligibility, verifier readiness, required bonds and gas.

| GitHub source | Independent observation from public issue | Decision | Reason | Missing proof |
| --- | --- | --- | --- | --- |
| [#334](https://github.com/NSPG13/agent-bounties/issues/334) | Title **QUARANTINED — DO NOT CLAIM**; body also says funded/claimable; current work state `in_progress`, verifier `ready: false` | **STOP** | Explicit no-claim warning defeats older marketing text; verifier not ready | On-chain live state not inspected |
| [#773](https://github.com/NSPG13/agent-bounties/issues/773) | Body advertises 2 USDC reward and funding, but embedded lifecycle says `in_progress` | **HOLD** | Cannot presume a new exclusive claim is possible | On-chain claimant and state not inspected |
| [#1500](https://github.com/NSPG13/agent-bounties/issues/1500) | GitHub issue closed; discovery section says `settled` and `paid` | **STOP** | Terminal opportunity; text is not independent settlement proof | Confirmation of actual BountySettled event not inspected |

### Defect discovered
Conflicting sections of the same issue can disagree. A lexical detector that only looks for “funded and claimable” has unacceptable false positives; explicit QUARANTINED and terminal statuses must override it. Even a HOLD/VERIFY decision should be a lead for live inspection, never a declaration of claimability or payment.

### Baseline and quality status
All three examples were inspected from their public GitHub issue snapshots on the same day. We did not measure independent human triage time; no claim of time savings. We did not run a blind independent verifier, inspect on-chain state, or receive independent client acceptance. A prospective blind holdout and cross-over timing experiment must follow before quality or efficiency claims.

### Buyer acceptance template
Independent buyer explicitly agrees to a list of 10 issues, delivery date, 15 Base USDC price, and risk limitations. OWL submits 10 timestamped evidence sheets. Buyer accepts/rejects with defect list. Payment attribution requires exact amount + native Base USDC token + recipient + confirmed transaction hash + independent payer context, and must not be confused with unrelated transfers. No key, wallet approval or bond requested from buyer.

Base recipient: `0xb9600De59dDa5741672989eECB36E3E440df3aBF` (public address only). No payment has been verified.
