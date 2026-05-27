from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_provider_health_queries import owner_mfa_provider_health_queries
from app.modules.accounts.models import OwnerMfaFactor


def _label(value: object) -> str:
    return str(value or "").strip().replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


@dataclass
class OwnerMfaProviderHealthMetricsQueryService:
    def export_prometheus_metrics(self) -> str:
        lines = [
            "# HELP hubx_accounts_owner_mfa_provider_health_status Estado do provider externo de segredo TOTP MFA owner/admin por tenant.",
            "# TYPE hubx_accounts_owner_mfa_provider_health_status gauge",
            "# HELP hubx_accounts_owner_mfa_provider_external_reference_total Total de referências externas TOTP MFA por tenant e estado.",
            "# TYPE hubx_accounts_owner_mfa_provider_external_reference_total gauge",
            "# HELP hubx_accounts_owner_mfa_secret_storage_total Total de fatores TOTP MFA por modo de storage.",
            "# TYPE hubx_accounts_owner_mfa_secret_storage_total gauge",
            "# HELP hubx_accounts_owner_mfa_provider_signal_total Sinais operacionais do provider TOTP MFA por tenant.",
            "# TYPE hubx_accounts_owner_mfa_provider_signal_total gauge",
        ]
        for tenant_id in self._tenant_ids_with_totp():
            health = owner_mfa_provider_health_queries.get_health(tenant_id=tenant_id)
            provider = _label(health["provider"])
            status = _label(health["status"])
            lines.append(f'hubx_accounts_owner_mfa_provider_health_status{{tenant_id="{tenant_id}",provider="{provider}",status="{status}"}} 1')
            lines.append(
                f'hubx_accounts_owner_mfa_provider_external_reference_total{{tenant_id="{tenant_id}",provider="{provider}",state="resolved"}} '
                f'{int(health["external_reference_count"]) - int(health["external_reference_unresolved_count"])}'
            )
            lines.append(
                f'hubx_accounts_owner_mfa_provider_external_reference_total{{tenant_id="{tenant_id}",provider="{provider}",state="unresolved"}} '
                f'{int(health["external_reference_unresolved_count"])}'
            )
            lines.append(
                f'hubx_accounts_owner_mfa_secret_storage_total{{tenant_id="{tenant_id}",storage_mode="external-reference"}} '
                f'{int(health["external_reference_count"])}'
            )
            lines.append(
                f'hubx_accounts_owner_mfa_secret_storage_total{{tenant_id="{tenant_id}",storage_mode="local-plain"}} '
                f'{int(health["local_plain_count"])}'
            )
            lines.append(
                f'hubx_accounts_owner_mfa_secret_storage_total{{tenant_id="{tenant_id}",storage_mode="missing"}} {int(health["missing_count"])}'
            )
            for signal in health["signals"]:
                lines.append(
                    f'hubx_accounts_owner_mfa_provider_signal_total{{tenant_id="{tenant_id}",provider="{provider}",signal="{_label(signal)}"}} 1'
                )
        return "\n".join(lines) + "\n"

    def _tenant_ids_with_totp(self) -> tuple[int, ...]:
        try:
            return tuple(
                OwnerMfaFactor.objects.filter(
                    factor_type=OwnerMfaFactor.FactorType.TOTP,
                    is_active=True,
                )
                .values_list("tenant_id", flat=True)
                .distinct()
                .order_by("tenant_id")
            )
        except Exception:
            return ()


owner_mfa_provider_health_metrics_queries = OwnerMfaProviderHealthMetricsQueryService()
