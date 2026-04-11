# Shipping Architecture

## Estratégia
Frete calculado por API desde o MVP.

## Fluxo
1. customer informa CEP
2. backend consulta API de frete
3. retorna opções disponíveis
4. customer escolhe serviço
5. valor integra o pedido

## Shipment
Após envio, o pedido recebe:
- carrier
- service
- tracking_code
