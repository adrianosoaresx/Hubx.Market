from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_vault_kms_rotation_closure_queries import (
    owner_mfa_vault_kms_rotation_closure_queries,
)


MONITORING_FLAG_NAMES = (
    "canary-monitoring-window-elapsed",
    "canary-provider-health-stable",
    "canary-owner-login-error-spike-absent",
    "canary-support-incidents-absent",
    "canary-rollback-signal-absent",
    "canary-evidence-redacted",
    "rollback-runbook-confirmed",
    "residual-risks-accepted",
    "tenant-expansion-plan-documented",
    "expansion-window-confirmed",
    "per-tenant-evidence-required",
    "support-standby-confirmed",
    "rollback-window-confirmed",
    "target-flags-enabled",
    "target-activation-evidence-captured",
    "target-monitoring-scheduled",
    "target-owner-login-challenge-passed",
    "target-provider-health-ready",
    "rollback-not-required",
    "expansion-evidence-redacted",
    "target-monitoring-window-elapsed",
    "target-provider-health-stable",
    "target-owner-login-error-spike-absent",
    "target-support-incidents-absent",
    "target-rollback-signal-absent",
    "evidence-redacted",
    "next-window-confirmed",
    "operator-capacity-confirmed",
    "previous-target-evidence-archived",
    "stop-after-current-target",
    "cadence-decision-recorded",
    "evidence-archive-complete",
    "residual-risks-reviewed",
    "rotation-runbook-queued",
    "audit-evidence-ready",
    "rotation-scope-documented",
    "rotation-owner-confirmed",
    "vault-access-validated",
    "rotation-window-confirmed",
    "rollback-credentials-available",
    "post-rotation-probe-defined",
    "affected-tenants-listed",
    "evidence-redaction-confirmed",
    "rotation-executed",
    "new-credential-active",
    "old-credential-revoked-or-scheduled",
    "post-rotation-probe-passed",
    "owner-login-challenge-passed",
    "provider-health-ready",
    "rotation-rollback-not-required",
    "rotation-evidence-redacted",
    "post-rotation-window-elapsed",
    "provider-health-stable",
    "owner-login-error-spike-absent",
    "support-incidents-absent",
    "rollback-signal-absent",
    "post-rotation-evidence-redacted",
)

CLOSURE_FLAG_NAMES = (
    "rotation-closure-decision-recorded",
    "rotation-evidence-archived",
    "closure-residual-risks-accepted",
    "expansion-resume-plan-documented",
    "rollback-window-closed-or-extended",
    "closure-audit-evidence-ready",
)


class Command(BaseCommand):
    help = "Fecha a rotação Vault/KMS MFA owner/admin após monitoramento pós-rotação."

    def add_arguments(self, parser):
        parser.add_argument("--canary-tenant-id", dest="canary_tenant_id", required=True)
        parser.add_argument("--current-target-tenant-id", dest="current_target_tenant_id", required=True)
        parser.add_argument("--next-target-tenant-ids", dest="next_target_tenant_ids", default="")
        parser.add_argument("--probe-reference", dest="probe_reference", default="owners/vault-kms/hashicorp-vault-probe")
        parser.add_argument("--canary-owner-email", dest="canary_owner_email", required=True)
        for name in MONITORING_FLAG_NAMES + CLOSURE_FLAG_NAMES:
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--max-parallel-tenants", type=int, default=1)
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        closure = owner_mfa_vault_kms_rotation_closure_queries.get_closure(
            canary_tenant_id=options["canary_tenant_id"],
            current_target_tenant_id=options["current_target_tenant_id"],
            next_target_tenant_ids=options["next_target_tenant_ids"],
            probe_reference=options["probe_reference"],
            canary_owner_email=options["canary_owner_email"],
            max_parallel_tenants=options["max_parallel_tenants"],
            **{name.replace("-", "_"): options[name.replace("-", "_")] for name in MONITORING_FLAG_NAMES},
            rotation_closure_decision_recorded=options["rotation_closure_decision_recorded"],
            rotation_evidence_archived=options["rotation_evidence_archived"],
            closure_residual_risks_accepted=options["closure_residual_risks_accepted"],
            expansion_resume_plan_documented=options["expansion_resume_plan_documented"],
            rollback_window_closed_or_extended=options["rollback_window_closed_or_extended"],
            closure_audit_evidence_ready=options["closure_audit_evidence_ready"],
        )
        self.stdout.write(
            f"[{str(closure['status']).upper()}] result={closure['result']} "
            f"canary_tenant_id={closure['canary_tenant_id']} current_target_tenant_id={closure['current_target_tenant_id']} "
            f"target_provider={closure['target_provider']}"
        )
        for key, value in closure["closure_signals"].items():
            self.stdout.write(f"closure_signal key={key} value={value}")
        for decision in closure["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in closure["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for risk in closure["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for guardrail in closure["resume_guardrails"]:
            self.stdout.write(f"resume_guardrail={guardrail}")
        for track in closure["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not closure["ready"]:
            raise CommandError("Owner MFA Vault/KMS rotation closure is not ready.")
