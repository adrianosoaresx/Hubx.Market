# Customers

## Responsabilidade
Gerenciar compradores, perfis, contato, endereços e visão operacional da conta.

## Entidades principais
- Customer
- CustomerAddress
- CustomerPreference

## Casos de uso
- listar clientes
- detalhar cliente
- manter dados de perfil e contato
- manter endereços usados na experiência logada do cliente

## Regras de negócio
- customer pertence a um tenant específico
- customer não deve ser misturado com accounts

## Integração UI
- views HTTP devem permanecer finas em `interfaces/`
- templates oficiais do Design System podem ser usados como contrato de apresentação
- adapters de contexto podem preparar dados para list/detail sem mover regra de negócio para a view
- queries de leitura para Admin Customers devem viver fora das views; enquanto o módulo ainda não expõe modelos/serviços reais, a camada `application/` pode centralizar fallback temporário sem quebrar o contrato dos templates

## Persistência mínima disponível
- `Customer` existe como base persistida mínima para leituras reais do Admin Customers
- `CustomerAddress` agora existe como base persistida mínima para futuras leituras reais da área logada do cliente
- a estrutura cobre o mínimo necessário para:
  - listagem administrativa
  - detalhe administrativo básico
  - endereços da experiência logada
  - identificação e isolamento por tenant

## O que a query layer poderá consumir depois
- de `Customer`:
  - `slug`
  - `reference`
  - `full_name`
  - `email`
  - `phone`
  - `status`
  - `account_type`
  - `last_seen_at`
  - `created_at`
  - `updated_at`
- de `CustomerAddress`:
  - `label`
  - `recipient_name`
  - `line_1`
  - `line_2`
  - `district`
  - `city`
  - `state`
  - `postal_code`
  - `is_default`
- de fontes já existentes reaproveitáveis:
  - `orders.Order` e `orders.OrderItem` para list/detail de pedidos do cliente
  - `accounts.AccountProfile` para identidade e preferências

## O que ainda permanece faltando
- resolução tenant-aware explícita entre `AccountProfile`, `Customer` e `Order`
- agregados reais de pedidos por cliente autenticado
- histórico operacional mais rico
- preferências além do escopo atual de `AccountProfile`

## Estado atual da leitura administrativa
- `Admin Customers` já pode ler `Customer` persistido quando registros existem
- a integração real cobre:
  - identidade básica
  - contato
  - status
  - tipo de conta
  - timestamps administrativos
- ainda permanece em fallback controlado:
  - resumo real de pedidos
  - histórico operacional mais rico

## Estado atual da readiness para customer area
- a próxima wave de persisted read da área logada já pode reaproveitar:
  - `AccountProfile` para perfil
  - `Order`/`OrderItem` para pedidos
  - `CustomerAddress` para endereços
- o próximo passo deixa de ser modelagem e passa a ser integração de leitura tenant-aware
