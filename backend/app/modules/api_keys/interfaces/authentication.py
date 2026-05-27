from __future__ import annotations

from dataclasses import dataclass

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission

from app.modules.api_keys.application.api_key_public_endpoint_metrics import api_key_public_endpoint_metrics
from app.modules.api_keys.application.api_key_runtime_authentication import api_key_runtime_authentication


def _string(value: object, *, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _authorization_header(request) -> str:
    return _string(getattr(request, "headers", {}).get("Authorization", ""), limit=512)


def _request_id(request) -> str:
    return _string(getattr(request, "headers", {}).get("X-Request-ID", ""), limit=120)


def _ip_address(request) -> str | None:
    value = _string(getattr(request, "META", {}).get("REMOTE_ADDR", ""), limit=64)
    return value or None


@dataclass(frozen=True)
class ApiKeyPrincipal:
    tenant_id: int | str
    api_key_id: int | str
    prefix: str
    scopes: tuple[str, ...]

    @property
    def is_authenticated(self) -> bool:
        return True


class ApiKeyAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        authorization_header = _authorization_header(request)
        if not authorization_header:
            return None
        scheme = authorization_header.partition(" ")[0].lower()
        if scheme != self.keyword.lower():
            return None

        tenant_id = getattr(getattr(request, "tenant", None), "id", None)
        result = api_key_runtime_authentication.authenticate(
            tenant_id=tenant_id,
            authorization_header=authorization_header,
            request_id=_request_id(request),
            ip_address=_ip_address(request),
        )
        setattr(request, "api_key_authentication_result", result)
        if not result.get("authenticated"):
            api_key_public_endpoint_metrics.record_auth_failure(
                tenant_id=tenant_id or "",
                endpoint=getattr(request, "path", ""),
                reason=result.get("result", "api-key-auth-failed"),
            )
            raise exceptions.AuthenticationFailed("Credencial de API key inválida.")

        api_key = result.get("api_key") or {}
        principal = ApiKeyPrincipal(
            tenant_id=api_key.get("tenant_id"),
            api_key_id=api_key.get("id"),
            prefix=_string(api_key.get("prefix"), limit=24),
            scopes=tuple(api_key.get("scopes") or ()),
        )
        auth = {
            "api_key_id": principal.api_key_id,
            "tenant_id": principal.tenant_id,
            "prefix": principal.prefix,
            "scopes": principal.scopes,
            "rate_limit_key": result.get("rate_limit_key"),
        }
        setattr(request, "api_key_principal", principal)
        setattr(request, "api_key_auth", auth)
        return principal, auth

    def authenticate_header(self, request):
        return self.keyword


class HasApiKeyScope(BasePermission):
    message = "API key sem escopo suficiente."

    def has_permission(self, request, view) -> bool:
        required_scope = _string(getattr(view, "required_api_key_scope", ""), limit=80)
        if not required_scope:
            return False
        auth = getattr(request, "auth", None) or {}
        scopes = set(auth.get("scopes") or ())
        return required_scope in scopes
