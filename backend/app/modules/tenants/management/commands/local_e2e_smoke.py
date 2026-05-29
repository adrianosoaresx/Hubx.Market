from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test import Client, override_settings

from app.modules.accounts.models import OwnerUser


@dataclass(frozen=True)
class E2EResult:
    key: str
    ready: bool
    summary: str


class LinkImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value for key, value in attrs}
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "img" and values.get("src"):
            self.images.append(str(values["src"]))


class Command(BaseCommand):
    help = "Executa E2E local de menus, links, acessos, templates e imagens por perfil."

    def add_arguments(self, parser):
        parser.add_argument("--central-host", default="localhost:8002")
        parser.add_argument("--store-host", default="hubx-demo.localhost:8002")
        parser.add_argument("--platform-email", default="platform.owner@hubx.market")
        parser.add_argument("--store-email", default="store.owner@hubx.market")
        parser.add_argument("--password", default="secret")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        central_host = str(options["central_host"])
        store_host = str(options["store_host"])
        platform_email = str(options["platform_email"])
        store_email = str(options["store_email"])
        password = str(options["password"])
        allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
        for host in (central_host, store_host, central_host.split(":")[0], store_host.split(":")[0], ".localhost"):
            if host not in allowed_hosts:
                allowed_hosts.append(host)

        with override_settings(
            HUBX_MARKET_ROOT_DOMAIN="localhost",
            HUBX_MARKET_PUBLIC_PORT=central_host.split(":")[-1] if ":" in central_host else "",
            ALLOWED_HOSTS=allowed_hosts,
            HUBX_OPS_AUTH_GATE_ENFORCED=True,
        ):
            results = self._run(
                central_host=central_host,
                store_host=store_host,
                platform_email=platform_email,
                store_email=store_email,
                password=password,
            )

        blockers = [result for result in results if not result.ready]
        status = "READY" if not blockers else "BLOCKED"
        self.stdout.write(f"[{status}] local-e2e-smoke results={len(results)} blockers={len(blockers)}")
        for result in results:
            marker = "ok" if result.ready else "blocker"
            self.stdout.write(f"{marker} key={result.key} {result.summary}")
        if blockers and options["fail_on_blockers"]:
            raise CommandError("Local E2E smoke is blocked.")

    def _run(self, *, central_host: str, store_host: str, platform_email: str, store_email: str, password: str) -> list[E2EResult]:
        results: list[E2EResult] = []
        results.extend(self._validate_seed(platform_email=platform_email, store_email=store_email))
        results.extend(self._platform_flow(host=central_host, email=platform_email, password=password))
        results.extend(self._store_flow(host=store_host, central_host=central_host, email=store_email, password=password))
        results.extend(self._visitor_storefront(host=store_host))
        return results

    def _validate_seed(self, *, platform_email: str, store_email: str) -> list[E2EResult]:
        platform_owner = OwnerUser.objects.filter(
            email__iexact=platform_email,
            tenant__slug=getattr(settings, "HUBX_PLATFORM_TENANT_SLUG", "platform-system"),
            is_active=True,
        ).exists()
        store_owner = OwnerUser.objects.filter(email__iexact=store_email, tenant__slug="hubx-demo", is_active=True).exists()
        platform_cross_store = OwnerUser.objects.filter(email__iexact=platform_email, tenant__slug="hubx-demo", is_active=True).exists()
        return [
            E2EResult("seed-platform-owner", platform_owner, "platform owner ativo no tenant platform-system"),
            E2EResult("seed-store-owner", store_owner, "store owner ativo na hubx-demo"),
            E2EResult("seed-no-platform-owner-store-leak", not platform_cross_store, "platform owner não está ativo na loja demo"),
        ]

    def _platform_flow(self, *, host: str, email: str, password: str) -> list[E2EResult]:
        client = Client(HTTP_HOST=host)
        results: list[E2EResult] = []
        response = client.post("/accounts/login/", {"login": email, "password": password}, HTTP_HOST=host)
        results.append(E2EResult("platform-login-redirect", response.status_code == 302 and response["Location"] == "/ops/platform/tenants/", f"status={response.status_code} location={response.get('Location', '')}"))
        ops_response = client.get("/ops/", HTTP_HOST=host)
        results.append(E2EResult("platform-central-ops-redirect", ops_response.status_code == 302 and ops_response["Location"] == "/ops/platform/tenants/", f"status={ops_response.status_code} location={ops_response.get('Location', '')}"))
        for path, markers, forbidden in (
            (
                "/ops/platform/tenants/",
                ("Platform admin", "Lojas", "Onboarding", "Portal central"),
                ("Dashboard", "Pedidos", "Catálogo", "Admin da loja"),
            ),
            (
                "/ops/platform/onboarding/",
                ("Platform admin", "Onboarding de lojas", "Lojas", "Portal central"),
                ("Dashboard", "Pedidos", "Catálogo", "Admin da loja"),
            ),
        ):
            response = client.get(path, HTTP_HOST=host)
            html = response.content.decode("utf-8", errors="replace")
            results.append(self._markers_result(key=f"platform-template:{path}", response=response, html=html, markers=markers, forbidden=forbidden))
            results.extend(self._check_page_links(client=client, host=host, path=path, html=html, scope="platform"))
        return results

    def _store_flow(self, *, host: str, central_host: str, email: str, password: str) -> list[E2EResult]:
        client = Client(HTTP_HOST=host)
        results: list[E2EResult] = []
        response = client.post("/accounts/login/?next=/ops/", {"login": email, "password": password}, HTTP_HOST=host)
        location = response.get("Location", "")
        results.append(
            E2EResult(
                "store-login-redirect",
                response.status_code == 302 and (location == "/ops/" or location == f"http://{host}/ops/"),
                f"status={response.status_code} location={location}",
            )
        )
        dashboard = client.get("/ops/", HTTP_HOST=host)
        html = dashboard.content.decode("utf-8", errors="replace")
        results.append(
            self._markers_result(
                key="store-dashboard-template",
                response=dashboard,
                html=html,
                markers=("Admin da loja", "Dashboard", "Operação da loja", "Pedidos", "Catálogo"),
                forbidden=("Platform admin", "Portal central", "/ops/platform/tenants/", "/ops/platform/onboarding/"),
            )
        )
        platform_on_store = client.get("/ops/platform/tenants/", HTTP_HOST=host)
        results.append(E2EResult("store-host-blocks-platform-surface", platform_on_store.status_code == 403, f"status={platform_on_store.status_code}"))
        central_client = Client(HTTP_HOST=central_host)
        central_login = central_client.post("/accounts/login/", {"login": email, "password": password}, HTTP_HOST=central_host)
        results.append(
            E2EResult(
                "store-owner-central-login-goes-store",
                central_login.status_code == 302 and central_login["Location"].startswith(f"http://{host}/ops/"),
                f"status={central_login.status_code} location={central_login.get('Location', '')}",
            )
        )
        results.extend(self._check_page_links(client=client, host=host, path="/ops/", html=html, scope="store-admin"))
        return results

    def _visitor_storefront(self, *, host: str) -> list[E2EResult]:
        client = Client(HTTP_HOST=host)
        results: list[E2EResult] = []
        for path, markers, forbidden in (
            ("/", ("Hubx Market", "Loja", "Entrar"), ("Page not found", 'href="/orders/"')),
            ("/catalog/", ("Loja", "Filtrar produtos", "storefront-product-grid"), ("Page not found", 'href="/orders/"')),
        ):
            response = client.get(path, HTTP_HOST=host)
            html = response.content.decode("utf-8", errors="replace")
            results.append(self._markers_result(key=f"storefront-template:{path}", response=response, html=html, markers=markers, forbidden=forbidden))
            results.extend(self._check_page_links(client=client, host=host, path=path, html=html, scope="storefront"))
            results.extend(self._check_page_images(client=client, host=host, path=path, html=html))
        return results

    def _markers_result(self, *, key: str, response, html: str, markers: tuple[str, ...], forbidden: tuple[str, ...]) -> E2EResult:
        missing = [marker for marker in markers if marker not in html]
        forbidden_found = [marker for marker in forbidden if marker in html]
        ready = response.status_code == 200 and not missing and not forbidden_found
        return E2EResult(key, ready, f"status={response.status_code} missing={missing} forbidden={forbidden_found}")

    def _check_page_links(self, *, client: Client, host: str, path: str, html: str, scope: str) -> list[E2EResult]:
        parser = LinkImageParser()
        parser.feed(html)
        results: list[E2EResult] = []
        for href in sorted(set(parser.links)):
            target = self._local_path(href=href, host=host)
            if not target or target in {"/accounts/logout/"} or target.startswith("/admin/"):
                continue
            if target.startswith("/ops/platform/") and scope != "platform":
                results.append(E2EResult(f"link-context:{scope}:{path}:{target}", False, "platform link exposed outside platform shell"))
                continue
            response = client.get(target, HTTP_HOST=host)
            ok = response.status_code in {200, 302, 403}
            results.append(E2EResult(f"link:{scope}:{path}:{target}", ok, f"status={response.status_code}"))
        return results

    def _check_page_images(self, *, client: Client, host: str, path: str, html: str) -> list[E2EResult]:
        parser = LinkImageParser()
        parser.feed(html)
        results: list[E2EResult] = []
        for src in sorted(set(parser.images)):
            target = self._local_path(href=src, host=host)
            if not target:
                continue
            response = client.get(target, HTTP_HOST=host)
            size = self._response_size(response)
            results.append(E2EResult(f"image:{path}:{target}", response.status_code == 200 and size > 0, f"status={response.status_code} bytes={size}"))
        return results

    def _local_path(self, *, href: str, host: str) -> str:
        href = str(href or "").strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
            return ""
        parsed = urlparse(href)
        if parsed.scheme and parsed.netloc and parsed.netloc != host:
            return ""
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return path

    def _response_size(self, response) -> int:
        if getattr(response, "streaming", False):
            return sum(len(chunk) for chunk in response.streaming_content)
        return len(getattr(response, "content", b"") or b"")
