# Brand – Hubx Market

## Nome oficial
- Marca: Hubx
- Produto: Hubx Market
- Domínio principal: `hubx.market`

## Posicionamento
Hubx Market é a infraestrutura de e-commerce da Hubx voltada para empresas que desejam criar, operar e escalar lojas online.

## Taglines sugeridas
- E-commerce infrastructure for modern businesses
- Crie, gerencie e escale sua loja online
- Plataforma SaaS de e-commerce para negócios modernos

## Domínios oficiais
- `hubx.market`
- `app.hubx.market`
- `api.hubx.market`
- `docs.hubx.market`
- `cdn.hubx.market`
- `<tenant>.hubx.market`

## Convenção de escrita
- Nome curto: Hubx Market
- Não usar grafias alternativas
- Em documentação técnica, preferir "Hubx Market"
- Em namespace Python, usar `hubx_market`

## Identidade visual inicial
- Logo highlight: `#FFE797`
- Logo gold: `#D6A937`
- Primary: `#9A6410`
- Primary hover/shadow: `#794A0C`
- Conversion Primary: `#9A6410` com texto branco; tenants podem sobrescrever apenas por cor hexadecimal validada com contraste AA.
- Background/Text: `#0F172A`

As cores funcionais de feedback continuam semânticas e não devem ser substituídas por ouro quando comunicarem sucesso, erro, alerta ou informação operacional.

## Uso do nome em exemplos
- `lojax.hubx.market`
- `nike.hubx.market`
- `demo.hubx.market`

## Identidade em produto
- Em storefront tenant-owned, a marca principal é a loja.
- Hubx Market aparece como plataforma operadora, especialmente no footer.
- Em admin da loja, a identidade do tenant aparece como contexto operacional.
- Em project/platform owner, Hubx Market é a marca principal.
- O hero institucional da storefront deve priorizar imagem real e copy da loja; Hubx Market não deve assumir a narrativa principal em host tenant-owned.

## Fallback de logo
- Quando `Tenant.logo_url` estiver configurado, usar essa imagem como marca principal da loja em shells tenant-owned e blocos institucionais.
- Quando `Tenant.conversion_primary_color` estiver configurado, usar essa cor apenas para CTAs primários de conversão e estados de foco correlatos, mantendo feedback funcional separado.
- Quando não houver imagem de logo, usar monograma derivado do nome exibido.
- O nome comercial preferencial é `store_display_name` quando existir.
- Na ausência de nome comercial, usar `request.tenant.name`.
- O corte atual aceita URL pública de logo; upload/storage de arquivo permanece fora desta etapa.

## Footer
- Texto padrão permitido: "Operado com Hubx Market".
- Evitar transformar o footer em bloco promocional da Hubx.
- Links úteis da loja devem ficar no footer para preservar header limpo.
