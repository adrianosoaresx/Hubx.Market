from __future__ import annotations

from dataclasses import dataclass

from django.db import connection


class DjangoOrmCustomerCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.customers import models as customer_models
        except Exception:
            self.customer_model = None
            return
        self.customer_model = getattr(customer_models, "Customer", None)

    def is_ready(self) -> bool:
        if self.customer_model is None:
            return False
        try:
            table_name = self.customer_model._meta.db_table
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return table_name in set(tables)

    def get_by_slug(self, customer_slug: str):
        if not self.is_ready():
            return None
        try:
            return self.customer_model._default_manager.filter(slug=customer_slug).first()
        except Exception:
            return None

    @staticmethod
    def save(customer: object, *, update_fields: list[str]) -> None:
        customer.save(update_fields=update_fields)


@dataclass
class AdminCustomerCommandService:
    repository: DjangoOrmCustomerCommandRepository

    def mark_for_followup(self, *, customer_slug: str) -> tuple[object | None, str]:
        return self._mark_flag(
            customer_slug=customer_slug,
            field_name="marked_for_followup",
            success_result="customer-followup-marked",
            unchanged_result="customer-followup-already-marked",
        )

    def mark_for_reengagement(self, *, customer_slug: str) -> tuple[object | None, str]:
        return self._mark_flag(
            customer_slug=customer_slug,
            field_name="marked_for_reengagement",
            success_result="customer-reengagement-marked",
            unchanged_result="customer-reengagement-already-marked",
        )

    def mark_priority(self, *, customer_slug: str) -> tuple[object | None, str]:
        return self._mark_flag(
            customer_slug=customer_slug,
            field_name="marked_as_priority",
            success_result="customer-priority-marked",
            unchanged_result="customer-priority-already-marked",
        )

    def _mark_flag(
        self,
        *,
        customer_slug: str,
        field_name: str,
        success_result: str,
        unchanged_result: str,
    ) -> tuple[object | None, str]:
        customer = self.repository.get_by_slug(customer_slug)
        if customer is None:
            return None, "customer-not-found"
        if bool(getattr(customer, field_name, False)):
            return customer, unchanged_result
        setattr(customer, field_name, True)
        self.repository.save(customer, update_fields=[field_name, "updated_at"])
        return customer, success_result


admin_customer_commands = AdminCustomerCommandService(
    repository=DjangoOrmCustomerCommandRepository(),
)
