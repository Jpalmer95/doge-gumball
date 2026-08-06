#!/usr/bin/env python3
"""End-to-end demo of the machine (no real payment needed).

* --tx: any 64-hex string (defaults to a random one) — in production this is
  the user's real DOGE tx hash.
* --category: force a category (directed demo). Default: blind random draw.
* --desc: directed description (implies 5-DOGE tier semantics in prod).
* --verify: actually hit Blockcypher for the tx (use a REAL tx hash).
  Without it, payment verification is skipped (demo mode) and the receipt is
  tagged tier "blind"/"directed" but no payment facts are recorded.
* --category-live: allow network generators (FLUX/TRELLIS/ACE-Step). Default
  runs the offline procedural SFX generator so the demo works anywhere.

Usage:
    python3 scripts/demo_flow.py
    python3 scripts/demo_flow.py --category image --category-live
    python3 scripts/demo_flow.py --category asset_3d --category-live
    python3 scripts/demo_flow.py --desc "a glowing potion bottle" --category-live
"""
import argparse
import random
import sys

sys.path.insert(0, ".")

from app import config, ledger, machine, randomness  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tx", default=None, help="64-hex tx hash (demo default: random)")
    ap.add_argument("--category", default=None, choices=config.CATEGORIES)
    ap.add_argument("--desc", default=None)
    ap.add_argument("--verify", action="store_true", help="verify against Blockcypher (needs real tx)")
    ap.add_argument("--category-live", action="store_true", help="allow live HF Space generators")
    args = ap.parse_args()

    tx = args.tx or ("%064x" % random.getrandbits(256))
    print(f"tx hash      : {tx}")

    if args.category or args.desc:
        spec = randomness.draw(tx, description=args.desc, category_hint=args.category)
        print(f"draw (directed): {spec['category']} — {spec['prompt']}")
    else:
        spec = randomness.draw(tx)
        print(f"draw (blind)  : {spec['category']} — {spec['prompt']}")
        print("  (category + description randomized by tx hash, as the contract promises)")

    if spec["category"] in ("image", "asset_3d", "song") and not args.category_live:
        print("\nNOTE: category is a network generator; rerun with --category-live to")
        print("actually generate. Falling back to the offline procedural SFX path")
        print("(the machine re-draws with category_hint so the receipt stays replayable).")
        hint = "game_sfx"
    else:
        hint = args.category

    receipt = machine.dispense(tx, description=args.desc,
                               category_hint=hint,
                               verify_payment=args.verify)
    print(f"\nreceipt       : {receipt['id']}  ({receipt['status']})")
    print(f"generator     : {receipt['generator']}")
    print(f"asset         : {receipt['asset']['path']} "
          f"({receipt['asset']['size_bytes']} bytes, {receipt['asset']['license']})")
    print(f"payment       : {receipt.get('payment')}")
    print(f"\nverify replay : python3 scripts/verify_fairness.py --tx {tx}")
    print(f"verify file   : python3 scripts/verify_fairness.py {config.RECEIPTS_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
