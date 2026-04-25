from django.core.management.base import BaseCommand

from app.modules.customers.application.customer_data_issues import customer_data_issues


class Command(BaseCommand):
    help = "Lista problemas operacionais de dados de clientes por tenant."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument(
            "--issue",
            dest="issue",
            default="",
            choices=[
                "",
                "missing_name",
                "missing_email",
                "duplicate_email_case",
                "missing_address",
                "missing_default_address",
                "incomplete_default_address",
                "order_email_fallback",
            ],
        )
        parser.add_argument("--limit", dest="limit", type=int, default=50)

    def handle(self, *args, **options):
        tenant_id = str(options["tenant_id"] or "").strip()
        issue_filter = str(options.get("issue") or "").strip()
        limit = min(max(1, int(options.get("limit") or 50)), 250)
        issues = customer_data_issues.list_issues(
            tenant_id=tenant_id,
            issue_code=issue_filter,
            limit=limit,
        )
        for issue in issues:
            self.stdout.write(
                "customer_data_issue "
                f"tenant_id={issue.tenant_id} "
                f"customer_id={issue.customer_id} "
                f"slug={issue.slug} "
                f"email={issue.email} "
                f"issue={issue.issue_code}"
            )
        self.stdout.write(self.style.SUCCESS(f"customer_data_issues={len(issues)} limit={limit}"))
