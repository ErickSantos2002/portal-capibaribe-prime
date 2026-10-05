# M1 Onda 1 · Contrato · Plano de implementação

> **Para agentes:** executar tarefa por tarefa, com TDD (`superpowers:test-driven-development`).
> Passos em checkbox (`- [ ]`). Execução nesta onda: o próprio agente do contrato, em sequência.

**Objetivo:** base do M1 pronta para três épicos em paralelo: migração 0002, contrato da API
(spec + schemas + tipos TS), sessão/permissões/CSRF/histórico testados e casca do front.

**Arquitetura:** a API ganha `app/seguranca/` (sessões, senhas, dependências), `app/erros_api.py`
(formato de erro), `app/servicos/historico.py`, `app/esquemas/` e um roteador vazio por épico já
incluído no `main.py`. O front ganha `react-router` 8, uma casca (`web/src/casca/`) e uma pasta
por épico com tipos, funções de API e páginas de marcação de lugar.

**Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2, Alembic, psycopg 3, argon2-cffi, pytest ·
React 19, TypeScript, Vite 8, react-router 8, Vitest + Testing Library · Postgres 17.

**Spec:** `docs/superpowers/specs/m1-contrato.md`

## Restrições globais

- Python 3.12 via `uv run --frozen`; nunca o python3 do sistema.
- Textos, comentários e commits em PT-BR com acentuação; commit termina com o `Co-Authored-By`.
- Nenhum dado pessoal no repo; unidade de exemplo é sempre fictícia (1101, 2304...).
- Banco de teste desta cópia: `PORTAL_TESTE_BANCO=portal_m1_contrato` (container `portal-pg-m0`).
- Sem push, sem merge, sem Vercel/Neon.
- Nenhum `style=` nem script embutido no front (CSP).

## Foco de revisão

1. Cookie `Secure` não é enviado por `http://` → o `TestClient` precisa de `base_url="https://testserver"`; teste de ida e volta do cookie na Tarefa 3.
2. Papel retirado com a unidade logada → a próxima requisição já recusa (papéis lidos a cada requisição). Teste na Tarefa 3.
3. Dois admins se retirando ao mesmo tempo → um dos dois falha (trava no trigger). Teste com duas conexões na Tarefa 1.
4. Erro 422 devolvendo a senha digitada no corpo da resposta → o formato próprio nunca inclui `input`. Teste na Tarefa 2.
5. Sessão de unidade desativada ou encerrada, ou com mais de 180 dias sem uso → 401. Teste na Tarefa 3.

---

### Tarefa 1: Migração 0002 e modelos

**Arquivos:** `api/migracoes/versions/0002_avisos_e_regras_do_m1.py`, `api/app/modelos/avisos.py`,
`api/app/modelos/acesso.py`, `api/app/modelos/__init__.py`, `api/testes/conftest.py` (TABELAS),
`api/testes/test_migracoes.py`, `api/testes/test_avisos_banco.py`, `api/testes/test_papeis_banco.py`,
`api/app/servicos/dados_ficticios.py` (celular só dígitos, ambiente `previa`).

- [x] Testes falhando: tabelas novas existem após upgrade e somem no downgrade da 0002; `app` não
  apaga `aviso`, `aviso_versao`, `aviso_bloco`, `aviso_leitura`; não altera `aviso_versao`,
  `aviso_bloco`, `aviso_leitura`, nem `aviso.para_todos`/`publicado_por`; altera `fixado` e
  `arquivado_em`; datas carimbadas (`publicado_em`, `criada_em`, `lido_em`, `arquivado_em`,
  `concedido_em`, `retirado_em`); versão pulada (1 → 3) recusada; aviso sem versão 1 ou sem bloco
  recusado no commit; `aviso_bloco` em aviso `para_todos` recusado; retirar o último admin
  recusado com restrição `ultimo_admin`, retirar um de dois admins aceito; papel retirado não
  volta; `app` não muda a coluna `papel`; unidade ativada sem celular recusada; celular com
  máscara recusado; `test_modelos_iguais_ao_banco_migrado` continua verde.
- [x] Implementar a migração (SQL à mão) e os modelos `Aviso`, `AvisoVersao`, `AvisoBloco`,
  `AvisoLeitura` (+ CHECKs novos em `Unidade`).
- [x] Dados fictícios: celular `8190000xxxx`; `previa` aceito em `PORTAL_AMBIENTE`.
- [x] Commit.

### Tarefa 2: Formato de erro, senhas e histórico

**Arquivos:** `api/app/erros_api.py`, `api/app/seguranca/__init__.py`, `api/app/seguranca/senhas.py`,
`api/app/servicos/historico.py`, `api/testes/test_erros_api.py`, `api/testes/test_historico.py`,
`api/testes/test_senhas.py`.

**Produz:** `ErroApi(status, codigo, mensagem, **extras)`, `instalar_tratadores(app)`,
`gerar_hash`, `senha_confere`, `SENHA_INICIAL`, `Acao`, `registrar(...)`.

