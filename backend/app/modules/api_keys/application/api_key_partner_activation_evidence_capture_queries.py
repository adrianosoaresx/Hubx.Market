from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPartnerActivationEvidenceCaptureDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPartnerActivationEvidenceCaptureQueryService:
    def get_review(
        self,
        *,
        smoke_execution_ready: bool = False,
        evidence_reference: str = "",
        list_result_attached: bool = False,
        detail_result_attached: bool = False,
        negative_auth_result_attached: bool = False,
        metrics_snapshot_attached: bool = False,
        audit_log_reference_attached: bool = False,
        partner_handoff_reference_attached: bool = False,
        support_handoff_reference_attached: bool = False,
        redaction_confirmed: bool = False,
        no_secret_material_recorded: bool = False,
        rollback_note_attached: bool = False,
    ) -> dict[str, object]:
        safe_reference = self._sanitize_reference(evidence_reference)
        signals = {
            "smoke_execution_ready": bool(smoke_execution_ready),
            "evidence_reference_present": bool(safe_reference),
            "list_result_attached": bool(list_result_attached),
            "detail_result_attached": bool(detail_result_attached),
            "negative_auth_result_attached": bool(negative_auth_result_attached),
            "metrics_snapshot_attached": bool(metrics_snapshot_attached),
            "audit_log_reference_attached": bool(audit_log_reference_attached),
            "partner_handoff_reference_attached": bool(partner_handoff_reference_attached),
            "support_handoff_reference_attached": bool(support_handoff_reference_attached),
            "redaction_confirmed": bool(redaction_confirmed),
            "no_secret_material_recorded": bool(no_secret_material_recorded),
            "rollback_note_attached": bool(rollback_note_attached),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-partner-activation-evidence-capture-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "evidence_reference": safe_reference,
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "evidence_items": self._evidence_items(),
            "blockers": blockers,
            "out_of_scope": self._out_of_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        return tuple(
            f"partner-activation-evidence-capture:{key}:missing"
            for key, value in signals.items()
            if not value
        )

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPartnerActivationEvidenceCaptureDecision, ...]:
        return (
            ApiKeyPartnerActivationEvidenceCaptureDecision(
                key="execution",
                status="ready" if signals["smoke_execution_ready"] else "blocked",
                summary="captura depende de smoke executado e classificado como ready",
            ),
            ApiKeyPartnerActivationEvidenceCaptureDecision(
                key="coverage",
                status="complete"
                if signals["list_result_attached"]
                and signals["detail_result_attached"]
                and signals["negative_auth_result_attached"]
                else "blocked",
                summary="evidência cobre listagem, detalhe e caminho negativo de autenticação",
            ),
            ApiKeyPartnerActivationEvidenceCaptureDecision(
                key="observability",
                status="attached"
                if signals["metrics_snapshot_attached"] and signals["audit_log_reference_attached"]
                else "blocked",
                summary="snapshot de métricas e referência auditável acompanham a evidência",
            ),
            ApiKeyPartnerActivationEvidenceCaptureDecision(
                key="handoff",
                status="attached"
                if signals["partner_handoff_reference_attached"] and signals["support_handoff_reference_attached"]
                else "blocked",
                summary="handoff para parceiro e suporte fica referenciado sem material sensível",
            ),
            ApiKeyPartnerActivationEvidenceCaptureDecision(
                key="sensitive-data",
                status="guarded"
                if signals["redaction_confirmed"] and signals["no_secret_material_recorded"]
                else "blocked",
                summary="evidência capturada permanece sanitizada",
            ),
            ApiKeyPartnerActivationEvidenceCaptureDecision(
                key="classification",
                status=status,
                summary="classificação decide se a ativação pode entrar em monitoramento pós-smoke",
            ),
        )

    def _evidence_items(self) -> tuple[str, ...]:
        return (
            "sanitized list endpoint result",
            "sanitized detail endpoint result",
            "sanitized negative auth result",
            "public endpoint metrics snapshot",
            "audit log reference",
            "partner/support handoff references",
            "rollback note",
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não anexar credenciais ou headers",
            "não anexar payload com segredo ou hash",
            "não validar SLA comercial",
            "não abrir novo endpoint público",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Partner Activation Post-Smoke Monitoring",
                "API Key Partner Activation Closure Review",
            )
        return (
            "API Key Partner Activation Evidence Capture Follow-Up",
            "API Key Partner Activation Smoke Execution",
        )

    def _sanitize_reference(self, value: str) -> str:
        sanitized = str(value or "").strip()
        forbidden_fragments = ("secret", "token=", "key_hash", "authorization", "x-hubx-api-key", "api_key=", "bearer ")
        lowered = sanitized.lower()
        if any(fragment in lowered for fragment in forbidden_fragments):
            return ""
        return sanitized


api_key_partner_activation_evidence_capture_queries = ApiKeyPartnerActivationEvidenceCaptureQueryService()
