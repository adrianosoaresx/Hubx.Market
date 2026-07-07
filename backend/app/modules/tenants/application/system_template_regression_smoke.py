from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SystemTemplateSmokeTarget:
    key: str
    path: str
    expected_status: int
    markers: tuple[str, ...]
    forbidden_markers: tuple[str, ...] = ()
    host_scope: str = "tenant"
    marker_groups: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class SystemTemplateSmokeResult:
    key: str
    path: str
    host: str
    status_code: int
    expected_status: int
    missing_markers: tuple[str, ...]
    forbidden_markers_found: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return (
            self.status_code == self.expected_status
            and not self.missing_markers
            and not self.forbidden_markers_found
        )


class HttpClient(Protocol):
    def get(self, path: str, **extra: object): ...


def central_host_from_tenant_host(host: str) -> str:
    normalized_host = str(host or "").strip()
    if "." not in normalized_host:
        return normalized_host
    hostname, separator, port = normalized_host.partition(":")
    parts = hostname.split(".", 1)
    central_host = parts[1] if len(parts) == 2 else hostname
    return f"{central_host}{separator}{port}" if separator else central_host


STORE_FRONT_ADMIN_SMOKE_TARGETS: tuple[SystemTemplateSmokeTarget, ...] = (
    SystemTemplateSmokeTarget(
        key="storefront-home-nav",
        path="/",
        expected_status=200,
        markers=(
            'href="/"',
            'href="/catalog/"',
            'href="/accounts/account/orders/"',
        ),
        forbidden_markers=('href="/orders/"',),
        marker_groups=(("Entrar", "Sair"),),
    ),
    SystemTemplateSmokeTarget(
        key="storefront-catalog-list",
        path="/catalog/",
        expected_status=200,
        markers=(
            "Loja",
            "Filtrar produtos",
            "storefront-product-grid",
        ),
    ),
    SystemTemplateSmokeTarget(
        key="customer-login-form",
        path="/accounts/login/",
        expected_status=200,
        markers=(
            "Acessar conta",
            'type="submit"',
            "Criar conta",
        ),
    ),
    SystemTemplateSmokeTarget(
        key="central-home-public-entrypoints",
        path="/",
        expected_status=200,
        markers=(
            "Crie sua loja virtual com uma operação pronta para vender.",
            "Iniciar onboarding",
            'href="/accounts/login/"',
            'href="/plans/"',
            'href="/plans/#aquisicao"',
            'href="/demo/"',
        ),
        forbidden_markers=("/ops/platform/",),
        host_scope="central",
    ),
    SystemTemplateSmokeTarget(
        key="central-login-public-nav",
        path="/accounts/login/",
        expected_status=200,
        markers=(
            'href="/plans/"',
            'href="/demo/"',
            "Criar conta",
        ),
        forbidden_markers=('href="/catalog/"', 'href="/accounts/account/orders/"'),
        host_scope="central",
    ),
    SystemTemplateSmokeTarget(
        key="customer-orders-nav-target",
        path="/accounts/account/orders/",
        expected_status=200,
        markers=(
            "Meus pedidos",
            "customer-orders-page",
        ),
        forbidden_markers=("Page not found",),
    ),
    SystemTemplateSmokeTarget(
        key="ops-dashboard",
        path="/ops/",
        expected_status=200,
        markers=(
            "Operação da loja",
            "admin-dashboard-page",
        ),
    ),
    SystemTemplateSmokeTarget(
        key="public-demo-access",
        path="/demo/",
        expected_status=200,
        markers=(
            "Escolha como deseja acessar a loja demo.",
            "Admin da loja",
            "Cliente da loja",
            "/accounts/demo-session/?profile=admin",
            "/accounts/demo-session/?profile=customer",
        ),
        host_scope="central",
    ),
    SystemTemplateSmokeTarget(
        key="public-plans",
        path="/plans/",
        expected_status=200,
        markers=(
            "Planos Hubx Market",
            "Iniciar onboarding",
            "Acessar demo",
            "Onboarding assistido",
        ),
        forbidden_markers=("Demo lifestyle", "/media/demo-catalog/fixtures/"),
        host_scope="central",
    ),
    SystemTemplateSmokeTarget(
        key="platform-acquisitions-list",
        path="/ops/platform/acquisitions/",
        expected_status=200,
        markers=(
            "Aquisições SaaS",
            "Fila de aquisições",
        ),
        host_scope="central",
    ),
    SystemTemplateSmokeTarget(
        key="platform-onboarding-list",
        path="/ops/platform/onboarding/",
        expected_status=200,
        markers=(
            "Onboarding de lojas",
            "Jornadas de onboarding",
        ),
        host_scope="central",
    ),
    SystemTemplateSmokeTarget(
        key="platform-tenants-list",
        path="/ops/platform/tenants/",
        expected_status=200,
        markers=(
            "Inventário de lojas",
            "Esta tela não cria, edita ou remove tenants.",
        ),
        host_scope="central",
    ),
)


@dataclass
class SystemTemplateRegressionSmokeService:
    def run(
        self,
        *,
        client: HttpClient,
        host: str,
        targets: tuple[SystemTemplateSmokeTarget, ...] = STORE_FRONT_ADMIN_SMOKE_TARGETS,
    ) -> dict[str, object]:
        central_host = central_host_from_tenant_host(host)
        results = tuple(
            self._check_target(client=client, host=host, central_host=central_host, target=target)
            for target in targets
        )
        blockers = self._blockers(results=results)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"system-template-regression-smoke-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "tenants",
            "host": host,
            "results": results,
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _check_target(
        self,
        *,
        client: HttpClient,
        host: str,
        central_host: str,
        target: SystemTemplateSmokeTarget,
    ) -> SystemTemplateSmokeResult:
        target_host = central_host if target.host_scope == "central" else host
        response = client.get(target.path, HTTP_HOST=target_host)
        content = response.content.decode("utf-8", errors="replace")
        missing_markers = [marker for marker in target.markers if marker not in content]
        for marker_group in target.marker_groups:
            if not any(marker in content for marker in marker_group):
                missing_markers.append(" or ".join(marker_group))
        return SystemTemplateSmokeResult(
            key=target.key,
            path=target.path,
            host=target_host,
            status_code=response.status_code,
            expected_status=target.expected_status,
            missing_markers=tuple(missing_markers),
            forbidden_markers_found=tuple(marker for marker in target.forbidden_markers if marker in content),
        )

    def _blockers(self, *, results: tuple[SystemTemplateSmokeResult, ...]) -> tuple[str, ...]:
        blockers: list[str] = []
        for result in results:
            if result.status_code != result.expected_status:
                blockers.append(
                    f"system-template-regression:{result.key}:status:{result.status_code}:expected:{result.expected_status}"
                )
            blockers.extend(f"system-template-regression:{result.key}:missing:{marker}" for marker in result.missing_markers)
            blockers.extend(
                f"system-template-regression:{result.key}:forbidden:{marker}"
                for marker in result.forbidden_markers_found
            )
        return tuple(blockers)

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "System Validation Pass 2 — Browser Smoke Evidence",
                "Payments Production Readiness Review",
            )
        return (
            "Storefront/Admin Template Regression Fix",
            "System Validation Pass 2 — Storefront/Admin Smoke & Template Regression",
        )


system_template_regression_smoke = SystemTemplateRegressionSmokeService()
