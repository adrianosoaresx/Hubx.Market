from __future__ import annotations

from dataclasses import dataclass, field
import json
from secrets import token_urlsafe
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model, login as django_login
from django.core import signing
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from app.modules.accounts.application.demo_session_login_commands import (
    ACCOUNT_PROFILE_SESSION_KEY,
    ACCOUNT_SESSION_KIND_KEY,
)
from app.modules.accounts.application.owner_login_commands import OWNER_MFA_PENDING_SESSION_KEY
from app.modules.accounts.application.owner_session_policy import (
    OWNER_SESSION_EXPIRES_AT_KEY,
    OWNER_SESSION_KIND_KEY,
    OWNER_SESSION_REMEMBERED_KEY,
)
from app.modules.accounts.models import AccountProfile
from app.modules.customers.models import Customer
from app.modules.tenants.models import Tenant


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_OAUTH_STATE_SALT = "hubx.accounts.google-oauth-state"
GOOGLE_OAUTH_STATE_MAX_AGE_SECONDS = 600
GOOGLE_OAUTH_HTTP_TIMEOUT_SECONDS = 10


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


def _email(value: object) -> str:
    return _string(value, limit=254).lower()


def _boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _username_from_email(email: str) -> str:
    user_model = get_user_model()
    base = slugify(email.split("@", 1)[0]) or "customer"
    username = base[:120]
    if not user_model.objects.filter(username__iexact=username).exists():
        return username
    suffix = 2
    while True:
        candidate = f"{base[:110]}-{suffix}"
        if not user_model.objects.filter(username__iexact=candidate).exists():
            return candidate
        suffix += 1


def _customer_slug_from_email(email: str) -> str:
    base = slugify(email.split("@", 1)[0]) or "cliente"
    return base[:140]


def _unique_customer_slug(*, tenant_id: int, email: str) -> str:
    base = _customer_slug_from_email(email=email)
    candidate = base
    suffix = 2
    while Customer.objects.filter(tenant_id=tenant_id, slug__iexact=candidate).exists():
        candidate = f"{base[:132]}-{suffix}"
        suffix += 1
    return candidate


def _split_name(*, name: str, given_name: str = "", family_name: str = "") -> tuple[str, str]:
    first_name = _string(given_name, limit=120)
    last_name = _string(family_name, limit=120)
    if first_name or last_name:
        return first_name, last_name
    parts = _string(name, limit=240).split()
    if not parts:
        return "", ""
    return parts[0][:120], " ".join(parts[1:])[:120]


@dataclass
class GoogleOAuthHttpClient:
    timeout_seconds: int = GOOGLE_OAUTH_HTTP_TIMEOUT_SECONDS

    def post_form(self, *, url: str, data: dict[str, str]) -> dict[str, object]:
        payload = urlencode(data).encode("utf-8")
        request = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            method="POST",
        )
        return self._json_response(request)

    def get_json(self, *, url: str, bearer_token: str) -> dict[str, object]:
        request = Request(url, headers={"Authorization": f"Bearer {bearer_token}", "Accept": "application/json"})
        return self._json_response(request)

    def _json_response(self, request: Request) -> dict[str, object]:
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise GoogleOAuthProviderError(str(exc)) from exc
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise GoogleOAuthProviderError("Invalid JSON returned by Google OAuth.") from exc
        return payload if isinstance(payload, dict) else {}


class GoogleOAuthProviderError(Exception):
    pass


