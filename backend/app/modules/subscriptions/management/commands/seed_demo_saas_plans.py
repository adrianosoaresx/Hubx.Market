from __future__ import annotations

from django.core.management.base import BaseCommand

from app.modules.subscriptions.application.subscription_commands import subscription_commands


DEMO_PLANS = (
    {
        "code": "starter",
        "name": "Essencial",
        "description": "Para começar sem mensalidade: a Hubx ganha quando a loja vende.",
        "monthly_price": "0.00",
        "included_api_quota": 0,
        "trial_days": 0,
        "requires_payment_method": False,
        "billing_model": "take_rate_only",
        "platform_fee_percent": "2.00",
        "minimum_monthly_fee": "0.00",
        "product_limit": 100,
        "monthly_paid_order_limit": 300,
        "requires_hubx_checkout": True,
        "requires_billing_method": False,
        "features": (
            "Até 100 produtos",
            "Até 300 pedidos pagos por mês",
            "R$ 0/mês + 2% por pedido pago",
            "Checkout Hubx com split automático",
            "Loja em subdomínio Hubx",
            "Catálogo, carrinho e checkout",
        ),
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "Para operação em crescimento com mais capacidade e compromisso mínimo abatível.",
        "monthly_price": "0.00",
        "included_api_quota": 50000,
        "trial_days": 0,
        "requires_payment_method": False,
        "billing_model": "minimum_commitment",
        "platform_fee_percent": "2.00",
        "minimum_monthly_fee": "259.90",
        "product_limit": 500,
        "monthly_paid_order_limit": 1500,
        "requires_hubx_checkout": True,
        "requires_billing_method": True,
        "features": (
            "Até 500 produtos",
            "Até 1.500 pedidos pagos por mês",
            "R$ 259,90 mínimo ou 2% por pedido pago",
            "API de catálogo e operação incluída",
            "Domínio e customização ampliados",
            "Relatórios e suporte prioritário",
        ),
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Para operações maiores com limites, percentual, SLA e implantação negociados.",
        "monthly_price": "0.00",
        "included_api_quota": 200000,
        "trial_days": 0,
        "requires_payment_method": False,
        "billing_model": "custom",
        "platform_fee_percent": "0.00",
        "minimum_monthly_fee": "0.00",
        "product_limit": 0,
        "monthly_paid_order_limit": 0,
        "requires_hubx_checkout": True,
        "requires_billing_method": True,
        "features": (
            "Produtos e pedidos sob consulta",
            "Percentual e mínimo negociados",
            "API e integrações avançadas",
            "SLA e implantação assistida",
            "Acompanhamento executivo",
            "Plano de rollout por tenant",
        ),
    },
)


class Command(BaseCommand):
    help = "Cria ou atualiza planos SaaS demo para a página pública /plans/."

    def add_arguments(self, parser):
        parser.add_argument("--actor-label", default="seed-demo-saas-plans")

    def handle(self, *args, **options):
        actor_label = str(options["actor_label"] or "seed-demo-saas-plans")
        results = []
        for plan in DEMO_PLANS:
            result = subscription_commands.upsert_plan(actor_label=actor_label, **plan)
            results.append(result)

        self.stdout.write(
            self.style.SUCCESS(
                "demo_saas_plans_seeded "
                f"plans={len(results)} "
                f"codes={','.join(str(result.get('plan', {}).get('code', '')) for result in results)}"
            )
        )
