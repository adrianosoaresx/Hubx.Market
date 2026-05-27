from __future__ import annotations

from django.core.management.base import BaseCommand

from app.modules.reviews.application.review_submission_commands import product_review_submission_commands


class Command(BaseCommand):
    help = "Registra uma avaliação de produto como pending, sem publicação automática."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", type=int, required=True, help="Tenant da avaliação.")
        parser.add_argument("--product-id", dest="product_id", type=int, default=None, help="ID do produto.")
        parser.add_argument("--product-slug", dest="product_slug", default="", help="Slug do produto.")
        parser.add_argument("--rating", dest="rating", type=int, required=True, help="Nota de 1 a 5.")
        parser.add_argument("--title", dest="title", default="", help="Título curto da avaliação.")
        parser.add_argument("--body", dest="body", default="", help="Texto da avaliação.")
        parser.add_argument("--author-name", dest="author_name", default="", help="Nome público do autor.")
        parser.add_argument("--customer-id", dest="customer_id", type=int, default=None, help="Customer opcional.")
        parser.add_argument("--source", dest="source", default="internal_cli", help="Origem operacional da submissão.")

    def handle(self, *args, **options):
        result, review = product_review_submission_commands.submit_product_review(
            tenant_id=options["tenant_id"],
            product_id=options.get("product_id"),
            product_slug=options.get("product_slug") or "",
            rating=options["rating"],
            title=options.get("title") or "",
            body=options.get("body") or "",
            author_name=options.get("author_name") or "",
            customer_id=options.get("customer_id"),
            source=options.get("source") or "internal_cli",
        )
        if review is None:
            self.stdout.write(self.style.WARNING(f"product_review_submission={result}"))
            return
        self.stdout.write(
            "product_review_submission "
            f"result={result} "
            f"tenant_id={review.tenant_id} "
            f"product_id={review.product_id} "
            f"review_id={review.id} "
            f"status={review.status} "
            f"rating={review.rating}"
        )
