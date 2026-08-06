"""Payment verification rules with an injected fake Blockcypher fetcher."""
import sys

sys.path.insert(0, ".")

from app import config, payments

TX = "ab" * 32


def fake_tx(confirmations=3, to_machine=100_000_000, extra_out=0):
    outs = [{"addresses": [config.DOGE_ADDRESS], "value": to_machine}]
    if extra_out:
        outs.append({"addresses": ["DSOMEOTHERADDRESS"], "value": extra_out})
    return {
        "hash": TX,
        "confirmations": confirmations,
        "total": to_machine + extra_out,
        "fees": 1000,
        "received": "2026-01-01T00:00:00Z",
        "outputs": outs,
    }


def test_valid_blind_payment():
    v = payments.verify_tx(TX, fetcher=lambda h: fake_tx())
    assert v["amount_satoshis"] == 100_000_000
    assert v["amount_doge"] == 1.0
    assert v["confirmations"] == 3


def test_valid_directed_payment_requires_five_doge():
    ok = payments.verify_tx(TX, description="potion", fetcher=lambda h: fake_tx(to_machine=500_000_000))
    assert ok["amount_doge"] == 5.0
    try:
        payments.verify_tx(TX, description="potion", fetcher=lambda h: fake_tx(to_machine=100_000_000))
        assert False, "should raise InsufficientAmount"
    except payments.InsufficientAmount:
        pass


def test_change_output_ignored():
    # 1 DOGE to machine + 0.5 DOGE change back to sender -> still valid blind
    v = payments.verify_tx(TX, fetcher=lambda h: fake_tx(to_machine=100_000_000, extra_out=50_000_000))
    assert v["amount_satoshis"] == 100_000_000


def test_unconfirmed_rejected():
    try:
        payments.verify_tx(TX, fetcher=lambda h: fake_tx(confirmations=0))
        assert False
    except payments.TxUnconfirmed:
        pass


def test_used_tx_rejected():
    try:
        payments.verify_tx(TX, used_txs={TX}, fetcher=lambda h: fake_tx())
        assert False
    except payments.TxAlreadyUsed:
        pass


def test_bad_format_rejected():
    for bad in ["", "zz" * 32, "abc", TX[:-1] + "Z"]:
        try:
            payments.verify_tx(bad, fetcher=lambda h: fake_tx())
            assert False, f"should reject {bad!r}"
        except payments.BadTxFormat:
            pass


def test_tx_not_found():
    def missing(h):
        raise payments.TxNotFound("nope")
    try:
        payments.verify_tx(TX, fetcher=missing)
        assert False
    except payments.TxNotFound:
        pass


def test_required_satoshis_tiers():
    assert payments.required_satoshis(None, None) == 100_000_000
    assert payments.required_satoshis("x", None) == 500_000_000
    assert payments.required_satoshis(None, "image") == 500_000_000
