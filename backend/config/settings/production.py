from .base import *  # noqa: F401,F403
import os

DEBUG = False
# SECRET_KEY must be provided via environment in production
SECRET_KEY = os.environ["SECRET_KEY"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "hubx"),
        "USER": os.environ.get("DB_USER", "hubx"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Example:
# ALLOWED_HOSTS=".hubx.market,localhost" -> [".hubx.market", "localhost"]
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h] or [".hubx.market"]

if not CSRF_TRUSTED_ORIGINS:
    root_domain = os.environ.get("HUBX_MARKET_ROOT_DOMAIN", "hubx.market").strip()
    derived_origins = []
    if root_domain:
        derived_origins.append(f"https://{root_domain}")
    for host in ALLOWED_HOSTS:
        normalized_host = host.strip()
        if not normalized_host or normalized_host == "*":
            continue
        if normalized_host.startswith("."):
            derived_origins.append(f"https://*{normalized_host}")
        else:
            derived_origins.append(f"https://{normalized_host}")
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(derived_origins))
