# Indicações de serviços · Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para executar este plano tarefa por tarefa. Os passos usam caixas (`- [ ]`) para acompanhar.

**Objetivo:** os moradores indicam prestadores de serviço e dão a opinião deles (recomendo ou não recomendo), numa lista com busca e categorias, e a gestão só modera quando alguém avisa.

**Arquitetura:** a migração 0010, escrita à mão, cria quatro tabelas com as regras no banco (uma opinião por unidade, telefone único, unidade ativa, limite por dia, opinião escondida travada), no padrão da 0007 a 0009. A API (FastAPI) tem dois roteadores com o prefixo `/api/indicacoes` (morador e gestão), serviços separados por papel e a tradução dos erros do banco para 4xx. O front ganha a pasta `web/src/indicacoes/` e entra no menu com uma entrada só em `casca/menu.ts`.

**Tecnologias:** PostgreSQL 17, Alembic (migração à mão), SQLAlchemy 2, FastAPI, Pydantic 2, pytest. React 19, react-router 8, vitest e Testing Library. Conferência visual com playwright-core e o Chrome do sistema, **sempre headless**.

**Spec:** `docs/superpowers/specs/2026-10-18-indicacoes-design.md` (commit 23e7722). Quem executa lê o spec e este plano. Quando os dois divergem, vale o spec, e a divergência vai para a seção "Dúvidas" do relatório final.

## Restrições globais

- **NUNCA abrir janela visível de navegador.** Só o Chrome headless do `scripts/dev/conferir-letra.mjs`. Nada de Claude in Chrome, MCP do Playwright, `vite --open` ou `xdg-open`.
- **Sem push, merge, deploy (Vercel) nem Neon.** A 0010 é aplicada no Neon pelo coordenador **antes** do push (regra do backup), e isso fica fora deste plano.
- Execução por **um agente, em sequência**, numa worktree (`superpowers:using-git-worktrees`) em `.claude/worktrees/indicacoes`, na branch **`indicacoes`** criada a partir da `main`. Na worktree, rodar `npm ci --prefix web` uma vez.
- Commits em português. O pre-commit roda sempre, **nunca `--no-verify`**. Toda mensagem termina com a linha
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`.
- Python **sempre** com `uv run --frozen`, de dentro de `api/`. Nunca o `python3` do sistema.
- **Postgres de teste** (o mesmo dos testes atuais: `api/testes/conftest.py`, padrão `postgresql://postgres:teste@127.0.0.1:55432/postgres`):
  ```sh
  docker start portal-pg-m0 || docker run -d --name portal-pg-m0 -e POSTGRES_PASSWORD=teste -p 127.0.0.1:55432:5432 postgres:17
  cd api && PORTAL_TESTE_BANCO=portal_teste_indicacoes uv run --frozen pytest -q
  ```
  O nome próprio do banco (`portal_teste_indicacoes`) evita apagar o banco de outra cópia de trabalho. Em todo comando `pytest` deste plano, entenda `cd api && PORTAL_TESTE_BANCO=portal_teste_indicacoes uv run --frozen pytest ...`.
- **Ambiente de conferência:** nome `indicacoes`, portas **55490** (Postgres), **8190** (API) e **5190** (web).
  Sobe com `scripts/dev/ambiente-conferencia.sh subir indicacoes 55490 8190 5190` e desce no fim com `... descer indicacoes`.
- Front: `cd web && npx vitest run <arquivo>`. Para fechar uma tarefa de front: `npm test && npm run lint && npx tsc -b`.
- Valores do spec, sem mudar: nome 2 a 80; comentário até 500; motivo até 300; telefone com 10 ou 11 dígitos e DDD; limites de **10 indicações e 30 opiniões por unidade por dia** (janela de 24 horas, como na 0007); 1 aviso aberto por unidade e prestador; até 3 parecidos; versão **1.8.0**.
- Categorias iniciais, nesta ordem: Móveis planejados · Ar-condicionado · Cortinas e persianas · Mudança · Eletricista · Encanador · Pintura · Gesso · Vidraçaria e box · Diarista · Outros.
- Textos na voz do morador, sem termo técnico. Nome do responsável **nunca** aparece; a opinião mostra só a placa (bloco e apartamento).
- CSS segue a regra do M5 (rem, sem px fora das exceções, sem media query de tamanho); o guarda é `web/testes/letra.test.ts`.
- Só dados fictícios (RNF-16) em teste, semente e prints.

## Decisões deste plano (o spec deixou com o builder)

1. **Normalização em Python** (`normalizar()`: NFKD, tira os acentos, `casefold`, junta os espaços). `prestador.nome_busca` é gravado pela API. Nada de `unaccent` nem `pg_trgm`, que exigiriam extensão no Neon.
2. **Busca** em Python, sobre a lista já calculada no banco (nome, categoria e comentários visíveis). São poucas centenas de prestadores e não há paginação, então nada é agregado depois de paginar.
3. **Parecidos:** `nome_busca` contém o termo normalizado (a partir de 3 letras), ou a primeira palavra (a partir de 3 letras) é igual. Escondidos ficam de fora. Mais recomendados primeiro, até 3.
4. **"Mais recente"** é `coalesce(editada_em, criada_em)`. Mudar a opinião a traz para cima.
5. **Limite das 30 opiniões:** conta as linhas criadas nas últimas 24 horas e também as opiniões que a própria unidade apagou (ação `indicacao_opiniao_apagada` no histórico, como o `arquivo_recusado` da 0007). Sem isso, apagar e escrever de novo não teria fim. Mudar a opinião é `UPDATE` e não conta. A API faz `select … for update` e depois `UPDATE` ou `INSERT`, nunca `insert … on conflict`, porque o `BEFORE INSERT` contaria a mudança.
6. **Esconder é definitivo** (o spec não tem "mostrar de novo"). Esconder o prestador resolve, na mesma transação, os avisos abertos dele.
7. **Prestador escondido:** para o morador, `GET /{id}` responde 404. A gestão o vê com `escondido: true`. Opinião escondida não aparece para os outros, nem para a gestão. Só a própria unidade a vê, com o recado.
8. **Aviso repetido** da mesma unidade é idempotente (204, nada muda). A tela diz "Você já avisou a gestão".
9. **Aviso para a gestão não mostra quem avisou** (só o motivo e a data).
10. **E-mail do primeiro aviso:** vai para os admins com e-mail cadastrado, mesmo os que desligaram "receber avisos por e-mail" (que vale para o mural). Leva o nome e a categoria do prestador e o link, sem o motivo e sem a placa. Entra na cota do Gmail pela coluna nova `aviso_servico.emails_reservados`, somada em `emails_nas_ultimas_24h`.
11. **Categoria nova** entra no fim, antes de "Outros" (as iniciais têm ordem 10, 20, …, 100, e "Outros" tem 999). O nome tem de 2 a 40 letras e é único sem diferenciar maiúscula. A tela fica em `/indicacoes/categorias` (só `Admin`), com o link ao lado de "Histórico de ações" no painel.
12. **Telefone:** a API aceita máscara, espaço e `+55` e guarda só os dígitos (DDD sem zero; com 11 dígitos, o terceiro é 9). O botão "WhatsApp" aparece sempre, e o "Ligar" (`tel:`) também aparece quando o número é fixo (10 dígitos). O Instagram aceita de 1 a 30 caracteres `[A-Za-z0-9._]`, com ou sem `@`, e é guardado sem o `@`.
13. **Faixa de categorias:** rola dentro dela com a letra de fábrica e quebra em linhas com `html[data-letra="grande"]` (a marca de `casca/letra.ts`). O `conferir-letra.mjs` passa a separar o "rola dentro de um elemento" do "passa da tela", e isso é testado por mutação (Tarefa 14).
14. **Telas a mais na conferência:** além de `indicacoes`, `indicacao` e `nova-indicacao`, também `indicacao-gestao` e `categorias-servico`.

## Foco da revisão

