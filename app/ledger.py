"""Receipt and used-tx ledger (append-only JSONL, stdlib only).

Every dispensed gumball produces a machine-readable receipt that carries:
  * the full deterministic spec (replayable by scripts/verify_fairness.py)
  * the payment facts (tx hash, amount)
  * the asset that was produced, its license, and the cost estimate

The used-tx ledger is the reuse guard: one tx hash = one gumball, forever.
"""
import hashlib
import json
import os
import threading
from datetime import datetime, timezone

from . import config

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def receipt_id(tx_hash: str) -> str:
    return hashlib.sha256(tx_hash.strip().lower().encode()).hexdigest()[:12]


def ensure_dirs() -> None:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.ASSET_DIR, exist_ok=True)


def _append(path: str, record: dict) -> None:
    ensure_dirs()
    with _lock, open(path, "a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_used_txs() -> set[str]:
    """Active reservations: any tx that has been used and not voided."""
    return {r["tx_hash"].lower() for r in load_jsonl(config.USED_TXS_FILE)
            if not r.get("void")}


def load_receipts() -> list[dict]:
    return load_jsonl(config.RECEIPTS_FILE)


def mark_tx_used(tx_hash: str) -> None:
    _append(config.USED_TXS_FILE, {"tx_hash": tx_hash.strip().lower(), "at": _now_iso()})


def void_tx(tx_hash: str) -> None:
    """Release a tx reservation (used when generation fails so the payer can
    retry with the same tx — the deterministic spec guarantees the same draw)."""
    _append(config.USED_TXS_FILE, {"tx_hash": tx_hash.strip().lower(), "at": _now_iso(), "void": True})


def write_receipt(spec: dict, payment: dict | None, asset: dict,
                  status: str = "generated", cost_usd: float | None = None,
                  generator: str | None = None, error: str | None = None) -> dict:
    """Persist a receipt. `spec` is the draw() output; `asset` describes the
    produced file (path, mime, size, license)."""
    receipt = {
        "id": receipt_id(spec["tx_hash"]),
        "created_at": _now_iso(),
        "spec": spec,
        "payment": payment,
        "generator": generator,
        "asset": asset,
        "status": status,
        "cost_usd": cost_usd,
        "error": error,
    }
    _append(config.RECEIPTS_FILE, receipt)
    return receipt
