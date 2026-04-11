from pathlib import Path
import os

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:
    pass

_env = os.getenv("DJANGO_ENV", "development").lower()
if _env == "production":
    from .production import *  # noqa: F401,F403
else:
    from .development import *  # noqa: F401,F403
