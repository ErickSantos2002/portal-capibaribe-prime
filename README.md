# Portal Capibaribe Prime

Sistema web do condomínio **Capibaribe Prime Residence** (Recife/PE, 320 unidades, em obra até
2028). Concentra num lugar só o que hoje se perde no grupo de WhatsApp: **avisos oficiais,
enquetes e documentos** na fase de obra; reservas, chamados e encomendas depois da entrega.

**Protótipo navegável:** https://capibaribe-prototipo.vercel.app
(dados fictícios; já está em teste com os futuros vizinhos, e as opiniões voltam pro protótipo)

## Em que pé está

| Etapa | Situação |
|---|---|
| Visão, requisitos, histórias, modelo de dados, arquitetura | Feito (`docs/01` a `05`) |
| Protótipo de alta fidelidade | Feito e publicado (`prototipo/`, `docs/06`) |
| Teste com moradores | Em andamento |
| Roadmap | Feito (`docs/07`): 6 marcos na E1, primeiro uso real no M1 |
| Código do app | M0 (fundação) no ar em https://portal-capibaribe-prime.vercel.app · próximo: M1 (acesso e mural) |

## Como foi pensado

- **Quem manda no desenho é a pessoa menos acostumada com tecnologia.** A persona de teste é a
  Dona Socorro, 62 anos: fonte Atkinson Hyperlegible, alvos de toque grandes, textos na voz do
  morador ("Bloco e apartamento", nunca "login").
- **Uma conta por unidade**, não por pessoa: é como o condomínio já funciona (um voto por
  apartamento) e dispensa aprovação de cadastro.
- **Custo zero de verdade**, sem depender de ninguém: Vercel Hobby, Neon Free, Cloudflare R2.
  Cada escolha está justificada, com o que foi descartado, em [`docs/adr/`](docs/adr/README.md).
- **LGPD desde o modelo de dados:** só nome, celular, e-mail e unidade. Sem CPF, contrato ou renda.

## Stack

React + TypeScript (Vite) · FastAPI + SQLAlchemy 2 + Alembic (Python 3.12) · PostgreSQL 17.

## Estrutura

```
web/               front-end React (Vite)
api/               FastAPI: app/ (rotas, serviços, modelos, comandos), migracoes/, testes/
docs/              visão, requisitos, histórias, modelo de dados, arquitetura, protótipo, roadmap
docs/adr/          registros de decisão de arquitetura
prototipo/         protótipo em HTML único, publicado na Vercel
scripts/dev/       teste automatizado do protótipo e gerador da imagem de prévia
vercel.json        front + API no mesmo projeto: /api/* vai para a FastAPI, o resto para o front
```

## Rodar localmente

Precisa de Docker, [uv](https://docs.astral.sh/uv/) e Node. O Python (3.12) vem do uv.

```sh
# 1. Postgres de desenvolvimento (só em 127.0.0.1)
docker run -d --name portal-pg-m0 -e POSTGRES_PASSWORD=teste -p 127.0.0.1:55432:5432 postgres:17

# 2. Testes da API: criam sozinhos os papéis dono e app e um banco descartável
cd api && uv run pytest

# 3. Banco de desenvolvimento: papéis, migração (como dono), carga e dados fictícios (como app)
docker exec portal-pg-m0 psql -U postgres -c "create database portal_dev owner dono"
cp .env.example .env
uv run --env-file .env alembic upgrade head
uv run --env-file .env python -m app.comandos.carga_inicial
uv run --env-file .env python -m app.comandos.dados_ficticios

# 4. API em http://127.0.0.1:8000/api/saude
uv run --env-file .env uvicorn app.main:app --reload

# 5. Front em http://localhost:5173 (o Vite repassa /api para a API)
cd ../web && npm ci && npm run dev
```

Os papéis `dono` e `app` só existem no Postgres local depois que os testes rodaram uma vez
(passo 2). As variáveis estão explicadas em `api/.env.example`.

Antes do primeiro commit: `pre-commit install` e `npm ci --prefix web` (o pre-commit roda ruff,
eslint e tsc).

Autor: Erick Santos Dantas
