#!/usr/bin/env python3
"""Replay a receipt and verify the machine's fairness.

Every gumball's category, prompt, and model seed must be a pure function of
its tx hash (and the description/category the user paid for). This script
recomputes the spec from a receipt and fails loudly if anything differs.

Usage:
    python3 scripts/verify_fairness.py outputs/receipts.jsonl            # all
    python3 scripts/verify_fairness.py <receipt.json>                    # one file
    python3 scripts/verify_fairness.py --tx <txhash> --desc "..."        # fresh replay
"""
import json
import sys

sys.path.insert(0, ".")

from app import randomness  # noqa: E402


def verify_receipt(receipt: dict) -> tuple[bool, list[str]]:
    spec = receipt["spec"]
    problems = []
    try:
        replay = randomness.draw(
            spec["tx_hash"],
            description=spec.get("description"),
            category_hint=spec.get("category_hint"),
            rng_version=spec["rng_version"],
            pools_version=spec["pools_version"],
        )
    except Exception as e:
        return False, [f"replay crashed: {e}"]

    # The full spec must be byte-for-byte reproducible from the recorded
    # inputs (tx hash + user description + category hint + versions).
    problems = []
    for field in ("category", "prompt", "model_seed", "rng_version",
                  "pools_version", "description", "category_hint"):
        if replay[field] != spec.get(field):
            problems.append(f"{field}: receipt={spec.get(field)!r} replay={replay[field]!r}")
    if receipt["spec"]["tier"] != replay["tier"]:
        problems.append(f"tier: receipt={receipt['spec']['tier']!r} replay={replay['tier']!r}")
    return not problems, problems


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2

    if args[0] == "--tx":
        tx = args[1]
        desc = None
        if "--desc" in args:
            desc = args[args.index("--desc") + 1]
        spec = randomness.draw(tx, description=desc)
        print("fresh spec for", tx)
        print(json.dumps(spec, indent=2))
        return 0

    ok_total = 0
    bad = []
    for path in args:
        if path.endswith(".json"):
            receipts = [json.load(open(path))]
        else:
            receipts = [json.loads(l) for l in open(path) if l.strip()]
        for receipt in receipts:
            ok, problems = verify_receipt(receipt)
            if ok:
                ok_total += 1
            else:
                bad.append((receipt.get("id"), problems))

    print(f"verified {ok_total} receipts")
    for rid, problems in bad:
        print(f"FAIL {rid}:")
        for p in problems:
            print("   -", p)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
