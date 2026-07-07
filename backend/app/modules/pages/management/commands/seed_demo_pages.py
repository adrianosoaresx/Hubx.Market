from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from app.modules.pages.models import Page
from app.modules.tenants.models import Tenant


@dataclass(frozen=True)
class DemoPageBlueprint:
    title: str
    slug: str
    seo_title: str
    seo_description: str
    body: str


DEMO_PAGE_BLUEPRINTS = (
    DemoPageBlueprint(
        title="Sobre a loja",
        slug="sobre-a-loja",
        seo_title="Sobre a loja demo",
        seo_description="Conheça a curadoria, operação e proposta da loja demo Hubx Market.",
        body=(
            "A loja demo Hubx Market apresenta um e-commerce tenant-scoped com catálogo, conta do cliente, "
            "carrinho, checkout e admin da loja em um único fluxo.\n\n"
            "O objetivo desta página é validar como conteúdo institucional simples aparece no storefront "
            "sem exigir page builder avançado no MVP.\n\n"
            "Cada loja poderá adaptar este espaço para contar sua história, posicionamento, canais de "
            "atendimento e diferenciais comerciais."
        ),
    ),
    DemoPageBlueprint(
        title="Trocas e devoluções",
        slug="trocas-e-devolucoes",
        seo_title="Trocas e devoluções",
        seo_description="Veja as regras de troca, devolução e atendimento pós-compra da loja demo.",
        body=(
            "Solicitações de troca ou devolução devem ser iniciadas pelo canal de atendimento da loja em até "
            "7 dias corridos após o recebimento.\n\n"
            "O produto precisa estar sem sinais de uso indevido, com embalagem e acessórios preservados. "
            "Quando a solicitação for aprovada, a loja orienta o envio e acompanha o status até a conclusão.\n\n"
            "No MVP, esta página funciona como referência institucional. Regras avançadas por categoria, "
            "automação reversa e etiquetas logísticas ficam para etapas futuras."
        ),
    ),
    DemoPageBlueprint(
        title="Política de privacidade",
        slug="politica-de-privacidade",
        seo_title="Política de privacidade",
        seo_description="Entenda como dados de conta, pedidos e atendimento são usados pela loja demo.",
        body=(
            "A loja utiliza dados informados pelo cliente para identificar a conta, processar pedidos, "
            "calcular entrega, comunicar atualizações e prestar atendimento.\n\n"
            "Dados de cada loja são isolados por tenant. Informações de clientes, pedidos e pagamentos não "
            "devem ser compartilhadas entre lojas.\n\n"
            "Esta política é um texto base para avaliação do MVP e deve ser revisada juridicamente antes de "
            "uso em produção."
        ),
    ),
    DemoPageBlueprint(
        title="Termos de uso",
        slug="termos-de-uso",
        seo_title="Termos de uso",
        seo_description="Condições gerais para navegação, compra e uso da loja demo.",
        body=(
            "Ao navegar pela loja, o cliente concorda em fornecer informações corretas para cadastro, entrega "
            "e pagamento.\n\n"
            "Preços, disponibilidade e condições comerciais podem mudar conforme operação da loja. Pedidos "
            "são efetivados apenas após escolha de frete, método de pagamento e confirmação do fluxo de compra.\n\n"
            "Este texto é demonstrativo e ajuda a validar onde termos institucionais aparecem no storefront "
            "do MVP."
        ),
    ),
    DemoPageBlueprint(
        title="Contato",
        slug="contato",
        seo_title="Contato",
        seo_description="Fale com a loja demo para dúvidas sobre produtos, pedidos e atendimento.",
        body=(
            "Atendimento da loja demo\n\n"
            "E-mail: atendimento@hubx-demo.market\n"
            "Horário: segunda a sexta, das 9h às 18h\n\n"
            "Use este espaço para centralizar canais oficiais de suporte, prazos de resposta e orientações "
            "sobre pedidos. No MVP, o conteúdo permanece simples e gerenciado pelo admin da loja."
        ),
    ),
)


class Command(BaseCommand):
    help = "Cria ou atualiza páginas institucionais demo tenant-scoped."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-subdomain", default="hubx-demo")
        parser.add_argument("--reset-seed", action="store_true")

    def handle(self, *args, **options):
        tenant_subdomain = str(options["tenant_subdomain"] or "").strip()
        if not tenant_subdomain:
            raise CommandError("Informe --tenant-subdomain.")

        tenant = Tenant.objects.filter(subdomain=tenant_subdomain).first()
        if tenant is None:
            raise CommandError(f"Tenant não encontrado para subdomain={tenant_subdomain}")

        slugs = [page.slug for page in DEMO_PAGE_BLUEPRINTS]
        created_count = 0
        updated_count = 0
        now = timezone.now()

        with transaction.atomic():
            if options["reset_seed"]:
                Page.objects.filter(tenant=tenant, slug__in=slugs).delete()

            for blueprint in DEMO_PAGE_BLUEPRINTS:
                page = Page.objects.filter(tenant=tenant, slug=blueprint.slug).first()
                values = {
                    "title": blueprint.title,
                    "body": blueprint.body,
                    "status": Page.Status.PUBLISHED,
                    "seo_title": blueprint.seo_title,
                    "seo_description": blueprint.seo_description,
                }
                if page is None:
                    Page.objects.create(
                        tenant=tenant,
                        slug=blueprint.slug,
                        published_at=now,
                        **values,
                    )
                    created_count += 1
                    continue

                for field_name, value in values.items():
                    setattr(page, field_name, value)
                update_fields = [*values.keys(), "updated_at"]
                if page.published_at is None:
                    page.published_at = now
                    update_fields.append("published_at")
                page.save(update_fields=update_fields)
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "demo_pages_seeded "
                f"tenant_id={tenant.id} "
                f"tenant_subdomain={tenant.subdomain} "
                f"pages={len(DEMO_PAGE_BLUEPRINTS)} "
                f"created={created_count} "
                f"updated={updated_count}"
            )
        )
