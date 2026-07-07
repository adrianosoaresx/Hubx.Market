from __future__ import annotations

from django.core.management.base import BaseCommand

from app.modules.subscriptions.application.subscription_commands import subscription_commands


DEMO_PLANS = (
    {
        "code": "starter",
        "name": "Starter",
        "description": "Para validar a primeira loja com 30 dias grátis antes da ativação paga.",
        "monthly_price": "99.90",
        "included_api_quota": 10000,
        "trial_days": 30,
        "requires_payment_method": True,
        "features": (
            "30 dias grátis para configurar a loja",
            "Cartão obrigatório na ativação do trial",
            "Loja em subdomínio Hubx",
            "Admin tenant-owned",
            "Catálogo, carrinho e checkout modular",
            "Modo manutenção inicial até publicação",
        ),
    },
    {
        "code": "pro",
        "name": "Pro",
        "description": "Para operação em crescimento com mais quota operacional e 30 dias grátis.",
        "monthly_price": "249.90",
        "included_api_quota": 50000,
        "trial_days": 30,
        "requires_payment_method": True,
        "features": (
            "30 dias grátis para validar operação",
            "Cartão obrigatório na ativação do trial",
            "Tudo do Starter",
            "Domínio customizado contract-ready",
            "Mais quota operacional de API",
            "Relatórios e rotinas admin ampliadas",
        ),
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Para operações maiores com implantação assistida e trial controlado.",
        "monthly_price": "799.90",
        "included_api_quota": 200000,
        "trial_days": 30,
        "requires_payment_method": True,
        "features": (
            "30 dias grátis com onboarding acompanhado",
            "Cartão obrigatório na ativação do trial",
            "Tudo do Pro",
            "Capacidade ampliada de API",
            "Acompanhamento prioritário de implantação",
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
