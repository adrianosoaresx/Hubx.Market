# Tenants

## Responsabilidade
Gerenciar tenant, branding, contato, manutenção e onboarding.

## Entidades principais
- Tenant
- StoreTheme
- StoreContact

## Casos de uso
- criar tenant
- ativar manutenção
- configurar identidade visual

## Regras de negócio
- tenant resolvido por subdomínio
- superfícies de commerce devem falhar fechado quando `request.tenant` não estiver resolvido
- subdomínio inexistente sob `HUBX_MARKET_ROOT_DOMAIN` deve responder `404`
- domínios reservados (`www`, `app`, `api`, `docs`, `cdn`) continuam fora da resolução de loja
- `custom_domain` segue como contrato de modelo, mas ainda não participa da resolução HTTP neste estágio

## Clarificação do contrato atual
- a resolução HTTP oficial de tenant continua sendo apenas `subdomain + HUBX_MARKET_ROOT_DOMAIN`
- hosts fora desse domínio principal não devem ser tratados como loja por inferência
- enquanto `custom_domain` não entrar no resolver HTTP, o comportamento esperado para esses hosts é:
  - `request.tenant = None`
  - nenhuma superfície de commerce deve se comportar como se uma loja válida tivesse sido resolvida
- isso mantém o sistema honesto: `custom_domain` hoje é readiness de modelo, não capability ativa

## Contrato futuro mínimo para `custom_domain`
- quando essa capacidade entrar, ela deve definir explicitamente:
  - normalização do host (`lowercase`, sem porta, sem protocolo)
  - unicidade de domínio customizado entre tenants
  - precedência entre `custom_domain`, subdomínio e hosts reservados
  - comportamento explícito para domínio configurado porém tenant inativo
