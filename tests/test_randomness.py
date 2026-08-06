"""Fairness core: determinism, distribution, directed override, replayability."""
import json
import random
import sys

sys.path.insert(0, ".")

from app import config, randomness


def test_same_tx_same_spec():
    tx = "ab" * 32
    a = randomness.draw(tx)
    b = randomness.draw(tx)
    assert a == b
    assert a["category"] in config.CATEGORIES
    assert a["prompt"]
    assert 0 <= a["model_seed"] < 2**31


def test_spec_is_json_serializable():
    for tx in ["ab" * 32, "00" * 32, "ff" * 32]:
        spec = randomness.draw(tx)
        roundtrip = json.loads(json.dumps(spec))
        assert roundtrip == spec


def test_different_txs_differ():
    draws = {randomness.draw("%064x" % i)["category"] for i in range(64)}
    assert len(draws) >= 2  # statistically certain over 64 draws


def test_blind_prompts_are_varied():
    prompts = {randomness.draw("%064x" % i)["prompt"] for i in range(64)}
    assert len(prompts) > 30  # pools are large enough that repeats are rare


def test_case_insensitive_tx_hash():
    tx = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    assert randomness.draw(tx) == randomness.draw(tx.upper())


def test_directed_uses_description_verbatim():
    tx = "ab" * 32
    spec = randomness.draw(tx, description="a neon cactus knight")
    assert spec["tier"] == "directed"
    assert spec["prompt"] == "a neon cactus knight"
    # same tx, blind draw, differs:
    blind = randomness.draw(tx)
    assert blind["tier"] == "blind"
    assert blind["prompt"] != "a neon cactus knight"


def test_category_hint_respected():
    tx = "ab" * 32
    for cat in config.CATEGORIES:
        spec = randomness.draw(tx, category_hint=cat)
        assert spec["category"] == cat
        assert spec["tier"] == "directed"


def test_unknown_category_rejected():
    try:
        randomness.draw("ab" * 32, category_hint="meme")
        assert False, "should have raised"
    except ValueError:
        pass


def test_pools_are_stable_per_version():
    """Replaying with the same pools_version must reproduce old prompts."""
    tx = "cd" * 32
    a = randomness.draw(tx)
    b = randomness.draw(tx, pools_version=config.POOLS_VERSION)
    assert a["prompt"] == b["prompt"]


def test_rng_stream_reproducible_after_pickle_style_reseed():
    tx = "ef" * 32
    r1 = randomness.rng_from_tx(tx)
    s1 = [r1.getrandbits(31) for _ in range(5)]
    r2 = randomness.rng_from_tx(tx)
    s2 = [r2.getrandbits(31) for _ in range(5)]
    assert s1 == s2
