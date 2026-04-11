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