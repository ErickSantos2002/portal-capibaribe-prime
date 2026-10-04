# M0 Fundação · Plano de implementação

> **Para agentes:** executar tarefa por tarefa, com TDD (`superpowers:test-driven-development`).
> Passos em checkbox (`- [ ]`).

**Objetivo:** esqueleto do Portal no ar de ponta a ponta: Vite + FastAPI + Postgres, migração
inicial com permissões, carga das 320 unidades, tabela `erro`, CI e Vercel.

**Arquitetura:** monorepo com `web/` (estático) e `api/` (FastAPI como Vercel Function), unidos
pelo `vercel.json` no modelo `services`. A API fala com o Postgres por SQLAlchemy 2 síncrono
(psycopg 3, `NullPool`). Regras de permissão moram no banco e são provadas por teste que
conecta como o papel `app`.

**Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2, Alembic, psycopg 3, argon2-cffi, pytest,
ruff · Node 26, Vite, React 19, TypeScript, ESLint (flat config) · Postgres 17.

**Spec:** `docs/superpowers/specs/m0-fundacao.md`

## Restrições globais

- Python **3.12** fixado por `api/.python-version`; nunca o python3 do sistema.
- Textos, comentários e commits em PT-BR com acentuação.
- Nenhum dado pessoal no repo; unidade de exemplo/teste é sempre **1101**.
- Postgres de teste: container `portal-pg-m0` em `127.0.0.1:55432` (nunca o `radar-postgres`).
- Sem Neon, sem Vercel CLI linkada, sem push.

## Foco de revisão (o que os testes de cada tarefa precisam cobrir)

1. Exceção do SQLAlchemy carregando parâmetros (ex.: e-mail num INSERT) → a linha em `erro` não
   pode conter o valor. Teste em T4.
2. Banco fora do ar quando o handler tenta gravar o erro → resposta continua 500 limpo, sem
   exceção dupla. Teste em T4.
3. Cabeçalho de diagnóstico vazio, errado ou variável não configurada → 404, nunca 500. T4.
4. `PORTAL_ADMIN_UNIDADE` ausente ou apontando para unidade que não existe (`9999`) → carga
   falha com mensagem clara, sem deixar meio-carregado. T5.
5. `DATABASE_URL` no formato do Neon (`postgres://...?sslmode=require`) → vira
   `postgresql+psycopg://` mantendo os parâmetros. T3.

---

### T1: Esqueleto da API e ferramentas

**Arquivos:** `api/pyproject.toml`, `api/.python-version`, `api/uv.lock`, `api/app/__init__.py`,
`api/app/main.py`, `api/testes/test_app.py`, `.gitignore`.

- [ ] `uv init`/edição manual do `pyproject.toml` (`requires-python = ">=3.12,<3.13"`), deps:
  `fastapi`, `sqlalchemy>=2`, `alembic`, `psycopg[binary]`, `argon2-cffi`; dev: `pytest`,
  `httpx`, `ruff`, `uvicorn`.
- [ ] Teste falhando: `GET /api/inexistente` → 404 (prova que o app sobe).
- [ ] `main.py` mínimo; teste passa. Ruff configurado (`[tool.ruff]`, regras E,F,I,UP,B).
- [ ] Commit.

### T2: Modelos + migração inicial + permissões

**Arquivos:** `api/app/modelos/*.py`, `api/alembic.ini`, `api/migracoes/env.py`,
`api/migracoes/versions/0001_tabelas_de_acesso.py`, `api/testes/conftest.py`,
`api/testes/test_migracoes.py`, `api/testes/test_permissoes.py`.

**Produz:** fixtures `url_dono`, `url_app`, `engine_dono`, `engine_app`, `limpar_banco`.

- [ ] `conftest.py`: conecta como superusuário (`PORTAL_TESTE_ADMIN_URL`, padrão
  `postgresql://postgres:teste@127.0.0.1:55432/postgres`), cria os papéis `dono` e `app` se
  não existirem, recria o banco `portal_teste` com dono `dono` e roda `alembic upgrade head`
  como `dono`.
- [ ] Testes falhando:
  - `test_upgrade_downgrade_upgrade` num banco à parte.
  - `test_migracao_falha_sem_papel_app` (`-x papel_app=papel_que_nao_existe`) → erro com
    "papel" e "não existe" na mensagem.
  - `test_login_gerado_pelo_banco` (bloco 1 + `'101'` → `'1101'`, mesmo se o INSERT mandar
    outro login).
  - `test_app_nao_apaga_*` para `bloco`, `unidade`, `unidade_papel`, `historico` →
    `InsufficientPrivilege`.
  - `test_app_nao_altera_historico` → `InsufficientPrivilege`.
  - `test_app_insere_historico_e_erro`, `test_app_apaga_erro_e_sessao` (o que precisa
    funcionar funciona).
  - `test_um_papel_em_vigor_por_tipo` (índice parcial).