- [x] Testes falhando: `ErroApi` vira `{"codigo","mensagem",...extras}`; 422 vira
  `dados_invalidos` com `campos`, mensagem do validador em português, sem `input`; 404 de rota
  inexistente continua `{"detail": "Not Found"}`; `registrar` grava linha, recusa chave de dado
  pessoal e valor aninhado; `senha_confere` com hash inválido devolve `False`.
- [x] Implementar; commit.

### Tarefa 3: Sessões, dependências e CSRF

**Arquivos:** `api/app/seguranca/sessoes.py`, `api/app/seguranca/dependencias.py`,
`api/app/rotas/sessao.py`, `api/app/esquemas/comum.py`, `api/app/main.py`,
`api/testes/conftest.py` (fixtures `predio`, `logar`, `hasher_rapido`, `cliente` em https),
`api/testes/test_sessoes.py`, `api/testes/test_dependencias.py`, `api/testes/test_rota_sessao.py`.

**Produz:** `criar_sessao`, `buscar_sessao`, `encerrar_sessao`, `encerrar_todas`,
`gravar_cookie`, `apagar_cookie`, `descrever_aparelho`, `NOME_COOKIE = "__Host-sessao"`,
`Logado`, `sessao_qualquer`, `unidade_logada`, `exige_gestao`, `exige_admin`,
`exige_cabecalho_portal`; rotas `GET /api/acesso/eu` e `POST /api/acesso/sair`; fixtures
`predio` (5 blocos, 320 unidades, admin 1101, comissão 2304 ativada) e `logar(login) -> TestClient`.

- [x] Testes falhando: token guardado só como hash; cookie com `HttpOnly`, `Secure`,
  `SameSite=lax`, `Path=/`, `Max-Age` 180 dias; `eu` sem cookie 401 `sem_sessao`; com sessão
  restrita 200 e `precisa_trocar_senha`; sessão encerrada/vencida/unidade desativada 401;
  renovação de `ultimo_uso_em` só depois de 1 h; `unidade_logada` recusa restrita com 403
  `primeiro_acesso_pendente`; `exige_gestao`/`exige_admin` recusam unidade comum com 403
  `sem_permissao`; papel retirado no meio da sessão recusa na hora; POST sem `X-Portal` 403
  `requisicao_recusada`; `sair` encerra no banco e apaga o cookie; `descrever_aparelho`.
- [x] Implementar; commit.

### Tarefa 4: Esquemas do contrato e roteadores vazios

**Arquivos:** `api/app/esquemas/{__init__,acesso,administracao,avisos}.py`,
`api/app/rotas/{acesso,administracao,avisos}.py`, `api/app/main.py`,
`api/testes/test_esquemas.py`.

- [x] Testes falhando: validações do contrato (senha < 8, `mudar123`, senhas diferentes,
  celular com máscara vira dígitos, e-mail vazio vira nulo, título > 120, blocos vazios sem
  `para_todos`, `confirmo` diferente de `true`), mensagens exatas do spec; roteadores incluídos e
  com a dependência de CSRF.
- [x] Implementar; commit.

### Tarefa 5: Casca do front

**Arquivos:** `web/package.json` (+ `react-router`, `vitest`, `jsdom`, `@testing-library/react`,
`@testing-library/dom`), `web/vite.config.ts` (bloco `test`), `web/index.html`, `web/public/tema.js`,
`web/src/{main.tsx,rotas.tsx,estilo.css}`, `web/src/api/{cliente,tipos}.ts`,
`web/src/casca/*`, `web/src/{acesso,administracao,avisos}/{tipos.ts,api.ts,rotas.tsx,*.tsx}`,
testes `*.test.ts(x)` ao lado; remove `web/src/App.tsx`.

- [x] Testes falhando (Vitest): cliente manda `X-Portal: 1` e `credentials`, transforma erro em
  `ErroDaApi`, 204 vira `undefined`, falha de rede vira `sem_conexao`; tema começa claro, alterna,
  grava e lê `portal-tema`; guardas: sem sessão vai a `/entrar`, restrita vai a
  `/primeiro-acesso`, unidade comum em rota de admin vê "Sem permissão"; navegação mostra
  "Unidades" só para admin.
- [x] Implementar; `npm run lint`, `typecheck`, `build`, `test`; commit.

### Tarefa 6: Contrato TS × Python, dúvidas e verificação final

**Arquivos:** `api/testes/test_contrato.py`, `docs/superpowers/duvidas-m1.md`, `README.md`
(como rodar com `PORTAL_TESTE_BANCO`), `.github/workflows/ci.yml` (Vitest roda no `npm test`).

- [x] `test_contrato.py`: cada `BaseModel` de `app.esquemas` tem `export interface <Nome>` com os
  mesmos campos num dos `tipos.ts`.
- [x] Dúvidas registradas; suíte completa da API, migração do zero, lint/typecheck/test/build do
  front; commit.