1. **Telefone com máscara, `+55` ou espaços igual a um que já existe** tem de dar 409 `prestador_ja_existe` (a normalização vem antes da unicidade, também no corrigir). Teste na Tarefa 4 e na Tarefa 5.
2. **Busca sem acento ou com outra maiúscula** ("joao" acha "João", "ELETRICA" acha "Elétrica") acha nome, categoria e comentário. Busca vazia ou só com espaços é o mesmo que não buscar. Teste na Tarefa 4.
3. **Dois aparelhos da mesma unidade opinando ao mesmo tempo** dão uma opinião só e nenhum 500. Teste na Tarefa 5.
4. **A unidade cuja opinião foi escondida cai no 409 do telefone** (tenta indicar de novo). A tela do prestador mostra "A gestão escondeu a sua opinião", e não o formulário. Teste na Tarefa 11.
5. **Prestador com aviso aberto e sem nenhuma opinião visível** sai da lista comum, mas entra na contagem e no filtro "com aviso" da gestão, e a página dele abre. Teste na Tarefa 6.

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `api/migracoes/versions/0010_indicacoes.py` | tabelas, carga das categorias, triggers, grants |
| `api/app/modelos/indicacoes.py` | modelos e constantes (`CATEGORIAS_INICIAIS`, limites) |
| `api/app/esquemas/indicacoes.py` | entrada e saída (Pydantic); espelho em `web/src/indicacoes/tipos.ts` |
| `api/app/servicos/indicacoes.py` | leitura, criar, opinar, corrigir, avisar, apagar da unidade |
| `api/app/servicos/indicacoes_gestao.py` | esconder, resolver, categorias |
| `api/app/servicos/indicacoes_banco.py` | `RESTRICOES` e `traduzir` (erro do banco → 4xx) |
| `api/app/servicos/indicacoes_email.py` | e-mail do primeiro aviso, depois da resposta |
| `api/app/rotas/indicacoes.py`, `api/app/rotas/indicacoes_gestao.py` | rotas |
| `api/testes/apoio_indicacoes.py` + `test_indicacoes_*.py` | testes |
| `web/src/indicacoes/*` | telas, api, tipos, formatos, menu, rotas, css, testes |

---

### Tarefa 1: Migração 0010 (tabelas, categorias, grants) e modelos

**Arquivos:**
- Criar: `api/migracoes/versions/0010_indicacoes.py`, `api/app/modelos/indicacoes.py`, `api/testes/apoio_indicacoes.py`, `api/testes/test_indicacoes_banco.py`
- Modificar: `api/app/modelos/__init__.py` (exportar os modelos novos), `api/testes/conftest.py` (`TABELAS` e `banco_limpo`), `scripts/backup/verificacoes.sql` (`esperadas` e o comentário "até a migração 0010"), `api/testes/test_migracoes.py`

**Interfaces:**
- Produz: as tabelas `categoria_servico`, `prestador`, `opiniao_servico`, `aviso_servico`; os modelos `CategoriaServico`, `Prestador`, `OpiniaoServico`, `AvisoServico`; as constantes `CATEGORIAS_INICIAIS: tuple[tuple[str, int], ...]` (nome e ordem), `ORDEM_OUTROS = 999`, `LIMITE_NOME = 80`, `MIN_NOME = 2`, `LIMITE_COMENTARIO = 500`, `LIMITE_MOTIVO = 300`, `LIMITE_CATEGORIA = 40`, `INDICACOES_POR_DIA = 10`, `OPINIOES_POR_DIA = 30`; e o apoio `criar_prestador(con, autor: int, *, telefone="81999990001", nome="Marcenaria Exemplo", categoria: str = "Móveis planejados", recomenda=True, comentario=None) -> int`, `opinar(con, prestador: int, unidade: int, *, recomenda=True, comentario=None) -> None`, `categoria_id(con, nome: str) -> int`.

Colunas (as do spec, seção 5, com estas escolhas):
- `categoria_servico (id identity pk, nome text not null, ordem smallint not null, criada_em timestamptz not null default now())`, com o índice único `categoria_servico_nome_unico on (lower(nome))` e o check `categoria_servico_nome_tamanho` (de 2 a 40, sem espaço nas pontas).
- `prestador (id, categoria_id → categoria_servico not null, nome, nome_busca text not null, telefone text not null, instagram text null, criado_por → unidade null, criado_em, editado_em null, escondido_em null, escondido_por → unidade null)`, com estas restrições: `prestador_telefone_unico unique (telefone)`, `prestador_nome_tamanho` (de 2 a 80, e `btrim`), `prestador_telefone_formato` (`telefone ~ '^[1-9]{2}[0-9]{8,9}$' and (char_length(telefone) = 10 or substr(telefone, 3, 1) = '9')`), `prestador_instagram_formato` (`instagram ~ '^[A-Za-z0-9._]{1,30}$'`), `prestador_nome_busca` (não vazio) e o índice `prestador_categoria (categoria_id)`.
- `opiniao_servico (id, prestador_id → prestador, unidade_id → unidade, recomenda boolean not null, comentario null, criada_em, editada_em null, escondida_em null, escondida_por → unidade null)`, com `opiniao_servico_unica unique (prestador_id, unidade_id)`, `opiniao_servico_comentario_tamanho` (nulo, ou de 1 a 500 depois de `btrim`) e o índice `opiniao_servico_unidade (unidade_id, criada_em)`.
- `aviso_servico (id, prestador_id, unidade_id, motivo null, criado_em, resolvido_em null, resolvido_por null, emails_reservados smallint not null default 0)`, com `aviso_servico_motivo_tamanho` (nulo, ou de 1 a 300) e o índice único parcial `aviso_servico_aberto on (prestador_id, unidade_id) where resolvido_em is null`.
- Carga, na própria migração: as 11 categorias com ordem 10, 20, …, 100 e "Outros" com 999.
- Grants para `app` (padrão 0007/0008, por coluna): `select, insert` nas quatro; `update (nome) on categoria_servico`; `update (categoria_id, nome, nome_busca, telefone, instagram, criado_por, escondido_em, escondido_por) on prestador`; `update (recomenda, comentario, escondida_em, escondida_por), delete on opiniao_servico`; `update (resolvido_em, resolvido_por, emails_reservados), delete on aviso_servico`. Nada de `delete` em `prestador` nem em `categoria_servico`.
- `downgrade`: `drop table` das quatro (as funções da Tarefa 2 também saem).

- [ ] **Passo 1: Testes que falham**, em `test_indicacoes_banco.py` (como `app`, com as fixtures `ids` e `banco_limpo`):

```python
def test_categorias_iniciais_na_ordem(engine_app):
    with engine_app.connect() as con:
        nomes = con.execute(text("select nome from categoria_servico order by ordem")).scalars().all()
    assert nomes == [n for n, _ in CATEGORIAS_INICIAIS]
    assert nomes[0] == "Móveis planejados" and nomes[-1] == "Outros"

def test_segunda_opiniao_da_mesma_unidade_e_recusada(engine_app, ids):
    with engine_app.begin() as con:
        p = criar_prestador(con, ids["u"])
    with pytest.raises(IntegrityError, match="opiniao_servico_unica"), engine_app.begin() as con:
        opinar(con, p, ids["u"])

def test_telefone_repetido_e_recusado_mesmo_escondido(engine_app, engine_dono, ids):
    # cria, esconde (como dono, para não depender da Tarefa 2) e tenta o mesmo telefone
    ...
    with pytest.raises(IntegrityError, match="prestador_telefone_unico"): ...

@pytest.mark.parametrize("telefone", ["0812345678", "8112345678x", "81812345678", "123"])
def test_telefone_fora_do_formato(engine_app, ids, telefone): ...  # prestador_telefone_formato

def test_app_nao_apaga_prestador_nem_categoria(engine_app, ids):
    # delete from prestador / categoria_servico → InsufficientPrivilege

def test_segundo_aviso_aberto_da_mesma_unidade_e_recusado(engine_app, ids): ...  # aviso_servico_aberto

def test_categorias_iguais_sem_diferenciar_maiuscula(engine_app):
    # insert 'eletricista' → categoria_servico_nome_unico
```

E também `test_migracoes.py::test_downgrade_da_0010_volta_a_0009` (no padrão de `test_downgrade_da_0008_volta_a_0007`: as quatro tabelas somem e as da 0009 ficam).

- [ ] **Passo 2: Rodar e ver falhar.** `pytest testes/test_indicacoes_banco.py testes/test_migracoes.py -q`. Esperado: FAIL (as tabelas não existem).
- [ ] **Passo 3: Escrever a migração, os modelos, o apoio e a infraestrutura de teste.** A migração usa `_papel_app()` copiado da 0008, no mesmo padrão. Os modelos espelham colunas, checks e índices (o `test_modelos.py` confere modelo × banco). `conftest.TABELAS` ganha `aviso_servico`, `opiniao_servico`, `prestador` e `categoria_servico`. Depois do `truncate`, o `banco_limpo` insere de novo `CATEGORIAS_INICIAIS` como `dono`, porque o truncate apaga a carga da migração. O `verificacoes.sql` ganha as quatro tabelas em `esperadas`.
- [ ] **Passo 4: Rodar e ver passar.** `pytest testes/test_indicacoes_banco.py testes/test_migracoes.py testes/test_modelos.py testes/test_m2_backup.py -q`. Esperado: PASS.
- [ ] **Passo 5: Teste que confere a carga.** `test_carga_da_migracao_igual_a_constante`: lê o texto da 0010 e confere que os 11 nomes aparecem na ordem de `CATEGORIAS_INICIAIS` (a migração fica congelada e a constante é a que a app usa).
- [ ] **Passo 6: Commit.** `feat(api): migração 0010, tabelas das indicações e categorias iniciais`

