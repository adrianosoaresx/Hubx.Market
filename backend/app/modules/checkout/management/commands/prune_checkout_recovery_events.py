from django.core.management.base import BaseCommand, CommandError

from app.modules.checkout.application.checkout_recovery_event_retention_commands import checkout_recovery_event_retention_commands


class Command(BaseCommand):
    help = "Remove eventos antigos de recovery do checkout de forma tenant-scoped e conservadora."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument(
            "--older-than-days",
            dest="older_than_days",
            type=int,
            default=180,
            help="Remove eventos criados antes desta janela. Mínimo: 180 dias.",
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
            raise CommandError("--older-than-days precisa ser >= 180 para preservar analytics recentes.")
        summary = checkout_recovery_event_retention_commands.prune_events(
            tenant_id=tenant_id,
            older_than_days=older_than_days,
            limit=limit,
            dry_run=dry_run,
        )
        prefix = "Dry-run: " if summary.dry_run else ""
        self.stdout.write(
            self.style.WARNING(
                f"{prefix}checkout_recovery_event_pruning candidates={summary.candidates}; "
                f"deleted={summary.deleted}; tenant_id={summary.tenant_id}; "
                f"older_than_days={summary.older_than_days}; limit={summary.limit}"
            )
        )
