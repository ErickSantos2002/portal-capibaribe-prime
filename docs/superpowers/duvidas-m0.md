# Dúvidas e decisões do M0

Decisões tomadas sem certeza durante o M0. Cada item: a dúvida, o que foi decidido e por quê.
Revisar antes de fechar o marco; o que virar regra vai para os docs 04/05 ou para uma ADR.

## 1. Quem cria o papel `app`
- **Dúvida:** a migração cria o papel `app` ou só dá as permissões?
- **Decisão:** só as permissões. Se o papel não existir, a migração para com uma mensagem que
  diz como criá-lo. Testes e CI criam `dono` e `app` antes de migrar. O nome pode ser trocado
  com `alembic -x papel_app=<nome>` (usado no teste da mensagem).
- **Por quê:** criar papel exige senha, e a senha não pode estar no repositório. Em produção o
  papel nasce por SQL, uma vez, e a senha vai só para a Vercel.

## 2. Permissões além das listadas no modelo
- **Dúvida:** o modelo (seção 4) só lista tabelas oficiais de avisos, enquetes e histórico. E as
  tabelas de acesso?
- **Decisão:** `app` sem DELETE também em `bloco`, `unidade` e `unidade_papel` (o modelo diz que
  são desativados ou retirados, nunca apagados). Com DELETE em `sessao` (dado técnico) e em
  `erro` (limpeza de 90 dias). `historico`: só SELECT e INSERT. Tabela em `docs/superpowers/specs`.
- **Por quê:** é a leitura mais segura do modelo. Se o "apagar dados" do H-06 precisar de algo,
  ele é UPDATE (zerar colunas), não DELETE.

## 3. Login gerado por trigger
- **Dúvida:** "login gerado pelo banco" não cabe numa coluna gerada (depende de outra tabela).
- **Decisão:** trigger `before insert or update` em `unidade` recalcula o login a partir de
  `bloco.numero` + `numero`, ignorando o que a aplicação mandar; outro trigger atualiza os logins
  se o número do bloco mudar. Checks: bloco 1–9, número com 3 dígitos, andar 0–7.
- **Por quê:** garante RF-03 no banco, como pede a seção 4 do modelo.

## 4. Trigger do "último admin" e limpeza de 90 dias de `erro`
- **Dúvida:** o modelo põe as duas regras no banco; entram no M0?
- **Decisão:** ficam para depois. O trigger do último admin entra no M1 (H-09, junto da tela que
  retira papel). A limpeza de `erro` precisa de agendador (cron da Vercel ou Actions) e entra
  junto do backup (portão do M1). O `app` já tem DELETE em `erro` para isso.
- **Por quê:** o roadmap limita o M0 às tabelas e permissões; nada no M0 retira papel.

## 5. Carga roda como `app`, migração como `dono`
- **Decisão:** `alembic` usa `DATABASE_URL_DONO` (conexão direta do Neon, sem pooler);
  a carga e os dados fictícios usam `DATABASE_URL` (o `app`).
- **Por quê:** a carga só precisa de SELECT e INSERT; rodar como `app` prova que as permissões
  bastam e não dá ao script poder de apagar.

## 6. Comandos em `api/app/comandos/` e não em `scripts/`
- **Dúvida:** a arquitetura (seção 3) põe a carga em `scripts/`.
- **Decisão:** a lógica está em `api/app/servicos/` e os comandos em `api/app/comandos/`
  (`python -m app.comandos.carga_inicial`). `scripts/` continua com o que é de desenvolvimento
  do protótipo.
- **Por quê:** a carga reaproveita modelos, conexão e dependências da API (uv.lock). Um script
  fora do pacote teria que mexer em `sys.path` ou duplicar dependências.

## 7. Senha inicial com um hash por unidade
- **Decisão:** 320 hashes Argon2id com parâmetros padrão (cerca de 16 s na carga). Os testes
  usam custo baixo, ainda Argon2id.
- **Por quê:** o mesmo hash para todas exporia quem ainda não trocou a senha a quem visse o
  banco, e é o que a ADR-0005 manda (parâmetros padrão).

## 8. Rota de erro forçado
- **Decisão:** `POST /api/diagnostico/erro`, que só dispara com o cabeçalho
  `X-Portal-Diagnostico` igual a `PORTAL_DIAGNOSTICO_SEGREDO` (`hmac.compare_digest`). Sem a
  variável, ou com cabeçalho errado, 404 idêntico ao de rota inexistente.
- **Por quê:** o critério do M0 pede um erro forçado em produção sem abrir porta. Depois de
  verificar, a variável pode ser apagada na Vercel e a rota volta a ser 404 para todo mundo.

