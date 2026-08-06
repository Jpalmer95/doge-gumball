# 🐕🪙 Doge Gumball Machine

> Drop 1 DOGE in the slot. A gumball pops out: an **image**, a **3D asset**, a
> **song**, or a **game sound effect**. Fully random, fully fair, fully open source.

Pay **1 DOGE** for a blind draw — you don't know what you'll get, and neither
does the machine until your transaction hash says so. Pay **5 DOGE** and tell
the machine what you want ("a glowing potion bottle", "a chiptune boss
theme") and it'll aim at your description.

## House rules

**No refunds** — payments are final once confirmed on-chain. This is a
novelty machine, not a financial product. **Any DOGE over the listed price
is a much-appreciated donation**: the machine never sends change, so an
overpayment (e.g. 2 DOGE for a blind draw) keeps the difference in the
machine address as a tip. 🐕

## Why it's fair

Every gumball's outcome is a **pure deterministic function of your
transaction hash**. No server secrets, no operator override, no wall-clock
magic:

```
seed = SHA256(tx_hash)  →  category, prompt, and model seed all follow
```

Anyone can replay any receipt: `python3 scripts/verify_fairness.py outputs/receipts.jsonl`.
The category, description, and seed are randomized **before** generation and
locked in the receipt. One tx = one gumball, forever.

## Why it's open source

* All code: MIT (this repo).
* All models: Apache-2.0 / MIT (see `docs/license-audit.md`).
* All outputs: dedicated **CC0 / public domain** via every receipt — drop a
  gumball straight into your commercial game. No copyright cliffs.
* Generators run on free Hugging Face Spaces (ZeroGPU quota) wherever
  possible; the machine has an entry-price policy (`docs/cost-ledger.md`)
  that raises the entry if a paid API is ever needed.

## Quickstart

```bash
# offline demo — no payment, no network (procedural SFX)
python3 scripts/demo_flow.py --tx <any-64-hex>

# live image generation via HF Space (needs HF_TOKEN)
python3 scripts/demo_flow.py --category image --category-live

# audit fairness of all receipts
python3 scripts/verify_fairness.py outputs/receipts.jsonl

# check whether the entry price still covers generation cost
python3 scripts/assess_entry_price.py

# tests (24, offline)
python3 -m pytest tests/ -q
```

## How a real gumball works (production flow)

1. The machine shows its DOGE address and tier prices.
2. You send **1 DOGE** (blind) or **5 DOGE** (directed, with a description).
3. You (or the frontend) submit the tx hash.
4. The machine verifies it on-chain (Blockcypher): real tx, confirmed,
   paying the machine address, never used before.
5. The tx hash seeds the draw → category + prompt + model seed.
6. The asset is generated (HF Space or procedural), stamped with its license,
   and delivered with a replayable receipt.

## Repo layout

```
app/                 core: config, randomness (fairness), payments, ledger, machine,
                     api_helpers (friendly API), verification (receipt replay)
app/generators/      image_flux, asset_3d_trellis, song_acestep, game_sfx (procedural)
space/               HF Space: space_app.py (FastAPI), Dockerfile, README frontmatter
docs/                fairness spec, license audit, security model, cost policy,
                     operator-cli.md (Dogecoin Core CLI playbook)
scripts/             demo, fairness verification, entry-price assessor, Space deploy
frontend/            cartoon gumball machine UI (GitHub Pages / Space)
tests/               30 offline tests
MASTER_PLAN.md       the durable build/deploy roadmap
```

## Operator: wiring up the wallet (exact CLI commands)

See `docs/operator-cli.md` — it walks through creating the dedicated
`doge-gumball` wallet in Dogecoin Core via CLI, generating the receiving
address, setting the `DOGE_ADDRESS` Space secret, and sending a real test
payment.

## Roadmap status

- [x] Phase 0: fairness core, payment verification, ledger, offline generator, tests
- [x] Phase 1: HF Space backend (FastAPI, live at https://huggingface.co/spaces/jkorstad/doge-gumball),
      all 4 generators live-validated, frontend on GitHub Pages
      (https://jpalmer95.github.io/doge-gumball/)
- [ ] Phase 2: real DOGE address, receipts archive, cost-assessor cron, launch

See `MASTER_PLAN.md` for the full roadmap with success criteria.

*Not financial advice. Not an investment. It's a gumball machine.*
