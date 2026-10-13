# M4 Onda 1 · Contrato · Plano de implementação

> **Para agentes:** executar tarefa por tarefa, com TDD (`superpowers:test-driven-development`).
> Passos em checkbox (`- [ ]`). Execução nesta onda: o próprio agente do contrato, em sequência
> (`superpowers:executing-plans`).

**Objetivo:** base do M4 pronta para dois épicos em paralelo (A · criar e gerir, B · votar e
resultado): migração 0008 com as três regras do roadmap garantidas pelo banco, modelos, contrato
da API (spec + esquemas + tipos TS + rotas 501), campo `enquete` do aviso aberto e
`gravar_correcao` prontos, frases do histórico e pontos de encaixe no front que ainda não mudam
nada para o morador.

**Arquitetura:** a API ganha `app/modelos/enquetes.py`, `app/esquemas/enquetes.py`, dois
roteadores com o prefixo `/api/enquetes` (`rotas/enquetes.py` do épico B,
`rotas/enquetes_gestao.py` do épico A) e, em `servicos/avisos.py`, `gravar_correcao` e o
`enquete` do aviso. O front ganha `web/src/enquetes/` (comum: tipos, api, caminhos, rotas;
`gestao/` do A e `votar/` do B, com encaixes vazios).

**Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2, Alembic, psycopg 3, pytest · React 19,
TypeScript, Vite, Vitest · Postgres 17.

**Spec:** `docs/superpowers/specs/m4-contrato.md`

## Restrições globais

- Python 3.12 via `uv run --frozen`; nunca o python3 do sistema.
- Textos, comentários e commits em PT-BR com acentuação; commit termina com o `Co-Authored-By`.
- Nenhum dado pessoal no repo; unidade de exemplo é sempre fictícia (1101, 1203, 2304, 4203).
- Banco de teste desta cópia: container próprio `portal-pg-m4-contrato` (porta 55448),
  `PORTAL_TESTE_BANCO=portal_teste_m4_contrato`; removido no fim.
- Sem push, sem merge, sem Vercel/Neon/R2. Versão do `web/package.json` e `novidades.ts`
  intactos.
- Commit pequeno a cada passo verde; `pre-commit` passando; suíte inteira (pytest, vitest) no
  fim.

## Foco de revisão

1. Dois votos simultâneos da mesma unidade (duas conexões) → um voto só, com as opções de um
   deles inteiras, nunca misturadas. Teste na Tarefa 1.
2. Editar a enquete enquanto um voto está em andamento → a edição espera e é recusada
   (`enquete_com_voto`), não passa por baixo. Teste na Tarefa 1.
3. Trocar o voto depois do prazo mexendo só em `voto_opcao` (sem tocar em `voto`) → recusado.
   Teste na Tarefa 1.
4. Enquete encerrada sem voto não reabre mudando `encerra_em`. Teste na Tarefa 1.
5. Unidade comum fora do destino → 404 igual a inexistente; gestão fora do destino vê mas não
   vota (o banco recusa `voto_fora_do_destino`). Testes nas Tarefas 1 e 3.

---

### Tarefa 1: Migração 0008, modelos e testes que tentam burlar

**Arquivos:** `api/migracoes/versions/0008_enquetes.py`, `api/app/modelos/enquetes.py`,
`api/app/modelos/__init__.py`, `api/testes/conftest.py` (TABELAS), `api/testes/test_migracoes.py`,
`api/testes/test_m4_banco.py` (novo), `scripts/backup/verificacoes.sql`.

**Produz:** tabelas `enquete`, `enquete_opcao`, `enquete_bloco`, `voto`, `voto_opcao`; modelos
`Enquete`, `EnqueteOpcao`, `EnqueteBloco`, `Voto`, `VotoOpcao`; constantes `LIMITE_PERGUNTA = 200`,
`LIMITE_OPCAO = 100`, `MIN_OPCOES = 2`, `MAX_OPCOES = 10`, `DURACAO_MAXIMA = timedelta(days=366)`,
`MOSTRAR_RESULTADO = ("durante", "so_no_fim")`.

- [x] Testes falhando (`test_m4_banco.py`, `test_migracoes.py`, `test_m2_backup.py` já confere
  as verificações): tabelas novas após o upgrade e downgrade para 0007 sem deixar função;
  funções com `search_path` fixo; enquete: pergunta e opção com tamanho, `mostrar_resultado`
  só os dois valores, datas do banco, prazo no futuro e até 366 dias, completa no commit (2 a
  10 opções, bloco se não é para todos), 11ª opção recusada, destino só na criação e não em
  enquete para todos; **as três regras**, como `app` e como `dono`: segundo voto da unidade
  (PK), voto/troca/`voto_opcao` depois do prazo, editar pergunta/prazo/escolha/resultado e
  inserir/apagar opção depois do 1º voto; encerrada sem voto não reabre; voto fora do destino;
  escolha única com duas opções recusada no commit; opção de outra enquete recusada (FK);
  concorrência (dois votos simultâneos = um voto; editar com voto em andamento = recusado);
  permissões do `app` (sem DELETE em `enquete`/`voto`, sem UPDATE em destino, autor, aviso,
  datas); `test_modelos_iguais_ao_banco_migrado` e o teste de CHECKs continuam verdes.
