"""DOGE Gumball Machine — HF Space entry point (FastAPI orchestrator).

Serves the cartoon UI (frontend/index.html, served with BACKEND_URL='') plus
the machine API:
    GET  /gumball/machine            -> open status, address, tiers, categories
    POST /gumball/dispense           -> {tx_hash, description?, category?} -> receipt
    GET  /gumball/receipt/<id>       -> a stored receipt
    GET  /gumball/verify/<id>        -> fairness replay of a receipt
    GET  /gumball/health             -> liveness
    GET  /gumball/assets/<filename>  -> dispensed asset files

Architecture: cpu-basic *orchestrator*. Generation happens in remote GPU
Spaces (FLUX.1-schnell, TRELLIS.2, ACE-Step) via gradio_client with the
machine's HF_TOKEN secret. Payments are verified on-chain via Blockcypher.
Set GUMBALL_DEMO=1 to skip payment verification (dev/testing only).

Fairness: the draw is a pure function of the tx hash (app/randomness.py,
docs/fairness.md). This process has no override path.
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
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app import api_helpers, config, ledger, machine, payments  # noqa: E402

DEMO = os.environ.get("GUMBALL_DEMO", "0") == "1"

# --- per-IP rate limiting (in-memory; per Space replica) -------------------
RL_LIMIT = int(os.environ.get("GUMBALL_RATE_LIMIT", "5"))  # requests / window
RL_WINDOW = 60  # seconds
MAX_BODY_BYTES = 16 * 1024
_ratelimit: dict[str, list[float]] = {}
_rl_lock = threading.Lock()
_generation_slot = threading.Semaphore(config.MAX_PENDING_GENERATIONS)

# Origins allowed to call the API cross-origin (GitHub Pages frontend).
# Same-origin calls from the Space's own UI need no CORS.
CORS_ORIGINS = [
    "https://jpalmer95.github.io",
    "https://jpalmer95.github.io/",
]


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
    except (payments.PaymentError, machine.MachineError) as e:
        return {"_error": api_helpers.friendly_error(e, tx_hash)}
    receipt["asset"] = _asset_public(receipt.get("asset"))
    return receipt


app = FastAPI(title="DOGE Gumball Machine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/gumball/health")
async def get_health() -> JSONResponse:
    return JSONResponse({
        "ok": True, "demo": DEMO, "open": api_helpers.address_is_configured(),
        "time": time.time(), "version": "0.1.0",
    })


@app.get("/gumball/machine")
async def get_machine() -> JSONResponse:
    return JSONResponse(api_helpers.machine_info(demo=DEMO))


@app.post("/gumball/dispense")
async def post_dispense(request: Request) -> JSONResponse:
    ip = request.client.host if request.client else "unknown"
    if rate_limited(ip):
        return JSONResponse(
            {"error": "rate limited — slow down, friend",
             "help": "Wait a minute between draws."},
            status_code=429,
        )

    if int(request.headers.get("content-length") or 0) > MAX_BODY_BYTES:
        return JSONResponse({"error": "request too large"}, status_code=413)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "body must be JSON"}, status_code=400)

    try:
        tx_hash, description, category = api_helpers.validate_dispense_body(body)
    except api_helpers.RequestError as e:
        return JSONResponse({"error": e.message, "help": e.help}, status_code=e.status)

    result = await asyncio.to_thread(
        _dispense_impl, tx_hash, description, category
    )
    if "_error" in result:
        err = result["_error"]
        code = err.get("code")
        status = 409 if code == "already_used" else (
            400 if code in ("bad_tx_format", "unknown_category") else 402)
        if code == "generation":
            status = 503
        return JSONResponse({k: v for k, v in err.items() if k != "_error"},
                            status_code=status)
    return JSONResponse(result)


@app.get("/gumball/receipt/{receipt_id}")
async def get_receipt(receipt_id: str) -> JSONResponse:
    for r in ledger.load_receipts():
        if r.get("id") == receipt_id:
            r["asset"] = _asset_public(r.get("asset"))
            return JSONResponse(r)
    return JSONResponse({"error": "receipt not found"}, status_code=404)


@app.get("/gumball/verify/{receipt_id}")
async def verify_receipt(receipt_id: str) -> JSONResponse:
    """Replay a receipt's spec against its tx hash — the fairness audit."""
    from app.verification import verify_receipt as replay

    for r in ledger.load_receipts():
        if r.get("id") == receipt_id:
            ok, problems = replay(r)
            return JSONResponse({
                "id": receipt_id,
                "verified": ok,
                "problems": problems,
                "fairness": "outcome is a pure function of the tx hash" if ok
                            else "MISMATCH — receipt does not replay!",
            })
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
