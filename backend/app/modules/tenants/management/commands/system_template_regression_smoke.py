from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test import Client, override_settings

from app.modules.tenants.application.system_template_regression_smoke import system_template_regression_smoke


class Command(BaseCommand):
    help = "Executa smoke de templates e links críticos de storefront/admin."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="hubx-demo.hubx.market")
        parser.add_argument("--owner-email", default="")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        client = Client()
        owner_email = str(options["owner_email"] or "").strip()
        if owner_email:
            user = get_user_model().objects.filter(email=owner_email).first()
            if not user:
                raise CommandError("Owner user not found for smoke authentication.")
            client.force_login(user)

        host = str(options["host"])
        allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
        if host not in allowed_hosts:
            allowed_hosts.append(host)
        with override_settings(ALLOWED_HOSTS=allowed_hosts):
            payload = system_template_regression_smoke.run(client=client, host=host)
        self.stdout.write(
            f"[{str(payload['status']).upper()}] result={payload['result']} module={payload['module']} host={payload['host']}"
        )
        for result in payload["results"]:
            self.stdout.write(
                f"target key={result.key} path={result.path} status={result.status_code} ready={result.ready}"
            )
            for marker in result.missing_markers:
                self.stdout.write(f"missing key={result.key} marker={marker}")
            for marker in result.forbidden_markers_found:
                self.stdout.write(f"forbidden key={result.key} marker={marker}")
        for blocker in payload["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in payload["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not payload["ready"]:
            raise CommandError("System template regression smoke is blocked.")
