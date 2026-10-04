# Spec · M0 Fundação

| | |
|---|---|
| **Marco** | M0 (`docs/07-roadmap.md`, seção 4) |
| **Base** | `04-modelo-de-dados.md` v0.1, `05-arquitetura.md` v0.1, ADR-0001/0002/0003/0005/0007 |
| **Criado em** | 04/10/2026 |

## 1. Objetivo

O caminho inteiro funcionando de ponta a ponta, vazio: navegador → Vercel (front estático +
FastAPI) → Neon. Nenhuma tela de morador.

## 2. O que entra

### 2.1 Repositório

```
web/                 React + TS (Vite): página "no ar"
api/
  app/
    main.py          FastAPI, handler global de erro
    config.py        variáveis de ambiente
    banco.py         engine (NullPool), sessão, conversão da URL
    rotas/           saude.py, diagnostico.py
    servicos/        carga_inicial.py, dados_ficticios.py, erros.py
    modelos/         SQLAlchemy 2 (bloco, unidade, unidade_papel, sessao, historico, erro)
    comandos/        CLIs: carga_inicial, dados_ficticios
  migracoes/         Alembic
  testes/            pytest contra Postgres de verdade
vercel.json          services: web + api; /api/* → api; região gru1
.github/workflows/   ci.yml
.github/dependabot.yml
```

### 2.2 Banco (migração inicial)

Tabelas `bloco`, `unidade`, `unidade_papel`, `sessao`, `historico`, `erro` exatamente como no
modelo de dados (seção 3.1 e 3.6), com:

- PK `bigint generated always as identity`; datas `timestamptz`.
- `bloco.numero` único, 1 a 9. `unidade.numero` com 3 dígitos, único por bloco; `andar` 0 a 7.
- `unidade.login` único, **gerado pelo banco** (trigger a partir de `bloco.numero` + `numero`):
  a aplicação não consegue gravar um login fora do padrão.
- enum `papel` (`admin`, `comissao`, `sindico`, `conselho`); índice único parcial
  `(unidade_id, papel) where retirado_em is null`.
- `sessao.token_hash` único.

Permissões do papel `app` (a migração roda como `dono`, dono das tabelas):

| Tabela | SELECT | INSERT | UPDATE | DELETE | Por quê |
|---|---|---|---|---|---|
| `bloco` | sim | sim | sim | **não** | bloco é desativado, não apagado |
| `unidade` | sim | sim | sim | **não** | unidade é desativada, não apagada |
| `unidade_papel` | sim | sim | sim | **não** | papel retirado recebe `retirado_em` |
| `sessao` | sim | sim | sim | sim | dado técnico, não oficial |
| `historico` | sim | sim | **não** | **não** | só inclusão (RNF-14, H-11) |
| `erro` | sim | sim | não | sim | limpeza de 90 dias |

O papel `app` **não é criado pela migração** (em produção nasce por SQL, com senha fora do
repositório). Se ele não existir, a migração falha com mensagem clara. Os testes e o CI criam
`dono` e `app` antes de migrar.

### 2.3 API

- `GET /api/saude` → `200 {"status": "ok", "unidades": <count(*) de unidade>}`.
- Handler global: toda exceção não tratada grava uma linha em `erro` (`rota` no formato
  `MÉTODO /caminho/da/rota` usando o molde da rota, `tipo` = classe, `mensagem` = primeira
  linha da mensagem, sem parâmetros SQL nem `DETAIL` do Postgres, até 500 caracteres) e
  responde `500 {"detail": "Erro interno"}`. Se gravar o erro falhar, registra no log e
  responde 500 mesmo assim.
- `POST /api/diagnostico/erro`: dispara uma exceção de propósito **só** se o cabeçalho
  `X-Portal-Diagnostico` bater (comparação em tempo constante) com
  `PORTAL_DIAGNOSTICO_SEGREDO`. Sem a variável, ou com cabeçalho errado/ausente: `404`, igual a
  uma rota inexistente.
- Banco via `DATABASE_URL`; `postgres://` e `postgresql://` viram `postgresql+psycopg://`.
  `NullPool` (função serverless; o pooler do Neon faz o pool) e `prepare_threshold=None`
  (pooler em modo transação).

### 2.4 Carga inicial (`python -m app.comandos.carga_inicial`)

- 5 blocos (`Bloco 1`…`Bloco 5`), 320 unidades (andares 0–7, posições 01–08), senha
  `mudar123` em Argon2id (`argon2-cffi`, parâmetros padrão), `precisa_trocar_senha = true`.
- Papel `admin` na unidade cujo login vem de `PORTAL_ADMIN_UNIDADE` (obrigatória; no repo, só a
  fictícia `1101`).
- Idempotente: rodar de novo não duplica nem re-hasheia; só cria o que falta.
- Registra no `historico` (`carga_inicial`, `papel_concedido`) quando cria algo.

### 2.5 Dados fictícios (`python -m app.comandos.dados_ficticios`)

- Recusa rodar sem `PORTAL_AMBIENTE` igual a `local` ou `teste`.
- Ativa uma parte das unidades com nomes inventados, celulares `(81) 90000-0xxx` e e-mails
  `@example.com`; dá o papel `comissao` a uma unidade fictícia. Determinístico e idempotente.

### 2.6 Front

Página única "no ar" com a identidade do protótipo (tokens `--mata #1f5e3b`, `--ipe #e8b22a`,
`--papel #f4f6f2`, Atkinson Hyperlegible servida pelo próprio Portal via `@fontsource`, tema
escuro por `prefers-color-scheme`). Mostra o resultado de `/api/saude` ("320 unidades
cadastradas") ou uma mensagem neutra se a API não responder.

### 2.7 Qualidade

- Pre-commit: hooks atuais + `ruff` (lint e format) + `eslint` e `tsc` do `web/`.
- CI (GitHub Actions): lint (ruff, eslint, tsc), `vite build`, testes da API num service
  container Postgres 17, e "migrações do zero" (upgrade head → downgrade base → upgrade head).
- Dependabot: uv (`/api`), npm (`/web`), github-actions.

## 3. Fica de fora

Qualquer tela além da página "no ar"; login, sessão de verdade e CSRF (M1); trigger do
"último admin" (H-09, M1); limpeza automática de `erro` após 90 dias (precisa de agendador,
entra junto do backup); Vitest no front (nada para testar ainda).

## 4. Critério de pronto local

Testes verdes contra Postgres local; `pre-commit run --all-files` verde; `vite build` ok;
migrações do zero ok; `uvicorn` respondendo `/api/saude` com 320 após a carga; erro forçado
gravado em `erro`.
