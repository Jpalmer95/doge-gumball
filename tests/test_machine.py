"""End-to-end machine flow (offline): verified payment -> draw -> SFX -> receipt
-> fairness replay. Also covers the offline SFX generator itself."""
import os
import sys
import tempfile

sys.path.insert(0, ".")

from app import config, ledger, machine, payments
from app.generators.game_sfx import SfxGenerator
from scripts.verify_fairness import verify_receipt

TX = "cd" * 32


def fake_tx(h, amount=500_000_000):
    return {
        "hash": TX, "confirmations": 3, "fees": 1000,
        "outputs": [{"addresses": [config.DOGE_ADDRESS], "value": amount}],
    }


def offline_registry(monkeypatch):
    """Route every category to the offline SFX generator so tests never hit
    the network or retry backoff."""
    from app.generators.game_sfx import SfxGenerator
    monkeypatch.setattr(machine, "REGISTRY", {c: SfxGenerator() for c in config.CATEGORIES})


def test_full_dispense_offline(tmp_path, monkeypatch):
    offline_registry(monkeypatch)
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "ASSET_DIR", str(tmp_path / "assets"))
    monkeypatch.setattr(config, "RECEIPTS_FILE", str(tmp_path / "receipts.jsonl"))
    monkeypatch.setattr(config, "USED_TXS_FILE", str(tmp_path / "used_txs.jsonl"))

    receipt = machine.dispense(TX, verify_payment=True, fetcher=fake_tx)
    assert receipt["status"] == "generated"
    assert receipt["spec"]["tx_hash"] == TX
    assert receipt["spec"]["category"] in config.CATEGORIES
    assert receipt["payment"]["amount_doge"] >= 1.0
    assert receipt["asset"]["license"] in ("CC0-1.0", "Apache-2.0", "MIT")
    assert os.path.exists(receipt["asset"]["path"])
    assert TX in ledger.load_used_txs()

    # fairness replay passes
    ok, problems = verify_receipt(receipt)
    assert ok, problems

    # reuse guard: second dispense of same tx fails at payment
    try:
        machine.dispense(TX, verify_payment=True, fetcher=fake_tx)
        assert False, "should reject reused tx"
    except payments.TxAlreadyUsed:
        pass


def test_directed_dispense(tmp_path, monkeypatch):
    offline_registry(monkeypatch)
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "ASSET_DIR", str(tmp_path / "assets"))
    monkeypatch.setattr(config, "RECEIPTS_FILE", str(tmp_path / "receipts.jsonl"))
    monkeypatch.setattr(config, "USED_TXS_FILE", str(tmp_path / "used_txs.jsonl"))

    receipt = machine.dispense(TX, description="a glowing potion bottle",
                               category_hint="game_sfx",
                               verify_payment=True, fetcher=fake_tx)
    assert receipt["spec"]["tier"] == "directed"
    assert receipt["spec"]["prompt"] == "a glowing potion bottle"
    assert receipt["spec"]["category"] == "game_sfx"
    ok, problems = verify_receipt(receipt)
    assert ok, problems


def test_directed_by_hint_only_replays(tmp_path, monkeypatch):
    """Regression: directed via category hint with NO user description must
    replay byte-for-byte (the pools-built prompt is not a user description)."""
    offline_registry(monkeypatch)
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "ASSET_DIR", str(tmp_path / "assets"))
    monkeypatch.setattr(config, "RECEIPTS_FILE", str(tmp_path / "receipts.jsonl"))
    monkeypatch.setattr(config, "USED_TXS_FILE", str(tmp_path / "used_txs.jsonl"))

    receipt = machine.dispense(TX, category_hint="game_sfx",
                               verify_payment=True, fetcher=fake_tx)
    assert receipt["spec"]["tier"] == "directed"
    assert receipt["spec"]["description"] is None
    assert receipt["spec"]["category"] == "game_sfx"
    ok, problems = verify_receipt(receipt)
    assert ok, problems


def test_sfx_generator_outputs_valid_wav(tmp_path):
    gen = SfxGenerator()
    res = gen.generate("coin pickup", model_seed=7, out_dir=str(tmp_path))
    assert res.mime == "audio/wav"
    assert res.license == "CC0-1.0"
    assert res.size_bytes > 100
    # RIFF header
    with open(res.path, "rb") as fh:
        assert fh.read(4) == b"RIFF"
        fh.seek(8)
        assert fh.read(4) == b"WAVE"
    # deterministic from seed
    res2 = gen.generate("coin pickup", model_seed=7, out_dir=str(tmp_path / "again"))
    with open(res.path, "rb") as a, open(res2.path, "rb") as b:
        assert a.read() == b.read()


def test_sfx_archetypes_all_render(tmp_path):
    gen = SfxGenerator()
    for seed in range(12):
        res = gen.generate("any", model_seed=seed, out_dir=str(tmp_path))
        assert os.path.exists(res.path) and res.size_bytes > 100
