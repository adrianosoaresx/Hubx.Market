from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.assistant.application.assistant_knowledge_smoke_queries import assistant_knowledge_smoke_queries


class Command(BaseCommand):
    help = "Valida perguntas reais do assistente contra fontes esperadas em docs/assistant."

    def add_arguments(self, parser):
        parser.add_argument("--fail-on-error", action="store_true", help="Retorna erro quando algum caso falhar.")

    def handle(self, *args, **options):
        result = assistant_knowledge_smoke_queries.run()
        self.stdout.write(f"result={result['result']}")
        self.stdout.write(f"cases={result['case_count']} failures={result['failure_count']}")
        for case in result["cases"]:
            self.stdout.write(
                "case={status} quality={quality} question={question} top_source={top_source}".format(
                    status=case["status"],
                    quality=case["quality"],
                    question=case["question"],
                    top_source=case["top_source"] or "none",
                )
            )
        if options["fail_on_error"] and not result["passed"]:
            raise CommandError("assistant knowledge smoke failed")
