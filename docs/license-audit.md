# Generator License Audit

Requirement: **every dispensed asset must be free of downstream copyright
risk** — users must be able to drop a gumball into a commercial game, mod, or
project without worrying about model-license restrictions or sample
contamination.

Policy: a generator is only allowed in the machine if its **outputs** carry no
restrictions. We prefer models under MIT/Apache-2.0 (no output clause) and we
dedicate every dispensed asset to the public domain via its receipt (CC0-1.0),
which is valid because none of the underlying models restricts outputs.

| Category | Generator | Model license | Output status | Cost | Notes |
|---|---|---|---|---|---|
| image | FLUX.1-schnell (HF Space `black-forest-labs/FLUX.1-schnell`) | Apache-2.0 | ✅ commercial OK | $0 (ZeroGPU quota) | BFL ships weights under Apache-2.0; no output restrictions |
| asset_3d | TRELLIS.2 (HF Space `microsoft/TRELLIS.2`) | MIT | ✅ commercial OK | $0 (ZeroGPU quota) | Concept image via FLUX, then image→GLB |
| song | ACE-Step v1 3.5B (HF Space `ACE-Step/ACE-Step`) | Apache-2.0 | ✅ commercial OK | $0 (ZeroGPU quota) | Full songs with vocals; Apache-2.0 |
| game_sfx | Procedural jsfxr-style synth (in-repo) | original synthesis | ✅ CC0 by construction | $0 (offline) | No model at all — zero license surface |

## Explicitly rejected

| Model | Reason |
|---|---|
| MusicGen / AudioGen (Meta) | CC-BY-NC 4.0 — **non-commercial**; outputs can't be used in commercial games |
| Stable Audio Open | Custom StabilityAI license with revenue caps — murky for downstream |
| Suno / Udio APIs | Closed weights; ToS restricts commercial use of outputs |
| SDXL base | OpenRAIL-M allows commercial use but adds attribution/misuse clauses — acceptable, but FLUX is cleaner; kept as fallback only |
| VAST-AI/TripoSG | Output terms not fully auditable for a public vending machine; TRELLIS (MIT) preferred |

## How the machine stamps licenses

Every receipt records `asset.license` (the generator's output license) and
the receipt itself is the CC0 dedication. `outputs/receipts.jsonl` is the
public proof trail: prompt, seed, generator, license, tx hash.

## Policy for future generators

1. Check the **model** license (weights) *and* the **Space terms**.
2. Outputs must be usable commercially with no attribution requirement
   (CC0/Unlicense/MIT/Apache-2.0 only; OpenRAIL-M acceptable with a note).
3. No samples from copyrighted recordings in training data that could leak
   (favor models trained on licensed/CC data where this is documented).
4. Record the audit row before the generator goes live in the machine.
