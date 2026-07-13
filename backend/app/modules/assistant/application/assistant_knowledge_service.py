from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings


TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9_]{3,}")
MAX_DOC_CHARS = 50000
STOPWORDS = {
    "ainda",
    "como",
    "com",
    "das",
    "dos",
    "ele",
    "ela",
    "entre",
    "essa",
    "esse",
    "loja",
    "para",
    "pela",
    "pelo",
    "por",
    "qual",
    "que",
    "uma",
    "uns",
    "token",
}


@dataclass(frozen=True)
class KnowledgeHit:
    title: str
    path: str
    excerpt: str
    score: int


def _repo_root() -> Path:
    return Path(getattr(settings, "REPO_ROOT", Path.cwd())).resolve()


def _allowed_paths() -> list[Path]:
    root = _repo_root()
    docs = root / "docs"
    paths = [
        docs / "architecture-overview.md",
        docs / "context-map.md",
        docs / "module-boundaries.md",
        docs / "request-lifecycle.md",
        docs / "domain-model.md",
        docs / "events-map.md",
        docs / "implementation-inventory.md",
    ]
    paths.extend(
        path
        for path in sorted((docs / "assistant").glob("*.md"))
        if path.name != "roteiro-de-avaliacao.md"
    )
    paths.extend(sorted((docs / "modules").glob("*.md")))
    paths.extend(sorted((docs / "ui").glob("*.md")))
    return [path for path in paths if path.exists() and path.is_file()]


def _tokens(value: str, *, expand: bool = True) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    tokens = {token.lower() for token in TOKEN_RE.findall(normalized) if token.lower() not in STOPWORDS}
    if not expand:
        return tokens
    expanded = set(tokens)
    if {"cadastro", "cadastrar", "cadastrado"} & tokens:
        expanded.update({"cadastro", "cadastrar", "produto", "catalogo"})
    if {"tamanho", "tamanhos", "versao", "versoes", "cores", "cor"} & tokens:
        expanded.update({"tamanho", "tamanhos", "variante", "variantes", "sku", "produto"})
    if {"apagar", "apagado", "apagada", "apago", "deletar", "delete", "antigo", "inativo"} & tokens:
        expanded.update({"apagar", "desativar", "inativo", "produto", "historico", "catalogo"})
    if {"pagina", "paginas", "publico", "publicar", "publicada"} & tokens:
        expanded.update({"pagina", "paginas", "publicar", "publicada"})
    if {"marca", "branding", "hero", "logo", "home"} & tokens:
        expanded.update({"marca", "branding", "hero", "logo", "home"})
    if {"pendente", "pagamento"} & tokens:
        expanded.update({"pendente", "pagamento"})
    if {"pedido", "pedidos", "estoque"} & tokens:
        expanded.update({"pedido", "pedidos", "estoque"})
    if {"assistente", "ver", "ve", "meus"} & tokens:
        expanded.update({"assistente", "mvp", "dados", "reais", "pedidos"})
    return expanded


def _title_for(path: Path, content: str) -> str:
    for line in content.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()[:120] or path.stem
    return path.stem


def _best_excerpt(content: str, query_tokens: set[str]) -> str:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", content) if chunk.strip()]
    if not chunks:
        return ""
    combined_chunks = list(chunks)
    for index, chunk in enumerate(chunks[:-1]):
        if chunk.startswith("#"):
            combined_chunks.append("\n\n".join(chunks[index : index + 3]))
    scored = sorted(
        ((len(_tokens(chunk, expand=False) & query_tokens), len(chunk), chunk) for chunk in combined_chunks),
        key=lambda item: (item[0], item[1]),
        reverse=True,
    )
    excerpt = scored[0][2]
    return excerpt[:900].strip()


@lru_cache(maxsize=1)
def _documents() -> tuple[tuple[str, str, str, set[str]], ...]:
    docs: list[tuple[str, str, str, set[str]]] = []
    root = _repo_root()
    for path in _allowed_paths():
        try:
            content = path.read_text(encoding="utf-8")[:MAX_DOC_CHARS]
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="ignore")[:MAX_DOC_CHARS]
        relative_path = path.relative_to(root).as_posix()
        docs.append((_title_for(path, content), relative_path, content, _tokens(content, expand=False)))
    return tuple(docs)


class AssistantKnowledgeService:
    def search(self, *, question: str, limit: int = 5) -> list[KnowledgeHit]:
        query_tokens = _tokens(question)
        if not query_tokens:
            return []
        hits: list[KnowledgeHit] = []
        for title, path, content, doc_tokens in _documents():
            score = len(query_tokens & doc_tokens)
            if path.startswith("docs/assistant/"):
                score += 10 + len(query_tokens & doc_tokens)
            if "domain-model" in path:
                score += len(query_tokens & doc_tokens)
            if any(token in path for token in query_tokens):
                score += 2
            if score <= 0:
                continue
            hits.append(
                KnowledgeHit(
                    title=title,
                    path=path,
                    excerpt=_best_excerpt(content, query_tokens),
                    score=score,
                )
            )
        hits.sort(key=lambda item: (item.score, item.path.startswith("docs/assistant/"), item.path), reverse=True)
        return hits[:limit]

    def context_for_llm(self, *, hits: list[KnowledgeHit]) -> str:
        parts = []
        for hit in hits:
            parts.append(f"Fonte: {hit.path}\n{hit.excerpt}")
        return "\n\n---\n\n".join(parts)[:8000]


assistant_knowledge_service = AssistantKnowledgeService()
