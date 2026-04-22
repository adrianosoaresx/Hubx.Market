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

    def get_by_slug(self, customer_slug: str, *, tenant_id: int | None = None):
        if not self.is_ready():
            return None
        try:
            queryset = self.customer_model._default_manager.filter(slug=customer_slug)
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            return queryset.first()
        except Exception:
            return None

    @staticmethod
    def save(customer: object, *, update_fields: list[str]) -> None:
        customer.save(update_fields=update_fields)


@dataclass
class AdminCustomerCommandService:
    repository: DjangoOrmCustomerCommandRepository

    def mark_for_followup(self, *, customer_slug: str, tenant_id: int | None = None) -> tuple[object | None, str]:
        return self._mark_flag(
            customer_slug=customer_slug,
            tenant_id=tenant_id,
            field_name="marked_for_followup",
            success_result="customer-followup-marked",
            unchanged_result="customer-followup-already-marked",
        )

    def clear_followup(self, *, customer_slug: str, tenant_id: int | None = None) -> tuple[object | None, str]:
        return self._clear_flag(
            customer_slug=customer_slug,
            tenant_id=tenant_id,
            field_name="marked_for_followup",
            success_result="customer-followup-cleared",
            unchanged_result="customer-followup-already-clear",
        )

    def mark_for_reengagement(self, *, customer_slug: str, tenant_id: int | None = None) -> tuple[object | None, str]:
        return self._mark_flag(
            customer_slug=customer_slug,
            tenant_id=tenant_id,
            field_name="marked_for_reengagement",
            success_result="customer-reengagement-marked",
            unchanged_result="customer-reengagement-already-marked",
        )

    def clear_reengagement(self, *, customer_slug: str, tenant_id: int | None = None) -> tuple[object | None, str]:
        return self._clear_flag(
            customer_slug=customer_slug,
            tenant_id=tenant_id,
            field_name="marked_for_reengagement",
            success_result="customer-reengagement-cleared",
            unchanged_result="customer-reengagement-already-clear",
        )

    def mark_priority(self, *, customer_slug: str, tenant_id: int | None = None) -> tuple[object | None, str]:
        return self._mark_flag(
            customer_slug=customer_slug,
            tenant_id=tenant_id,
            field_name="marked_as_priority",
            success_result="customer-priority-marked",
            unchanged_result="customer-priority-already-marked",
        )

    def clear_priority(self, *, customer_slug: str, tenant_id: int | None = None) -> tuple[object | None, str]:
        return self._clear_flag(
            customer_slug=customer_slug,
            tenant_id=tenant_id,
            field_name="marked_as_priority",
            success_result="customer-priority-cleared",
            unchanged_result="customer-priority-already-clear",
        )

    def bulk_mark_for_followup(self, *, customer_slugs: list[str], tenant_id: int | None = None) -> tuple[int, str]:
        return self._bulk_mark_flag(
            customer_slugs=customer_slugs,
            tenant_id=tenant_id,
            field_name="marked_for_followup",
            success_result="customer-bulk-followup-marked",
            unchanged_result="customer-bulk-followup-unchanged",
        )

    def bulk_clear_followup(self, *, customer_slugs: list[str], tenant_id: int | None = None) -> tuple[int, str]:
        return self._bulk_clear_flag(
            customer_slugs=customer_slugs,
            tenant_id=tenant_id,
            field_name="marked_for_followup",
            success_result="customer-bulk-followup-cleared",
            unchanged_result="customer-bulk-followup-already-clear",
        )

    def bulk_mark_priority(self, *, customer_slugs: list[str], tenant_id: int | None = None) -> tuple[int, str]:
        return self._bulk_mark_flag(
            customer_slugs=customer_slugs,
            tenant_id=tenant_id,
            field_name="marked_as_priority",
            success_result="customer-bulk-priority-marked",
            unchanged_result="customer-bulk-priority-unchanged",
        )

    def bulk_mark_reengagement(self, *, customer_slugs: list[str], tenant_id: int | None = None) -> tuple[int, str]:
        return self._bulk_mark_flag(
            customer_slugs=customer_slugs,
            tenant_id=tenant_id,
            field_name="marked_for_reengagement",
            success_result="customer-bulk-reengagement-marked",
            unchanged_result="customer-bulk-reengagement-unchanged",
        )

    def bulk_clear_priority(self, *, customer_slugs: list[str], tenant_id: int | None = None) -> tuple[int, str]:
        return self._bulk_clear_flag(
            customer_slugs=customer_slugs,
            tenant_id=tenant_id,
            field_name="marked_as_priority",
            success_result="customer-bulk-priority-cleared",
            unchanged_result="customer-bulk-priority-already-clear",
        )

    def bulk_clear_reengagement(self, *, customer_slugs: list[str], tenant_id: int | None = None) -> tuple[int, str]:
        return self._bulk_clear_flag(
            customer_slugs=customer_slugs,
            tenant_id=tenant_id,
            field_name="marked_for_reengagement",
            success_result="customer-bulk-reengagement-cleared",
            unchanged_result="customer-bulk-reengagement-already-clear",
        )

    def _mark_flag(
        self,
        *,
        customer_slug: str,
        tenant_id: int | None,
        field_name: str,
        success_result: str,
        unchanged_result: str,
    ) -> tuple[object | None, str]:
        customer = self.repository.get_by_slug(customer_slug, tenant_id=tenant_id)
        if customer is None:
            return None, "customer-not-found"
        if bool(getattr(customer, field_name, False)):
            return customer, unchanged_result
        setattr(customer, field_name, True)
        self.repository.save(customer, update_fields=[field_name, "updated_at"])
        return customer, success_result

    def _clear_flag(
        self,
        *,
        customer_slug: str,
        tenant_id: int | None,
        field_name: str,
        success_result: str,
        unchanged_result: str,
    ) -> tuple[object | None, str]:
        customer = self.repository.get_by_slug(customer_slug, tenant_id=tenant_id)
        if customer is None:
            return None, "customer-not-found"
        if not bool(getattr(customer, field_name, False)):
            return customer, unchanged_result
        setattr(customer, field_name, False)
        self.repository.save(customer, update_fields=[field_name, "updated_at"])
        return customer, success_result

    def _bulk_mark_flag(
        self,
        *,
        customer_slugs: list[str],
        tenant_id: int | None,
        field_name: str,
        success_result: str,
        unchanged_result: str,
    ) -> tuple[int, str]:
        affected_count = 0
        for customer_slug in customer_slugs:
            customer = self.repository.get_by_slug(customer_slug, tenant_id=tenant_id)
            if customer is None or bool(getattr(customer, field_name, False)):
                continue
            setattr(customer, field_name, True)
            self.repository.save(customer, update_fields=[field_name, "updated_at"])
            affected_count += 1
        return affected_count, success_result if affected_count else unchanged_result

    def _bulk_clear_flag(
        self,
        *,
        customer_slugs: list[str],
        tenant_id: int | None,
        field_name: str,
        success_result: str,
        unchanged_result: str,
    ) -> tuple[int, str]:
        affected_count = 0
        for customer_slug in customer_slugs:
            customer = self.repository.get_by_slug(customer_slug, tenant_id=tenant_id)
            if customer is None or not bool(getattr(customer, field_name, False)):
                continue
            setattr(customer, field_name, False)
            self.repository.save(customer, update_fields=[field_name, "updated_at"])
            affected_count += 1
        return affected_count, success_result if affected_count else unchanged_result


admin_customer_commands = AdminCustomerCommandService(
    repository=DjangoOrmCustomerCommandRepository(),
)
