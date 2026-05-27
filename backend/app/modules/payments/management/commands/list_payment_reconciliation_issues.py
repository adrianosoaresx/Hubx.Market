from django.core.management.base import BaseCommand

from app.modules.payments.application.financial_reconciliation_queries import (
    payment_financial_reconciliation_queries,
)


class Command(BaseCommand):
    help = "Lista divergências financeiras entre PaymentAttempt e Order para triagem operacional."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", type=int, default=0, help="Restringe a auditoria a um tenant.")
        parser.add_argument("--limit", dest="limit", type=int, default=250, help="Número máximo de tentativas auditadas.")

    def handle(self, *args, **options):
        tenant_id = int(options.get("tenant_id") or 0) or None
        limit = min(max(1, int(options.get("limit") or 250)), 1000)
        issues = payment_financial_reconciliation_queries.list_reconciliation_issues(
            tenant_id=tenant_id,
            limit=limit,
        )
        if not issues:
            self.stdout.write("payment_reconciliation_issues=0")
            return

        for issue in issues:
            self.stdout.write(
                "payment_reconciliation_issue "
                f"tenant_id={issue['tenant_id']} "
                f"order_number={issue['order_number']} "
                f"attempt_key={issue['attempt_key']} "
                f"severity={issue['severity']} "
                f"issue_code={issue['issue_code']} "
                f"title=\"{issue['title']}\""
            )
        self.stdout.write(self.style.WARNING(f"payment_reconciliation_issues={len(issues)} limit={limit}"))
