from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse


def _string(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class ReadinessCheck:
    label: str
    status: str
    detail: str


class Command(BaseCommand):
    help = "Valida os bloqueadores mínimos para executar o piloto controlado de pagamento em sandbox."

    def add_arguments(self, parser):
        parser.add_argument(
            "--webhook-url",
            default="",
            help="URL pública esperada para o webhook do provider, se já estiver disponível.",
        )
        parser.add_argument(
            "--target",
            choices=["sandbox", "production"],
            default="sandbox",
            help="Perfil de readiness esperado para sandbox ou produção.",
        )

    def handle(self, *args, **options):
        target = _string(options.get("target")) or "sandbox"
        checks = self._build_checks(webhook_url=_string(options.get("webhook_url")), target=target)
        blocked_checks = [check for check in checks if check.status == "BLOCKED"]

        for check in checks:
            style = self.style.SUCCESS if check.status == "OK" else self.style.WARNING
            self.stdout.write(style(f"[{check.status}] {check.label}: {check.detail}"))

        summary = (
            f"payment_{target}_readiness={ 'blocked' if blocked_checks else 'ready' } "
            f"blocked={len(blocked_checks)} total={len(checks)}"
        )
        if blocked_checks:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))

    def _build_checks(self, *, webhook_url: str, target: str = "sandbox") -> list[ReadinessCheck]:
        provider_default = _string(getattr(settings, "PAYMENTS_PROVIDER_DEFAULT", ""))
        rollout_mode = _string(getattr(settings, "PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE", ""))
        enabled_tenants = list(getattr(settings, "PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS", []) or [])
        fallback_mode = _string(getattr(settings, "PAYMENTS_REAL_PROVIDER_FALLBACK_MODE", ""))
        live_global_enabled = bool(getattr(settings, "PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED", False))
        asaas_api_key = _string(getattr(settings, "ASAAS_API_KEY", ""))
        asaas_api_base_url = _string(getattr(settings, "ASAAS_BASE_URL", ""))
        asaas_webhook_token = _string(getattr(settings, "ASAAS_WEBHOOK_TOKEN", ""))
        pagarme_secret_key = _string(getattr(settings, "PAGARME_SECRET_KEY", ""))
        pagarme_api_base_url = _string(getattr(settings, "PAGARME_API_BASE_URL", ""))
        signature_header = _string(getattr(settings, "PAGARME_WEBHOOK_SIGNATURE_HEADER", ""))
        fallback_token = _string(getattr(settings, "PAYMENTS_WEBHOOK_TOKEN", ""))
        webhook_path = reverse("payments:webhook")
        supported_provider = provider_default in {"asaas", "pagarme"}
        provider_secret_ready = bool(asaas_api_key) if provider_default == "asaas" else bool(pagarme_secret_key)
        provider_base_url = asaas_api_base_url if provider_default == "asaas" else pagarme_api_base_url
        provider_secret_label = "Asaas API key" if provider_default == "asaas" else "Pagar.me secret key"
        provider_secret_detail = (
            "Configurada"
            if provider_secret_ready
            else ("Configure ASAAS_API_KEY com a chave de sandbox" if provider_default == "asaas" else "Configure PAGARME_SECRET_KEY com a chave de teste")
        )

        checks = [
            ReadinessCheck(
                label="Provider default",
                status="OK" if supported_provider else "BLOCKED",
                detail=provider_default or "Configure PAYMENTS_PROVIDER_DEFAULT=asaas",
            ),
            ReadinessCheck(
                label="Provider rollout mode",
                status=(
                    "OK"
                    if (
                        target == "sandbox"
                        and rollout_mode.lower() in {"off", "sandbox", "controlled", "live"}
                    )
                    or (
                        target == "production"
                        and rollout_mode.lower() in {"controlled", "live"}
                    )
                    else "BLOCKED"
                ),
                detail=rollout_mode or "Configure PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE",
            ),
            ReadinessCheck(
                label="Enabled rollout tenants",
                status=(
                    "OK"
                    if rollout_mode.lower() != "controlled"
                    or bool(enabled_tenants)
                    else "BLOCKED"
                ),
                detail=", ".join(str(item) for item in enabled_tenants) if enabled_tenants else "Configure PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS para rollout controlado",
            ),
            ReadinessCheck(
                label="Provider fallback mode",
                status=(
                    "OK"
                    if (
                        target == "sandbox"
                        and fallback_mode.lower() in {"lite", "block"}
                    )
                    or (
                        target == "production"
                        and fallback_mode.lower() == "block"
                    )
                    else "BLOCKED"
                ),
                detail=fallback_mode or "Configure PAYMENTS_REAL_PROVIDER_FALLBACK_MODE",
            ),
            ReadinessCheck(
                label="Live global flag",
                status=(
                    "OK"
                    if target == "sandbox"
                    or rollout_mode.lower() != "live"
                    or live_global_enabled
                    else "BLOCKED"
                ),
                detail=(
                    "Habilitada explicitamente"
                    if live_global_enabled
                    else "Obrigatória apenas para PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=live em produção"
                ),
            ),
            ReadinessCheck(
                label=provider_secret_label,
                status="OK" if provider_secret_ready else "BLOCKED",
                detail=provider_secret_detail,
            ),
            ReadinessCheck(
                label="API base URL",
                status="OK" if provider_base_url.startswith("https://") else "BLOCKED",
                detail=provider_base_url or ("Configure ASAAS_BASE_URL" if provider_default == "asaas" else "Configure PAGARME_API_BASE_URL"),
            ),
            ReadinessCheck(
                label="Provider webhook token/header",
                status="OK" if (provider_default == "asaas" and bool(asaas_webhook_token)) or (provider_default != "asaas" and bool(signature_header)) else "BLOCKED",
                detail=(
                    "Configurado"
                    if provider_default == "asaas" and asaas_webhook_token
                    else signature_header
                    if provider_default != "asaas" and signature_header
                    else ("Configure ASAAS_WEBHOOK_TOKEN" if provider_default == "asaas" else "Configure PAGARME_WEBHOOK_SIGNATURE_HEADER")
                ),
            ),
            ReadinessCheck(
                label="Fallback webhook token",
                status="OK" if bool(fallback_token) else "OK",
                detail="Configurado" if fallback_token else "Opcional para payloads genéricos internos",
            ),
            ReadinessCheck(
                label="Webhook route",
                status="OK",
                detail=webhook_path,
            ),
            ReadinessCheck(
                label="Public webhook URL",
                status="OK" if webhook_url.startswith(("http://", "https://")) else "BLOCKED",
                detail=webhook_url or "Passe --webhook-url com a URL pública cadastrável no provider",
            ),
        ]
        return checks
