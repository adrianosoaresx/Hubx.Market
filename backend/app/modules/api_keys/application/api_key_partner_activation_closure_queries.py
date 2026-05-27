from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPartnerActivationClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPartnerActivationClosureQueryService:
    def get_review(
        self,
        *,
        smoke_contract_ready: bool = False,
        smoke_execution_ready: bool = False,
        evidence_capture_ready: bool = False,
        post_smoke_monitoring_ready: bool = False,
        partner_handoff_closed: bool = False,
        support_handoff_closed: bool = False,
        rollback_window_closed: bool = False,
        no_sensitive_material_retained: bool = False,
        no_runtime_change_pending: bool = False,
        commercial_quota_track_selected: bool = False,
        docs_updated: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "smoke_contract_ready": bool(smoke_contract_ready),
            "smoke_execution_ready": bool(smoke_execution_ready),
            "evidence_capture_ready": bool(evidence_capture_ready),
            "post_smoke_monitoring_ready": bool(post_smoke_monitoring_ready),
            "partner_handoff_closed": bool(partner_handoff_closed),
            "support_handoff_closed": bool(support_handoff_closed),
            "rollback_window_closed": bool(rollback_window_closed),
            "no_sensitive_material_retained": bool(no_sensitive_material_retained),
            "no_runtime_change_pending": bool(no_runtime_change_pending),
            "commercial_quota_track_selected": bool(commercial_quota_track_selected),
            "docs_updated": bool(docs_updated),
            "decision_recorded": bool(decision_recorded),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-partner-activation-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "closure_scope": self._closure_scope(),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        return tuple(
            f"partner-activation-closure:{key}:missing"
            for key, value in signals.items()
            if not value
        )

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPartnerActivationClosureDecision, ...]:
        return (
            ApiKeyPartnerActivationClosureDecision(
                key="battery-a",
                status="complete"
                if signals["smoke_contract_ready"]
                and signals["smoke_execution_ready"]
                and signals["evidence_capture_ready"]
                and signals["post_smoke_monitoring_ready"]
                else "blocked",
                summary="todas as ondas operacionais da Battery A precisam estar prontas",
            ),
            ApiKeyPartnerActivationClosureDecision(
                key="handoff",
                status="closed"
                if signals["partner_handoff_closed"] and signals["support_handoff_closed"]
                else "blocked",
                summary="handoffs de parceiro e suporte precisam estar encerrados",
            ),
            ApiKeyPartnerActivationClosureDecision(
                key="risk",
                status="closed"
                if signals["rollback_window_closed"]
                and signals["no_sensitive_material_retained"]
                and signals["no_runtime_change_pending"]
                else "blocked",
                summary="risco residual fecha sem rollback pendente, segredo retido ou mudança runtime pendente",
            ),
            ApiKeyPartnerActivationClosureDecision(
                key="next-roi",
                status="selected" if signals["commercial_quota_track_selected"] else "blocked",
                summary="próximo ROI natural segue para quotas comerciais de API key",
            ),
            ApiKeyPartnerActivationClosureDecision(
                key="classification",
                status=status,
                summary="classificação encerra ou bloqueia a bateria de ativação de parceiro",
            ),
        )

    def _closure_scope(self) -> tuple[str, ...]:
        return (
            "smoke contract",
            "smoke execution",
            "sanitized evidence capture",
            "post-smoke monitoring",
            "partner/support handoff closure",
            "commercial quota track selection",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Commercial Quotas Contract Review",
                "System ROI Re-Selection Review",
            )
        return (
            "API Key Partner Activation Closure Follow-Up",
            "API Key Partner Activation Post-Smoke Monitoring",
        )


api_key_partner_activation_closure_queries = ApiKeyPartnerActivationClosureQueryService()
