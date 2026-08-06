# MASTER_PLAN.md — Doge Gumball Machine

> **How to use this document (for agents):**
> 1. Work phase-by-phase, top to bottom. Never skip ahead.
> 2. Mark `[x]` ONLY after the phase's Success Criteria demonstrably pass.
> 3. One commit per task with a descriptive message. Never commit secrets.
> 4. This document is authoritative. Record every pricing/fairness/architecture
>    decision in the **Recorded Decisions** section as you go.
> 5. If a phase is blocked, say so and stop — do not fake success.

## Vision

A fully open source, provably fair "gumball machine" on Dogecoin: users pay
1 DOGE for a blind draw or 5 DOGE for a directed request, and out pops an
image, 3D asset, song, or game sound effect — generated free via Hugging Face
Spaces, licensed CC0, and auditable by anyone from the tx hash alone.

## Sustainability / Cost Model

Who pays when this goes viral? The machine runs on free HF Spaces (ZeroGPU
quota) with a procedural offline category — marginal cost is **$0/gen** at
v1. The entry tiers (1/5 DOGE ≈ $0.07/$0.35) are pure margin while that
holds. The policy in `docs/cost-ledger.md` + `scripts/assess_entry_price.py`
automatically raises the entry if any category ever moves to a paid API
(threshold: avg cost > 75% of entry value). Quota exhaustion (HF daily
limits) is the real scaling constraint — the Phase 2 queue/rate-limit design
and the ability to route a category to a paid API (with cost logging) cover
it.

## Current State (2026-08-06)

* Repo: `github.com/Jpalmer95/doge-gumball` (public).
* Core (Phase 0) done: fairness RNG, Blockcypher verification, receipts +
  used-tx ledger with void-on-failure, 4-category registry, retry logic.
  **24 offline tests pass.**
* **All four generators validated live through `machine.dispense`**:
  FLUX.1-schnell (image), TRELLIS.2 (3D, ~100s → 10.4MB GLB), ACE-Step
  (song → MP3), procedural SFX. All receipts replay.
* **Backend deployed:** https://huggingface.co/spaces/jkorstad/doge-gumball
  (FastAPI orchestrator, sdk: docker, cpu-basic). Verified: UI at root,
  `/gumball/*` API live, fake txs rejected on-chain (payment verification
  active), per-IP rate limit + serialized generation queue.
* **Frontend deployed:** https://jpalmer95.github.io/doge-gumball/ (gh-pages).
* **Polish pass (2026-08-06):** UX overhaul — step indicator, category picker
  for directed draws, copy buttons, on-chain payment guidance, in-UI fairness
  verification (`GET /gumball/verify/<id>`), friendly error help for every
  failure mode; CORS for the Pages frontend; `GET /gumball/health`;
  `app/api_helpers` (offline-tested) + `app/verification` (replay shared by
  CLI and API). **30 offline tests pass.**
* **Not done:** real DOGE address (operator must create wallet + set the
  Space secret — see `docs/operator-cli.md`), public receipts archive, weekly
  cost assessor cron, production abuse monitoring.

---

## Phase 0 — Core Machine ✅ DONE

- [x] Repo scaffold (MIT, README, docs, .gitignore)
- [x] `app/randomness.py` — deterministic fair draw from tx hash
- [x] `app/payments.py` — Blockcypher verification (confirmations, amount,
      reuse guard, tier pricing)
- [x] `app/ledger.py` — receipts.jsonl + used_txs.jsonl (append-only,
      void-on-failure)
- [x] `app/machine.py` — verify → draw → generate (retries, same seed) → receipt
- [x] Generators: `game_sfx` (procedural, offline, CC0) + `image_flux` (live)
- [x] `scripts/verify_fairness.py` — receipt replay audit
- [x] `scripts/assess_entry_price.py` — cost/entry policy check
- [x] `scripts/demo_flow.py` — end-to-end demo (offline + live flags)
- [x] 24 tests green; live FLUX image gen verified
- [x] Initial commit + push to GitHub

**Success criteria (MET):** `pytest tests/ -q` → 24 passed; a live FLUX image
was generated through the machine's own draw path; every written receipt
replays byte-for-byte via `verify_fairness.py`.

---

## Phase 1 — Live Machine (HF Space backend)

Goal: a public machine on HF serving the cartoon UI and the payment flow
end-to-end, with a real DOGE address.

### 1.1 Operator wallet
- [ ] Create Dogecoin Core wallet (or hardware wallet) → set `DOGE_ADDRESS`
      as a Space secret. Back up `wallet.dat` offline.
- **Success:** address valid; a 1-DOGE test payment from a second wallet
  verifies end-to-end through `payments.verify_tx` with ≥1 confirmation.

### 1.2 HF Space backend ✅ DONE (2026-08-06)
- [x] `space/space_app.py` — FastAPI orchestrator: serves the cartoon UI
      (static, live-mode injected) + `GET /gumball/machine`,
      `POST /gumball/dispense`, `GET /gumball/receipt/<id>`,
      `GET /gumball/assets/<filename>`
- [x] `sdk: docker` + cpu-basic (gradio-sdk runtime conflicts with custom
      uvicorn on 7860; gr.HTML strips <script> — so the UI is plain static)