### Tarefa 2: Regras no banco (triggers da 0010) com testes de burla

**Arquivos:**
- Modificar: `api/migracoes/versions/0010_indicacoes.py` (bloco `REGRAS`), `api/testes/test_indicacoes_banco.py`, `api/testes/test_migracoes.py`

**Interfaces:**
- Consome: as tabelas da Tarefa 1.
- Produz: os nomes de regra (`constraint = '...'` nas triggers) que a Tarefa 3 traduz: `indicacao_de_unidade_inativa`, `prestador_limite_dia`, `opiniao_limite_dia`, `prestador_escondido`, `prestador_autor_fixo`, `opiniao_escondida`, `opiniao_fixa`, `aviso_servico_fixo`.

Funções (todas `language plpgsql`, `set search_path = pg_catalog, public, pg_temp`, com nomes qualificados, como na 0008):
- `prestador_conferir()`, `before insert or update on prestador`:
  - **No INSERT:** `criado_em := now()` e anula `editado_em`/`escondido_*`. `criado_por` não pode ser nulo e a unidade tem de estar ativa (`indicacao_de_unidade_inativa`). Trava a unidade (`for no key update`) e recusa a partir de 10 prestadores com esse `criado_por` nas últimas 24 horas (`prestador_limite_dia`).
  - **No UPDATE:** se `old.escondido_em` não é nulo, recusa qualquer mudança (`prestador_escondido`). `criado_por` só pode mudar para nulo (`prestador_autor_fixo`). `escondido_em` só vai de nulo para valor, e aí é carimbado com `now()`. Se mudou nome, categoria, telefone ou Instagram, `editado_em := now()`.
- `opiniao_conferir()`, `before insert or update on opiniao_servico`:
  - **No INSERT:** prestador escondido recusa (`prestador_escondido`), e unidade inativa também. Trava a unidade. Conta as opiniões dela com `criada_em` nas últimas 24 horas mais o histórico `indicacao_opiniao_apagada` dela nas últimas 24 horas, e recusa a partir de 30 (`opiniao_limite_dia`). Carimba `criada_em`.
  - **No UPDATE:** `prestador_id` e `unidade_id` não mudam (`opiniao_fixa`). Com `old.escondida_em` preenchido, recusa tudo (`opiniao_escondida`). Esconder é `escondida_em` de nulo para valor sem mudar `recomenda` e `comentario` (`opiniao_escondida` se misturar). Editar confere a unidade ativa e o prestador não escondido, e faz `editada_em := now()`.
- `aviso_servico_conferir()`, `before insert or update on aviso_servico`:
  - **No INSERT:** unidade ativa e prestador não escondido. Carimba `criado_em` e anula `resolvido_*`.
  - **No UPDATE:** `prestador_id`, `unidade_id`, `motivo` e `criado_em` não mudam (`aviso_servico_fixo`). `resolvido_em` só vai de nulo para valor (`now()`).
- O apagar continua sem trigger: "apagar meus dados" e o reset apagam opiniões escondidas. A recusa de apagar a opinião escondida é da rota (Tarefa 5).

- [ ] **Passo 1: Testes de burla que falham**, como `app` e direto no banco:

```python
def test_unidade_inativa_nao_indica_nem_opina_nem_avisa(engine_app, engine_dono, ids): ...
    # update unidade set ativa=false (dono); insert prestador/opiniao/aviso → "indicacao_de_unidade_inativa"
def test_limite_de_10_indicacoes_por_dia(engine_app, ids):
    # 10 criar_prestador com telefones diferentes passam; o 11º → "prestador_limite_dia"
def test_limite_de_30_opinioes_por_dia_conta_as_apagadas(engine_app, ids):
    # 31 prestadores criados como dono (fora do limite de 10); a unidade dá 29 opiniões
    # + 1 histórico indicacao_opiniao_apagada dela → a 30ª nova → "opiniao_limite_dia"
def test_mudar_a_opiniao_nao_conta_no_limite(engine_app, ids):
    # unidade no limite (30) ainda faz update recomenda=false numa opinião dela → passa
def test_opiniao_escondida_travada(engine_app, ids):
    # esconder via update escondida_em=now(); depois update comentario → "opiniao_escondida";
    # update escondida_em=null → "opiniao_escondida"; delete da linha → passa (apagar meus dados)
def test_prestador_escondido_nao_recebe_opiniao_nem_aviso_nem_correcao(engine_app, ids): ...
def test_criado_por_so_vira_nulo(engine_app, ids):  # update criado_por = ids["v"] → "prestador_autor_fixo"
def test_datas_sao_do_banco(engine_app, ids):
    # insert com criada_em '2000-01-01' → gravado com now()
def test_aviso_resolvido_nao_reabre(engine_app, ids): ...  # "aviso_servico_fixo" ao mudar motivo
```

Em `test_migracoes.py`: `test_funcoes_de_trigger_da_0010_com_search_path_fixo` (copiar o da 0008).

- [ ] **Passo 2: Rodar e ver falhar.** `pytest testes/test_indicacoes_banco.py -q`. Esperado: FAIL nos testes novos.
- [ ] **Passo 3: Escrever o bloco `REGRAS` na 0010** e executá-lo no `upgrade` antes dos grants. O `downgrade` faz `drop function` das três funções depois do `drop table`.
- [ ] **Passo 4: Rodar e ver passar.** `pytest testes/test_indicacoes_banco.py testes/test_migracoes.py -q`. Esperado: PASS.
- [ ] **Passo 5: Commit.** `feat(api): regras das indicações no banco (unidade ativa, limites, opinião escondida)`

### Tarefa 3: Esquemas, espelho TypeScript, tradução de erros e ações do histórico

**Arquivos:**
- Criar: `api/app/esquemas/indicacoes.py`, `web/src/indicacoes/tipos.ts`, `api/app/servicos/indicacoes_banco.py`, `api/testes/test_indicacoes_esquemas.py`, `api/testes/test_indicacoes_erros_do_banco.py`
- Modificar: `api/testes/test_contrato.py` (`ARQUIVOS_TS[indicacoes] = WEB / "indicacoes" / "tipos.ts"`), `api/app/servicos/historico.py` (`Acao`)

**Interfaces:**
- Produz (entrada): `Telefone` (Annotated: tira tudo que não é dígito, tira o `55` do começo quando sobram 12 ou 13 dígitos, e confere o mesmo formato do check). `Instagram` (tira o `@`). `NomePrestador` (NFC, `strip`, `sem_invisivel_nenhum`, de 2 a 80). `Comentario` e `Motivo` (NFC, `strip`, aceitam `\n`, `sem_controle(permitidos="\n")`, `sem_invisiveis`; só espaço vira `None`; até 500 e 300). `NomeCategoria` (de 2 a 40). Os modelos `NovaIndicacao(categoria_id: IdBanco, nome, telefone, instagram: Instagram | None = None, recomenda: bool, comentario: Comentario | None = None)`, `CorrigirPrestador(categoria_id, nome, telefone, instagram | None)`, `DarOpiniao(recomenda: bool, comentario | None = None)`, `AvisarGestao(motivo: Motivo | None = None)`, `NovaCategoria(nome)` e `RenomearCategoria(nome)`.
- Produz (saída): `Categoria(id, nome)`, `ListaCategorias(itens)`, `OpiniaoTrecho(unidade: UnidadeRef, comentario: str, em: datetime)`, `PrestadorResumo(id, categoria: Categoria, nome, recomendam: int, nao_recomendam: int, trecho: OpiniaoTrecho | None, avisos_abertos: int | None)`, `ListaIndicacoes(itens, com_aviso: int | None)`, `PrestadorRef(id, nome, categoria: Categoria)`, `Parecidos(itens)`, `Opiniao(id, unidade: UnidadeRef, recomenda, comentario: str | None, em: datetime, minha: bool)`, `MinhaOpiniao(recomenda, comentario: str | None, escondida: bool)`, `AvisoRecebido(id, motivo: str | None, em: datetime)`, `Prestador(id, categoria, nome, telefone: str, celular: bool, instagram: str | None, recomendam, nao_recomendam, opinioes: list[Opiniao], minha_opiniao: MinhaOpiniao | None, pode_corrigir: bool, ja_avisei: bool, escondido: bool, avisos: list[AvisoRecebido] | None)` e `IndicacaoCriada(id)`. Nas saídas, `None` quer dizer "não é para você" (os campos da gestão).
- Produz: `indicacoes_banco.RESTRICOES: dict[str, tuple[int, str, str]]` e `traduzir(erro: DBAPIError) -> ErroApi | None` (mesmo formato de `enquetes_banco`). Os códigos: `unidade_inativa` 403, `limite_do_dia` 429 ("Seu apartamento já fez muitas indicações hoje. Tente de novo amanhã." e a versão para opiniões), `prestador_escondido` 409, `opiniao_escondida` 409 ("A gestão escondeu a sua opinião. Ela não pode ser mudada nem apagada."), `prestador_ja_existe` 409, `aviso_ja_enviado` 409, `categoria_ja_existe` 409, `dados_invalidos` 422 para os checks, `tente_de_novo` 409 para chave primária, chave estrangeira e serialização.
- Produz: as `Acao` `indicacao_escondida`, `indicacao_opiniao_escondida`, `indicacao_opiniao_apagada`, `indicacao_aviso_resolvido`, `categoria_criada` e `categoria_renomeada`.

