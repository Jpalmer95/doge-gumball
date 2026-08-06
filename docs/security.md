# Security Model

## Assets and trust assumptions

* **The machine address** — the only thing that must not be lost. Operator
  holds the keys (Dogecoin Core wallet recommended). A leaked private key is
  catastrophic (coins stolen); a leaked HF token is costly (quota burned).
* **HF Spaces** — the backend runs on HF's free infrastructure; we trust HF
  with the machine process, but we do NOT trust the public network.
* **The public** — anyone can submit txs and call endpoints; assume malice.

## Threat model (top risks → mitigations)

| # | Risk | Mitigation |
|---|---|---|
| 1 | **Replay/double-spend of a gumball** — same tx hash redeemed twice | Append-only used-tx ledger; `verify_tx` rejects any hash already present; one gumball per tx forever |
| 2 | **Generation budget drain** — attacker floods requests to burn ZeroGPU quota or paid API credits | Serialized generation queue (MAX_PENDING_GENERATIONS=3); per-IP rate limit on the submit endpoint; only *verified* payments trigger generation |
| 3 | **Payment forgery** — submit a fake tx hash | Server always verifies on-chain via Blockcypher (confirmations + outputs to machine address); tx format validated (64-hex) |
| 4 | **Unconfirmed-tx abuse** — spam unconfirmed txs | MIN_CONFIRMATIONS=1 blocks unconfirmed; configurable to 6 for larger amounts |
| 5 | **Prompt injection via directed descriptions** | Descriptions are data passed to model APIs (never shell); length-capped (300 chars); no format strings built from them |
| 6 | **Secret exposure** — HF_TOKEN, private keys in repo | Secrets only via Space secrets / env; `.gitignore` excludes `.env`; code reads env at runtime; nothing client-side |
| 7 | **Denial of service on the Space** | HF platform rate-limits per Space; our queue bounds concurrency; Blockcypher free-tier limits are cached by the ledger (verified txs are never re-fetched) |
| 8 | **Receipt/ledger tampering** | Receipts are append-only JSONL; a tampered ledger fails the fairness replay (docs/fairness.md) — the audit tool is the integrity check |
| 9 | **SSRF / external calls** | Generators only talk to pinned HF Space URLs; no user-controlled URLs are ever fetched |
| 10 | **XSS via generated content** | Assets are served as files (never inlined HTML); frontend renders with explicit `textContent` for any receipt data |

## Operational rules

* `DOGE_ADDRESS` is set via Space secret; never hardcode a private key.
  Full CLI playbook for the dedicated Core wallet: `docs/operator-cli.md`.
* Before mainnet: generate the address from a Dogecoin Core wallet, back up
  the wallet.dat offline, verify a testnet/1-DOGE tx end-to-end.
* Watch `outputs/receipts.jsonl` growth; archive monthly and keep the archive
  public (it is the fairness proof trail).
* Run `scripts/assess_entry_price.py` weekly (see docs/cost-ledger.md) to
  decide whether the entry price still covers costs.
* HF_TOKEN secret must be a read-only token scoped to the machine's needs.

## CORS / frontend policy

* The API allows cross-origin calls only from the GitHub Pages frontend
  (`https://jpalmer95.github.io`). Same-origin calls from the Space's own
  UI need no CORS.
* `/gumball/machine` and `/gumball/verify/<id>` are intentionally public
  (fairness requires anyone to audit); `/gumball/dispense` is public by
  design too — the tx hash is the ticket — and is protected by the per-IP
  rate limit and the serialized generation queue.
* The UI never receives or displays secrets; machine info deliberately
  omits configuration internals (see `app/api_helpers.machine_info`).

## Known non-goals (v1)

* No per-user accounts or balances (the machine is stateless between txs).
* No automatic refunds (the gumball contract is final-on-confirmation;
  see docs/fairness.md).
* No multi-sig custody — single operator key until volume justifies
  multisig/community custody.
