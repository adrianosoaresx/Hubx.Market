# Assistant Module

## Responsabilidade

O módulo `assistant` fornece um assistente operacional para owners/admins em `/ops/assistant/`.

O MVP é um guia interno:

- responde perguntas sobre uso eficiente do Hubx Market;
- usa documentação versionada como fonte de conhecimento;
- salva histórico tenant-scoped sanitizado;
- usa LLM quando configurado e fallback textual quando indisponível;
- não consulta dados reais de catálogo, pedidos, clientes, pagamentos ou checkout;
- não executa ações operacionais.

## Entidades

### AssistantConversation

Conversa tenant-scoped iniciada por um owner/admin.

Campos principais:

- `tenant_id`
- `owner_id` opcional
- `owner_email`
- `title`
- timestamps

### AssistantMessage

Mensagem da conversa.

Campos principais:

- `conversation_id`
- `role`: `user`, `assistant` ou `system`
- `source`: `user`, `llm`, `fallback` ou `system`
- `content` sanitizado
- `sources` com lista sanitizada de fontes consultadas
- `created_at`

### AssistantFeedback

Feedback simples sobre resposta do assistente.

Campos principais:

- `message_id`
- `value`: `useful` ou `not_useful`
- `comment` sanitizado opcional
- `created_at`

## Fontes de conhecimento

O MVP usa busca textual simples, sem embeddings/vector DB, sobre:

- `docs/assistant/*` como fonte primária em linguagem de owner/admin;
- `docs/modules/*`
- `docs/ui/*`
- `docs/architecture-overview.md`
- `docs/context-map.md`
- `docs/module-boundaries.md`
- `docs/request-lifecycle.md`
- `docs/domain-model.md`
- `docs/events-map.md`
- `docs/implementation-inventory.md`

`docs/assistant/*` deve concentrar perguntas, passos e boas práticas orientadas a lojistas. A documentação técnica continua como apoio e fallback.

O arquivo `docs/assistant/roteiro-de-avaliacao.md` documenta perguntas reais do MVP, mas não entra na base pesquisável para evitar contaminar respostas.

## Segurança

- todo histórico é isolado por `tenant_id`;
- conteúdo salvo passa por sanitização e truncamento;
- metadados de auditoria não incluem pergunta nem resposta;
- segredos, tokens, API keys e senhas detectáveis são redigidos;
- o assistente deve responder que não encontrou base quando a documentação não sustentar a resposta.

## Lifecycle

Request `/ops/assistant/`
→ tenant resolution
→ owner context/gate `/ops/`
→ view fina
→ `assistant.application.assistant_query_service`
→ busca em documentação
→ LLM opcional ou fallback
→ persistência de conversa/mensagens
→ `AuditLog` tenant-scoped `assistant.question_answered`
→ response.

## Avaliação

Use o command:

```bash
python backend/manage.py assistant_knowledge_smoke --fail-on-error
```

Ele valida o roteiro inicial de perguntas reais, termos esperados e fonte principal esperada em `docs/assistant/*`.

## Evolução futura

Fases futuras podem adicionar contexto real da loja por providers tenant-scoped explícitos e ações guiadas com permissões próprias. Essas fases não fazem parte do MVP.
