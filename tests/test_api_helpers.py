"""Offline tests for the API helper layer (no fastapi/gradio needed)."""
import sys

sys.path.insert(0, ".")

from app import api_helpers, config, payments


def test_machine_info_shape_and_safety():
    info = api_helpers.machine_info(demo=False)
    assert info["name"] == "DOGE Gumball Machine"
    assert info["open"] is False  # placeholder address in test env
    assert "DXXX" in info["address"]
    assert info["tiers"]["blind"]["doge"] == 1.0
    assert info["tiers"]["directed"]["doge"] == 5.0
    assert {c["key"] for c in info["categories"]} == set(config.CATEGORIES)
    for c in info["categories"]:
        assert c["emoji"] and c["name"] and c["wait"]
    assert info["min_confirmations"] == 1
    assert "No refunds" in info["policy"] and "donation" in info["policy"]
    assert "secret" not in json_dumps(info).lower()  # no secrets leaked


def json_dumps(obj) -> str:
    import json
    return json.dumps(obj)


def test_address_is_configured():
    assert api_helpers.address_is_configured("D8r3A6KQVKmDvWyUCXvXjYsyNbNNQPLvG7") is True
    assert api_helpers.address_is_configured("DXXX...") is False
    assert api_helpers.address_is_configured("") is False


def test_validate_dispense_body():
    tx = "ab" * 32
    h, d, c = api_helpers.validate_dispense_body({"tx_hash": tx})
    assert h == tx and d is None and c is None

    h, d, c = api_helpers.validate_dispense_body(
        {"tx_hash": tx, "description": "  a glowing potion  ", "category": "image"})
    assert d == "a glowing potion" and c == "image"

    # whitespace-only description -> treated as blind
    h, d, c = api_helpers.validate_dispense_body({"tx_hash": tx, "description": "   "})
    assert d is None and c is None


def test_validate_dispense_body_errors():
    tx = "ab" * 32
    for body, frag in [
        (None, "JSON object"),
        ({}, "tx_hash is required"),
        ({"tx_hash": "short"}, "64 hex"),
        ({"tx_hash": tx, "description": "x" * 301}, "too long"),
        ({"tx_hash": tx, "category": "meme"}, "unknown category"),
    ]:
        try:
            api_helpers.validate_dispense_body(body)
            assert False, f"should reject {body!r}"
        except api_helpers.RequestError as e:
            assert frag in e.message, e.message


def test_friendly_errors_have_help():
    cases = [
        (payments.BadTxFormat("bad"), "bad_tx_format"),
        (payments.TxNotFound("nope"), "tx_not_found"),
        (payments.TxUnconfirmed("wait"), "unconfirmed"),
        (payments.InsufficientAmount("need more"), "insufficient"),
        (payments.TxAlreadyUsed("used"), "already_used"),
        (RuntimeError("boom"), "generation"),
    ]
    for exc, code in cases:
        out = api_helpers.friendly_error(exc, "ab" * 32)
        assert out["code"] == code
        assert out["error"] and out["help"]


def test_friendly_insufficient_mentions_tiers():
    out = api_helpers.friendly_error(payments.InsufficientAmount("paid 100 sat, need 500M"))
    assert "1 DOGE" in out["help"] and "5 DOGE" in out["help"]
