"""Fairness verification — replay a receipt's spec from its recorded inputs.

Shared by the CLI (`scripts/verify_fairness.py`) and the live machine's
`GET /gumball/verify/<id>` endpoint, so both audit with the same code.

The whole spec (category, prompt, model_seed, description, category_hint,
versions) must reproduce byte-for-byte from the recorded inputs
(tx hash + user description + category hint + versions).
"""
from . import randomness


def verify_receipt(receipt: dict) -> tuple[bool, list[str]]:
    """Replay one receipt. Returns (ok, problems)."""
    spec = receipt["spec"]
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

    problems = []
    for field in ("category", "prompt", "model_seed", "rng_version",
                  "pools_version", "description", "category_hint"):
        if replay[field] != spec.get(field):
            problems.append(f"{field}: receipt={spec.get(field)!r} replay={replay[field]!r}")
    if receipt["spec"]["tier"] != replay["tier"]:
        problems.append(f"tier: receipt={receipt['spec']['tier']!r} replay={replay['tier']!r}")
    return not problems, problems