- [x] Rodar: `uv run --frozen pytest testes/test_m4_banco.py testes/test_migracoes.py -q` →
  falha (tabelas não existem).
- [x] Implementar a migração (SQL à mão) e os modelos; `verificacoes.sql` com as 5 tabelas.
- [x] Rodar de novo → verde; `test_modelos.py`, `test_m2_backup.py` verdes.
- [x] Commit.

### Tarefa 2: Esquemas, aviso com `enquete` e `gravar_correcao`

**Arquivos:** `api/app/esquemas/enquetes.py` (novo), `api/app/esquemas/avisos.py`
(`EnqueteDoAviso`, `AvisoCompleto.enquete`), `api/app/servicos/avisos.py` (`gravar_correcao`,
`_enquete_do_aviso`), `api/app/servicos/historico.py` (`enquete_criada`, `enquete_editada`),
`api/testes/test_m4_esquemas.py` (novo), `api/testes/test_m4_rotas.py` (parte do aviso),
`api/testes/test_contrato.py` (+ módulo enquetes), `web/src/enquetes/tipos.ts`,
`web/src/avisos/tipos.ts` (+ objetos de teste do front com `enquete: null`).

**Produz:** `MostrarResultado`, `NovaEnquete`, `EditarEnquete`, `Votar`, `OpcaoEnquete`,
`Participacao`, `EnqueteResumo`, `Enquete`, `ListaEnquetes`, `EnqueteGravada`, `Votantes`;
`gravar_correcao(db, logado, aviso_id, dados) -> int`.

- [x] Testes falhando: validação de cada campo com as mensagens do spec (pergunta, opções em
  branco descartadas, 2 a 10, repetidas ignorando maiúsculas e espaços, término com fuso, no
  futuro, até 1 ano, blocos); `Votar` de 1 a 10 sem repetir; aviso aberto traz `enquete` com a
  pergunta atual; `gravar_correcao` não faz commit e `corrigir` continua igual; contrato TS
  igual.
- [x] Implementar; rodar os testes das áreas (avisos, contrato, m4) → verdes; commit.

### Tarefa 3: Rotas dos épicos (501)

**Arquivos:** `api/app/rotas/enquetes.py` e `api/app/rotas/enquetes_gestao.py` (novos),
`api/app/main.py`, `api/testes/test_m4_rotas.py`, `api/testes/test_m4_em_construcao.py` (novo),
`api/testes/test_cache.py` (rotas sem dado).

- [x] Testes falhando: as 6 rotas declaradas no OpenAPI; gestão recusa comum (403
  `sem_permissao`), restrita (403 `primeiro_acesso_pendente`) e sem sessão (401); leitura e
  voto recusam restrita e sem sessão; CSRF nas alterações; validação dos corpos (422 com o
  campo certo); 501 em cada rota de cada épico; `no-store` em todo GET novo; id fora do
  `bigint` é 422.
- [x] Implementar; commit.

### Tarefa 4: Front comum e encaixes

**Arquivos:** `web/src/enquetes/{api.ts,caminhos.ts,rotas.tsx}`,
`web/src/enquetes/gestao/rotas.tsx`, `web/src/enquetes/votar/{rotas.tsx,menu.ts,EnqueteDoAviso.tsx}`,
`web/src/rotas.tsx`, `web/src/casca/menu.ts`, `web/src/avisos/AvisoAberto.tsx`,
`web/src/administracao/frases.ts`, `web/src/m4contrato.test.ts` (novo).

- [x] Testes falhando: cada função de API chama o método e o caminho certos (com corpo);
  caminhos das telas; frases de `enquete_criada` e `enquete_editada`; encaixes ligados mas
  vazios (menu sem "Enquetes", aviso sem botão, rotas vazias) e, com os encaixes trocados por
  marcadores, cada um aparece no lugar certo.
- [x] Implementar; `npx vitest run`, `npx eslint .`, `npx tsc -b` verdes; commit.

### Tarefa 5: Documentos e dúvidas

**Arquivos:** `docs/04-modelo-de-dados.md`, `docs/05-arquitetura.md`, `docs/07-roadmap.md`
(próximo passo), `docs/superpowers/duvidas-m4.md` (novo).

- [x] Modelo de dados (seção 3.5 com as colunas e regras novas; seção 4 com onde cada regra é
  garantida); arquitetura (fluxo 6.3 com as rotas e a ordem da gravação do voto); dúvidas com
  os itens **[Erick]**.
- [x] Suíte inteira (`uv run --frozen pytest`, `npm test`) e `pre-commit run --all-files`;
  commit.

---

## Estado (13/10/2026, onda do contrato concluída)

Tarefas 1 a 5 feitas e commitadas na branch `m4/contrato` (sem push, sem merge). Suíte inteira
no fim: API 1636 testes verdes (eram 1483 antes da onda), web 543 (vitest) + 13 (cabeçalhos).
O teste "editar com voto em andamento" foi conferido por mutação: sem os `for share` das
triggers do voto, ele falha.

Próximo passo (coordenador): respostas do Erick aos itens **[Erick]** de `duvidas-m4.md` (3, 4,
7, 9, 11 e 12) e a onda dos dois épicos, cada um na própria worktree a partir desta branch, com
o próprio banco de teste.
