"""Central configuration for the Doge Gumball machine.

All knobs the operator needs live here or in environment variables.
Never put secrets here — use Space secrets / env vars (HF_TOKEN, etc.).
"""
import os

# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------
# Operator must set DOGE_ADDRESS (owned wallet, ideally Dogecoin Core).
DOGE_ADDRESS = os.environ.get(
    "DOGE_ADDRESS", "DXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
)

SATOSHIS_PER_DOGE = 100_000_000
TIER_BLIND_DOGE = 1.0          # 1 DOGE -> fully random gumball
TIER_DIRECTED_DOGE = 5.0       # 5 DOGE -> user supplies description (and optionally category)
MIN_CONFIRMATIONS = 1          # UX-friendly; consider 6 for large amounts
BLOCKCYPHER_TX_URL = "https://api.blockcypher.com/v1/doge/main/txs/{tx_hash}"

# ---------------------------------------------------------------------------
# Fairness (do NOT change once live without bumping versions — receipts replay on these)
# ---------------------------------------------------------------------------
RNG_VERSION = "gumball-v1"
POOLS_VERSION = "pools-v1"

# ---------------------------------------------------------------------------
# Categories served by the machine (drawn uniformly at random in blind mode)
# ---------------------------------------------------------------------------
CATEGORIES = ["image", "asset_3d", "song", "game_sfx"]

# ---------------------------------------------------------------------------
# Security / limits
# ---------------------------------------------------------------------------
MAX_DESCRIPTION_LEN = 300
MAX_PENDING_GENERATIONS = 3
TX_HASH_RE = r"^[0-9a-fA-F]{64}$"

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
OUTPUT_DIR = os.environ.get("GUMBALL_OUTPUT_DIR", "outputs")
ASSET_DIR = os.path.join(OUTPUT_DIR, "assets")
RECEIPTS_FILE = os.path.join(OUTPUT_DIR, "receipts.jsonl")
USED_TXS_FILE = os.path.join(OUTPUT_DIR, "used_txs.jsonl")