@dataclass
class GoogleOAuthLoginCommandService:
    http_client: GoogleOAuthHttpClient = field(default_factory=GoogleOAuthHttpClient)

    def build_authorization_url(self, *, request, tenant, next_url: object = "") -> dict[str, object]:
        if not self._is_enabled():
            return {"result": "google-oauth-unavailable"}
        if tenant is None or not getattr(tenant, "is_active", False):
            return {"result": "google-oauth-tenant-required"}

        redirect_uri = self._redirect_uri(request=request)
        state = signing.dumps(
            {
                "tenant_id": tenant.id,
                "next": _string(next_url, limit=500),
                "redirect_uri": redirect_uri,
                "nonce": token_urlsafe(24),
            },
            salt=GOOGLE_OAUTH_STATE_SALT,
        )
        query = urlencode(
            {
                "client_id": self._client_id(),
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
            }
        )
        return {"result": "google-oauth-ready", "authorization_url": f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}"}

    def authenticate_callback(self, *, request, code: object, state: object) -> dict[str, object]:
        if not self._is_enabled():
            return {"result": "google-oauth-unavailable"}
        normalized_code = _string(code, limit=2048)
        if not normalized_code:
            return {"result": "google-oauth-missing-code"}

        state_payload = self._load_state(state=state)
        if not state_payload:
            return {"result": "google-oauth-invalid-state"}

        tenant = Tenant.objects.filter(pk=state_payload.get("tenant_id"), is_active=True).first()
        if tenant is None:
            return {"result": "google-oauth-tenant-invalid"}

        redirect_uri = _string(state_payload.get("redirect_uri"), limit=500) or self._redirect_uri(request=request)
        userinfo = self._exchange_code_for_userinfo(code=normalized_code, redirect_uri=redirect_uri)
        email = _email(userinfo.get("email"))
        if not email:
            return {"result": "google-oauth-email-missing"}
        if not _boolish(userinfo.get("email_verified")):
            return {"result": "google-oauth-email-unverified"}

        profile_result = self._get_or_create_customer_profile(tenant=tenant, userinfo=userinfo, email=email)
        if profile_result.get("result") != "google-oauth-profile-ready":
            return profile_result

        user_result = self._get_or_create_user(email=email, userinfo=userinfo)
        if user_result.get("result") != "google-oauth-user-ready":
            return user_result

        user = user_result["user"]
        profile = profile_result["profile"]
        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session[ACCOUNT_PROFILE_SESSION_KEY] = profile.id
        request.session[ACCOUNT_SESSION_KIND_KEY] = "customer"
        request.session.pop(OWNER_MFA_PENDING_SESSION_KEY, None)
        request.session.pop(OWNER_SESSION_KIND_KEY, None)
        request.session.pop(OWNER_SESSION_REMEMBERED_KEY, None)
        request.session.pop(OWNER_SESSION_EXPIRES_AT_KEY, None)
        now = timezone.now()
        AccountProfile.objects.filter(pk=profile.id).update(last_login_at=now, last_seen_at=now)
        Customer.objects.filter(pk=profile.customer_id).update(last_seen_at=now)
        return {
            "result": "google-oauth-authenticated",
            "profile": profile,
            "tenant": tenant,
            "next_url": _string(state_payload.get("next"), limit=500),
        }

    def _exchange_code_for_userinfo(self, *, code: str, redirect_uri: str) -> dict[str, object]:
        token_payload = self.http_client.post_form(
            url=GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": self._client_id(),
                "client_secret": self._client_secret(),
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        access_token = _string(token_payload.get("access_token"), limit=4096)
        if not access_token:
            raise GoogleOAuthProviderError("Google OAuth did not return an access token.")
        return self.http_client.get_json(url=GOOGLE_USERINFO_ENDPOINT, bearer_token=access_token)

    def _get_or_create_customer_profile(self, *, tenant: Tenant, userinfo: dict[str, object], email: str) -> dict[str, object]:
        with transaction.atomic():
            inactive_profile = AccountProfile.objects.filter(tenant=tenant, email__iexact=email, is_active=False).first()
            if inactive_profile is not None:
                return {"result": "google-oauth-profile-inactive"}

            inactive_customer = Customer.objects.filter(tenant=tenant, email__iexact=email, status=Customer.Status.INACTIVE).first()
            if inactive_customer is not None:
                return {"result": "google-oauth-customer-inactive"}

            name = _string(userinfo.get("name"), limit=150)
            first_name, last_name = _split_name(
                name=name,
                given_name=_string(userinfo.get("given_name"), limit=120),
                family_name=_string(userinfo.get("family_name"), limit=120),
            )
            full_name = name or "Cliente"
            customer = Customer.objects.filter(tenant=tenant, email__iexact=email).first()
            if customer is None:
                customer = Customer.objects.create(
                    tenant=tenant,
                    slug=_unique_customer_slug(tenant_id=tenant.id, email=email),
                    full_name=full_name,
                    email=email,
                    status=Customer.Status.ACTIVE,
                    account_type="Google",
                )
            else:
                update_fields = []
                if not customer.full_name and full_name:
                    customer.full_name = full_name
                    update_fields.append("full_name")
                if customer.account_type != "Google":
                    customer.account_type = "Google"
                    update_fields.append("account_type")
                if update_fields:
                    update_fields.append("updated_at")
                    customer.save(update_fields=update_fields)

            try:
                profile, created = AccountProfile.objects.get_or_create(
                    tenant=tenant,
                    email=email,
                    defaults={
                        "customer": customer,
                        "first_name": first_name,
                        "last_name": last_name,
                        "is_active": True,
                    },
                )
            except IntegrityError:
                profile = AccountProfile.objects.get(tenant=tenant, email__iexact=email)
                created = False

            update_fields = []
            if profile.customer_id is None:
                profile.customer = customer
                update_fields.append("customer")
            if not profile.first_name and first_name:
                profile.first_name = first_name
                update_fields.append("first_name")
            if not profile.last_name and last_name:
                profile.last_name = last_name
                update_fields.append("last_name")
            if not profile.is_active:
                return {"result": "google-oauth-profile-inactive"}
            if update_fields:
                update_fields.append("updated_at")
                profile.save(update_fields=update_fields)
            return {"result": "google-oauth-profile-ready", "profile": profile, "created": created}

    def _get_or_create_user(self, *, email: str, userinfo: dict[str, object]) -> dict[str, object]:
        user_model = get_user_model()
        matches = list(user_model.objects.filter(email__iexact=email).order_by("id")[:2])
        if len(matches) > 1:
            return {"result": "google-oauth-ambiguous-user"}
        if matches:
            user = matches[0]
            if not user.is_active:
                return {"result": "google-oauth-user-inactive"}
            return {"result": "google-oauth-user-ready", "user": user, "created": False}

        first_name, last_name = _split_name(
            name=_string(userinfo.get("name"), limit=240),
            given_name=_string(userinfo.get("given_name"), limit=120),
            family_name=_string(userinfo.get("family_name"), limit=120),
        )
        user = user_model.objects.create_user(
            username=_username_from_email(email),
            email=email,
            password=None,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_unusable_password()
        user.save(update_fields=("password",))
        return {"result": "google-oauth-user-ready", "user": user, "created": True}

    def _load_state(self, *, state: object) -> dict[str, object] | None:
        try:
            payload = signing.loads(
                _string(state, limit=4096),
                salt=GOOGLE_OAUTH_STATE_SALT,
                max_age=GOOGLE_OAUTH_STATE_MAX_AGE_SECONDS,
            )
        except signing.BadSignature:
            return None
        return payload if isinstance(payload, dict) else None

    def _redirect_uri(self, *, request) -> str:
        configured = _string(getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", ""), limit=500)
        if configured:
            return configured
        return request.build_absolute_uri(reverse("accounts:social-login-callback", kwargs={"provider": "google"}))

    def _is_enabled(self) -> bool:
        return bool(getattr(settings, "GOOGLE_OAUTH_ENABLED", False) and self._client_id() and self._client_secret())

    def _client_id(self) -> str:
        return _string(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", ""), limit=500)

    def _client_secret(self) -> str:
        return _string(getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", ""), limit=500)


google_oauth_login_commands = GoogleOAuthLoginCommandService()
