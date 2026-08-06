#!/usr/bin/env python3
"""Assess whether the entry price still covers average generation cost.

Policy (see docs/cost-ledger.md): if average cost per gumball exceeds 75% of
the entry value (at current DOGE price), raise the entry tier. Free Space
generation costs 0 USD but burns ZeroGPU quota — quota exhaustion is the soft
constraint; if the operator switches any generator to a paid API, log the
per-gen cost in the receipt's `cost_usd` field and this script will surface it.

Usage:
    python3 scripts/assess_entry_price.py [--receipts outputs/receipts.jsonl]
"""
import argparse
import json
import urllib.request

from app import config


def doge_price_usd() -> float:
    with urllib.request.urlopen(
        "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd",
        timeout=15,
    ) as r:
        return json.loads(r.read())["dogecoin"]["usd"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipts", default=config.RECEIPTS_FILE)
    args = ap.parse_args()

    receipts = []
    try:
        with open(args.receipts) as fh:
            receipts = [json.loads(l) for l in fh if l.strip()]
    except FileNotFoundError:
        print(f"no receipts yet at {args.receipts} — nothing to assess")
        return 0

    price = doge_price_usd()
    print(f"DOGE price: ${price:.4f}")
    print(f"blind entry :  {config.TIER_BLIND_DOGE} DOGE = ${config.TIER_BLIND_DOGE * price:.3f}")
    print(f"directed    :  {config.TIER_DIRECTED_DOGE} DOGE = ${config.TIER_DIRECTED_DOGE * price:.3f}")

    by_cat: dict[str, list[float]] = {}
    for r in receipts:
        if r.get("cost_usd") is None:
            continue
        by_cat.setdefault(r["spec"]["category"], []).append(r["cost_usd"])

    print("\nper-category average cost:")
    recommend_raise = False
    for cat, costs in sorted(by_cat.items()):
        avg = sum(costs) / len(costs)
        entry_usd = config.TIER_BLIND_DOGE * price
        ratio = avg / entry_usd if entry_usd else float("inf")
        flag = "  <-- RAISE ENTRY" if ratio > 0.75 else ""
        if flag:
            recommend_raise = True
        print(f"  {cat:10s} avg ${avg:.4f}/gen over {len(costs):4d} gens  (ratio {ratio:.2f}){flag}")

    if not by_cat:
        print("  (no cost_usd logged yet — free Space generations cost 0)")

    print("\nverdict:", "RAISE ENTRY PRICE" if recommend_raise
          else "entry price OK — generation cost is covered")
    return 1 if recommend_raise else 0


if __name__ == "__main__":
    raise SystemExit(main())
