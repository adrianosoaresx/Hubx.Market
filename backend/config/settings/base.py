from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BASE_DIR.parent

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-key")
DEBUG = os.getenv("DEBUG", "1") == "1"

ALLOWED_HOSTS = [host for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host] or (
    ["*"] if DEBUG else ["localhost"]
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "modules.accounts",
    "modules.tenants",
    "modules.catalog",
    "modules.customers",
    "modules.cart",
    "modules.checkout",
    "modules.orders",
    "modules.payments",
    "modules.shipping",
    "modules.coupons",
    "modules.reviews",
    "modules.subscriptions",
    "modules.notifications",
    "modules.pages",
    "modules.newsletter",
    "modules.audit",
    "modules.api_keys",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "app.modules.tenants.interfaces.middleware.TenantSubdomainMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [REPO_ROOT / "ui" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "staticfiles")
STATICFILES_DIRS = [REPO_ROOT / "ui" / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = str(BASE_DIR / "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TIMEZONE = TIME_ZONE

HUBX_MARKET_ROOT_DOMAIN = os.getenv("HUBX_MARKET_ROOT_DOMAIN", "hubx.market")
PAYMENTS_WEBHOOK_TOKEN = os.getenv("PAYMENTS_WEBHOOK_TOKEN", "")
PAYMENTS_OBSERVABILITY_TOKEN = os.getenv("PAYMENTS_OBSERVABILITY_TOKEN", "")
PAYMENTS_PROVIDER_DEFAULT = os.getenv("PAYMENTS_PROVIDER_DEFAULT", "pagarme")
PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE = os.getenv("PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE", "sandbox")
PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS = [
    tenant.strip()
    for tenant in os.getenv("PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS", "").split(",")
    if tenant.strip()
]
PAYMENTS_REAL_PROVIDER_FALLBACK_MODE = os.getenv("PAYMENTS_REAL_PROVIDER_FALLBACK_MODE", "lite")
PAGARME_API_BASE_URL = os.getenv("PAGARME_API_BASE_URL", "https://api.pagar.me/core/v5")
PAGARME_SECRET_KEY = os.getenv("PAGARME_SECRET_KEY") or os.getenv("PAGARME_API_KEY", "")
PAGARME_WEBHOOK_SIGNATURE_HEADER = os.getenv("PAGARME_WEBHOOK_SIGNATURE_HEADER", "X-Hub-Signature")
PAGARME_HTTP_TIMEOUT_SECONDS = float(os.getenv("PAGARME_HTTP_TIMEOUT_SECONDS", "15"))
HUBX_MARKET_RESERVED_SUBDOMAINS = [
    subdomain
    for subdomain in os.getenv(
        "HUBX_MARKET_RESERVED_SUBDOMAINS",
        "www,app,api,docs,cdn,admin",
    ).split(",")
    if subdomain
]
