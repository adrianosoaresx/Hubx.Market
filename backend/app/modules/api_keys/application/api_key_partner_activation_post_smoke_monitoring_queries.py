from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPartnerActivationPostSmokeMonitoringDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPartnerActivationPostSmokeMonitoringQueryService:
    def get_review(
        self,
        *,
        evidence_capture_ready: bool = False,
        monitoring_window_observed: bool = False,
        partner_access_stable: bool = False,
        auth_failure_rate_expected: bool = False,
        rate_limit_noise_expected: bool = False,
        endpoint_error_rate_expected: bool = False,
        support_ticket_status_recorded: bool = False,
        rollback_not_required: bool = False,
        no_sensitive_data_observed: bool = False,
        commercial_quota_pressure_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "evidence_capture_ready": bool(evidence_capture_ready),
            "monitoring_window_observed": bool(monitoring_window_observed),
            "partner_access_stable": bool(partner_access_stable),
            "auth_failure_rate_expected": bool(auth_failure_rate_expected),
            "rate_limit_noise_expected": bool(rate_limit_noise_expected),
            "endpoint_error_rate_expected": bool(endpoint_error_rate_expected),
            "support_ticket_status_recorded": bool(support_ticket_status_recorded),
            "rollback_not_required": bool(rollback_not_required),
            "no_sensitive_data_observed": bool(no_sensitive_data_observed),
            "commercial_quota_pressure_recorded": bool(commercial_quota_pressure_recorded),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-partner-activation-post-smoke-monitoring-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "monitoring_checks": self._monitoring_checks(),
            "blockers": blockers,
            "out_of_scope": self._out_of_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        return tuple(
            f"partner-activation-post-smoke-monitoring:{key}:missing"
            for key, value in signals.items()
            if not value
        )

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPartnerActivationPostSmokeMonitoringDecision, ...]:
        return (
            ApiKeyPartnerActivationPostSmokeMonitoringDecision(
                key="evidence",
                status="ready" if signals["evidence_capture_ready"] else "blocked",
                summary="monitoramento pós-smoke depende de evidência sanitizada pronta",
            ),
            ApiKeyPartnerActivationPostSmokeMonitoringDecision(
                key="stability",
                status="stable"
                if signals["monitoring_window_observed"] and signals["partner_access_stable"]
                else "blocked",
                summary="janela inicial precisa mostrar acesso estável do parceiro",
            ),
            ApiKeyPartnerActivationPostSmokeMonitoringDecision(
                key="traffic-health",
                status="expected"
                if signals["auth_failure_rate_expected"]
                and signals["rate_limit_noise_expected"]
                and signals["endpoint_error_rate_expected"]
                else "blocked",
                summary="falhas de auth, rate limit e erro de endpoint precisam ficar dentro do esperado",
            ),
            ApiKeyPartnerActivationPostSmokeMonitoringDecision(
                key="operations",
                status="recorded"
                if signals["support_ticket_status_recorded"] and signals["rollback_not_required"]
                else "blocked",
                summary="suporte registra status e confirma que rollback não é necessário",
            ),
            ApiKeyPartnerActivationPostSmokeMonitoringDecision(
                key="next-roi",
                status="recorded" if signals["commercial_quota_pressure_recorded"] else "blocked",
                summary="pressão por quota comercial fica registrada para priorização posterior",
            ),
            ApiKeyPartnerActivationPostSmokeMonitoringDecision(
                key="classification",
                status=status,
                summary="classificação decide se a ativação de parceiro pode ser encerrada",
            ),
        )

    def _monitoring_checks(self) -> tuple[str, ...]:
        return (
            "observar janela inicial definida para o parceiro",
            "comparar auth failures e rate limit com baseline do smoke",
            "verificar erro 5xx/4xx inesperado no endpoint público",
            "confirmar ticket de suporte e handoff do parceiro",
            "registrar pressão por quota/billing sem implementar quota nesta bateria",
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não ajustar thresholds nesta etapa",
            "não criar quotas comerciais",
            "não alterar billing",
            "não armazenar segredo em evidência operacional",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Partner Activation Closure Review",
                "API Key Commercial Quotas Contract Review",
            )
        return (
            "API Key Partner Activation Post-Smoke Monitoring Follow-Up",
            "API Key Partner Activation Evidence Capture",
        )


api_key_partner_activation_post_smoke_monitoring_queries = (
    ApiKeyPartnerActivationPostSmokeMonitoringQueryService()
)
