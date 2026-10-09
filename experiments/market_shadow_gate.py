#!/usr/bin/env python3
"""OWL shadow-only market gate. Python 3.10+, stdlib only.

Input JSON:
 {"observed_at":"2026-10-09T19:00:00Z","symbol":"BTCUSDT",
  "prices":[{"venue":"OKX","price":60000,"observed_at":"2026-10-09T19:00:00Z"},
            {"venue":"Bitget","price":60004,"observed_at":"2026-10-09T19:00:00Z"}],
  "candidates":[{"source":"x","url":"https://x.com/...","claim":"LONG BTC","direction":"LONG"}]}
Never authorizes exchange orders. Social media is provenance only, NOT price confirmation.
"""
import argparse
import datetime as dt
import hashlib
import json
import sys

def timestamp(s):
    value = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("naive timestamps forbidden")
    return value.astimezone(dt.timezone.utc)

def evaluate(record, max_age_seconds=30, max_divergence_bps=20):
    now = timestamp(record["observed_at"])
    clean = []
    for p in record.get("prices", []):
        try:
            age = (now - timestamp(p["observed_at"])).total_seconds()
            price = float(p["price"])
            if 0 <= age <= max_age_seconds and 0 < price < float("inf"):
                clean.append((str(p["venue"]), price))
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
    venues = {name for name, _ in clean}
    status = "NO_TRADE"
    reason = "INSUFFICIENT_INDEPENDENT_VENUES"
    median = None
    divergence_bps = None
    if len(venues) >= 2:
        # More than one quote per venue must not count as another independent venue.
        if len(venues) != len(clean):
            reason = "DUPLICATE_VENUE"
        else:
            values = sorted(p for _, p in clean)
            median = (values[(len(values)-1)//2] + values[len(values)//2]) / 2
            divergence_bps = (max(values) - min(values)) / median * 10000
            reason = "CONSENSUS_SHADOW_ONLY" if divergence_bps <= max_divergence_bps else "VENUE_DISAGREEMENT"
            if divergence_bps <= max_divergence_bps:
                status = "SHADOW_OBSERVATION"
    sources = [{"source": str(c.get("source", "")), "url": str(c.get("url", "")),
                "direction": str(c.get("direction", "UNKNOWN"))}
               for c in record.get("candidates", [])]
    payload = {"schema":"OWL_SHADOW_GATE_V1", "symbol":record["symbol"],
               "observed_at":record["observed_at"], "status":status, "reason":reason,
               "mid_price":median, "divergence_bps":divergence_bps,
               "independent_venues":len(venues), "candidate_provenance":sources,
               "exchange_execution_authorized":False}
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload["evidence_sha256"] = hashlib.sha256(serialized.encode()).hexdigest()
    return payload

def selftest():
    r = {"observed_at":"2026-10-09T19:00:00Z", "symbol":"BTCUSDT",
         "prices":[{"venue":"OKX","price":60000,"observed_at":"2026-10-09T19:00:00Z"},
                   {"venue":"Bitget","price":60004,"observed_at":"2026-10-09T19:00:00Z"}],
         "candidates":[{"source":"x", "url":"https://x.com/sample", "direction":"LONG"}]}
    ok = evaluate(r)
    assert ok["status"] == "SHADOW_OBSERVATION"
    assert not ok["exchange_execution_authorized"]
    assert evaluate({**r, "prices":r["prices"][:1]})["status"] == "NO_TRADE"
    assert evaluate({**r, "prices":[r["prices"][0], {**r["prices"][1], "price":62000}]})["reason"] == "VENUE_DISAGREEMENT"
    assert evaluate({**r, "prices":[r["prices"][0], {**r["prices"][0], "price":60001}]})["reason"] == "INSUFFICIENT_INDEPENDENT_VENUES"
    stale = {**r["prices"][1], "observed_at":"2026-10-09T18:00:00Z"}
    assert evaluate({**r, "prices":[r["prices"][0], stale]})["status"] == "NO_TRADE"
    assert evaluate(r)["evidence_sha256"] == ok["evidence_sha256"]
    return "6 shadow-only checks PASS"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--input", help="JSON evidence file; defaults to stdin")
    args = parser.parse_args()
    if args.self_test:
        print(selftest())
        return
    try:
        with open(args.input, encoding="utf8") if args.input else sys.stdin as f:
            record = json.load(f)
        print(json.dumps(evaluate(record), indent=2, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as ex:
        print(f"REJECTED: {ex}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