- [ ] **Passo 1: Testes que falham:**

```python
@pytest.mark.parametrize("digitado,guardado", [
    ("(81) 9 9999-0001", "81999990001"), ("+55 81 99999-0001", "81999990001"),
    ("81 3333-4444", "8133334444"), ("5581999990001", "81999990001")])
def test_telefone_vira_so_digitos(digitado, guardado):
    assert NovaIndicacao(**BASE, telefone=digitado).telefone == guardado

@pytest.mark.parametrize("ruim", ["81 8999-00011", "0819999-0001", "9999-0001", "(81) 2999-000"])
def test_telefone_invalido(ruim): ...  # ValidationError

def test_comentario_so_com_espaco_vira_nulo(): assert DarOpiniao(recomenda=True, comentario="   ").comentario is None
def test_comentario_com_501_letras_e_recusado(): ...
def test_nome_com_caractere_invisivel_e_recusado(): ...  # "Marce​naria"
def test_nome_em_nfc(): assert NovaIndicacao(**BASE, nome="José").nome == "José"
def test_instagram_sem_arroba(): assert ...instagram == "marcenaria.x"
def test_recomenda_e_obrigatorio(): ...  # sem padrão marcado
```

`test_indicacoes_erros_do_banco.py` segue `test_m4_erros_do_banco.py`: toda `constraint = '...'` da 0010 está em `RESTRICOES`; toda restrição das quatro tabelas (`pg_constraint`, `contype not in ('n','t')`) **e todo índice único** (`pg_index.indisunique`, que pega `aviso_servico_aberto` e `categoria_servico_nome_unico`) está em `RESTRICOES`; e todo status fica entre 400 e 499.

- [ ] **Passo 2: Rodar e ver falhar.** `pytest testes/test_indicacoes_esquemas.py testes/test_indicacoes_erros_do_banco.py testes/test_contrato.py -q`.
- [ ] **Passo 3: Escrever os esquemas, o `tipos.ts` (espelho campo a campo), `indicacoes_banco.py` e as ações.**
- [ ] **Passo 4: Rodar e ver passar.** O mesmo comando: PASS.
- [ ] **Passo 5: Commit.** `feat(api): esquemas das indicações, espelho no front e tradução dos erros do banco`

### Tarefa 4: Leitura e indicar (categorias, lista, parecidos, criar, abrir)

**Arquivos:**
- Criar: `api/app/servicos/indicacoes.py`, `api/app/rotas/indicacoes.py`, `api/testes/test_indicacoes_rotas.py`
- Modificar: `api/app/main.py` (`include_router(indicacoes.rotas)` depois das enquetes)

**Interfaces:**
- Consome: Tarefas 1 a 3.
- Produz:
  - `normalizar(texto: str) -> str`;
  - `listar_categorias(db) -> list[Categoria]`, em ordem;
  - `listar(db, logado: Logado, *, categoria: int | None, busca: str | None, com_aviso: bool) -> ListaIndicacoes`;
  - `parecidos(db, nome: str) -> list[PrestadorRef]`;
  - `criar(db, logado, dados: NovaIndicacao) -> int`, que grava o prestador e a primeira opinião numa transação, com `nome_busca = normalizar(nome)`;
  - `abrir(db, logado, prestador_id: int) -> Prestador`;
  - `erro_de_telefone(db, telefone: str, *, menos: int | None = None) -> ErroApi | None`: o 409 `prestador_ja_existe` com `id=` em `extras`, ou o 409 `prestador_indisponivel`, sem id, quando o prestador está escondido. A mensagem é "Esse prestador não está disponível no Portal.".
- Rotas (`APIRouter(prefix="/api/indicacoes", dependencies=[Depends(exige_cabecalho_portal)])`, todas com `UnidadeLogada`), **nesta ordem** (as fixas antes de `/{prestador_id}`):
  - `GET /categorias` → `ListaCategorias`;
  - `GET ""` (`categoria: IdBanco | None`, `busca: str | None` até 80, `com_aviso: bool = False`, que só vale para a gestão) → `ListaIndicacoes`;
  - `GET /parecidos?nome=` → `Parecidos`;
  - `POST ""` → 201 `IndicacaoCriada`;
  - `GET /{prestador_id}` → `Prestador`.
- A lista (o algoritmo que os testes não determinam sozinhos): uma consulta com os prestadores não escondidos, contagens só das opiniões visíveis (`escondida_em is null`), `ultima = max(coalesce(editada_em, criada_em))` e, por `lateral`, a opinião visível mais recente **com comentário**. Sem `com_aviso`, entra só quem tem pelo menos uma opinião visível. Com `com_aviso` (só a gestão), entra todo não escondido que tem aviso aberto. A ordem é `recomendam desc, ultima desc nulls last, id desc`. Depois, a busca filtra em Python por `normalizar(termo)` contido em `normalizar(nome + categoria + comentários visíveis)`. A gestão recebe `com_aviso` (contagem) e `avisos_abertos` por item; o morador recebe `None` nos dois.
- `abrir`: escondido dá 404 `indicacao_nao_encontrada` para o morador. As opiniões visíveis vêm da mais recente para a mais antiga, e a própria escondida não vai para a lista (vai em `minha_opiniao.escondida`). `pode_corrigir = gestao or criado_por == logado.unidade_id`. `avisos` (os abertos) só para a gestão.

- [ ] **Passo 1: Testes que falham**, pela API, com `predio` e `logar`:

```python
def test_indicar_cria_prestador_e_primeira_opiniao(logar, predio):
    r = logar(COMUM).post("/api/indicacoes", json=NOVA)
    assert r.status_code == 201
    p = logar(COMISSAO).get(f"/api/indicacoes/{r.json()['id']}").json()
    assert p["recomendam"] == 1 and p["opinioes"][0]["unidade"]["apartamento"] == "203"
    assert "responsavel" not in r.text and "Responsável" not in str(p)

@pytest.mark.parametrize("mesmo", ["(81) 9 9999-0001", "+55 81 99999 0001", "81999990001"])
def test_telefone_igual_com_mascara_da_409_com_id(logar, predio, mesmo):  # Foco 1
    criado = logar(COMUM).post(...).json()["id"]
    r = logar(ADMIN).post("/api/indicacoes", json={**NOVA, "telefone": mesmo, "nome": "Outro"})
    assert r.status_code == 409 and r.json() == {"codigo": "prestador_ja_existe", "mensagem": ANY, "id": criado}

def test_telefone_de_escondido_da_409_sem_id(...):
    assert r.json()["codigo"] == "prestador_indisponivel" and "id" not in r.json()

def test_ordem_mais_recomendados_e_desempate_pela_mais_recente(...): ...
@pytest.mark.parametrize("termo", ["joao", "JOÃO", "  joão  ", "eletrica", "pontual"])  # Foco 2
def test_busca_sem_acento_nem_maiuscula_acha_nome_categoria_e_comentario(...): ...
def test_busca_vazia_e_igual_a_sem_busca(...): ...
def test_filtro_por_categoria(...): ...
def test_prestador_sem_opiniao_visivel_sai_da_lista_mas_abre(...): ...
def test_parecidos_ate_3_sem_escondidos(...):
    # "Marcenaria Silva", "Marcenária Silva & Filhos", "Silva Marcenaria", "Marcenaria Souza", um escondido
    assert [i["nome"] for i in r.json()["itens"]] == [...]  # no máximo 3, sem o escondido
def test_morador_nao_ve_campos_da_gestao(...): assert lista["com_aviso"] is None
def test_sem_sessao_401_e_id_fora_da_faixa_422(cliente, logar, predio): ...
def test_categoria_inexistente_422(...): ...
def test_limite_do_dia_vira_429(logar, predio): ...  # 11ª indicação
```

- [ ] **Passo 2: Rodar e ver falhar.** `pytest testes/test_indicacoes_rotas.py -q`.
- [ ] **Passo 3: Escrever o serviço e as rotas.** No `POST`, `erro_de_telefone` vem antes do insert. Na corrida, a `IntegrityError` em `prestador_telefone_unico` faz `rollback` e chama `erro_de_telefone` de novo. Os outros erros do banco passam por `indicacoes_banco.traduzir`.
- [ ] **Passo 4: Rodar e ver passar.** `pytest testes/test_indicacoes_rotas.py -q`: PASS.
- [ ] **Passo 5: Commit.** `feat(api): lista, busca, parecidos e indicar`

