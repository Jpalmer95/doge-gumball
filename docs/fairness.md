# Fairness Specification (v1)

The Doge Gumball machine is **provably fair by construction**: the outcome of
every gumball is a pure deterministic function of public on-chain data, so
neither the operator nor the player can influence it, and anyone can audit
any past draw.

## 1. The draw

For a payment transaction `tx` on the Dogecoin mainnet:

```
seed    = SHA256( lowercase(tx_hash) + "|" + RNG_VERSION )
rng     = Mersenne Twister(seed)            # Python random.Random
draw 1  = rng.choice(CATEGORIES)            # uniform: image | asset_3d | song | game_sfx
draw 2+ = pool picks for the blind prompt   # adjectives/subjects/styles
seed N  = rng.getrandbits(31)               # model seed, reproducible
```

Everything that matters — category, prompt, model seed — is recorded in the
machine-readable receipt at generation time (`outputs/receipts.jsonl`).

## 2. Directed requests (5 DOGE tier)

The user may supply a description (and optionally a category). The description
is used verbatim as the prompt; a category hint short-circuits draw 1. Both
inputs are recorded in the receipt (`spec.description`, `spec.category_hint`)
so the draw is still fully replayable. Tier is decided by the *presence* of
those inputs, which the payment verifier checks against the amount paid
(5 DOGE minimum).

## 3. Verification

`python3 scripts/verify_fairness.py outputs/receipts.jsonl` replays every
receipt: it recomputes the spec from the recorded inputs and fails if any
field (category, prompt, model_seed, versions) differs. This is the audit
tool — the community can run it against the public receipts archive any time.

## 4. Trade-offs (documented, deliberate)

* **Pre-image visibility.** The outcome is computable by anyone who sees the
  broadcast tx hash. A player who dislikes the outcome can only *decline to
  submit* the tx — the coins are already spent on-chain. We treat confirmed
  payments as final: 1 DOGE buys exactly one draw, no refunds for
  disappointment. This is the gumball contract.
* **Determinism is the point.** It is what makes retries safe (same tx →
  same prize even if generation fails) and what makes audits possible.
* **Versioning.** `RNG_VERSION` and `POOLS_VERSION` are baked into every
  receipt. Changing the pools or the algorithm requires bumping the version;
  old receipts stay replayable forever.
* **No server secrets.** There is no hidden salt, no operator override path,
  no wall-clock input. The machine cannot rig a draw even if compromised at
  the application layer (it could, of course, deny service — that is outside
  the fairness model and addressed in docs/security.md).

## 5. Edge cases

| Case | Behavior |
|---|---|
| Same tx submitted twice | Rejected by the used-tx ledger (one gumball per tx) |
| Generation fails | Reservation is voided; retrying the same tx re-draws the SAME spec |
| Directed payment, no description submitted | Treated as blind (amount still ≥ 5 DOGE is fine) |
| Operator disables a category | Blind draws re-roll from remaining categories; directed draws are rejected with a clear error |
