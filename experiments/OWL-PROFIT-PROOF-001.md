# OWL-PROFIT-PROOF-001 — preregistered evaluation contract
Created 2026-10-09. Status: PROTOCOL_ONLY. No trade, realized outcome, or verified edge claimed.

## Scope
Shadow only, BTCUSDT and ETHUSDT linear USDT-margined perpetuals; one position max across symbols. Evaluation requires archived timestamped venue quotes (at least two independent venues), 1h candles, 1h-volume and funding from a named venue. Fail closed on missing inputs, stale quotes (>30 seconds at decision), divergent venue mid prices (>20 bps), or inconsistent candle timestamps. An unavailable third party must never be simulated as an independent judge.

## Candidate A (precommitted rule; no tuning on evaluation period)
Evaluate on each completed UTC 1h bar. Use previous 50 completed hourly closes to compute SMA(20) and SMA(50). LONG if previous bar SMA20 <= SMA50 and latest closed bar SMA20 > SMA50, and latest close > previous 20-hour rolling high (excluding latest bar). SHORT reverse: SMA20 >= SMA50 becoming < SMA50 and close < prior 20-hour low. At most one signal per 4 hours; never enter on the signal bar. Entry is next observed executable quote after the bar close, not bar close. No partial bar or backfilled late signal. If unavailable in real time => NO_TRADE. Fixed stop at 1.5 * ATR(14) based on completed hourly bars, fixed target at 3 * ATR(14); expiry after 4h; touch of both stop and target in same unsampled interval => stop-first conservative settlement, unless independently timestamped tick/order-book observations resolve order. Simulate isolated 1x notional and risk 0.25% of test equity per stop; no leverage assumptions, execution or real capital.

## Baseline B
NO_TRADE, equivalent equity held in USDT; zero position PnL. Supplement with equal-frequency frozen direction-neutral comparator (coin-flip seeded and recorded before evaluation) solely for inference; do not cherry-pick the best comparator ex post.

## Costs
Use archived exchange fee tier at signal time; in absence of proof assume 6 bps taker per side (12 bps round trip), plus 2 bps adverse slippage per side (4 bps round trip); funding applied using observed per-symbol per-venue timestamped actual funding events through exit, or fail settlement as INCOMPLETE if exact funding cannot be reconstructed. Bid/ask spread must be included if executable bid/ask quotes are available; avoid counting spread twice if bid/ask fill already models it. Net PnL = signed price movement * position size - commissions - spread/slippage (as applicable) - funding cashflow. Show dollar and % test-equity results separately.

## Mandatory sequence
1. External observer records raw evidence timestamp/venue and content hash BEFORE decision.
2. Freeze decision ID, algorithm commit SHA, signal side, timestamp, entry mechanism, stop, target, expiry, model confidence and evidence hash. Append to persistent immutable ledger.
3. Wait for future 4h market outcome; independent evaluator reads frozen decision and future venue observations, settles without allowing agent to alter outcome, logs independently derived fees/funding/PnL and settlement hash.
4. Compare A to B by paired evaluation on every eligible hourly decision and record missed opportunities on NO_TRADE.
5. Never upgrade candidate because of a single winning trade. Precommit >=100 prospective decisions and >=30 actual signals spanning >=20 trading days; report all losses, maximum drawdown, trade expectancy, confidence intervals using day-block bootstrap and a permutation/paired comparison against comparator. Require lower 95% CI of net edge >0 in a separate untouched walk-forward period to consider promotion; no live execution without independent permissions and a scoped risk grant.
6. An initial profitable trade may earn FIRST_PROFIT_VERIFIED only if points 1–3 succeeded. No historical backtest may be labeled prospective or FIRST_PROFIT_VERIFIED.

## Current attestation
2026-10-09 read-only Supabase check: owl.outcomes=0, owl.economic_events=0, owl_ablation_004.outcomes=1 (owl-ablation-004-canary, payload=verified); this is NOT a trade.
KISA Railway project not visible from connected Railway account; KISA PostgreSQL venue ledger not independently located.
Protocol commit is not execution; first eligible signal, PostgreSQL row, independent settlement and realized net shadow PnL remain UNVERIFIED.
