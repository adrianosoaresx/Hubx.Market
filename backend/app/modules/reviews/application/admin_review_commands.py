from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from app.modules.accounts.application.admin_permissions import PERMISSION_REVIEWS_MODERATE, admin_permissions
from app.modules.audit.application.audit_log_commands import audit_log_commands


ALLOWED_ACTIONS = {"approve", "reject"}


def _string(value: object) -> str:
    return str(value or "").strip()


class DjangoOrmAdminReviewCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.reviews.models import ProductReview
        except Exception:
            self.product_review_model = None
            return
        self.product_review_model = ProductReview

    def get_review(self, *, tenant_id: int | None, review_id: int | str | None):
        if self.product_review_model is None or not tenant_id or not review_id:
            return None
        return self.product_review_model._default_manager.filter(tenant_id=tenant_id, id=review_id).first()

    def save_moderation(self, review) -> None:
        review.save(update_fields=["status", "moderated_at", "updated_at"])


@dataclass
class AdminReviewCommandService:
    repository: DjangoOrmAdminReviewCommandRepository

    def moderate_review(
        self,
        *,
        tenant_id: int | None,
        review_id: int | str | None,
        action: str,
        moderated_by: str = "",
        actor_role: str = "",
    ) -> tuple[str, object | None]:
        normalized_action = _string(action)
        if normalized_action not in ALLOWED_ACTIONS:
            return "review-moderation-blocked", None
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_REVIEWS_MODERATE)
        if not permission.allowed:
            return "review-permission-denied", None
        if not tenant_id or not review_id:
            return "review-moderation-unavailable", None

        review = self.repository.get_review(tenant_id=tenant_id, review_id=review_id)
        if review is None:
            return "review-moderation-unavailable", None

        if normalized_action == "approve":
            review.status = self.repository.product_review_model.Status.APPROVED
            result = "review-approved"
        else:
            review.status = self.repository.product_review_model.Status.REJECTED
            result = "review-rejected"
        review.moderated_at = timezone.now()
        self.repository.save_moderation(review)
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="reviews",
            action=result.replace("review-", "review."),
            entity_type="ProductReview",
            entity_id=str(review.id),
            actor_label=moderated_by,
            summary=f"Avaliação {review.id} {review.status}",
            metadata={
                "status": review.status,
                "product_id": review.product_id,
                "rating": review.rating,
            },
        )
        return result, review


admin_review_commands = AdminReviewCommandService(repository=DjangoOrmAdminReviewCommandRepository())
