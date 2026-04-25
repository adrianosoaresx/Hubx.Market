from django.core.management.base import BaseCommand

from app.modules.checkout.application.checkout_session_issues import CHECKOUT_SESSION_ISSUE_CODES, checkout_session_issues


class Command(BaseCommand):
    help = "Lista problemas operacionais de sessões de checkout por tenant."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--issue", dest="issue", default="", choices=["", *CHECKOUT_SESSION_ISSUE_CODES])
        parser.add_argument("--limit", dest="limit", type=int, default=50)

    def handle(self, *args, **options):
        tenant_id = str(options["tenant_id"] or "").strip()
        issue_filter = str(options.get("issue") or "").strip()
        limit = min(max(1, int(options.get("limit") or 50)), 250)
        issues = checkout_session_issues.list_issues(
            tenant_id=tenant_id,
            issue_code=issue_filter,
            limit=limit,
        )
        for issue in issues:
            self.stdout.write(
                "checkout_session_issue "
                f"tenant_id={issue.tenant_id} "
                f"session_id={issue.session_id} "
                f"session_key={issue.session_key} "
                f"status={issue.status} "
                f"issue={issue.issue_code}"
            )
        self.stdout.write(self.style.SUCCESS(f"checkout_session_issues={len(issues)} limit={limit}"))
