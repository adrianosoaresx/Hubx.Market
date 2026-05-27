from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyPartnerActivationSmokeExecutionDecision:
    key: str
    status: str
    summary: str


@dataclass
class ApiKeyPartnerActivationSmokeExecutionQueryService:
    def get_review(
        self,
        *,
        smoke_contract_ready: bool = False,
        partner_reference: str = "",
        tenant_reference: str = "",
        target_environment: str = "",
        list_endpoint_checked: bool = False,
        detail_endpoint_checked: bool = False,
        list_status_expected: bool = False,
        detail_status_expected: bool = False,
        auth_failure_negative_checked: bool = False,
        observability_signal_checked: bool = False,
        rollback_not_required: bool = False,
        evidence_reference: str = "",
        redaction_confirmed: bool = False,
        no_secret_material_recorded: bool = False,
        no_runtime_change_performed: bool = False,
    ) -> dict[str, object]:
        identifiers = {
            "partner_reference": self._sanitize_reference(partner_reference),
            "tenant_reference": self._sanitize_reference(tenant_reference),
            "target_environment": self._sanitize_reference(target_environment),
            "evidence_reference": self._sanitize_reference(evidence_reference),
        }
        signals = {
            "smoke_contract_ready": bool(smoke_contract_ready),
            "partner_reference_present": bool(identifiers["partner_reference"]),
            "tenant_reference_present": bool(identifiers["tenant_reference"]),
            "target_environment_present": bool(identifiers["target_environment"]),
            "list_endpoint_checked": bool(list_endpoint_checked),
            "detail_endpoint_checked": bool(detail_endpoint_checked),
            "list_status_expected": bool(list_status_expected),
            "detail_status_expected": bool(detail_status_expected),
            "auth_failure_negative_checked": bool(auth_failure_negative_checked),
            "observability_signal_checked": bool(observability_signal_checked),
            "rollback_not_required": bool(rollback_not_required),
            "evidence_reference_present": bool(identifiers["evidence_reference"]),
            "redaction_confirmed": bool(redaction_confirmed),
            "no_secret_material_recorded": bool(no_secret_material_recorded),
            "no_runtime_change_performed": bool(no_runtime_change_performed),
        }
        blockers = self._blockers(signals=signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"api-key-partner-activation-smoke-execution-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "api_keys",
            "identifiers": identifiers,
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "executed_checks": self._executed_checks(),
            "blockers": blockers,
            "out_of_scope": self._out_of_scope(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        blockers: list[str] = []
        for key, value in signals.items():
            if not value:
                blockers.append(f"partner-activation-smoke-execution:{key}:missing")
        return tuple(blockers)

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[ApiKeyPartnerActivationSmokeExecutionDecision, ...]:
        return (
            ApiKeyPartnerActivationSmokeExecutionDecision(
                key="contract",
                status="ready" if signals["smoke_contract_ready"] else "blocked",
                summary="execução depende do contrato de smoke aprovado",
            ),
            ApiKeyPartnerActivationSmokeExecutionDecision(
                key="scope",
                status="ready"
                if signals["list_endpoint_checked"] and signals["detail_endpoint_checked"]
                else "blocked",
                summary="smoke cobre apenas listagem e detalhe públicos de catálogo",
            ),
            ApiKeyPartnerActivationSmokeExecutionDecision(
                key="responses",
                status="expected"
                if signals["list_status_expected"] and signals["detail_status_expected"]
                else "blocked",
                summary="status codes observados precisam bater com o contrato do endpoint",
            ),
            ApiKeyPartnerActivationSmokeExecutionDecision(
                key="negative-path",
                status="checked" if signals["auth_failure_negative_checked"] else "blocked",
                summary="caminho negativo de autenticação deve ser exercitado sem credencial real em evidência",
            ),
            ApiKeyPartnerActivationSmokeExecutionDecision(
                key="observability",
                status="checked" if signals["observability_signal_checked"] else "blocked",
                summary="métrica/audit signal do endpoint público deve ser observável após o smoke",
            ),
            ApiKeyPartnerActivationSmokeExecutionDecision(
                key="sensitive-data",
                status="guarded"
                if signals["redaction_confirmed"] and signals["no_secret_material_recorded"]
                else "blocked",
                summary="evidência não pode conter API key, header, hash, token ou segredo",
            ),
            ApiKeyPartnerActivationSmokeExecutionDecision(
                key="classification",
                status=status,
                summary="classificação decide se a execução pode seguir para captura de evidência",
            ),
        )

    def _executed_checks(self) -> tuple[str, ...]:
        return (
            "GET /api/v1/catalog/products/",
            "GET /api/v1/catalog/products/<slug>/",
            "negative auth path without storing credential material",
            "public endpoint metrics/audit signal check",
            "rollback not required confirmation",
        )

    def _out_of_scope(self) -> tuple[str, ...]:
        return (
            "não criar endpoint novo",
            "não alterar quotas, billing ou contrato comercial",
            "não persistir API key, header, hash ou segredo",
            "não executar rollback automaticamente",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "API Key Partner Activation Evidence Capture",
                "API Key Partner Activation Post-Smoke Monitoring",
            )
        return (
            "API Key Partner Activation Smoke Execution Follow-Up",
            "API Key Partner Activation Smoke Contract Review",
        )

    def _sanitize_reference(self, value: str) -> str:
        sanitized = str(value or "").strip()
        forbidden_fragments = ("secret", "token=", "key_hash", "authorization", "x-hubx-api-key", "api_key=", "bearer ")
        lowered = sanitized.lower()
        if any(fragment in lowered for fragment in forbidden_fragments):
            return ""
        return sanitized


api_key_partner_activation_smoke_execution_queries = ApiKeyPartnerActivationSmokeExecutionQueryService()
