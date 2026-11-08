"""Central configuration. Everything can be overridden with environment variables."""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]          # .../backend
DB_PATH = Path(os.getenv("TALENTHUB_DB_PATH", BASE_DIR / "talenthub.db"))
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"
STATIC_DIR = BASE_DIR / "static"

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12
ALGORITHM = "HS256"

# Business-rule constants (documented in the Placement Policy and README)
OFFER_DEFAULT_RESPONSE_DAYS = 7
OFFER_MAX_RESPONSE_DAYS = 30
INTERVIEW_MIN_MINUTES = 15
INTERVIEW_MAX_MINUTES = 480
MAX_ROUNDS = 6


def get_secret_key() -> str:
    """Use TALENTHUB_SECRET_KEY if set, otherwise generate one once and keep it in .secret_key
    (so tokens survive restarts and no secret is hard-coded in source control)."""
    env = os.getenv("TALENTHUB_SECRET_KEY")
    if env:
        return env
    key_file = Path(os.getenv("TALENTHUB_SECRET_FILE", BASE_DIR / ".secret_key"))
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_urlsafe(48)
    key_file.write_text(key)
    return key