### Tarefa 5: Minha opinião, corrigir prestador e avisar a gestão

**Arquivos:**
- Modificar: `api/app/servicos/indicacoes.py`, `api/app/rotas/indicacoes.py`
- Criar: `api/testes/test_indicacoes_opiniao.py`

**Interfaces:**
- Produz:
  - `opinar(db, logado, prestador_id, dados: DarOpiniao) -> None`: `select … for update` da opinião da unidade, e depois `UPDATE` ou `INSERT`. Na corrida, a `IntegrityError` em `opiniao_servico_unica` faz `rollback` e tenta **uma vez** como `UPDATE`.
  - `apagar_opiniao(db, logado, prestador_id) -> None`: a opinião escondida dá 409 `opiniao_escondida`, a inexistente dá 404 `opiniao_nao_encontrada`. Registra `indicacao_opiniao_apagada` (entidade `prestador`, sem detalhes).
  - `corrigir(db, logado, prestador_id, dados: CorrigirPrestador) -> None`: quem não pode recebe 403 `sem_permissao`. O telefone de outro prestador dá o mesmo 409 da Tarefa 4 (`erro_de_telefone(..., menos=prestador_id)`). Atualiza `nome_busca`.
  - `avisar(db, logado, prestador_id, dados: AvisarGestao) -> int | None`: trava o prestador (`for no key update`) e confere se já há aviso aberto da unidade (se há, não faz nada e devolve `None`). Grava e devolve o id do aviso **se ele é o primeiro aviso aberto do prestador** (a Tarefa 8 usa esse id), ou `None`.
- Rotas: `PUT /{prestador_id}/opiniao` → `Prestador`; `DELETE /{prestador_id}/opiniao` → 204; `PUT /{prestador_id}` → `Prestador`; `POST /{prestador_id}/aviso` → 204. As quatro respondem 404 para o morador quando o prestador está escondido.

- [ ] **Passo 1: Testes que falham:**

```python
def test_dar_e_mudar_a_opiniao(logar, predio): ...  # 👍 → 👎; recomendam 0, nao_recomendam 1; uma linha só
def test_dois_aparelhos_ao_mesmo_tempo_uma_opiniao_so(logar, predio, engine_app):  # Foco 3
    # duas threads com PUT /opiniao (recomenda True e False) da mesma unidade, liberadas juntas por um Barrier
    assert sorted(status) == [200, 200]  # nenhum 500
    assert contar_opinioes(engine_app, prestador, COMUM) == 1
def test_apagar_a_minha_opiniao_e_registrar(...):
    assert historico(engine_app, "indicacao_opiniao_apagada")[0]["unidade_id"] == predio[COMUM]
def test_opiniao_escondida_nao_muda_nem_apaga(...):  # 409 opiniao_escondida nas duas
def test_minha_opiniao_escondida_aparece_so_para_mim(...):
    assert eu["minha_opiniao"] == {"recomenda": True, "comentario": ..., "escondida": True}
    assert all(not o["minha"] for o in outro["opinioes"])  # e a escondida não está na lista do outro
def test_corrigir_quem_indicou_e_gestao_sim_outro_nao(...): ...  # 200, 200, 403
def test_corrigir_para_telefone_de_outro_da_409_com_id(...): ...  # Foco 1
def test_avisar_uma_vez_aberto_por_unidade(...):
    # 2 POST da mesma unidade → 204, 204 e 1 linha; outra unidade → 2 linhas; ja_avisei True
def test_motivo_com_301_letras_422(...): ...
def test_prestador_escondido_404_para_morador_nas_quatro_rotas(...): ...
```

- [ ] **Passo 2: Rodar e ver falhar.** `pytest testes/test_indicacoes_opiniao.py -q`.
- [ ] **Passo 3: Escrever.**
- [ ] **Passo 4: Rodar e ver passar.** `pytest testes/test_indicacoes_opiniao.py testes/test_indicacoes_rotas.py -q`: PASS.
- [ ] **Passo 5: Commit.** `feat(api): minha opinião, corrigir o prestador e avisar a gestão`

### Tarefa 6: Gestão (esconder, resolver, categorias)

**Arquivos:**
- Criar: `api/app/servicos/indicacoes_gestao.py`, `api/app/rotas/indicacoes_gestao.py`, `api/testes/test_indicacoes_gestao.py`
- Modificar: `api/app/main.py`

**Interfaces:**
- Produz:
  - `esconder_prestador(db, logado, prestador_id) -> None`: se já está escondido, não faz nada. Resolve os avisos abertos na mesma transação e registra `indicacao_escondida` (entidade `prestador`).
  - `esconder_opiniao(db, logado, opiniao_id) -> None`: registra `indicacao_opiniao_escondida` (entidade `prestador`, `detalhes={"opiniao": id}`).
  - `resolver_aviso(db, logado, aviso_id) -> None`: registra `indicacao_aviso_resolvido`.
  - `criar_categoria(db, logado, nome) -> Categoria`: a `ordem` é a maior abaixo de 999 mais 10. Registra `categoria_criada` com `detalhes={"categoria": nome}` (a chave `nome` é proibida em `historico._PROIBIDAS`).
  - `renomear_categoria(db, logado, categoria_id, nome) -> Categoria`: registra `categoria_renomeada`.
- Rotas (`Gestao`): `POST /{prestador_id}/esconder` → 204, `POST /opinioes/{opiniao_id}/esconder` → 204, `POST /avisos/{aviso_id}/resolver` → 204. Rotas (`Admin`): `POST /categorias` → 201 `Categoria`, `PUT /categorias/{categoria_id}` → `Categoria`. O nome repetido sem diferenciar maiúscula dá 409 `categoria_ja_existe`.

- [ ] **Passo 1: Testes que falham:**

```python
def test_so_gestao_esconde_e_resolve(logar, predio): ...  # comum 403 sem_permissao; Comissão e admin 204
def test_so_admin_mexe_em_categoria(...): ...  # Comissão 403; admin 201
def test_esconder_tira_da_lista_resolve_avisos_e_registra(...):
    assert historico(engine_app, "indicacao_escondida") == [{... "unidade_id": predio[COMISSAO], "entidade_id": p}]
def test_esconder_a_unica_opiniao_tira_da_lista_e_a_pagina_abre(...): ...
def test_aviso_sem_opiniao_visivel_conta_para_a_gestao(logar, predio):  # Foco 5
    # prestador com a única opinião escondida e um aviso aberto
    assert gestao_lista(com_aviso=False)["com_aviso"] == 1
    assert [i["id"] for i in gestao_lista(com_aviso=True)["itens"]] == [p]
    assert logar(ADMIN).get(f"/api/indicacoes/{p}").status_code == 200
def test_resolver_tira_do_filtro(...): ...
def test_categoria_nova_entra_antes_de_outros(...):
    assert [c["nome"] for c in cats][-2:] == ["Jardinagem", "Outros"]
def test_renomear_e_repetida_da_409(...): ...  # "eletricista" → categoria_ja_existe
def test_historico_sem_nome_do_prestador(...): ...  # nenhum detalhe contém o nome
```

- [ ] **Passo 2: Rodar e ver falhar.** `pytest testes/test_indicacoes_gestao.py -q`.
- [ ] **Passo 3: Escrever.**
- [ ] **Passo 4: Rodar e ver passar.** `pytest testes/test_indicacoes_gestao.py -q`: PASS.
- [ ] **Passo 5: Commit.** `feat(api): moderação das indicações e categorias`

### Tarefa 7: "Apagar meus dados" e reset levam as indicações

**Arquivos:**
- Modificar: `api/app/servicos/indicacoes.py`, `api/app/servicos/acesso.py` (`apagar_dados`), `api/app/servicos/administracao.py` (`resetar`)
- Criar: `api/testes/test_indicacoes_apagar.py`

**Interfaces:**
- Produz: `apagar_da_unidade(db, unidade_id: int) -> None`, sem commit. Apaga todas as opiniões da unidade (as escondidas também) e todos os avisos dela, e põe `criado_por = null` nos prestadores que ela indicou. É chamada em `apagar_dados` (depois de conferir a senha e o papel) e em `resetar` (dentro do `try`, antes do `flush`).

- [ ] **Passo 1: Testes que falham:**

