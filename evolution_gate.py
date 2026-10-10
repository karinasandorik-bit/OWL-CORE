"""OWL Evolution Gate v1: deterministic offline candidate screening.

No candidate code execution, deployment, private keys, trading, or arbitrary shell.
Screening is NOT promotion. Independent held-out proof remains mandatory.
"""
import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = {"candidate_id", "baseline_id", "cases", "candidate_predictions", "baseline_predictions"}
MAX_CASES = 10000


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def evaluate(payload):
    if not isinstance(payload, dict) or not REQUIRED.issubset(payload):
        raise ValueError("missing required fields")
    cases = payload["cases"]
    if not isinstance(cases, list) or not 2 <= len(cases) <= MAX_CASES:
        raise ValueError("cases must contain 2..10000 items")
    ids = [c.get("id") for c in cases if isinstance(c, dict)]
    if len(ids) != len(cases) or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("case IDs must be unique nonempty strings")
    if any(type(c.get("expected")) is not bool for c in cases):
        raise ValueError("expected must be boolean")
    expected = {c["id"]: c["expected"] for c in cases}
    scores = {}
    for label, field in (("candidate", "candidate_predictions"), ("baseline", "baseline_predictions")):
        preds = payload[field]
        if not isinstance(preds, dict) or set(preds) != set(expected):
            raise ValueError("prediction IDs must exactly match cases")
        if any(type(v) is not bool for v in preds.values()):
            raise ValueError("predictions must be boolean")
        scores[label] = sum(preds[k] == expected[k] for k in expected) / len(expected)
    delta = scores["candidate"] - scores["baseline"]
    return {
        "schema": "owl.evolution.screen.v1",
        "candidate_id": str(payload["candidate_id"]),
        "baseline_id": str(payload["baseline_id"]),
        "dataset_sha256": digest(cases),
        "candidate_predictions_sha256": digest(payload["candidate_predictions"]),
        "baseline_predictions_sha256": digest(payload["baseline_predictions"]),
        "n_cases": len(cases),
        "candidate_accuracy": scores["candidate"],
        "baseline_accuracy": scores["baseline"],
        "delta_accuracy": round(delta, 12),
        "screen_pass": delta > 0,
        "promotion_authorized": False,
        "status": "AWAITING_INDEPENDENT_HELDOUT_PROOF" if delta > 0 else "REJECTED_BY_SCREEN",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSON fixture including baseline and candidate predictions")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
