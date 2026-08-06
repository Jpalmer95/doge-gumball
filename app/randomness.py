"""Provably fair randomness for the gumball machine.

Fairness model (v1)
-------------------
The outcome of every gumball is a *pure deterministic function* of the
payment transaction hash. Nothing else — no server secret, no wall-clock
time, no operator input. This means:

  * Anyone can verify any past gumball by replaying `draw()` with the
    receipt's tx hash (see scripts/verify_fairness.py).
  * The outcome cannot be influenced by the operator or the user after
    the transaction is broadcast.
  * Retries are safe: if generation fails, the same seed reproduces the
    same draw, so "works each time" never silently changes the prize.

Security notes (trade-offs, see docs/fairness.md for the full analysis):
  * The outcome is computable by anyone who sees the broadcast tx hash.
    A user who dislikes the outcome can only choose not to submit it —
    the tx is still confirmed on-chain and is not refunded. That is the
    gumball contract: every confirmed payment buys exactly one draw.
  * We never reuse a tx hash (ledger) — one tx = one gumball, forever.
"""
import hashlib
import json
import random

from . import config

# --- Blind-mode prompt pools (draw from these with the tx-derived RNG) ---
POOLS = {
    "image": {
        "adjectives": [
            "cartoon", "glowing", "chunky", "retro", "cosmic", "bouncy",
            "sparkly", "neon", "hand-drawn", "low-poly", "misty", "heroic",
        ],
        "subjects": [
            "space llama", "giant gumball", "robot barista", "corgi astronaut",
            "mushroom wizard", "cassette-tape monster", "cactus knight",
            "dragon koi", "steampunk turtle", "alien cat", "bubblegum ghost",
            "moon bunny",
        ],
        "styles": [
            "flat vector illustration", "pixel art", "watercolor",
            "voxel art", "comic book style", "studio ghibli inspired",
            "cyberpunk poster", "children's book art", "sticker style",
            "graffiti mural",
        ],
    },
    "asset_3d": {
        "adjectives": ["cute", "stylized", "chunky", "glowing", "rusted",
                       "cartoonish", "miniature", "epic"],
        "subjects": [
            "robot companion", "treasure chest", "magic potion bottle",
            "star fighter ship", "woodland mushroom house", "cartoon skateboard",
            "floating island", "gemstone crystal", "viking axe", "monster egg",
        ],
        "styles": ["game-ready prop", "toy collectible", "board game piece",
                   "action figure", "diorama piece"],
    },
    "song": {
        "adjectives": ["bouncy", "dreamy", "epic", "funky", "melancholy",
                       "triumphant", "playful", "mysterious"],
        "subjects": [
            "synthwave", "lo-fi beats", "orchestral fanfare", "acoustic folk",
            "chiptune adventure", "disco", "ambient", "latin pop", "jazz trio",
            "southern rock",
        ],
        "styles": ["8-bar loop", "full track with a catchy hook",
                   "video game battle theme", "menu music", "boss theme"],
    },
    "game_sfx": {
        "subjects": [
            "coin pickup", "power-up blip", "explosion", "jump boing",
            "laser zap", "level-up jingle", "menu select", "boss roar",
            "door creak", "magic spell", "bubble pop", "victory fanfare",
        ],
    },
}


def seed_from_tx(tx_hash: str, rng_version: str = config.RNG_VERSION) -> bytes:
    """Derive the deterministic seed for a payment tx hash."""
    return hashlib.sha256(f"{tx_hash.strip().lower()}|{rng_version}".encode()).digest()


def rng_from_tx(tx_hash: str, rng_version: str = config.RNG_VERSION) -> random.Random:
    """Random instance whose stream is fully determined by the tx hash."""
    return random.Random(seed_from_tx(tx_hash, rng_version))


def _fmt(pool: dict) -> str:
    return " ".join(str(v) for v in pool.values())


def build_blind_prompt(rng: random.Random, category: str,
                       pools_version: str = config.POOLS_VERSION) -> str:
    """Assemble a random description for a blind gumball.

    Deterministic for a given (tx_hash, pools_version): the same rng stream
    always produces the same prompt.
    """
    pool = POOLS[category]
    if category == "game_sfx":
        return rng.choice(pool["subjects"])
    adj = rng.choice(pool["adjectives"])
    subj = rng.choice(pool["subjects"])
    style = rng.choice(pool["styles"])
    return f"{adj} {subj}, {style}"


def draw(tx_hash: str, description: str | None = None,
         category_hint: str | None = None,
         rng_version: str = config.RNG_VERSION,
         pools_version: str = config.POOLS_VERSION) -> dict:
    """Compute the full deterministic gumball spec for a tx hash.

    Returns a JSON-serializable spec that scripts/verify_fairness.py can
    replay against a receipt. The first RNG draw is the category, so the
    category is random even for directed requests unless category_hint is set
    (directed tier only — the user paid for that privilege).
    """
    tx_hash = tx_hash.strip().lower()
    rng = rng_from_tx(tx_hash, rng_version)

    if category_hint is not None:
        if category_hint not in config.CATEGORIES:
            raise ValueError(f"unknown category: {category_hint}")
        category = category_hint
    else:
        category = rng.choice(config.CATEGORIES)

    user_description = description.strip() if description and description.strip() else None
    if user_description:
        prompt = user_description
    else:
        prompt = build_blind_prompt(rng, category, pools_version)

    model_seed = rng.getrandbits(31)  # model-friendly unsigned 31-bit seed

    return {
        "rng_version": rng_version,
        "pools_version": pools_version,
        "tx_hash": tx_hash,
        "tier": "directed" if (user_description or category_hint) else "blind",
        "category": category,
        "category_hint": category_hint,  # recorded so receipts are replayable
        "description": user_description,  # the user's exact input (None = pools-built)
        "prompt": prompt,
        "model_seed": model_seed,
    }


def spec_to_json(spec: dict) -> str:
    return json.dumps(spec, sort_keys=True, separators=(",", ":"))