- [ ] Implementar modelos e migração escrita à mão (DDL + trigger do login + GRANT/REVOKE).
- [ ] Commit.

### T3: Configuração e conexão

**Arquivos:** `api/app/config.py`, `api/app/banco.py`, `api/testes/test_banco.py`.

**Produz:** `url_sqlalchemy(url: str) -> str`, `obter_engine() -> Engine`,
`obter_sessao() -> Iterator[Session]` (dependência FastAPI).

- [ ] Testes falhando: `postgres://u:s@h/db?sslmode=require` →
  `postgresql+psycopg://u:s@h/db?sslmode=require`; `postgresql://` idem; `postgresql+psycopg://`
  intacto; vazio → `RuntimeError` com "DATABASE_URL".
- [ ] Implementar; engine com `poolclass=NullPool`, `connect_args={"prepare_threshold": None}`.
- [ ] Commit.

### T4: `/api/saude`, handler de erro e rota de diagnóstico

**Arquivos:** `api/app/rotas/saude.py`, `api/app/rotas/diagnostico.py`,
`api/app/servicos/erros.py`, `api/app/main.py`, `api/testes/test_saude.py`,
`api/testes/test_erros.py`.

- [ ] Testes falhando:
  - saúde com banco vazio → `{"status":"ok","unidades":0}`; com 3 unidades → 3.
  - diagnóstico: sem variável → 404; cabeçalho ausente/errado/vazio → 404; certo → 500 e uma
    linha em `erro` com `rota = "POST /api/diagnostico/erro"` e `tipo = "ErroDiagnostico"`.
  - `mensagem_segura` de um `IntegrityError` com parâmetro `fulano@example.com` não contém o
    e-mail nem `DETAIL`.
  - handler com banco inacessível → 500, sem exceção vazando do handler.
- [ ] Implementar (o teste roda a API com `DATABASE_URL` = URL do `app`).
- [ ] Commit.

### T5: Carga inicial e dados fictícios

**Arquivos:** `api/app/servicos/carga_inicial.py`, `api/app/servicos/dados_ficticios.py`,
`api/app/comandos/carga_inicial.py`, `api/app/comandos/dados_ficticios.py`,
`api/testes/test_carga.py`, `api/testes/test_dados_ficticios.py`.

**Produz:** `carregar(sessao, admin_login: str, hasher: PasswordHasher | None = None) -> ResumoCarga`,
`preencher_ficticios(sessao, ambiente: str | None) -> int`.

- [ ] Testes falhando: 5 blocos, 320 unidades, logins `1001`…`5708`; senha verifica
  `mudar123`; `precisa_trocar_senha` em todas; admin em `1101`; rodar 2× não duplica e não
  troca o hash; admin ausente/inexistente → `ErroCarga` e nada gravado; histórico registra.
  Fictícios: recusa sem ambiente; preenche só `@example.com` e `(81) 90000-`; idempotente.
- [ ] Implementar (a carga roda como `app`: só precisa de SELECT/INSERT).
- [ ] Commit.

### T6: Front "no ar"

**Arquivos:** `web/` (scaffold Vite react-ts), `web/src/App.tsx`, `web/src/estilo.css`,
`web/vite.config.ts` (proxy `/api` → `127.0.0.1:8000`), `web/index.html`.

- [ ] Scaffold, `@fontsource/atkinson-hyperlegible`, tokens do protótipo, tema escuro.
- [ ] `npm run lint`, `npx tsc -b`, `npm run build` verdes.
- [ ] Commit.

### T7: Vercel, CI, pre-commit, Dependabot, README

**Arquivos:** `vercel.json`, `.github/workflows/ci.yml`, `.github/dependabot.yml`,
`.pre-commit-config.yaml`, `README.md`, `api/.env.example`.

- [ ] `vercel.json` com `services` (`web`, `api` com `entrypoint: app.main:app`), `regions:
  ["gru1"]`, rewrites `/api/(.*)` → api e `/(.*)` → web, e rewrite SPA no serviço web.
- [ ] CI: jobs `lint`, `web`, `api` (service postgres:17), `migracoes`.
- [ ] Pre-commit: ruff (lint+format) via `astral-sh/ruff-pre-commit`, eslint e tsc como hooks
  `local`/`system` restritos a `^web/`.
- [ ] `pre-commit run --all-files` verde. README curto. Commit.

### T8: Verificação ponta a ponta

- [ ] Banco local `portal_dev`: migração como `dono`, carga como `app`, `uvicorn` →
  `curl /api/saude` = 320; `curl -X POST /api/diagnostico/erro` com o segredo → linha em `erro`.
- [ ] `docs/superpowers/duvidas-m0.md` completo.