```python
def test_apagar_meus_dados_leva_opinioes_avisos_e_o_direito_de_corrigir(logar, predio, engine_app):
    # COMUM indicou P1 (opinião visível), opinou em P2 (escondida pela gestão) e avisou P2
    # POST /api/acesso/apagar-dados com a senha
    assert opinioes_da(engine_app, predio[COMUM]) == [] and avisos_da(...) == []
    assert criado_por(engine_app, p1) is None
    assert logar(ADMIN).get(f"/api/indicacoes/{p1}").status_code == 200  # prestador não some
    assert p1 not in ids_da_lista(logar(ADMIN))  # sem opinião visível, sai da lista
def test_reset_faz_o_mesmo(...): ...
def test_proximo_morador_nao_corrige(...): ...  # depois do reset, a mesma unidade reativada: pode_corrigir False
```

- [ ] **Passo 2: Rodar e ver falhar.** `pytest testes/test_indicacoes_apagar.py -q`.
- [ ] **Passo 3: Escrever** e atualizar as docstrings de `apagar_dados` e `resetar` (o que fica e o que sai).
- [ ] **Passo 4: Rodar a suíte inteira da API.** `pytest -q`: PASS, sem regressão em `test_acesso_*` e `test_administracao_reset.py`.
- [ ] **Passo 5: Commit.** `feat(api): apagar meus dados e reset levam as opiniões e os avisos das indicações`

### Tarefa 8: E-mail para a administração no primeiro aviso

**Arquivos:**
- Criar: `api/app/servicos/indicacoes_email.py`, `api/testes/test_indicacoes_email.py`
- Modificar: `api/app/servicos/email.py` (`mensagem_de_aviso_de_indicacao`), `api/app/servicos/notificacoes.py` (`emails_nas_ultimas_24h`), `api/app/rotas/indicacoes.py` (a rota do aviso agenda)

**Interfaces:**
- Consome: `avisar(...) -> int | None` (Tarefa 5), `segundo_plano.agendar`, `notificacoes.TRAVA_COTA_EMAIL`, `cota_email_avisos`, `email.enviar_uma`, `email.conexao_smtp`, `config_email()`.
- Produz:
  - `ASSUNTO_DO_AVISO_DE_INDICACAO = "Portal Capibaribe Prime: aviso numa indicação"`;
  - `mensagem_de_aviso_de_indicacao(nome: str, categoria: str, prestador_id: int, para: str, config: ConfigEmail) -> EmailMessage`, com texto e HTML no padrão `_pagina`, o botão "Abrir a indicação" e o link `{url_base}/indicacoes/{prestador_id}`;
  - `avisar_administracao(aviso_id: int, fabrica: Callable[[], Session] | None = None) -> None`: nunca levanta e registra no log sem dado pessoal. Em transação própria, pega `pg_advisory_xact_lock(TRAVA_COTA_EMAIL)` e reserva `min(len(admins), cota_email_avisos(db))` em `aviso_servico.emails_reservados`. Depois manda para os primeiros reservados.
  - Destinatários: unidades com papel `admin` em vigor, `ativa` e com `email` não nulo, em ordem de id.
- `emails_nas_ultimas_24h` passa a somar `aviso_servico.emails_reservados` com `criado_em` nas últimas 24 horas.
- A rota `POST /{prestador_id}/aviso` recebe `BackgroundTasks`. Depois do `commit`, se `avisar` devolveu um id, chama `segundo_plano.agendar(tarefas, indicacoes_email.avisar_administracao, aviso_id)`.

- [ ] **Passo 1: Testes que falham** (as fixtures `smtp`, `email_ligado` e `email_desligado` de `test_email_apoio.py`, como em `test_recuperacao_pedido.py`):

```python
def test_primeiro_aviso_manda_um_email_para_cada_admin(...):
    assert smtp.enviadas() == 1 and smtp.mensagens()[0]["To"] == "admin@example.com"
    corpo = ...get_content()
    assert f"{URL_BASE}/indicacoes/{p}" in corpo and "Marcenaria Exemplo" in corpo
    assert "1203" not in corpo and MOTIVO not in corpo  # nem placa nem motivo
def test_segundo_aviso_aberto_do_mesmo_prestador_nao_manda(...): assert smtp.enviadas() == 1
def test_depois_de_resolvido_o_proximo_aviso_manda_de_novo(...): ...
def test_comissao_nao_recebe(...): ...
def test_admin_sem_email_ou_que_desligou_os_avisos(...):  # sem e-mail: nada; desligou: recebe (decisão 10)
def test_cota_esgotada_nao_manda_e_conta(monkeypatch, ...):
    monkeypatch.setattr(notificacoes, "LIMITE_EMAILS_24H", 0); ...; assert smtp.enviadas() == 0
def test_emails_reservados_entram_na_cota(engine_app, ...): assert notificacoes.emails_nas_ultimas_24h(db) == 1
def test_email_desligado_nao_levanta(...): ...
def test_falha_no_smtp_nao_levanta_e_o_log_nao_tem_o_nome(caplog, ...): ...
```

- [ ] **Passo 2: Rodar e ver falhar.** `pytest testes/test_indicacoes_email.py -q`.
- [ ] **Passo 3: Escrever.**
- [ ] **Passo 4: Rodar e ver passar.** `pytest testes/test_indicacoes_email.py testes/test_m2_notificacoes.py testes/test_recuperacao_pedido.py -q`: PASS.
- [ ] **Passo 5: Commit.** `feat(api): e-mail para a administração no primeiro aviso de uma indicação`

### Tarefa 9: Front, base: api, caminhos, formatos, ícone, menu, rotas e a lista

**Arquivos:**
- Criar: `web/src/indicacoes/api.ts`, `caminhos.ts`, `formatos.ts`, `formatos.test.ts`, `menu.ts`, `rotas.tsx`, `Lista.tsx`, `indicacoes.css`, `lista.test.tsx`, `apoioDeTeste.ts`
- Modificar: `web/src/casca/menu.ts` (uma entrada), `web/src/casca/menu.test.ts`, `web/src/casca/Icone.tsx` (ícone `indicacoes`, traço único), `web/src/rotas.tsx` (`...rotasIndicacoes` antes do `*`)

**Interfaces:**
- Consome: `tipos.ts` (Tarefa 3).
- Produz:
  - `caminhos.ts`: `CAMINHO_INDICACOES = '/indicacoes'`, `CAMINHO_NOVA_INDICACAO = '/indicacoes/nova'`, `CAMINHO_CATEGORIAS = '/indicacoes/categorias'`, `caminhoIndicacao(id: number, opinar = false)` (com `?opinar=1`).
  - `api.ts`: uma função por rota (`listarCategorias`, `listarIndicacoes({categoria?, busca?, com_aviso?})`, `parecidos(nome)`, `indicar`, `abrirIndicacao`, `opinar`, `apagarOpiniao`, `corrigir`, `avisarGestao`, `esconderPrestador`, `esconderOpiniao`, `resolverAviso`, `criarCategoria`, `renomearCategoria`).
  - `formatos.ts`: `telefoneNaTela(d: string): string` ("(81) 9 9999-0001" e "(81) 3333-4444"), `ehCelular(d)`, `linkWhatsApp(d) = https://wa.me/55${d}`, `linkTelefone(d) = tel:+55${d}`, `linkInstagram(u) = https://www.instagram.com/${u}/`, `recomendamEmTexto(n)` ("1 vizinho recomenda", "3 vizinhos recomendam") e `naoRecomendamEmTexto(n)` ("1 não recomenda", "2 não recomendam").
  - `menu.ts`: `itemIndicacoes(eu): Lugar` = `{ para: '/indicacoes', icone: 'indicacoes', texto: 'Indicações', frase: 'Serviços que os vizinhos recomendam', grupo: 'dia-a-dia' }`, **sem `naBarra`**. Em `casca/menu.ts`, entra depois de Documentos e antes de Minha unidade.
  - `rotas.tsx`, atrás de `ExigeUnidade`: `indicacoes`, `indicacoes/nova` e `indicacoes/:id`; `indicacoes/categorias` atrás de `ExigeAdmin`. As fixas vêm antes de `:id`.
  - `ListaIndicacoes`: `Tela titulo="Indicações"` e o `extra` com `Link.flutuante` "＋ Indicar alguém". A busca tem o rótulo "Procurar: nome ou serviço" e espera 300 ms. A faixa de categorias é um `nav` com botões `aria-pressed`, "Todos" primeiro. O filtro mora na URL (`?categoria=&busca=&com_aviso=1`). Os cartões seguem o spec 3.1 (a categoria em caixa alta, o trecho com `Placa`). A lista vazia mostra "Ainda não tem indicação aqui. Seja o primeiro a indicar alguém." e o botão. Para a gestão, com `com_aviso > 0`, aparece no topo o botão "N indicações com aviso da vizinhança" (1: "1 indicação com aviso da vizinhança"), que liga e desliga o filtro.
  - CSS: a faixa com `display: flex; overflow-x: auto`, e `html[data-letra='grande'] .faixa-categorias { flex-wrap: wrap; overflow-x: visible }`. O botão flutuante usa a classe `flutuante` (já fica acima da barra e não cobre o último cartão).

