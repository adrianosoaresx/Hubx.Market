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
        secret_key = _string(getattr(settings, "PAGARME_SECRET_KEY", ""))
        api_base_url = _string(getattr(settings, "PAGARME_API_BASE_URL", ""))
        signature_header = _string(getattr(settings, "PAGARME_WEBHOOK_SIGNATURE_HEADER", ""))
        fallback_token = _string(getattr(settings, "PAYMENTS_WEBHOOK_TOKEN", ""))
        webhook_path = reverse("payments:webhook")

        checks = [
            ReadinessCheck(
                label="Provider default",
                status="OK" if provider_default == "pagarme" else "BLOCKED",
                detail=provider_default or "Configure PAYMENTS_PROVIDER_DEFAULT=pagarme",
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
                label="Pagar.me secret key",
                status="OK" if bool(secret_key) else "BLOCKED",
                detail="Configurada" if secret_key else "Configure PAGARME_SECRET_KEY com a chave de teste",
            ),
            ReadinessCheck(
                label="API base URL",
                status="OK" if api_base_url.startswith("https://") else "BLOCKED",
                detail=api_base_url or "Configure PAGARME_API_BASE_URL",
            ),
            ReadinessCheck(
                label="Webhook signature header",
                status="OK" if bool(signature_header) else "BLOCKED",
                detail=signature_header or "Configure PAGARME_WEBHOOK_SIGNATURE_HEADER",
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
