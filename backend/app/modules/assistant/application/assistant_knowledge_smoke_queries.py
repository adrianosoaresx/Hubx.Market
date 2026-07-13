from __future__ import annotations

from dataclasses import dataclass

from app.modules.assistant.application.assistant_knowledge_service import AssistantKnowledgeService, assistant_knowledge_service
from app.modules.assistant.application.assistant_knowledge_service import _tokens


SMOKE_CASES = (
    {
        "question": "Como cadastro um produto?",
        "expected_sources": ("docs/assistant/catalogo.md",),
        "expected_terms": ("produto",),
    },
    {
        "question": "Qual a diferenca entre produto e variante?",
        "expected_sources": ("docs/assistant/catalogo.md",),
        "expected_terms": ("produto", "variante"),
    },
    {
        "question": "Quando o estoque baixa?",
        "expected_sources": ("docs/assistant/pedidos-e-estoque.md",),
        "expected_terms": ("estoque", "pagamento"),
    },
    {
        "question": "Como configuro a marca da loja?",
        "expected_sources": ("docs/assistant/marca-da-loja.md",),
        "expected_terms": ("marca", "hero"),
    },
    {
        "question": "Como publico uma pagina?",
        "expected_sources": ("docs/assistant/paginas.md",),
        "expected_terms": ("pagina", "publicada"),
    },
    {
        "question": "O que significa pagamento pendente?",
        "expected_sources": ("docs/assistant/pedidos-e-estoque.md", "docs/assistant/pagamentos.md"),
        "expected_terms": ("pagamento", "pendente"),
    },
    {
        "question": "O assistente pode ver meus pedidos?",
        "expected_sources": ("docs/assistant/faq.md",),
        "expected_terms": ("mvp", "dados reais"),
    },
    {
        "question": "Quero vender um produto com tamanhos diferentes",
        "expected_sources": ("docs/assistant/catalogo.md",),
        "expected_terms": ("tamanhos", "variante", "sku"),
    },
    {
        "question": "Posso apagar produto antigo?",
        "expected_sources": ("docs/assistant/catalogo.md",),
        "expected_terms": ("desativar", "historico"),
    },
    {
        "question": "Pedido pendente ja baixa estoque?",
        "expected_sources": ("docs/assistant/pedidos-e-estoque.md",),
        "expected_terms": ("pendente", "pagamento confirmado"),
    },
    {
        "question": "Onde mudo a logo?",
        "expected_sources": ("docs/assistant/marca-da-loja.md",),
        "expected_terms": ("logo", "/ops/branding/"),
    },
    {
        "question": "Por que o assistente nao ve meus pedidos?",
        "expected_sources": ("docs/assistant/faq.md",),
        "expected_terms": ("mvp", "dados reais", "tenants"),
    },
    {
        "question": "Produto sem estoque deve ser apagado?",
        "expected_sources": ("docs/assistant/catalogo.md",),
        "expected_terms": ("estoque", "desative"),
    },
    {
        "question": "Onde mudo a imagem principal da home?",
        "expected_sources": ("docs/assistant/marca-da-loja.md",),
        "expected_terms": ("hero", "/ops/branding/"),
    },
    {
        "question": "Posso preparar pedido com pagamento pendente?",
        "expected_sources": ("docs/assistant/pedidos-e-estoque.md",),
        "expected_terms": ("pendente", "pagamento confirmado"),
    },
)


@dataclass
class AssistantKnowledgeSmokeService:
    knowledge_service: AssistantKnowledgeService

    def run(self) -> dict[str, object]:
        cases = []
        failures = []
        for case in SMOKE_CASES:
            question = str(case["question"])
            hits = self.knowledge_service.search(question=question)
            paths = [hit.path for hit in hits]
            excerpt_tokens = _tokens(" ".join(hit.excerpt for hit in hits[:3]))
            expected_sources = tuple(case["expected_sources"])
            expected_terms = tuple(case["expected_terms"])
            source_ok = bool(paths) and paths[0] in expected_sources
            terms_ok = all(_tokens(term).issubset(excerpt_tokens) for term in expected_terms)
            status = "pass" if source_ok and terms_ok else "fail"
            quality = "util" if status == "pass" else "clara-mas-incompleta"
            result = {
                "question": question,
                "status": status,
                "quality": quality,
                "top_source": paths[0] if paths else "",
                "sources": paths[:5],
                "expected_sources": expected_sources,
                "expected_terms": expected_terms,
            }
            cases.append(result)
            if status != "pass":
                failures.append(result)
        return {
            "result": "assistant-knowledge-smoke-passed" if not failures else "assistant-knowledge-smoke-failed",
            "passed": not failures,
            "case_count": len(cases),
            "failure_count": len(failures),
            "cases": cases,
            "failures": failures,
        }


assistant_knowledge_smoke_queries = AssistantKnowledgeSmokeService(knowledge_service=assistant_knowledge_service)
