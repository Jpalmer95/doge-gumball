# 🐕🪙 Doge Gumball Machine

> Drop 1 DOGE in the slot. A gumball pops out: an **image**, a **3D asset**, a
> **song**, or a **game sound effect**. Fully random, fully fair, fully open source.

Pay **1 DOGE** for a blind draw — you don't know what you'll get, and neither
does the machine until your transaction hash says so. Pay **5 DOGE** and tell
the machine what you want ("a glowing potion bottle", "a chiptune boss
theme") and it'll aim at your description.

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
app/                 core: config, randomness (fairness), payments, ledger, machine
app/generators/      image_flux, asset_3d_trellis, song_acestep, game_sfx (procedural)
docs/                fairness spec, license audit, security model, cost policy
scripts/             demo, fairness verification, entry-price assessor
frontend/            cartoon gumball machine UI (GitHub Pages / Space embed)
tests/               24 offline tests
MASTER_PLAN.md       the durable build/deploy roadmap
```

## Roadmap status

- [x] Phase 0: fairness core, payment verification, ledger, offline generator, tests
- [x] Live image generation (FLUX.1-schnell) verified
- [ ] Phase 1: HF Space backend (Gradio + API), real DOGE address, live 3D/song validation
- [ ] Phase 2: public launch — GitHub Pages frontend, receipts archive, asset vault

See `MASTER_PLAN.md` for the full roadmap with success criteria.

*Not financial advice. Not an investment. It's a gumball machine.*
