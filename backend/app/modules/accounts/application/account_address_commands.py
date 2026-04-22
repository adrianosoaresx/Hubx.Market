from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ProfileLookupRepository(Protocol):
    def get_primary_profile(self, *, tenant_id: int | None = None) -> dict[str, object] | None:
        ...


class DjangoOrmAccountAddressCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.accounts import models as account_models
            from app.modules.customers import models as customer_models
        except Exception:
            self.profile_model = None
            self.customer_model = None
            self.address_model = None
            return

        self.profile_model = getattr(account_models, "AccountProfile", None)
        self.customer_model = getattr(customer_models, "Customer", None)
        self.address_model = getattr(customer_models, "CustomerAddress", None)

    def resolve_current_customer(self, *, tenant_id: int | None = None):
        if not all([self.profile_model, self.customer_model]):
            return None
        try:
            queryset = self.profile_model._default_manager.select_related("customer").filter(is_active=True)
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            profile = queryset.order_by("-updated_at", "-id").first()
        except Exception:
            return None
        if profile is None or not getattr(profile, "tenant_id", None):
            return None
        try:
            if getattr(profile, "customer_id", None):
                linked_customer = (
                    self.customer_model._default_manager.filter(tenant_id=profile.tenant_id, pk=profile.customer_id)
                    .prefetch_related("addresses")
                    .first()
                )
                if linked_customer is not None:
                    return linked_customer
            return (
                self.customer_model._default_manager.filter(tenant_id=profile.tenant_id, email=profile.email)
                .prefetch_related("addresses")
                .order_by("-updated_at", "-id")
                .first()
            )
        except Exception:
            return None

    def get_address_for_current_customer(self, address_id: int, *, tenant_id: int | None = None):
        customer = self.resolve_current_customer(tenant_id=tenant_id)
        if customer is None or self.address_model is None:
            return None
        try:
            return customer.addresses.filter(pk=address_id).first()
        except Exception:
            return None

    def create_address(self, cleaned_data: dict[str, object], *, tenant_id: int | None = None):
        customer = self.resolve_current_customer(tenant_id=tenant_id)
        if customer is None or self.address_model is None:
            return None
        self._normalize_defaults(customer=customer, is_default=bool(cleaned_data.get("is_default")))
        return self.address_model._default_manager.create(
            customer=customer,
            label=str(cleaned_data.get("label") or ""),
            recipient_name=str(cleaned_data.get("recipient_name") or ""),
            line_1=str(cleaned_data.get("line_1") or ""),
            line_2=str(cleaned_data.get("line_2") or ""),
            district=str(cleaned_data.get("district") or ""),
            city=str(cleaned_data.get("city") or ""),
            state=str(cleaned_data.get("state") or ""),
            postal_code=str(cleaned_data.get("postal_code") or ""),
            is_default=bool(cleaned_data.get("is_default")),
        )

    def update_address(self, address_id: int, cleaned_data: dict[str, object], *, tenant_id: int | None = None):
        address = self.get_address_for_current_customer(address_id, tenant_id=tenant_id)
        if address is None:
            return None
        self._normalize_defaults(customer=address.customer, is_default=bool(cleaned_data.get("is_default")), exclude_id=address.pk)
        address.label = str(cleaned_data.get("label") or "")
        address.recipient_name = str(cleaned_data.get("recipient_name") or "")
        address.line_1 = str(cleaned_data.get("line_1") or "")
        address.line_2 = str(cleaned_data.get("line_2") or "")
        address.district = str(cleaned_data.get("district") or "")
        address.city = str(cleaned_data.get("city") or "")
        address.state = str(cleaned_data.get("state") or "")
        address.postal_code = str(cleaned_data.get("postal_code") or "")
        address.is_default = bool(cleaned_data.get("is_default"))
        address.save()
        return address

    @staticmethod
    def _normalize_defaults(*, customer, is_default: bool, exclude_id: int | None = None) -> None:
        if not is_default:
            return
        queryset = customer.addresses.all()
        if exclude_id is not None:
            queryset = queryset.exclude(pk=exclude_id)
        queryset.update(is_default=False)


@dataclass
class AccountAddressCommandService:
    repository: DjangoOrmAccountAddressCommandRepository

    @staticmethod
    def _tenant_required(tenant_id: int | None) -> bool:
        return tenant_id is not None

    def get_address_initial(self, address_id: int, *, tenant_id: int | None = None) -> dict[str, object] | None:
        if not self._tenant_required(tenant_id):
            return None
        address = self.repository.get_address_for_current_customer(address_id, tenant_id=tenant_id)
        if address is None:
            return None
        return {
            "label": address.label,
            "recipient_name": address.recipient_name,
            "line_1": address.line_1,
            "line_2": address.line_2,
            "district": address.district,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "is_default": address.is_default,
        }

    def create_address(self, cleaned_data: dict[str, object], *, tenant_id: int | None = None):
        if not self._tenant_required(tenant_id):
            return None
        return self.repository.create_address(cleaned_data, tenant_id=tenant_id)

    def update_address(self, address_id: int, cleaned_data: dict[str, object], *, tenant_id: int | None = None):
        if not self._tenant_required(tenant_id):
            return None
        return self.repository.update_address(address_id, cleaned_data, tenant_id=tenant_id)

    def get_address_summary(self, address_id: int, *, tenant_id: int | None = None) -> dict[str, object] | None:
        if not self._tenant_required(tenant_id):
            return None
        address = self.repository.get_address_for_current_customer(address_id, tenant_id=tenant_id)
        if address is None:
            return None
        content_parts = [
            address.line_1,
            address.line_2,
            address.district,
            f"{address.city}/{address.state}".strip("/"),
        ]
        return {
            "address_id": address.pk,
            "title": address.label,
            "subtitle": address.recipient_name or "Endereço salvo",
            "content": " · ".join(part for part in content_parts if part),
            "footer": f"CEP {address.postal_code}" if address.postal_code else "",
        }

    def delete_address(self, address_id: int, *, tenant_id: int | None = None) -> bool:
        if not self._tenant_required(tenant_id):
            return False
        address = self.repository.get_address_for_current_customer(address_id, tenant_id=tenant_id)
        if address is None:
            return False
        address.delete()
        return True


account_address_commands = AccountAddressCommandService(
    repository=DjangoOrmAccountAddressCommandRepository(),
)