- [x] Deployed: https://huggingface.co/spaces/jkorstad/doge-gumball
      (secrets: HF_TOKEN set; DOGE_ADDRESS pending the operator wallet)
- [x] Serialized generation queue (semaphore, MAX_PENDING=3) + per-IP
      rate limit (5 req/min)
- [x] **Success (MET):** Space RUNNING; fake tx correctly rejected on-chain
      ("transaction ... not found on DOGE mainnet"); UI served at root;
      local end-to-end demo dispense generated + served a real asset

### 1.3 Live-validate the generators ✅ DONE (2026-08-06)
- [x] `image_flux`: dispensed live (FLUX.1-schnell, Apache-2.0, ~10s)
- [x] `asset_3d_trellis`: dispensed live (TRELLIS.2 chain ~100s → 10.4MB GLB,
      MIT) — requires `handle_file()` on every image input and `resolution`
      as STRING `'512'`
- [x] `song_acestep`: dispensed live (ACE-Step → MP3, Apache-2.0) —
      `infer_step` must be INT (float → server TypeError)
- [x] `game_sfx`: procedural, offline, always works
- [x] Move categories from `PENDING_LIVE_CATEGORIES` to `LIVE_CATEGORIES`
- [x] **Success (MET):** every category dispensed through `machine.dispense`
      with a real draw; all receipts replay via `scripts/verify_fairness.py`

### 1.4 GitHub Pages frontend ✅ DONE (2026-08-06)
- [x] Published: https://jpalmer95.github.io/doge-gumball/ (gh-pages branch,
      HTTP 200 verified) — DEMO mode standalone; LIVE mode via BACKEND_URL
- [x] **Success (MET):** site loads; demo plays a local cartoon draw; live
      mode wired to the Space API

---

## Phase 2 — Public Launch

- [ ] Public receipts archive: push `outputs/receipts.jsonl` + assets to a
      public HF dataset/repo after each dispense (the fairness proof trail)
- [ ] Weekly cron: `scripts/assess_entry_price.py` + Space liveness check
      (`scripts/check_spaces.py` from daggr-pipelines)
- [ ] Abuse hardening from `docs/security.md`: confirm queue caps, verify
      Blockcypher rate-limit headroom, monitor used-tx ledger growth
- [ ] Announce: X (@JonathanKorstad — human-gated), GitHub, HF
- **Success:** real user dispenses ≥1 blind and ≥1 directed gumball for real
  DOGE; receipts public; assessor runs weekly with a clean verdict.

---

## Future Roadmap (do not execute until Phases 1–2 are done)

- More categories: video clips, TTS voice lines, voxel models, sprite sheets
- Directed tier: optional explicit category picker (costs 5 DOGE either way)
- Gumball rarity tiers / collectible serials in receipts
- Multi-machine addresses (one per category) to remove amount ambiguity
- Dogecoin node self-hosting to drop Blockcypher dependency
- Community custody / multisig when volume justifies it
- Community fairness audits: a "verify the machine" page on the frontend

---

## Recorded Decisions

| Date | Decision |
|---|---|
| 2026-08-05 | Fairness = SHA256(tx_hash) seeded MT; no server secrets; outcome visible pre-confirmation is an accepted trade-off (see docs/fairness.md) |
| 2026-08-05 | Tiers: 1 DOGE blind / 5 DOGE directed; payments final on confirmation; failed generations void the reservation so the same tx retries the same draw |
| 2026-08-05 | Generators: FLUX.1-schnell (Apache-2.0), TRELLIS.2 (MIT), ACE-Step (Apache-2.0), procedural SFX (CC0). MusicGen/AudioGen excluded (CC-BY-NC). See docs/license-audit.md |
| 2026-08-05 | Entry-price policy: raise entry when avg gen cost > 75% of entry value; automated by scripts/assess_entry_price.py |
| 2026-08-05 | Backend = cpu-basic HF Space orchestrator calling GPU Spaces; frontend = static cartoon page on GitHub Pages |
| 2026-08-05 | Blockcypher free API chosen over dogechain.info (Cloudflare-walled as of 2026-08) and sochain (timeouts); ledger caches verified txs |
| 2026-08-06 | Backend = **sdk: docker** FastAPI orchestrator on cpu-basic. Gradio 6 was rejected for the UI: `launch()` re-creates the FastAPI app (wipes custom routes), `/api`+`/gradio_api` namespaces collide with its client API, and `gr.HTML` strips `<script>` (the cartoon UI would be dead). Machine still *uses* Gradio (GPU Spaces) for generation |
| 2026-08-06 | 3D chain requires `gradio_client.handle_file()` on every image input + `resolution` as string `'512'`; song requires `infer_step` as int. Raw paths / floats raise opaque server errors |
| 2026-08-06 | Per user steer: 3D generations go through the trellis-image-to-3d skill workflow; the machine's semaphore + ZeroGPU serialization queue them; parallelization only if the cost model proves out (docs/cost-ledger.md) |
| 2026-08-06 | House rules: no refunds (payments final on confirmation); overpayment beyond the 1/5 DOGE tiers = donation (machine never sends change). Posted in UI footer, `/gumball/machine` → `policy`, docs/fairness.md §6 |

---

**Owner:** Jonathan Korstad (Jpalmer95 / jkorstad)
**Status:** Phase 0 complete; Phase 1 next
**Updated:** 2026-08-05
