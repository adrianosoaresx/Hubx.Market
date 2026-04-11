from __future__ import annotations
from typing import Optional

from django.http import HttpRequest

from ..models import Tenant


def get_current_tenant(request: HttpRequest) -> Optional[Tenant]:
    return getattr(request, "tenant", None)