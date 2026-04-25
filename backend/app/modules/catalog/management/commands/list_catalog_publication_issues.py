from django.core.management.base import BaseCommand

from app.modules.catalog.application.catalog_publication_issues import catalog_publication_issues


class Command(BaseCommand):
    help = "Lista problemas operacionais de publicação do catálogo por tenant."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument(
            "--issue",
            dest="issue",
            default="",
            choices=[
                "",
                "status_mismatch",
                "missing_variant",
                "missing_default_variant",
                "missing_price",
                "stock_unavailable",
            ],
        )
        parser.add_argument("--limit", dest="limit", type=int, default=50)

    def handle(self, *args, **options):
        tenant_id = str(options["tenant_id"] or "").strip()
        issue_filter = str(options.get("issue") or "").strip()
        limit = min(max(1, int(options.get("limit") or 50)), 250)
        issues = catalog_publication_issues.list_issues(
            tenant_id=tenant_id,
            issue_code=issue_filter,
            limit=limit,
        )
        for issue in issues:
            self.stdout.write(
                "catalog_publication_issue "
                f"tenant_id={issue.tenant_id} "
                f"product_id={issue.product_id} "
                f"slug={issue.slug} "
                f"status={issue.status} "
                f"is_active={str(issue.is_active).lower()} "
                f"issue={issue.issue_code}"
            )
        self.stdout.write(self.style.SUCCESS(f"catalog_publication_issues={len(issues)} limit={limit}"))
