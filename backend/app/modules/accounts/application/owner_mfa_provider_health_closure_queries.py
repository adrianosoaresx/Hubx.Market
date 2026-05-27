from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.modules.accounts.application.owner_mfa_provider_health_queries import owner_mfa_provider_health_queries


@dataclass(frozen=True)
class OwnerMfaProviderHealthClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaProviderHealthClosureQueryService:
    dashboard_path: Path = Path(__file__).resolve().parents[5] / "infra" / "observability" / "grafana" / "accounts-owner-mfa-provider-health-dashboard.json"
    scrape_path: Path = Path(__file__).resolve().parents[5] / "infra" / "observability" / "prometheus" / "accounts-scrape.example.yml"
    alerts_path: Path = Path(__file__).resolve().parents[5] / "infra" / "observability" / "prometheus" / "accounts-alert-rules.yml"

    def get_closure(self, *, tenant_id: int | str | None) -> dict[str, object]:
        health = owner_mfa_provider_health_queries.get_health(tenant_id=tenant_id)
        artifacts = self._artifacts()
        decisions = self._decisions(health=health, artifacts=artifacts)
        blockers = []
        if health["status"] == "CRITICAL":
            blockers.extend(f"health:{signal}" for signal in health["signals"])
        for name, present in artifacts.items():
            if not present:
                blockers.append(f"artifact-missing:{name}")
        status = "ready"
        if health["status"] == "WATCH":
            status = "watch"
        if blockers:
            status = "blocked"
        return {
            "result": f"owner-mfa-provider-health-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": str(tenant_id or "").strip(),
            "provider_health": health,
            "artifacts": artifacts,
            "decisions": decisions,
            "blockers": tuple(blockers),
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(),
        }

    def _artifacts(self) -> dict[str, bool]:
        return {
            "prometheus-scrape": self.scrape_path.exists(),
            "prometheus-alert-rules": self.alerts_path.exists(),
            "grafana-dashboard": self.dashboard_path.exists(),
        }

    def _decisions(
        self,
        *,
        health: dict[str, object],
        artifacts: dict[str, bool],
    ) -> tuple[OwnerMfaProviderHealthClosureDecision, ...]:
        return (
            OwnerMfaProviderHealthClosureDecision(
                key="provider-health",
                status=str(health["status"]).lower(),
                summary="provider TOTP MFA é classificado por tenant como HEALTHY, WATCH ou CRITICAL",
            ),
            OwnerMfaProviderHealthClosureDecision(
                key="prometheus-metrics",
                status="ready" if artifacts["prometheus-scrape"] and artifacts["prometheus-alert-rules"] else "blocked",
                summary="endpoint, scrape example e alert rules iniciais existem para provider health",
            ),
            OwnerMfaProviderHealthClosureDecision(
                key="grafana-dashboard",
                status="ready" if artifacts["grafana-dashboard"] else "blocked",
                summary="dashboard Grafana inicial acompanha status, refs, storage e sinais ativos",
            ),
            OwnerMfaProviderHealthClosureDecision(
                key="secret-exposure",
                status="guarded",
                summary="métricas/dashboard não incluem owner, factor, segredo ou reference path completo",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "scrape e dashboard ainda precisam ser ativados no Prometheus/Grafana real",
            "provider env é adapter mínimo; vault/KMS real continua evolução posterior",
            "dashboard não faz drill-down por owner/factor para preservar cardinalidade e sigilo",
            "rollback do setting OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET permanece ação operacional manual",
        )

    def _next_tracks(self) -> tuple[str, ...]:
        return (
            "Owner MFA Local Secret Code Retirement Review",
            "Owner MFA Vault/KMS Provider Review",
            "Owner MFA Incident Runbook Review",
        )


owner_mfa_provider_health_closure_queries = OwnerMfaProviderHealthClosureQueryService()
