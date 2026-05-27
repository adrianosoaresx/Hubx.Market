from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_quota_commands import api_key_quota_commands


class Command(BaseCommand):
    help = "Cria ou atualiza quota comercial mínima tenant-scoped para uma API key."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", required=True)
        parser.add_argument("--api-key-id", required=True)
        parser.add_argument("--endpoint", required=True)
        parser.add_argument("--limit", default=10000)
        parser.add_argument("--window-seconds", default=86400)
        parser.add_argument("--scope", default="read:catalog")
        parser.add_argument("--status", default="active")
        parser.add_argument("--actor-label", default="")
        parser.add_argument("--fail-on-error", action="store_true")

    def handle(self, *args, **options):
        result = api_key_quota_commands.upsert_quota(
            tenant_id=options["tenant_id"],
            api_key_id=options["api_key_id"],
            endpoint=options["endpoint"],
            limit=options["limit"],
            window_seconds=options["window_seconds"],
            scope=options["scope"],
            status=options["status"],
            actor_label=options["actor_label"],
        )
        self.stdout.write(f"result={result['result']}")
        if "quota" in result:
            quota = result["quota"]
            self.stdout.write(
                "quota "
                f"id={quota['id']} tenant_id={quota['tenant_id']} api_key_id={quota['api_key_id']} "
                f"endpoint={quota['endpoint']} limit={quota['limit']} window_seconds={quota['window_seconds']} "
                f"status={quota['status']}"
            )
        if options["fail_on_error"] and not str(result["result"]).endswith(("created", "updated")):
            raise CommandError("API key quota upsert failed.")
