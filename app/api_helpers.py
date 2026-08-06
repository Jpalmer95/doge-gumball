"""API helper logic for the machine Space — pure functions so they are
unit-testable offline (no fastapi/gradio imports here).

Everything the web layer needs to build friendly responses lives here:
machine info, category metadata, request validation, and payment-error
mapping with human guidance.
"""
from . import config, ledger, payments

CATEGORY_META = {
    "image": {"emoji": "🖼️", "name": "Image", "blurb": "a one-of-a-kind picture",
              "wait": "~15s"},
    "asset_3d": {"emoji": "🧊", "name": "3D Asset", "blurb": "a game-ready GLB model",
                 "wait": "1-2 min"},
    "song": {"emoji": "🎵", "name": "Song", "blurb": "an original track",
             "wait": "1-3 min"},
    "game_sfx": {"emoji": "🔊", "name": "Game SFX", "blurb": "a retro sound effect",
                 "wait": "instant"},
}

PLACEHOLDER_ADDRESS = config.DOGE_ADDRESS.startswith("DXXX")


def address_is_configured(address: str | None = None) -> bool:
    addr = address or config.DOGE_ADDRESS
    return bool(addr) and not addr.startswith("DXXX") and len(addr) >= 27


def machine_info(demo: bool = False) -> dict:
    """Public machine metadata (never exposes secrets)."""
    return {
        "name": "DOGE Gumball Machine",
        "open": address_is_configured(),
        "address": config.DOGE_ADDRESS,
        "address_hint": "machine open for business" if address_is_configured()
                        else "operator is wiring up the wallet — check back soon",
        "tiers": {
            "blind": {
                "doge": config.TIER_BLIND_DOGE,
                "label": "Blind — total surprise",
                "what": "random category + random description",
            },
            "directed": {
                "doge": config.TIER_DIRECTED_DOGE,
                "label": "Directed — you choose",
                "what": "your description (and optionally a category)",
            },
        },
        "categories": [
            {"key": k, **CATEGORY_META[k]} for k in config.CATEGORIES
        ],
        "min_confirmations": config.MIN_CONFIRMATIONS,
        "demo": demo,
        "fairness": "outcome = f(tx_hash) — SHA256 of your transaction hash "
                    "seeds the draw; every receipt is publicly replayable.",
        "docs": {
            "fairness": "https://github.com/Jpalmer95/doge-gumball/blob/main/docs/fairness.md",
            "license": "https://github.com/Jpalmer95/doge-gumball/blob/main/docs/license-audit.md",
            "source": "https://github.com/Jpalmer95/doge-gumball",
        },
        "receipts_count": len(ledger.load_receipts()),
        "version": "0.1.0",
    }


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------
class RequestError(Exception):
    def __init__(self, status: int, message: str, help: str | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.help = help


def validate_dispense_body(body: dict | None) -> tuple[str, str | None, str | None]:
    """Returns (tx_hash, description, category) or raises RequestError."""
    if not isinstance(body, dict):
        raise RequestError(400, "request body must be a JSON object",
                           "Send JSON like {\"tx_hash\": \"...\"}.")

    tx_hash = (body.get("tx_hash") or "").strip()
    if not tx_hash:
        raise RequestError(400, "tx_hash is required",
                           "Paste the transaction hash from your wallet — it is the ticket.")
    if len(tx_hash) != 64:
        raise RequestError(400, "tx_hash must be 64 hex characters",
                           "A Dogecoin transaction hash is 64 hex chars (0-9a-f). "
                           "Copy it from your wallet's transaction details.")

    description = (body.get("description") or "").strip() or None
    if description and len(description) > config.MAX_DESCRIPTION_LEN:
        raise RequestError(400, f"description too long (max {config.MAX_DESCRIPTION_LEN} chars)",
                           "Keep your request under 300 characters.")

    category = (body.get("category") or "").strip() or None
    if category and category not in config.CATEGORIES:
        raise RequestError(400, f"unknown category '{category}'",
                           f"Choose one of: {', '.join(config.CATEGORIES)}.")

    if description or category:
        return tx_hash, description, category
    return tx_hash, None, None


# ---------------------------------------------------------------------------
# Friendly payment/generation error mapping
# ---------------------------------------------------------------------------
def _receipt_for_tx(tx_hash: str) -> dict | None:
    for r in ledger.load_receipts():
        if r.get("spec", {}).get("tx_hash") == tx_hash:
            return r
    return None


def friendly_error(exc: Exception, tx_hash: str | None = None) -> dict:
    """Map machine/payment exceptions to a {error, help, code} response."""
    if isinstance(exc, payments.BadTxFormat):
        return {"error": str(exc), "code": "bad_tx_format",
                "help": "A Dogecoin tx hash is 64 hex characters. Copy it from your wallet."}
    if isinstance(exc, payments.TxNotFound):
        return {"error": str(exc), "code": "tx_not_found",
                "help": "We couldn't find this transaction on the Dogecoin network. "
                        "Double-check the hash and make sure it's on mainnet (not testnet)."}
    if isinstance(exc, payments.TxUnconfirmed):
        return {"error": str(exc), "code": "unconfirmed",
                "help": f"Transactions usually confirm within a minute or two. "
                        f"Wait for {config.MIN_CONFIRMATIONS} confirmation, then retry "
                        f"with the SAME tx hash (the draw is locked to it)."}
    if isinstance(exc, payments.InsufficientAmount):
        return {"error": str(exc), "code": "insufficient",
                "help": "You can claim any payment of at least 1 DOGE as a blind draw. "
                        "Descriptions/categories need 5 DOGE. Either remove the request, "
                        "or send the difference and resubmit the new tx hash."}
    if isinstance(exc, payments.TxAlreadyUsed):
        receipt = _receipt_for_tx(tx_hash) if tx_hash else None
        return {"error": str(exc), "code": "already_used",
                "help": "One payment = one gumball, forever (that's the fairness rule). "
                        + (f"Your receipt id: {receipt.get('id')} — you can re-download "
                           "your asset from the receipts archive."
                           if receipt else "Find your receipt in the public archive.")}
    if isinstance(exc, Exception):  # generation failures etc.
        return {"error": str(exc), "code": "generation",
                "help": "The machine's generator is busy or briefly down. Your payment is "
                        "safe: retry with the SAME tx hash and you'll get the SAME draw "
                        "(that's the fairness guarantee). If it keeps failing, the "
                        "operator has been alerted."}
    return {"error": str(exc), "code": "unknown",
            "help": "Something unexpected happened. Please retry with the same tx hash."}
