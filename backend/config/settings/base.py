from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BASE_DIR.parent

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-key")
DEBUG = os.getenv("DEBUG", "1") == "1"


def _allowed_hosts_from_env(raw_value: str, *, debug: bool) -> list[str]:
    hosts = [host.strip() for host in raw_value.split(",") if host.strip()]
    if not hosts:
        return ["*"] if debug else ["localhost"]
    if debug and "*" not in hosts:
        for local_host in (".localhost", "localhost", "127.0.0.1"):
            if local_host not in hosts:
                hosts.append(local_host)
    return hosts


def _list_from_env(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


ALLOWED_HOSTS = _allowed_hosts_from_env(os.getenv("ALLOWED_HOSTS", ""), debug=DEBUG)

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
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "app.modules.tenants.interfaces.middleware.TenantSubdomainMiddleware",
    "app.modules.tenants.interfaces.middleware.DemoTenantReadOnlyMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "app.modules.accounts.interfaces.middleware.OwnerContextMiddleware",
    "app.modules.accounts.interfaces.middleware.PlatformOwnerContextMiddleware",
    "app.modules.accounts.interfaces.middleware.OpsAuthenticationGateMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

HUBX_OPS_AUTH_GATE_ENFORCED = os.environ.get("HUBX_OPS_AUTH_GATE_ENFORCED", "0") == "1"
OWNER_LOGIN_RATE_LIMIT_MAX_ATTEMPTS = int(os.environ.get("OWNER_LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
OWNER_LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("OWNER_LOGIN_RATE_LIMIT_WINDOW_SECONDS", "900"))
OWNER_LOGIN_RATE_LIMIT_LOCKOUT_SECONDS = int(os.environ.get("OWNER_LOGIN_RATE_LIMIT_LOCKOUT_SECONDS", "900"))
OWNER_MFA_REQUIRED = os.environ.get("OWNER_MFA_REQUIRED", "0") == "1"
OWNER_MFA_CHALLENGE_PENDING_SECONDS = int(os.environ.get("OWNER_MFA_CHALLENGE_PENDING_SECONDS", "300"))
OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET = os.environ.get("OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET", "0") == "1"
OWNER_MFA_SECRET_PROVIDER = os.environ.get("OWNER_MFA_SECRET_PROVIDER", "none")
OWNER_MFA_SECRET_ENV_PREFIX = os.environ.get("OWNER_MFA_SECRET_ENV_PREFIX", "OWNER_MFA_SECRET_")
OWNER_MFA_SECRET_TIMEOUT_MS = int(os.environ.get("OWNER_MFA_SECRET_TIMEOUT_MS", "1500"))
OWNER_MFA_SECRET_RETRY_COUNT = int(os.environ.get("OWNER_MFA_SECRET_RETRY_COUNT", "0"))
OWNER_MFA_SECRET_NAMESPACE = os.environ.get("OWNER_MFA_SECRET_NAMESPACE", "")
OWNER_MFA_SECRET_CACHE_SECONDS = int(os.environ.get("OWNER_MFA_SECRET_CACHE_SECONDS", "0"))
OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS = os.environ.get("OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS", "unavailable")
OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS = {}
OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED = os.environ.get("OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED", "0") == "1"
OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS = os.environ.get("OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS", "unavailable")
OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS = {}
OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED = os.environ.get("OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED", "0") == "1"
OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS = os.environ.get("OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS", "unavailable")
OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS = {}
OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED = os.environ.get("OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED", "0") == "1"
OWNER_MFA_HASHICORP_VAULT_ADDR = os.environ.get("OWNER_MFA_HASHICORP_VAULT_ADDR", "")
OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD = os.environ.get("OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD", "token")
OWNER_MFA_HASHICORP_VAULT_TOKEN = os.environ.get("OWNER_MFA_HASHICORP_VAULT_TOKEN", "")
OWNER_MFA_HASHICORP_VAULT_ROLE_ID = os.environ.get("OWNER_MFA_HASHICORP_VAULT_ROLE_ID", "")
OWNER_MFA_HASHICORP_VAULT_SECRET_ID = os.environ.get("OWNER_MFA_HASHICORP_VAULT_SECRET_ID", "")
OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT = os.environ.get("OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT", "secret")
OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD = os.environ.get("OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD", "totp_secret")
OWNER_MFA_BREAK_GLASS_ENABLED = os.environ.get("OWNER_MFA_BREAK_GLASS_ENABLED", "0") == "1"
OWNER_MFA_BREAK_GLASS_OWNER_EMAILS = tuple(
    email.strip().lower()
    for email in os.environ.get("OWNER_MFA_BREAK_GLASS_OWNER_EMAILS", "").split(",")
    if email.strip()
)
OWNER_SESSION_IDLE_SECONDS = int(os.environ.get("OWNER_SESSION_IDLE_SECONDS", "7200"))
OWNER_SESSION_REMEMBER_SECONDS = int(os.environ.get("OWNER_SESSION_REMEMBER_SECONDS", "43200"))
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "0") == "1"
CSRF_TRUSTED_ORIGINS = _list_from_env(os.environ.get("CSRF_TRUSTED_ORIGINS", ""))
if os.environ.get("SECURE_PROXY_SSL_HEADER", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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
                "app.modules.accounts.interfaces.context_processors.admin_shell_context",
                "app.modules.pages.interfaces.context_processors.storefront_pages_context",
                "app.modules.tenants.interfaces.context_processors.tenant_branding_context",
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
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = "/media/"
MEDIA_ROOT = str(BASE_DIR / "media")
HUBX_SERVE_MEDIA_LOCALLY = os.environ.get("HUBX_SERVE_MEDIA_LOCALLY", "0") == "1"

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
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "")
NOTIFICATIONS_EMAIL_DRY_RUN = os.getenv("NOTIFICATIONS_EMAIL_DRY_RUN", "1") == "1"
NOTIFICATIONS_EMAIL_BATCH_SIZE = int(os.getenv("NOTIFICATIONS_EMAIL_BATCH_SIZE", "25"))

HUBX_MARKET_ROOT_DOMAIN = os.getenv("HUBX_MARKET_ROOT_DOMAIN", "hubx.market")
HUBX_MARKET_PUBLIC_PORT = os.getenv("HUBX_MARKET_PUBLIC_PORT", "")
HUBX_PLATFORM_TENANT_SLUG = os.getenv("HUBX_PLATFORM_TENANT_SLUG", "platform-system")
HUBX_MARKET_DEMO_TENANT_SUBDOMAIN = os.getenv("HUBX_MARKET_DEMO_TENANT_SUBDOMAIN", "hubx-demo")
HUBX_PUBLIC_SIGNUP_ENABLED = os.getenv("HUBX_PUBLIC_SIGNUP_ENABLED", "0") == "1"
HUBX_PUBLIC_SIGNUP_REQUIRE_ACCESS_TOKEN = os.getenv("HUBX_PUBLIC_SIGNUP_REQUIRE_ACCESS_TOKEN", "1") == "1"
HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN = os.getenv("HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN", "")
HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv("HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS", "5"))
HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS", "900"))
PAYMENTS_WEBHOOK_TOKEN = os.getenv("PAYMENTS_WEBHOOK_TOKEN", "")
PAYMENTS_OBSERVABILITY_TOKEN = os.getenv("PAYMENTS_OBSERVABILITY_TOKEN", "")
NOTIFICATIONS_OBSERVABILITY_TOKEN = os.getenv("NOTIFICATIONS_OBSERVABILITY_TOKEN", "")
ACCOUNTS_OBSERVABILITY_TOKEN = os.getenv("ACCOUNTS_OBSERVABILITY_TOKEN", "")
API_KEYS_OBSERVABILITY_TOKEN = os.getenv("API_KEYS_OBSERVABILITY_TOKEN", "")
API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED = os.getenv("API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED", "0") == "1"
API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED = os.getenv("API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED", "0") == "1"
API_KEYS_RATE_LIMIT_DEFAULT_LIMIT = int(os.getenv("API_KEYS_RATE_LIMIT_DEFAULT_LIMIT", "120"))
API_KEYS_RATE_LIMIT_DEFAULT_WINDOW_SECONDS = int(os.getenv("API_KEYS_RATE_LIMIT_DEFAULT_WINDOW_SECONDS", "60"))
API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT = int(
    os.getenv("API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT", str(API_KEYS_RATE_LIMIT_DEFAULT_LIMIT))
)
API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT_WINDOW_SECONDS = int(
    os.getenv(
        "API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT_WINDOW_SECONDS",
        str(API_KEYS_RATE_LIMIT_DEFAULT_WINDOW_SECONDS),
    )
)
API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_RATE_LIMIT = int(
    os.getenv("API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_RATE_LIMIT", str(API_KEYS_RATE_LIMIT_DEFAULT_LIMIT))
)
API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_RATE_LIMIT_WINDOW_SECONDS = int(
    os.getenv(
        "API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_RATE_LIMIT_WINDOW_SECONDS",
        str(API_KEYS_RATE_LIMIT_DEFAULT_WINDOW_SECONDS),
    )
)
PAYMENTS_PROVIDER_DEFAULT = os.getenv("PAYMENTS_PROVIDER_DEFAULT", "asaas")
PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE = os.getenv("PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE", "sandbox")
PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS = [
    tenant.strip()
    for tenant in os.getenv("PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS", "").split(",")
    if tenant.strip()
]
PAYMENTS_REAL_PROVIDER_FALLBACK_MODE = os.getenv("PAYMENTS_REAL_PROVIDER_FALLBACK_MODE", "lite")
ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "").strip()
ASAAS_SANDBOX = os.getenv("ASAAS_SANDBOX", "1").strip().lower() in {"1", "true", "yes", "on"}
ASAAS_BASE_URL = os.getenv(
    "ASAAS_BASE_URL",
    "https://api-sandbox.asaas.com/v3" if ASAAS_SANDBOX else "https://api.asaas.com/v3",
).rstrip("/")
ASAAS_WEBHOOK_TOKEN = os.getenv("ASAAS_WEBHOOK_TOKEN", "")
ASAAS_HTTP_TIMEOUT_SECONDS = float(os.getenv("ASAAS_HTTP_TIMEOUT_SECONDS", "15"))
SUBSCRIPTIONS_BILLING_PROVIDER_DEFAULT = os.getenv("SUBSCRIPTIONS_BILLING_PROVIDER_DEFAULT", "asaas").strip().lower()
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
