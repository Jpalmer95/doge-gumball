"""DOGE Gumball Machine — HF Space entry point (FastAPI orchestrator).

Serves the cartoon UI (frontend/index.html, served with BACKEND_URL='') plus
the machine API:
    GET  /gumball/machine            -> address, tiers, categories, status
    POST /gumball/dispense           -> {tx_hash, description?, category?} -> receipt
    GET  /gumball/receipt/<id>       -> a stored receipt
    GET  /gumball/assets/<filename>  -> dispensed asset files

Architecture note: this Space is a cpu-basic *orchestrator*. Generation
happens in remote GPU Spaces (FLUX.1-schnell, TRELLIS.2, ACE-Step) called via
gradio_client with the machine's HF_TOKEN secret. Payments are verified on the
Dogecoin chain via Blockcypher. Set GUMBALL_DEMO=1 to skip payment
verification (dev/testing only — never in production).

Why not a Gradio UI here? Gradio 6's gr.HTML sanitizes <script> tags (the
cartoon machine's JS would never run) and its launcher re-creates the FastAPI
app, discarding custom routes. Serving the static UI from FastAPI gives full
control, and the machine still *uses* Gradio (the GPU Spaces) for generation.

Fairness: the machine's draw is a pure function of the tx hash (see
app/randomness.py and docs/fairness.md). This process has no override path.
"""
import asyncio
import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app import config, ledger, machine, payments  # noqa: E402

DEMO = os.environ.get("GUMBALL_DEMO", "0") == "1"

# --- per-IP rate limiting (in-memory; per Space replica) -------------------
RL_LIMIT = int(os.environ.get("GUMBALL_RATE_LIMIT", "5"))  # requests / window
RL_WINDOW = 60  # seconds
_ratelimit: dict[str, list[float]] = {}
_rl_lock = threading.Lock()
_generation_slot = threading.Semaphore(config.MAX_PENDING_GENERATIONS)


def rate_limited(ip: str) -> bool:
    now = time.time()
    with _rl_lock:
        bucket = [t for t in _ratelimit.get(ip, []) if t > now - RL_WINDOW]
        if len(bucket) >= RL_LIMIT:
            _ratelimit[ip] = bucket
            return True
        bucket.append(now)
        _ratelimit[ip] = bucket
        return False


def machine_info() -> dict:
    return {
        "name": "DOGE Gumball Machine",
        "address": config.DOGE_ADDRESS,
        "tiers": {
            "blind_doge": config.TIER_BLIND_DOGE,
            "directed_doge": config.TIER_DIRECTED_DOGE,
        },
        "categories": config.CATEGORIES,
        "min_confirmations": config.MIN_CONFIRMATIONS,
        "demo": DEMO,
        "fairness": "outcome = f(tx_hash) — see docs/fairness.md",
    }


def _asset_public(asset: dict | None) -> dict | None:
    if not asset or not asset.get("path"):
        return asset
    out = dict(asset)
    out["url"] = "/gumball/assets/" + Path(str(asset["path"])).name
    return out


def _dispense_impl(tx_hash: str, description: str | None,
                   category: str | None) -> dict:
    """Blocking part — runs in a worker thread so the API stays responsive."""
    try:
        with _generation_slot:
            receipt = machine.dispense(
                tx_hash, description=description, category_hint=category,
                verify_payment=not DEMO,
            )
    except payments.BadTxFormat as e:
        return {"_error": 400, "error": str(e)}
    except payments.PaymentError as e:
        return {"_error": 402, "error": str(e), "code": "payment"}
    except machine.MachineError as e:
        return {"_error": 503, "error": str(e), "code": "generation"}
    receipt["asset"] = _asset_public(receipt.get("asset"))
    return receipt


app = FastAPI(title="DOGE Gumball Machine")


@app.get("/gumball/machine")
async def get_machine() -> JSONResponse:
    return JSONResponse(machine_info())


@app.post("/gumball/dispense")
async def post_dispense(request: Request) -> JSONResponse:
    ip = request.client.host if request.client else "unknown"
    if rate_limited(ip):
        return JSONResponse({"error": "rate limited — slow down, friend"}, status_code=429)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "body must be JSON"}, status_code=400)

    tx_hash = (body or {}).get("tx_hash") or ""
    if not tx_hash:
        return JSONResponse({"error": "tx_hash is required"}, status_code=400)
    if len(tx_hash) != 64:
        return JSONResponse({"error": "tx_hash must be 64 hex characters"}, status_code=400)

    description = (body.get("description") or "").strip() or None
    category = (body.get("category") or "").strip() or None

    result = await asyncio.to_thread(
        _dispense_impl, tx_hash, description, category
    )
    if "_error" in result:
        return JSONResponse(
            {k: v for k, v in result.items() if k != "_error"},
            status_code=result["_error"],
        )
    return JSONResponse(result)


@app.get("/gumball/receipt/{receipt_id}")
async def get_receipt(receipt_id: str) -> JSONResponse:
    for r in ledger.load_receipts():
        if r.get("id") == receipt_id:
            r["asset"] = _asset_public(r.get("asset"))
            return JSONResponse(r)
    return JSONResponse({"error": "receipt not found"}, status_code=404)


@app.get("/gumball/assets/{filename}")
async def get_asset(filename: str):
    """Serve a dispensed asset (path-traversal safe)."""
    name = Path(filename).name  # strips any directory components
    path = Path(config.ASSET_DIR) / name
    if not path.is_file():
        return JSONResponse({"error": "asset not found"}, status_code=404)
    return FileResponse(path)


# --- static frontend: serve index.html with BACKEND_URL='' (live mode) -----
_www = ROOT / "_www"
_www.mkdir(exist_ok=True)
_ui = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8").replace(
    "const BACKEND_URL = null;", "const BACKEND_URL = '';"
)
(_www / "index.html").write_text(_ui, encoding="utf-8")
app.mount("/", StaticFiles(directory=_www, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "7860")))