- [ ] **Passo 1: Testes que falham:**

```ts
// formatos.test.ts
expect(telefoneNaTela('81999990001')).toBe('(81) 9 9999-0001')
expect(telefoneNaTela('8133334444')).toBe('(81) 3333-4444')
expect(linkWhatsApp('81999990001')).toBe('https://wa.me/5581999990001')
expect(recomendamEmTexto(1)).toBe('1 vizinho recomenda')
// casca/menu.test.ts
const DIA_A_DIA = ['Avisos', 'Enquetes', 'Documentos', 'Indicações', 'Minha unidade']
it('Indicações fica fora da barra, com a frase', ...)  // naBarra undefined; frase 'Serviços que os vizinhos recomendam'
// lista.test.tsx (apiFalsa + o Portal montado, como acesso/apoioDeTeste)
it('mostra os cartões na ordem da API, com recomendam, não recomendam e a placa')
it('tocar numa categoria filtra e marca aria-pressed; "Todos" volta')
it('a busca chama a API com ?busca= depois de digitar')
it('lista vazia mostra o convite e o botão Indicar alguém')
it('a gestão vê "2 indicações com aviso da vizinhança" e o toque filtra com com_aviso=1')
it('o morador não vê a faixa da gestão')
it('o lugar Indicações aparece na folha do Menu e no menu lateral')
```

- [ ] **Passo 2: Rodar e ver falhar.** `cd web && npx vitest run src/indicacoes src/casca/menu.test.ts`.
- [ ] **Passo 3: Escrever.**
- [ ] **Passo 4: Rodar e ver passar.** O mesmo comando, mais `node --test testes/letra.test.ts`: PASS.
- [ ] **Passo 5: Commit.** `feat(web): lista de indicações e o lugar novo no menu`

### Tarefa 10: Prestador aberto, minha opinião e avisar a gestão

**Arquivos:**
- Criar: `web/src/indicacoes/PrestadorAberto.tsx`, `FormOpiniao.tsx`, `AvisarGestao.tsx`, `CorrigirPrestador.tsx`, `prestador.test.tsx`

**Interfaces:**
- Consome: `api.ts` e `formatos.ts` (Tarefa 9).
- Produz:
  - `PaginaIndicacao` (rota `indicacoes/:id`, voltar para `/indicacoes`), com o conteúdo do spec 3.2. O botão "WhatsApp: (81) 9 9999-0001" (`target="_blank" rel="noopener noreferrer"`) aparece sempre, e o "Ligar" quando `!celular`. O Instagram é um link.
  - "Dar a minha opinião" ou "Mudar a minha opinião" abre o `FormOpiniao`, que também abre direto com `?opinar=1`. "O que os vizinhos disseram" lista as opiniões, cada uma com `Placa`, 👍/👎, data e comentário.
  - Com `minha_opiniao.escondida`, a tela mostra "A gestão escondeu a sua opinião" e nenhum botão de opinião.
  - `FormOpiniao({ inicial, aoSalvar })`: o radiogroup "Você recomenda?" (👍 Recomendo / 👎 Não recomendo, sem padrão), "Conte como foi (opcional)" com contador até 500 e "Apagar a minha opinião" (pergunta antes) quando já existe.
  - `AvisarGestao`: o link "Tem algo errado aqui? Avisar a gestão" abre a confirmação com o motivo opcional (até 300). Com `ja_avisei`, fica o texto "Você já avisou a gestão".
  - `CorrigirPrestador`, quando `pode_corrigir`: o formulário de nome, categoria, telefone e Instagram. O 409 `prestador_ja_existe` mostra o erro com o link para o outro prestador.

- [ ] **Passo 1: Testes que falham:**

```ts
it('mostra o WhatsApp com o link wa.me e o Ligar só quando o número é fixo')
it('sem opinião: "Dar a minha opinião"; com opinião: "Mudar a minha opinião" com o que ela escreveu')
it('o formulário não envia sem escolher recomendo ou não recomendo')
it('salvar chama PUT /api/indicacoes/7/opiniao com {recomenda, comentario} e atualiza a contagem')
it('apagar pergunta antes e chama DELETE')
it('?opinar=1 abre o formulário direto')
it('avisar a gestão manda o motivo e troca o link por "Você já avisou a gestão"')
it('quem indicou vê "Corrigir"; outro morador não')
it('as opiniões mostram a placa e nunca nome de pessoa')
```

- [ ] **Passo 2: Rodar e ver falhar.** `cd web && npx vitest run src/indicacoes/prestador.test.tsx`.
- [ ] **Passo 3: Escrever.**
- [ ] **Passo 4: Rodar e ver passar.** O mesmo comando: PASS.
- [ ] **Passo 5: Commit.** `feat(web): prestador aberto, minha opinião e avisar a gestão`

### Tarefa 11: Indicar alguém (parecidos, 409, sair sem publicar)

**Arquivos:**
- Criar: `web/src/indicacoes/NovaIndicacao.tsx`, `nova.test.tsx`

**Interfaces:**
- Consome: `api.ts`, `useAvisarAoSair` (`enquetes/gestao/useAvisarAoSair.ts`), `PerguntaSairSemPublicar` (`avisos/SairSemPublicar.tsx`) e `FormOpiniao`, só a parte de recomendo e comentário (exportar `CamposDaOpiniao` dele).
- Produz: `PaginaNovaIndicacao` (rota `indicacoes/nova`, voltar para `/indicacoes`), com os campos do spec 3.3 na ordem e com os mesmos rótulos.
  - **Parecidos:** a partir de 3 letras, com espera de 400 ms, mostra "Já tem uma **X** na lista. É a mesma?" e o link "Dar minha opinião lá" (`caminhoIndicacao(id, true)`), um por parecido.
  - **409 `prestador_ja_existe`:** `liberar()`, o recado "Esse telefone já está na lista. Dê a sua opinião aqui." e a navegação para `caminhoIndicacao(id, true)`.
  - **409 `prestador_indisponivel`:** a mensagem da API na caixa de erro, sem link.
  - "Publicar indicação" leva ao prestador criado. Com algo escrito, sair pergunta "Sair sem publicar?".

- [ ] **Passo 1: Testes que falham:**

```ts
it('digitar "Marcen" mostra "Já tem uma Marcenaria Silva na lista" com o link para /indicacoes/3?opinar=1')
it('menos de 3 letras não procura parecidos')
it('não publica sem categoria, nome, telefone e recomendo/não recomendo; erros nos campos')
it('publicar manda POST /api/indicacoes com os campos e vai para o prestador criado')
it('409 prestador_ja_existe leva ao prestador com o formulário de opinião aberto')
it('409 prestador_indisponivel mostra a mensagem e nenhum link')
it('sair com algo escrito pergunta "Sair sem publicar?"')
// Foco 4: na página do prestador, depois do 409, a unidade com a opinião escondida
it('após o 409, a unidade com opinião escondida vê "A gestão escondeu a sua opinião" e não o formulário')
```

- [ ] **Passo 2: Rodar e ver falhar.** `cd web && npx vitest run src/indicacoes/nova.test.tsx`.
- [ ] **Passo 3: Escrever.** Ajustar `PaginaIndicacao` se o teste do Foco 4 pedir (o `?opinar=1` não abre o formulário quando `minha_opiniao.escondida`).
- [ ] **Passo 4: Rodar e ver passar.** `cd web && npx vitest run src/indicacoes`: PASS.
- [ ] **Passo 5: Commit.** `feat(web): indicar alguém, com aviso de parecido e de telefone repetido`

### Tarefa 12: Gestão no front (seção do prestador, categorias, histórico)

**Arquivos:**
- Criar: `web/src/indicacoes/ParaAGestao.tsx`, `Categorias.tsx`, `gestao.test.tsx`
- Modificar: `web/src/indicacoes/PrestadorAberto.tsx`, `web/src/administracao/Painel.tsx` (o link "Categorias das indicações" ao lado do "Histórico de ações", só para o admin), `web/src/administracao/frases.ts` (as 6 ações novas), `web/src/m4contrato.test.ts` ou um teste novo das frases

**Interfaces:**
- Produz:
  - `ParaAGestao({ prestador, recarregar })`: a seção "Para a gestão", com os avisos recebidos (motivo e data, e "Resolver" em cada um) e "Esconder este prestador" (pergunta antes: "Ele sai da lista e não volta. Quem tem o telefone dele não consegue indicá-lo de novo."). Nas opiniões, cada uma ganha "Esconder esta opinião", também com pergunta. Com `escondido`, o selo é "Escondido da lista".
  - `PaginaCategorias` (`/indicacoes/categorias`): a lista em ordem com "Renomear" e o campo "Categoria nova". Sem apagar.
  - Frases: `indicacao_escondida` "escondeu uma indicação", `indicacao_opiniao_escondida` "escondeu uma opinião numa indicação", `indicacao_opiniao_apagada` "apagou a própria opinião numa indicação", `indicacao_aviso_resolvido` "resolveu um aviso numa indicação", `categoria_criada` "criou a categoria “X”" e `categoria_renomeada` "renomeou uma categoria para “X”" (X vem de `detalhes.categoria`).

