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
scripts/backup/    backup diário do banco (dump, cifra, R2, retenção) e restauração
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
uv run --env-file .env python -m app.comandos.dados_ficticios   # inclui um admin fictício

# 4. API em http://127.0.0.1:8000/api/saude
uv run --env-file .env uvicorn app.main:app --reload

# 5. Front em http://localhost:5173 (o Vite repassa /api para a API)
cd ../web && npm ci && npm run dev
```

Os papéis `dono` e `app` só existem no Postgres local depois que os testes rodaram uma vez
(passo 2). As variáveis estão explicadas em `api/.env.example`.

## Backup

Todo dia às 03:00 (Recife), o workflow `Backup` (`.github/workflows/backup.yml`) faz o
`pg_dump` da produção com o papel `backup` (só leitura), cifra com `age` e envia ao bucket
privado `portal-capibaribe-backups`: `diarios/AAAA-MM-DD.dump.age` e, no dia 1,
`mensais/AAAA-MM.dump.age`. Guarda 30 diários + 12 mensais. No dia 2 de cada mês ele restaura o
backup num Postgres temporário e confere tudo; se algo falhar, o GitHub manda e-mail.
Decisões: [ADR-0007](docs/adr/0007-backup.md) e [ADR-0009](docs/adr/0009-backup-bucket-papel-e-chave.md).

- **Disparar à mão:** `gh workflow run backup.yml -f restaurar=true` (backup + restauração de
  teste) ou `gh workflow run backup.yml` (só backup).
- **Testar o ciclo inteiro localmente** (Postgres do passo 1 de "Rodar localmente", S3 falso,
  nada de R2 nem Neon): `scripts/backup/testes/testar-ciclo.sh`. Precisa de Docker, `uv` e
  `age`; sem `pg_dump` 17 no PATH, usa o da imagem `postgres:17`.

### Restaurar num desastre (passo a passo)

O script nunca escreve por cima de um banco em uso: restaura num banco **novo e vazio**, confere,
e só então a aplicação passa a usá-lo.

1. **Ferramentas:** cliente do Postgres **17** (`pg_restore`, `psql`), `age` e `uv`. Em outra
   versão, aponte `PG_BIN` para a pasta do 17.
2. **Chave privada:** a cópia offline do dono, num arquivo com permissão 600
   (`chmod 600 chave.age`). O segredo `BACKUP_AGE_KEY` do GitHub não pode ser lido de volta.
3. **O backup:** baixe o `.dump.age` pelo painel da Cloudflare (R2 → `portal-capibaribe-backups`
   → `diarios/`), ou deixe o script baixar, com as variáveis `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`,
   `R2_SECRET_ACCESS_KEY` e `R2_BUCKET` de uma chave do bucket de backups.
4. **Banco vazio:** no Neon, crie o banco `portal_restaurado` com dono `dono` (os papéis `dono`
   e `app` já existem no projeto). Use a URL **direta** do `dono` (host sem `-pooler`).
5. **Restaurar e conferir** (da raiz do repositório):
   ```sh
   head="$(uv run --directory api --frozen alembic heads | awk '{print $1}')"
   BACKUP_AGE_KEY_FILE=chave.age scripts/backup/restaurar.sh \
     --destino "postgresql://dono:...@<host-direto>/portal_restaurado?sslmode=require" \
     --arquivo 2026-10-05.dump.age --head "$head"
   ```
   Sem `--arquivo`, baixa o diário mais novo (ou `--objeto diarios/AAAA-MM-DD.dump.age`). Se a
   produção estava numa migração mais velha que a `main`, a conferência acusa; rode sem `--head`
   e aplique as migrações depois (`alembic upgrade head`, como `dono`).
   O script termina com "restauração ok" e a contagem de linhas por tabela; qualquer outra
   saída é falha, e nada foi gravado pela metade (o `pg_restore` roda numa transação só).
6. **Apontar a aplicação:** na Vercel, troque o nome do banco em `DATABASE_URL` (e no
   `DATABASE_URL_DONO` de onde as migrações rodam) para `portal_restaurado` e faça um redeploy. Confira
   `/api/saude` e um login. O banco antigo fica guardado até a causa do desastre ser entendida.
7. **Papel de backup:** rode `scripts/backup/criar-papel-backup.sql` no banco novo e atualize o
   segredo `BACKUP_DATABASE_URL` (o backup das 03:00 passa a ler o banco novo).

## O primeiro administrador (produção)

A carga inicial não dá papel nenhum: uma conta de administrador com a senha inicial, que todo
mundo conhece, seria tomada por quem conhece o padrão. A sequência é:

1. deploy (migrações aplicadas e carga feita);
2. o administrador faz o **primeiro acesso** na unidade dele, pelo Portal;
3. de `api/`, com a URL do usuário `app`:
   `uv run python -m app.comandos.promover_admin <login>` (recusa unidade que ainda não fez o
   primeiro acesso; rodar de novo não muda nada; fica registrado no histórico).

A unidade real só aparece na linha de comando, nunca no repositório. Detalhes em
`docs/superpowers/specs/m1-contrato.md`, seção 2.5.

Várias cópias de trabalho ao mesmo tempo (um agente por épico): cada uma usa o próprio banco de
teste, com `PORTAL_TESTE_BANCO=portal_teste_<nome> uv run pytest`. Um `portal_dev` criado antes
da migração 0002 (celulares com máscara) precisa ser recriado.

Testes do front: `npm test` em `web/` roda os testes de componente (Vitest) e, depois do
`npm run build`, os de configuração (cabeçalhos e `vercel.json`).

Antes do primeiro commit: `pre-commit install` e `npm ci --prefix web` (o pre-commit roda ruff,
eslint e tsc).

Autor: Erick Santos Dantas
