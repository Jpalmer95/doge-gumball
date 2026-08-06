# Cost Ledger & Entry-Price Policy

## The sustainability question: "who pays when this goes viral?"

The machine's margin must stay positive at scale. The policy below makes the
entry price self-correcting instead of a guess.

## Current cost basis (v1)

| Category | Generator | Marginal cost/gen |
|---|---|---|
| image | FLUX.1-schnell via HF Space | $0 (machine's ZeroGPU quota) |
| asset_3d | TRELLIS.2 via HF Space | $0 (ZeroGPU quota) |
| song | ACE-Step via HF Space | $0 (ZeroGPU quota) |
| game_sfx | procedural (offline) | $0 |
| payment check | Blockcypher free tier | $0 (rate-limited; ledger caches) |

ZeroGPU quota is **free but finite**: heavy use can hit per-account daily
limits, which manifests as queue waits, not dollar costs. If quota becomes the
bottleneck, the machine can route a category to a paid API — that is when the
cost policy below kicks in.

## Paid-API fallback reference prices (checked 2026-08)

| Category | Paid option | ~Cost/gen |
|---|---|---|
| image | FLUX.1-schnell via Replicate | ~$0.003 |
| asset_3d | TRELLIS via Replicate | ~$0.05–0.30 |
| song | ACE-Step via self-hosted GPU | ~$0.01–0.05 compute |
| game_sfx | n/a (procedural) | $0 |

Compare with the entry tiers at 1 DOGE ≈ $0.07 (CoinGecko, 2026-08-05):
blind 1 DOGE ≈ $0.07, directed 5 DOGE ≈ $0.35. Even the most expensive
category (3D) fits comfortably under the blind entry when paid-API prices
hold; 3D under the directed tier is extremely safe.

## Entry-price policy (automated)

`scripts/assess_entry_price.py` reads every receipt's `cost_usd` and computes
per-category average cost vs. entry value at the live DOGE price. It flags
`RAISE ENTRY` when:

    avg_cost_per_gen > 0.75 × entry_usd

Rationale: the 0.75 threshold leaves margin for price volatility, gas/fees,
and the (rare) failed generation that must be retried for free.

**Recorded decisions**

* 2026-08-05 — Entry set at **1 DOGE blind / 5 DOGE directed** with all-free
  generators. No change needed: avg cost = $0.
* If a category is ever routed to a paid API: log `cost_usd` on its receipts,
  run the assessor weekly (cron), and follow its verdict. Suggested ladder
  if flagged: 2/10 DOGE → 5/20 DOGE → disable that category until costs fall.

## Ledger

`outputs/receipts.jsonl` is the cost ledger: each receipt carries
`cost_usd` (None = free), category, timestamp. The assessor only counts
receipts with a real cost; free generations are excluded from the ratio.
