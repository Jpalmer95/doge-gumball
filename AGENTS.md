# AGENTS.md — Doge Gumball Machine

Drop 1 DOGE in the slot, get a gumball: an image, a 3D asset, a song, or a game sound effect.
Fully random, fully fair, fully open source.

## Commands
```bash
python3 scripts/demo_flow.py --tx <any-64-hex>          # offline demo, no payment/network
python3 scripts/demo_flow.py --category image --category-live   # live gen via HF Space (needs HF_TOKEN)
python3 scripts/verify_fairness.py outputs/receipts.jsonl       # audit all receipts
python3 scripts/assess_entry_price.py                          # does the price still cover cost?
python3 -m pytest tests/ -q                                    # 24 tests, offline
```

## Fairness model (do not weaken)
**Fairness = `SHA256(tx_hash)` seeded Mersenne Twister.** No server secrets. The accepted
trade-off is that the outcome is visible before confirmation — documented in `docs/fairness.md`.

Tiers: **1 DOGE blind**, **5 DOGE directed**. Payments are final on confirmation; a failed
generation **voids the reservation** so the same tx retries the same draw (no double-spend of a
draw).

## Cost policy
**Raise the entry price when average generation cost exceeds 75% of entry value.**
`scripts/assess_entry_price.py` automates the check — run it after changing generators.
Cost ledger: `docs/cost-ledger.md`.

## Architecture decisions (recorded — don't relitigate)
- **Backend = `sdk: docker` FastAPI orchestrator on `cpu-basic`.** Gradio 6 was **rejected** for
  the UI: `launch()` re-creates the FastAPI app (wiping custom routes), `/api` + `/gradio_api`
  namespaces collide with its client API, and `gr.HTML` strips `<script>` — which would kill the
  cartoon UI. The machine still *uses* Gradio (GPU Spaces) for generation.
- **Frontend = static cartoon page on GitHub Pages.**
- **Blockcypher** chosen over dogechain.info (Cloudflare-walled as of 2026-08) and sochain
  (timeouts). The ledger caches verified txs.
- **Generators:** FLUX.1-schnell (Apache-2.0), TRELLIS.2 (MIT), ACE-Step (Apache-2.0), procedural
  SFX (CC0). **MusicGen / AudioGen are excluded — CC-BY-NC.** See `docs/license-audit.md`.

## Integration gotchas (each cost real time)
- The 3D chain requires `gradio_client.handle_file()` on **every** image input, and `resolution`
  must be the **string** `'512'` — not an int.
- Song generation requires `infer_step` as an **int**. Raw paths and floats raise opaque server
  errors.
- 3D generations go through the `trellis-image-to-3d` skill workflow; the machine's semaphore plus
  ZeroGPU serialization queue them. **Parallelize only if the cost model proves out.**

## House rules
No refunds.

## Cross-cutting context
`~/dev/knowledge` → `wiki/projects/huggingface-surfaces.md`, `wiki/projects/game-and-xr.md`.
