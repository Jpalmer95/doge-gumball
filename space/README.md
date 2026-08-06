---
title: DOGE Gumball Machine
emoji: 🐕
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
license: mit
short_description: "Fair Dogecoin gumball machine: 1 DOGE in, CC0 asset out"
---

# 🐕🪙 DOGE Gumball Machine

Drop 1 DOGE in the slot: a random **image**, **3D asset**, **song**, or
**game SFX** pops out. Pay 5 DOGE and tell the machine what you want.

Fair: the prize is a pure function of your tx hash (SHA256 → category,
prompt, model seed). Every receipt is replayable:
`python3 scripts/verify_fairness.py outputs/receipts.jsonl`.

Open: all code MIT, all models Apache-2.0/MIT, all assets CC0.

- Source: https://github.com/Jpalmer95/doge-gumball
- This Space is a cpu-basic **orchestrator** — the cartoon UI and API run
  here; generation happens in remote GPU Spaces (FLUX.1-schnell, TRELLIS.2,
  ACE-Step) called via gradio_client with the machine's HF_TOKEN secret.
- API: `GET /gumball/machine` · `POST /gumball/dispense` ·
  `GET /gumball/receipt/<id>` · `GET /gumball/assets/<filename>`
