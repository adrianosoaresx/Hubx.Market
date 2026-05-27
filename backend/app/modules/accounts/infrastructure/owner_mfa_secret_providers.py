from __future__ import annotations

import importlib
import os
from dataclasses import dataclass

from django.conf import settings


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaSecretProviderResult:
    result: str
    secret: str
    ready: bool
    provider: str
    reference: str


@dataclass
class OwnerMfaSecretProviderRegistry:
    vault_kms_providers: tuple[str, ...] = (
        "hashicorp-vault",
        "aws-secrets-manager",
        "aws-kms",
        "gcp-secret-manager",
        "azure-key-vault",
    )
    sdk_provider_imports: dict[str, tuple[str, ...]] = None

    def __post_init__(self):
        if self.sdk_provider_imports is None:
            self.sdk_provider_imports = {
                "hashicorp-vault": ("hvac",),
                "aws-secrets-manager": ("boto3",),
                "gcp-secret-manager": ("google.cloud.secretmanager",),
                "azure-key-vault": ("azure.identity", "azure.keyvault.secrets"),
            }

    def resolve(self, reference: object) -> OwnerMfaSecretProviderResult:
        normalized_reference = _string(reference)
        provider = self._provider()
        if not normalized_reference:
            return OwnerMfaSecretProviderResult(
                result="owner-mfa-secret-reference-missing",
                secret="",
                ready=False,
                provider=provider,
                reference="",
            )
        if provider == "env":
            env_name = self._env_name(normalized_reference)
            secret = _string(os.environ.get(env_name, ""))
            return OwnerMfaSecretProviderResult(
                result="owner-mfa-secret-provider-env-ready" if secret else "owner-mfa-secret-provider-env-missing",
                secret=secret,
                ready=bool(secret),
                provider=provider,
                reference=normalized_reference,
            )
        if provider in self.vault_kms_providers:
            return self._resolve_vault_kms(provider=provider, reference=normalized_reference)
        return OwnerMfaSecretProviderResult(
            result="owner-mfa-secret-provider-unavailable",
            secret="",
            ready=False,
            provider=provider,
            reference=normalized_reference,
        )

    def _provider(self) -> str:
        return _string(getattr(settings, "OWNER_MFA_SECRET_PROVIDER", "none"), limit=32).lower() or "none"

    def _resolve_vault_kms(self, *, provider: str, reference: str) -> OwnerMfaSecretProviderResult:
        if self._invalid_reference(reference):
            return OwnerMfaSecretProviderResult(
                result="owner-mfa-secret-provider-vault-invalid-reference",
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        if bool(getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED", False)):
            return self._resolve_vault_kms_real_adapter(provider=provider, reference=reference)
        status = _string(getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS", "unavailable"), limit=32).lower()
        if status in {"timeout", "permission-denied", "unavailable"}:
            return OwnerMfaSecretProviderResult(
                result=f"owner-mfa-secret-provider-vault-{status}",
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        namespace = _string(getattr(settings, "OWNER_MFA_SECRET_NAMESPACE", ""), limit=120).strip("/")
        lookup_reference = f"{namespace}/{reference}" if namespace else reference
        secrets = getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS", {}) or {}
        secret = _string(secrets.get(lookup_reference, ""))
        return OwnerMfaSecretProviderResult(
            result="owner-mfa-secret-provider-vault-ready" if secret else "owner-mfa-secret-provider-vault-missing",
            secret=secret,
            ready=bool(secret),
            provider=provider,
            reference=reference,
        )

    def _resolve_vault_kms_real_adapter(self, *, provider: str, reference: str) -> OwnerMfaSecretProviderResult:
        if bool(getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED", False)):
            return self._resolve_vault_kms_sdk_adapter(provider=provider, reference=reference)
        status = _string(getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS", "unavailable"), limit=32).lower()
        if status in {"timeout", "permission-denied", "unavailable"}:
            return OwnerMfaSecretProviderResult(
                result=f"owner-mfa-secret-provider-vault-{status}",
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        namespace = _string(getattr(settings, "OWNER_MFA_SECRET_NAMESPACE", ""), limit=120).strip("/")
        lookup_reference = f"{namespace}/{reference}" if namespace else reference
        secrets = getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS", {}) or {}
        secret = _string(secrets.get(lookup_reference, ""))
        return OwnerMfaSecretProviderResult(
            result="owner-mfa-secret-provider-vault-ready" if secret else "owner-mfa-secret-provider-vault-missing",
            secret=secret,
            ready=bool(secret),
            provider=provider,
            reference=reference,
        )

    def _resolve_vault_kms_sdk_adapter(self, *, provider: str, reference: str) -> OwnerMfaSecretProviderResult:
        if provider == "hashicorp-vault" and bool(getattr(settings, "OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED", False)):
            return self._resolve_hashicorp_vault_endpoint(provider=provider, reference=reference)
        status = _string(getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS", "unavailable"), limit=32).lower()
        if status in {"timeout", "permission-denied", "unavailable"}:
            return OwnerMfaSecretProviderResult(
                result=f"owner-mfa-secret-provider-vault-{status}",
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        if not self._sdk_imports_ready(provider=provider):
            return OwnerMfaSecretProviderResult(
                result="owner-mfa-secret-provider-vault-unavailable",
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        namespace = _string(getattr(settings, "OWNER_MFA_SECRET_NAMESPACE", ""), limit=120).strip("/")
        lookup_reference = f"{namespace}/{reference}" if namespace else reference
        secrets = getattr(settings, "OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS", {}) or {}
        secret = _string(secrets.get(lookup_reference, ""))
        return OwnerMfaSecretProviderResult(
            result="owner-mfa-secret-provider-vault-ready" if secret else "owner-mfa-secret-provider-vault-missing",
            secret=secret,
            ready=bool(secret),
            provider=provider,
            reference=reference,
        )

    def _resolve_hashicorp_vault_endpoint(self, *, provider: str, reference: str) -> OwnerMfaSecretProviderResult:
        hvac = self._import_sdk_module(provider=provider)
        if hvac is None:
            return OwnerMfaSecretProviderResult(
                result="owner-mfa-secret-provider-vault-unavailable",
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        address = _string(getattr(settings, "OWNER_MFA_HASHICORP_VAULT_ADDR", ""), limit=255)
        mount = _string(getattr(settings, "OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT", "secret"), limit=120).strip("/")
        field = _string(getattr(settings, "OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD", "totp_secret"), limit=120)
        auth_method = _string(getattr(settings, "OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD", "token"), limit=32).lower()
        if not address or not mount or not field or auth_method not in {"token", "approle"}:
            return OwnerMfaSecretProviderResult(
                result="owner-mfa-secret-provider-vault-unavailable",
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        try:
            client = self._hashicorp_vault_client(hvac=hvac, address=address, auth_method=auth_method)
            response = client.secrets.kv.v2.read_secret_version(path=reference, mount_point=mount)
        except TimeoutError:
            return OwnerMfaSecretProviderResult(
                result="owner-mfa-secret-provider-vault-timeout",
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        except PermissionError:
            return OwnerMfaSecretProviderResult(
                result="owner-mfa-secret-provider-vault-permission-denied",
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        except Exception as exc:
            mapped = self._map_hashicorp_vault_exception(exc)
            return OwnerMfaSecretProviderResult(
                result=mapped,
                secret="",
                ready=False,
                provider=provider,
                reference=reference,
            )
        data = response.get("data", {}).get("data", {}) if isinstance(response, dict) else {}
        secret = _string(data.get(field, ""))
        return OwnerMfaSecretProviderResult(
            result="owner-mfa-secret-provider-vault-ready" if secret else "owner-mfa-secret-provider-vault-missing",
            secret=secret,
            ready=bool(secret),
            provider=provider,
            reference=reference,
        )

    def _hashicorp_vault_client(self, *, hvac: object, address: str, auth_method: str) -> object:
        timeout = float(getattr(settings, "OWNER_MFA_SECRET_TIMEOUT_MS", 1500)) / 1000
        if auth_method == "approle":
            client = hvac.Client(url=address, timeout=timeout)
            role_id = _string(getattr(settings, "OWNER_MFA_HASHICORP_VAULT_ROLE_ID", ""), limit=255)
            secret_id = _string(getattr(settings, "OWNER_MFA_HASHICORP_VAULT_SECRET_ID", ""), limit=255)
            if not role_id or not secret_id:
                raise PermissionError("vault approle credentials missing")
            client.auth.approle.login(role_id=role_id, secret_id=secret_id)
            return client
        token = _string(getattr(settings, "OWNER_MFA_HASHICORP_VAULT_TOKEN", ""), limit=255)
        if not token:
            raise PermissionError("vault token missing")
        return hvac.Client(url=address, token=token, timeout=timeout)

    def _map_hashicorp_vault_exception(self, exc: Exception) -> str:
        name = exc.__class__.__name__.lower()
        message = str(exc).lower()
        if "timeout" in name or "timeout" in message:
            return "owner-mfa-secret-provider-vault-timeout"
        if "forbidden" in name or "unauthorized" in name or "permission" in name or "permission" in message:
            return "owner-mfa-secret-provider-vault-permission-denied"
        if "invalidpath" in name or "not found" in message or "missing" in message:
            return "owner-mfa-secret-provider-vault-missing"
        return "owner-mfa-secret-provider-vault-unavailable"

    def _import_sdk_module(self, *, provider: str) -> object | None:
        modules = self.sdk_provider_imports.get(provider, ())
        if not modules:
            return None
        try:
            return importlib.import_module(modules[0])
        except ImportError:
            return None

    def _sdk_imports_ready(self, *, provider: str) -> bool:
        modules = self.sdk_provider_imports.get(provider, ())
        if not modules:
            return False
        try:
            for module in modules:
                importlib.import_module(module)
        except ImportError:
            return False
        return True

    def _invalid_reference(self, reference: str) -> bool:
        return (
            not reference
            or reference.startswith(("/", "\\"))
            or "://" in reference
            or any(part == ".." for part in reference.replace("\\", "/").split("/"))
        )

    def _env_name(self, reference: str) -> str:
        prefix = _string(getattr(settings, "OWNER_MFA_SECRET_ENV_PREFIX", "OWNER_MFA_SECRET_"), limit=64)
        safe_reference = "".join(char if char.isalnum() else "_" for char in reference.upper())
        return f"{prefix}{safe_reference}"


owner_mfa_secret_providers = OwnerMfaSecretProviderRegistry()
