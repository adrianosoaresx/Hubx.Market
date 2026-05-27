from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.audit.application.audit_evidence_closure_queries import audit_evidence_closure_queries


class Command(BaseCommand):
    help = "Fecha a trilha de exportação de evidências de auditoria."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Tenant usado para validar closure.")
        parser.add_argument("--platform-scope", action="store_true", help="Valida closure com amostra platform-scope.")
        parser.add_argument("--fail-on-blockers", action="store_true", help="Retorna erro quando closure estiver bloqueado.")

    def handle(self, *args, **options):
        closure = audit_evidence_closure_queries.get_closure(
            tenant_id=str(options.get("tenant_id") or "").strip(),
            allow_platform_scope=bool(options.get("platform_scope")),
        )
        status = str(closure["status"]).upper()
        blockers = ",".join(closure["blockers"]) if closure["blockers"] else "none"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] tenant_id={closure['tenant_id'] or 'none'} platform_scope={str(closure['platform_scope']).lower()} "
                f"sample_count={closure['sample_count']} blockers={blockers}"
            )
        )
        for decision in closure["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for risk in closure["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for track in closure["next_tracks"]:
            self.stdout.write(f"next_track={track}")

        if options.get("fail_on_blockers") and not closure["ready"]:
            raise CommandError("Audit evidence closure is blocked.")
