"""The machine: verify payment -> draw fair spec -> generate -> receipt.

Invariants (the fairness contract):
  * One verified tx hash -> exactly one gumball, forever (used-tx ledger).
  * The drawn category/prompt/seed are a pure function of the tx hash
    (app/randomness.py) and are recorded in the receipt for replay.
  * If generation fails, we retry the SAME category with the SAME seed —
    the prize never silently changes. A failed category is re-drawn ONLY
    for blind gumballs if the operator has disabled that category.
"""
import time

from . import config, ledger, payments, randomness
from .generators import REGISTRY

RETRIES = 3
RETRY_BACKOFF_SECONDS = 10


class MachineError(Exception):
    pass


def dispense(tx_hash: str, description: str | None = None,
             category_hint: str | None = None,
             verify_payment: bool = True,
             fetcher=payments.fetch_tx) -> dict:
    """Run one gumball end-to-end and return the receipt."""
    tx_hash = (tx_hash or "").strip().lower()

    if description and len(description) > config.MAX_DESCRIPTION_LEN:
        raise MachineError(
            f"description too long (max {config.MAX_DESCRIPTION_LEN} chars)"
        )

    payment = None
    if verify_payment:
        used = ledger.load_used_txs()
        payment = payments.verify_tx(
            tx_hash, description=description, category_hint=category_hint,
            used_txs=used, fetcher=fetcher,
        )
        ledger.mark_tx_used(tx_hash)

    spec = randomness.draw(tx_hash, description=description,
                           category_hint=category_hint)

    generator = REGISTRY[spec["category"]]
    asset = None
    error = None
    last_exc = None
    for attempt in range(RETRIES):
        try:
            result = generator.generate(spec["prompt"], spec["model_seed"],
                                        config.ASSET_DIR)
            asset = result.as_dict()
            break
        except Exception as e:  # network/queue failures are retryable
            last_exc = e
            error = f"{type(e).__name__}: {e}"
            if attempt < RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))

    if asset is None:
        # Release the reservation: the payer must be able to retry with the
        # same tx (same deterministic draw) until the machine works.
        if verify_payment:
            ledger.void_tx(tx_hash)
        receipt = ledger.write_receipt(
            spec, payment, {"path": None}, status="failed",
            generator=generator.name, error=error,
        )
        raise MachineError(f"generation failed after {RETRIES} attempts: {error}")

    receipt = ledger.write_receipt(
        spec, payment, asset, status="generated", generator=generator.name,
    )
    return receipt