- [ ] **Passo 1: Testes que falham:**

```ts
it('morador não vê "Para a gestão"; Comissão e admin veem')
it('esconder o prestador pergunta e chama POST /api/indicacoes/7/esconder')
it('esconder uma opinião chama POST /api/indicacoes/opinioes/31/esconder')
it('resolver um aviso chama POST /api/indicacoes/avisos/5/resolver e o tira da seção')
it('categorias: admin cria "Jardinagem" e renomeia; 409 categoria_ja_existe mostra o erro')
it('Comissão não vê o link de categorias no painel; admin vê')
it('frases do histórico das 6 ações novas')
```

- [ ] **Passo 2: Rodar e ver falhar.** `cd web && npx vitest run src/indicacoes/gestao.test.tsx src/m4contrato.test.ts`.
- [ ] **Passo 3: Escrever.**
- [ ] **Passo 4: Fechar o front.** `cd web && npm test && npm run lint && npx tsc -b`: PASS.
- [ ] **Passo 5: Commit.** `feat(web): moderação das indicações e categorias na administração`

### Tarefa 13: Privacidade e inventário da LGPD

**Arquivos:**
- Modificar: `docs/04-modelo-de-dados.md` (seção 5, e a tabela de volume da seção 6), `web/src/acesso/Privacidade.tsx`, `web/src/acesso/Privacidade.test.tsx`

**Interfaces:**
- Inventário, duas linhas novas na tabela da seção 5:
  - **"Nome e telefone de prestador indicado (pode ser pessoa física; Instagram opcional)":** onde é `prestador`. A finalidade é mostrar aos moradores logados um contato profissional indicado por vizinhos. Quem vê são as unidades logadas. Some quando a gestão esconde o prestador (a pedido dele ou por aviso); o telefone fica guardado para ele não voltar à lista.
  - **"Opinião sobre prestador (recomenda, comentário) e aviso à gestão":** onde é `opiniao_servico` e `aviso_servico`. A opinião é vista por todas as unidades logadas, com a placa e sem o nome. O aviso, só a gestão vê, sem a placa. Some em H-06 e H-08, e a própria unidade pode apagar a opinião.
  - Também na seção 5: em H-06 e H-08, o prestador indicado fica, mas sem o vínculo com a unidade. Na seção 6, uma linha para `opiniao_servico`.
- Privacidade (na voz do morador, nas seções que já existem): em "O que guardamos e para quê", as indicações (o nome e o telefone do prestador, a sua opinião). Em "Quem vê", a opinião aparece com o bloco e o apartamento para quem entra no Portal, nunca com o seu nome. Em "Seus direitos", "Apagar meus dados" apaga as suas opiniões e avisos, e o prestador pode pedir à Comissão para sair da lista.

- [ ] **Passo 1: Teste que falha** (`Privacidade.test.tsx`):

```ts
it('fala das indicações: opinião com bloco e apartamento, sem nome, e o prestador pode pedir para sair')
// getByText(/opinião .* bloco e o apartamento/i), getByText(/prestador .* pedir .* sair/i)
```

- [ ] **Passo 2: Rodar e ver falhar.** `cd web && npx vitest run src/acesso/Privacidade.test.tsx`.
- [ ] **Passo 3: Escrever o texto e as linhas do inventário.**
- [ ] **Passo 4: Rodar e ver passar.** O mesmo comando: PASS.
- [ ] **Passo 5: Commit.** `docs(lgpd): indicações no inventário e na página de privacidade` (os dois arquivos no mesmo commit, como o spec pede)

### Tarefa 14: Conferência visual headless das telas novas

**Arquivos:**
- Modificar: `scripts/dev/conferir-letra.mjs` (telas, semente, "rola dentro"), CSS de `web/src/indicacoes/indicacoes.css` conforme o que a rodada achar

**Interfaces:**
- Telas (grupo `indicacoes`):
  - `indicacoes` (morador, `/indicacoes`);
  - `indicacao` (morador, `/indicacoes/{indicacao}`);
  - `nova-indicacao` (morador, `/indicacoes/nova`);
  - `indicacao-gestao` (admin, `/indicacoes/{indicacao}`);
  - `categorias-servico` (admin, `/indicacoes/categorias`).
- Semente (`--semear`, idempotente pelo telefone):
  - como admin (1002): 3 prestadores em categorias diferentes, um com nome longo ("Marcenaria e Móveis Planejados Irmãos Albuquerque de Paulista") e outro com comentário de 500 letras;
  - como a Comissão (1003): uma opinião 👎 e um aviso no primeiro prestador;
  - `ids.indicacao` é o primeiro.
- "Rola dentro": em `medir()`, o elemento cujo ancestral tem `overflow-x` `auto` ou `scroll` e cabe na tela (`right <= largura + 1`) sai de `foraDaTela` e entra numa lista informativa, `rolamDentro`, no `resumo.txt`, que não conta como problema. A rolagem da página (`scrollWidth > clientWidth` da raiz) continua sendo problema.

- [ ] **Passo 1: Prova por mutação do "rola dentro".** Sobe o ambiente (`scripts/dev/ambiente-conferencia.sh subir indicacoes 55490 8190 5190`). Com a faixa temporariamente em `overflow-x: visible`, roda `node scripts/dev/conferir-letra.mjs --base http://localhost:5190 --tarefa indicacoes-mutacao --telas indicacoes --larguras 360 --fontes 16 --semear`. Esperado: código 1, com a faixa em "passa da tela". Desfaz a mutação, faz `cd web && npx vite build --logLevel warn`, roda de novo e espera código 0, com a faixa em "rola dentro".
- [ ] **Passo 2: Rodada completa.** `node scripts/dev/conferir-letra.mjs --base http://localhost:5190 --tarefa indicacoes --grupo indicacoes --larguras 320,360,412,1280 --fontes 16,24,32 --temas claro,escuro`. Esperado: código 0 e o `resumo.txt` sem problema. Rodar também `--grupo comum` (menu-aberto), que deve continuar sem problema, agora com Indicações na folha.
- [ ] **Passo 3: Corrigir o que aparecer** (só CSS e marcação das indicações), refazer o build e repetir o Passo 2 até dar 0. Abrir alguns prints com o Read (`/tmp/portal-letra-indicacoes/indicacoes-360-32.png`, `indicacao-1280-16-escuro.png`) para conferir a quebra da faixa e o botão flutuante sobre o último cartão.
- [ ] **Passo 4: Descer o ambiente.** `scripts/dev/ambiente-conferencia.sh descer indicacoes`.
- [ ] **Passo 5: Commit.** `test(conferencia): telas das indicações e rolagem dentro de elemento`

### Tarefa 15: Versão 1.8.0, novidades e verificação final

**Arquivos:**
- Modificar: `web/package.json` (`"version": "1.8.0"`), `web/package-lock.json` (a versão da raiz), `web/src/sobre/novidades.ts`, `README.md` (se a lista de pastas ou as migrações citarem até a 0009)

**Interfaces:**
- A entrada nova, primeira da lista: `{ versao: '1.8.0', data: '<dia do commit, AAAA-MM-DD>', nome: 'Indicações', itens: [...] }`, com três itens na voz do morador:
  - o que é ("Indicações" no Menu, com serviços que os vizinhos recomendam, busca e categorias);
  - como indicar e dar a opinião (uma por apartamento, que dá para mudar ou apagar);
  - "Tem algo errado aqui?" avisa a gestão.

- [ ] **Passo 1: Escrever a versão e a novidade.**
- [ ] **Passo 2: Verificação completa.**
  `cd api && PORTAL_TESTE_BANCO=portal_teste_indicacoes uv run --frozen pytest -q && uv run --frozen ruff check . && uv run --frozen ruff format --check .`
  `cd web && npm test && npm run lint && npx tsc -b`
  Esperado: tudo PASS (o `novidades.test.ts` confere a versão do `package.json` e que a data não está no futuro).
- [ ] **Passo 3: Commit.** `feat: indicações de serviços (1.8.0)`
- [ ] **Passo 4: Relatório para o coordenador:** os commits, a contagem de testes, o resultado da conferência, as dúvidas, e o lembrete de que **a 0010 precisa ir para o Neon antes do push**. Seguem a revisão independente (código e UX) e as correções, que o coordenador dispara depois desta branch.
