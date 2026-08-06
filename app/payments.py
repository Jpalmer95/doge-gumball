"""Dogecoin payment verification via Blockcypher (free, no key required).

Rules enforced:
  * tx hash format is a 64-char hex string
  * tx exists on the DOGE mainnet
  * tx has >= MIN_CONFIRMATIONS confirmations
  * the sum of outputs paying to the machine's DOGE_ADDRESS covers the
    required tier amount (satoshis)
  * the tx hash has never been used for a gumball before (reuse guard)

Blockcypher free tier is rate-limited (~3 req/s); the ledger caches every
verified tx so repeat submissions of the same hash cost nothing.
"""
import json
import re
import time
import urllib.error
import urllib.request

from . import config


class PaymentError(Exception):
    """Base class for payment verification failures."""


class BadTxFormat(PaymentError):
    pass


class TxNotFound(PaymentError):
    pass


class TxUnconfirmed(PaymentError):
    pass


class InsufficientAmount(PaymentError):
    pass


class TxAlreadyUsed(PaymentError):
    pass


def fetch_tx(tx_hash: str, timeout: int = 20) -> dict:
    """Fetch a raw transaction from Blockcypher. Raises TxNotFound on 404."""
    url = config.BLOCKCYPHER_TX_URL.format(tx_hash=tx_hash)
    req = urllib.request.Request(url, headers={"User-Agent": "doge-gumball/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise TxNotFound(f"transaction {tx_hash} not found on DOGE mainnet")
        raise PaymentError(f"blockcypher HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise PaymentError(f"blockcypher unreachable: {e.reason}")


def received_satoshis(tx: dict, address: str) -> int:
    """Sum of outputs paying to `address` (satoshis)."""
    total = 0
    for out in tx.get("outputs", []):
        addrs = out.get("addresses") or []
        if address in addrs:
            total += int(out.get("value", 0))
    return total


def required_satoshis(description: str | None, category_hint: str | None) -> int:
    """Tier price in satoshis: directed requests cost more."""
    if description or category_hint:
        return int(config.TIER_DIRECTED_DOGE * config.SATOSHIS_PER_DOGE)
    return int(config.TIER_BLIND_DOGE * config.SATOSHIS_PER_DOGE)


def verify_tx(tx_hash: str, description: str | None = None,
              category_hint: str | None = None,
              used_txs: set | None = None,
              min_confirmations: int | None = None,
              fetcher=fetch_tx) -> dict:
    """Verify a payment tx and return the verified facts.

    `used_txs`: set of tx hashes already redeemed (from the ledger).
    `fetcher`: injectable for tests.
    """
    if not re.match(config.TX_HASH_RE, tx_hash or ""):
        raise BadTxFormat("tx hash must be 64 hex characters")

    required = required_satoshis(description, category_hint)

    if used_txs and tx_hash.lower() in used_txs:
        raise TxAlreadyUsed(f"tx {tx_hash[:16]}… already redeemed")

    tx = fetcher(tx_hash)

    confirmations = int(tx.get("confirmations", 0) or 0)
    conf_needed = min_confirmations if min_confirmations is not None else config.MIN_CONFIRMATIONS
    if confirmations < conf_needed:
        raise TxUnconfirmed(
            f"tx {tx_hash[:16]}… has {confirmations} confirmations, need {conf_needed}"
        )

    amount = received_satoshis(tx, config.DOGE_ADDRESS)
    if amount < required:
        raise InsufficientAmount(
            f"paid {amount} satoshis to machine, need {required} "
            f"({amount / config.SATOSHIS_PER_DOGE:.2f} DOGE)"
        )

    return {
        "tx_hash": tx_hash.lower(),
        "confirmations": confirmations,
        "amount_satoshis": amount,
        "amount_doge": amount / config.SATOSHIS_PER_DOGE,
        "fee_satoshis": int(tx.get("fees", 0) or 0),
        "received_at": tx.get("received"),
        "required_satoshis": required,
    }
