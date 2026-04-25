from django.core.management.base import BaseCommand, CommandError

from app.modules.checkout.application.checkout_session_retention_commands import checkout_session_retention_commands


class Command(BaseCommand):
    help = "Expira sessões abertas antigas de checkout de forma tenant-scoped."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument(
            "--older-than-hours",
            dest="older_than_hours",
            type=int,
            default=24,
            help="Expira sessões abertas sem atualização além desta janela. Mínimo: 6 horas.",
        )
        parser.add_argument("--limit", dest="limit", type=int, default=250)
        parser.add_argument("--dry-run", dest="dry_run", action="store_true")

    def handle(self, *args, **options):
        tenant_id = str(options["tenant_id"] or "").strip()
        older_than_hours = int(options.get("older_than_hours") or 24)
        limit = min(max(1, int(options.get("limit") or 250)), 1000)
        dry_run = bool(options.get("dry_run"))
        if not tenant_id:
            raise CommandError("--tenant-id é obrigatório.")
        if older_than_hours < 6:
            raise CommandError("--older-than-hours precisa ser >= 6 para evitar expiração agressiva.")
        summary = checkout_session_retention_commands.expire_stale_open_sessions(
            tenant_id=tenant_id,
            older_than_hours=older_than_hours,
            limit=limit,
            dry_run=dry_run,
        )
        prefix = "Dry-run: " if summary.dry_run else ""
        self.stdout.write(
            self.style.WARNING(
                f"{prefix}checkout_session_expiration candidates={summary.candidates}; "
                f"expired={summary.expired}; tenant_id={summary.tenant_id}; "
                f"older_than_hours={summary.older_than_hours}; limit={summary.limit}"
            )
        )
