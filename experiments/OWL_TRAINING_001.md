# OWL LAB · Training Experiment 001

Status: LOCALLY_VERIFIED (synthetic only). Branch: `owl-lab-training-001`.

## Purpose
Borrow task *structures* from public agent evaluations, without confusing evaluation data with model training. Three tracks:
- Architecture: permission and revocation invariants.
- Design: minimal accessibility/editability publication gates.
- Operations: receipts and duplicate-prevention gates.

## Run
```sh
python experiments/owl_training_001.py
```

## Results from local execution on 2026-10-10
| Policy | Passing / total | Architecture | Design | Operations |
|---|---:|---:|---:|---:|
| Baseline (always approve) | 4/9 | 2/3 | 1/3 | 1/3 |
| Guarded deterministic policy | 9/9 | 3/3 | 3/3 | 3/3 |

The nine cases were written together with the policy, so this is a **smoke test, NOT independent evaluation** and does not demonstrate learning, generalized ability, robust design taste, or external execution. The 4.5 contrast check is only a simplified numerical proxy, not a WCAG conformance audit.

## Next falsification gates
1. Freeze code and hold out tasks written by an independent evaluator.
2. Add failure injections: lost database lease, duplicated HTTP response, revoked grant during action.
3. For design, compare independent blinded human judgments for originality, hierarchy, and functional quality; run real contrast checks on rendered artifacts.
4. For architecture, prove properties with executable integration tests against a temporary PostgreSQL instance.
5. For operations, evaluate real idempotent external actions in a sandbox against provider-side receipts.
6. Report success rates, false approvals, false refusals, total costs and repeated-trial reliability.

## Inspirations
- SWE-bench Verified: https://www.swebench.com/verified
- OSWorld: https://os-world.github.io/
- Design2Code: https://github.com/jiahuigeng/Design2Code
- TheAgentCompany: https://github.com/TheAgentCompany/TheAgentCompany
- tau-bench: https://github.com/sierra-research/tau2-bench
- WebArena: https://webarena.dev/