## 9. Mensagem da tabela `erro` sem dado pessoal
- **Decisão:** erro do banco vira só classe + SQLSTATE + nome da restrição/tabela/coluna; erro
  do pydantic vira campo + tipo; outros, a primeira linha da mensagem (máx. 500 caracteres).
  A rota é gravada pelo molde (`/api/avisos/{aviso_id}`), não pela URL real.
- **Por quê:** a mensagem do Postgres traz valores (`DETAIL: Key (email)=(...)`) e a do
  SQLAlchemy traz os parâmetros. Fica a regra para o código do Portal: nunca pôr dado pessoal na
  mensagem de uma exceção.

## 10. Conexão: `NullPool` e sem prepared statements
- **Decisão:** psycopg 3, `NullPool`, `prepare_threshold=None`; `postgres://` e `postgresql://`
  viram `postgresql+psycopg://` mantendo `?sslmode=require`.
- **Por quê:** função serverless não deve guardar conexões (o pooler do Neon faz o pool), e o
  pooler em modo transação não combina com prepared statements automáticos do psycopg.

## 11. Vercel com `services` (e o que não deu para validar)
- **Decisão:** `vercel.json` no modelo `services` (doc atual da Vercel para front + backend no
  mesmo projeto): serviço `web` (Vite, com rewrite de SPA para `/index.html`) e `api`
  (FastAPI, `entrypoint: app.main:app`, também em `[tool.vercel]` do pyproject); rewrites
  `/api/(.*)` → `api` e o resto → `web`; `regions: ["gru1"]`. As rotas da FastAPI já têm o
  prefixo `/api` (a Vercel repassa o caminho original). Cabeçalhos básicos (`nosniff`,
  `Referrer-Policy`, `X-Frame-Options`).
- **Validado:** o arquivo passa no JSON Schema oficial (`openapi.vercel.sh/vercel.json`);
  `uvicorn` e `vite build`/`vite preview` funcionam com os mesmos caminhos.
- **Não validado (precisa de deploy):** detecção do Python 3.12 pelo `.python-version` dentro de
  `api/`, instalação pelo `uv.lock`, se `regions` vale para a função do serviço, e se a pasta
  `testes/` entra no pacote da função (inofensivo, mas pode ser excluída depois). A CSP
  restritiva da arquitetura (seção 4) ficou para o M1, testada junto das telas.

## 12. ESLint em vez do oxlint do template
- **Dúvida:** o `create-vite` atual gera o projeto com oxlint, não ESLint.
- **Decisão:** ESLint (flat config, `typescript-eslint`, `react-hooks`, `react-refresh`), como
  pedem o roadmap e o pre-commit.
- **Por quê:** é o que os documentos decidiram; trocar de linter é decisão separada.

## 13. Ruff, ESLint e tsc no pre-commit como hooks locais
- **Decisão:** os hooks chamam `uv run --frozen ruff` e `npm --prefix web run lint|typecheck`,
  em vez de repositórios de hooks com versão própria.
- **Por quê:** uma versão só (a do `uv.lock` e do `package-lock.json`), a mesma do CI, e o
  Dependabot atualiza as duas. Custo: precisa de `npm ci --prefix web` uma vez por clone.

## 14. Documentação interativa (`/docs`) desligada
- **Decisão:** `docs_url`, `redoc_url` e `openapi_url` desligados.
- **Por quê:** a API é pública na internet e o contrato não precisa ficar exposto; quando o
  front precisar dos tipos, eles saem de `app.openapi()` localmente.

## 15. Node 24 no CI, versão da Vercel em aberto
- **Decisão:** CI com Node 24 (LTS); local é Node 26. `engines` não foi fixado no
  `package.json`, então a Vercel usa a versão padrão do projeto.
- **Por quê:** Vite 8 e ESLint 10 aceitam 20.19+; fixar a versão da Vercel é decisão de quem
  cria o projeto lá. Conferir no painel ao criar.

## 16. Sem Vitest no front no M0
- **Decisão:** sem testes de front no M0.
- **Por quê:** a página não tem lógica além de um `fetch`; a arquitetura prevê Vitest, que
  entra no M1 com as primeiras telas. A página foi conferida no navegador com a API local.

## 17. Dados fictícios ativam 40% e deixam a senha inicial
- **Decisão:** 128 unidades ativadas (meta de adesão de 3 meses), celulares `(81) 90000-xxxx`,
  e-mails `@example.com` em metade delas, nomes com "(fictício)", 2 unidades da Comissão.
  Elas entram com `mudar123` sem troca obrigatória. Só roda com `PORTAL_AMBIENTE=local|teste`.
- **Por quê:** dá um prédio realista para desenvolver o painel de ativação (H-07) no M1, sem
  arriscar rodar em produção.

## 18. `httpx2` nos testes
- **Decisão:** a dependência de teste é `httpx2`, não `httpx`.
- **Por quê:** o Starlette atual marca o `TestClient` com `httpx` como obsoleto e pede `httpx2`.
