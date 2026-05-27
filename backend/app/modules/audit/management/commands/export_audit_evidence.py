from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.audit.application.audit_evidence_export_queries import audit_evidence_export_queries


class Command(BaseCommand):
    help = "Exporta evidências de AuditLog em formato JSONL ou CSV."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Tenant alvo da exportação.")
        parser.add_argument("--platform-scope", action="store_true", help="Exporta apenas eventos platform-scope.")
        parser.add_argument("--module", dest="module", default="", help="Filtra por módulo.")
        parser.add_argument("--action", dest="action", default="", help="Filtra por ação.")
        parser.add_argument("--since", dest="since", default="", help="Data/hora inicial ISO-8601.")
        parser.add_argument("--until", dest="until", default="", help="Data/hora final ISO-8601.")
        parser.add_argument("--limit", dest="limit", type=int, default=500, help="Limite de linhas, máximo 5000.")
        parser.add_argument("--format", dest="output_format", choices=["jsonl", "csv"], default="jsonl")
        parser.add_argument("--include-metadata", action="store_true", help="Inclui metadata no JSONL.")
        parser.add_argument("--fail-on-empty", action="store_true", help="Retorna erro quando não houver linhas.")

    def handle(self, *args, **options):
        result = audit_evidence_export_queries.export(
            tenant_id=str(options.get("tenant_id") or "").strip(),
            allow_platform_scope=bool(options.get("platform_scope")),
            module=options.get("module") or "",
            action=options.get("action") or "",
            since=options.get("since") or "",
            until=options.get("until") or "",
            limit=int(options.get("limit") or 500),
            output_format=options.get("output_format") or "jsonl",
            include_metadata=bool(options.get("include_metadata")),
        )
        if result["result"] != "audit-evidence-exported":
            raise CommandError(result["errors"])
        if options.get("fail_on_empty") and result["count"] == 0:
            raise CommandError("Audit evidence export is empty.")
        content = str(result["content"])
        if content:
            self.stdout.write(content)
