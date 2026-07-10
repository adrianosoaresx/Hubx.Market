# Deploy

Artefatos de deploy e infraestrutura de publicação.

## VPS Traefik

`docker-compose.vps.yml` publica o Hubx Market como stack Docker isolada para a VPS compartilhada.

Contrato operacional:

- projeto Compose: `hubxmarket`
- domínio principal: `hubx.market`
- hosts roteados: `hubx.market`, aliases da plataforma e lojas publicadas explicitamente nas labels Traefik
- DNS pode usar wildcard `*.hubx.market`, mas TLS via ACME `tlschallenge` exige host explícito até existir emissão wildcard por DNS challenge
- rede externa Traefik: `docker_traefik`
- arquivo de ambiente local da VPS: `.env.vps` no mesmo diretório do compose

Comando padrão na VPS:

```bash
docker compose --env-file .env.vps -p hubxmarket -f docker-compose.vps.yml up -d --build
```
