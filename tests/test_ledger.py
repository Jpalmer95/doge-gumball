"""Ledger round-trips, receipt shape, reuse guard."""
import json
import sys
import tempfile

sys.path.insert(0, ".")

from app import config, ledger


def test_receipt_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "RECEIPTS_FILE", str(tmp_path / "receipts.jsonl"))
    monkeypatch.setattr(config, "USED_TXS_FILE", str(tmp_path / "used_txs.jsonl"))

    spec = {"tx_hash": "ab" * 32, "category": "game_sfx", "prompt": "coin pickup",
            "model_seed": 42, "rng_version": "gumball-v1", "pools_version": "pools-v1",
            "tier": "blind"}
    payment = {"tx_hash": "ab" * 32, "amount_satoshis": 100_000_000, "amount_doge": 1.0}
    asset = {"path": "outputs/assets/sfx_42.wav", "mime": "audio/wav",
             "size_bytes": 1000, "license": "CC0-1.0", "model": "procedural"}

    receipt = ledger.write_receipt(spec, payment, asset)
    assert receipt["id"] == ledger.receipt_id("ab" * 32)
    assert receipt["status"] == "generated"

    loaded = ledger.load_receipts()
    assert len(loaded) == 1
    assert loaded[0]["spec"] == spec
    assert loaded[0]["asset"] == asset

    ledger.mark_tx_used("AB" * 32)  # uppercase should normalize
    assert "ab" * 32 in ledger.load_used_txs()
    assert "ab" * 32 in ledger.load_used_txs()
