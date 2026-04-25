
# Scalability Strategy — Hubx Market

Este documento descreve a **estratégia de escalabilidade** do Hubx Market.

Hubx Market é um SaaS multi-tenant de e-commerce. A arquitetura deve permitir crescimento em:

- número de lojas (tenants)
- número de produtos
- volume de pedidos
- tráfego de usuários
- integrações externas

O objetivo deste documento é orientar decisões técnicas para garantir que o sistema continue performático conforme cresce.

---

# Princípios de escalabilidade

1. **Escalar horizontalmente sempre que possível**
2. **Separar responsabilidades**
3. **Evitar gargalos centralizados**
4. **Usar cache estrategicamente**
5. **Processar tarefas pesadas de forma assíncrona**

---

# Escalabilidade da aplicação

A aplicação backend pode escalar horizontalmente.

Arquitetura típica:

Load Balancer
→ múltiplas instâncias Django
→ Redis
→ PostgreSQL

Cada instância da aplicação deve ser **stateless**.

Sessões devem ser armazenadas em:

- Redis
ou
- banco

Nunca em memória local.

---

# Escalabilidade do banco de dados

Inicialmente:

PostgreSQL único.

Com crescimento:

1. **Leitura replicada (read replicas)**

Aplicação pode direcionar:

- escrita → master
- leitura → replicas

2. **Particionamento por tenant (futuro)**

Quando necessário, dados podem ser particionados usando:

tenant_id

3. **Separação de bases por domínio (extremo crescimento)**

Exemplo:

orders DB
catalog DB
analytics DB

---

# Estratégia multi-tenant

Modelo inicial:

- banco único
- isolamento lógico por `tenant_id`

Vantagens:

- simplicidade operacional
- consultas centralizadas
- menor custo

Escala suportada:

- milhares de lojas
- milhões de produtos
- milhões de pedidos

Quando necessário:

- shard por tenant
- mover tenants grandes para bancos dedicados

---

# Escalabilidade de workers

Tarefas assíncronas executadas por **Celery workers**.

Filas típicas:

- emails
- webhooks
- integração com gateway
- atualização de estoque
- notificações

Readiness atual:

- notificações já possuem comando operacional `process_email_logs` para dry-run/batch tenant-scoped
- Celery deve chamar a mesma boundary de application quando for habilitado
- envio real permanece atrás de configuração explícita de provider/backend e `NOTIFICATIONS_EMAIL_DRY_RUN=0`
- notifications agora também expõe tasks Celery finas:
  - `notifications.process_email_log`
  - `notifications.process_planned_email_logs`
- ambas reaproveitam commands application e preservam tenant scope
- notifications expõe métricas Prometheus protegidas por token em:
  - `/notifications/metrics/email-logs/`
  - métrica `hubx_notifications_email_log_total`

Escalabilidade:

mais workers → maior throughput.

---

# Escalabilidade de cache

Redis usado para:

- cache de queries
- sessões
- rate limiting
- filas Celery

Boas práticas:

- cachear listagens populares
- cachear configurações do tenant
- evitar cachear dados altamente mutáveis

---

# Escalabilidade do catálogo

Catálogo pode crescer muito.

Estratégias:

- índices adequados
- paginação obrigatória
- evitar SELECT *
- carregar apenas campos necessários

Busca avançada futura:

- ElasticSearch
ou
- Meilisearch

---

# Escalabilidade de mídia

Imagens e arquivos devem ser armazenados em storage externo.

Exemplo:

- S3
- Cloudflare R2

Benefícios:

- CDN global
- menor carga no servidor
- alta disponibilidade

---

# Escalabilidade de eventos

Sistema orientado a eventos permite:

- desacoplamento
- processamento paralelo
- automações

Eventos são processados por Celery.

Exemplo:

order.created
payment.paid
shipment.sent

---

# Escalabilidade de tenants grandes

Quando um tenant crescer muito:

Possíveis estratégias:

1. mover para banco dedicado
2. mover para cluster dedicado
3. separar serviços críticos

Exemplo:

tenant enterprise
→ cluster dedicado

---

# Observabilidade

Monitoramento obrigatório:

- tempo de resposta
- erros HTTP
- uso de CPU
- uso de memória
- latência do banco

Ferramentas:

Prometheus
Grafana

---

# Estratégia de evolução

Fase 1
→ monólito modular Django

Fase 2
→ monólito escalado horizontalmente

Fase 3
→ extração de serviços específicos

Exemplo:

- serviço de busca
- serviço de analytics
- serviço de recomendações

---

# Objetivo

Garantir que o Hubx Market possa crescer:

- sem reescrever arquitetura
- sem downtime significativo
- mantendo desempenho consistente
