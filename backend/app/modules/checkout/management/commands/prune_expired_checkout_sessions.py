from django.core.management.base import BaseCommand, CommandError

from app.modules.checkout.application.checkout_session_retention_commands import checkout_session_retention_commands


class Command(BaseCommand):
    help = "Remove sessões expiradas antigas de checkout de forma tenant-scoped e conservadora."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument(
            "--older-than-days",
            dest="older_than_days",
            type=int,
            default=180,
            help="Remove sessões expiradas atualizadas antes desta janela. Mínimo: 180 dias.",
        )
        parser.add_argument("--limit", dest="limit", type=int, default=250)
        parser.add_argument("--dry-run", dest="dry_run", action="store_true")

    def handle(self, *args, **options):
        tenant_id = str(options["tenant_id"] or "").strip()
        older_than_days = int(options.get("older_than_days") or 180)
        limit = min(max(1, int(options.get("limit") or 250)), 1000)
        dry_run = bool(options.get("dry_run"))
        if not tenant_id:
            raise CommandError("--tenant-id é obrigatório.")
        if older_than_days < 180:
            raise CommandError("--older-than-days precisa ser >= 180 para preservar rastreabilidade operacional.")
        summary = checkout_session_retention_commands.prune_expired_sessions(
            tenant_id=tenant_id,
            older_than_days=older_than_days,
            limit=limit,
            dry_run=dry_run,
        )
        prefix = "Dry-run: " if summary.dry_run else ""
        self.stdout.write(
            self.style.WARNING(
                f"{prefix}checkout_expired_session_pruning candidates={summary.candidates}; "
                f"deleted={summary.deleted}; tenant_id={summary.tenant_id}; "
                f"older_than_days={summary.older_than_days}; limit={summary.limit}"
            )
        )
