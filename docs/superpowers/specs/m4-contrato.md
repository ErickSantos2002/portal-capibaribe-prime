# Spec · M4 Onda 1 · Contrato

| | |
|---|---|
| **Marco** | M4 · Enquetes (`docs/07-roadmap.md`, seção do M4) |
| **Base** | `02-requisitos.md` (RF-20 a RF-25, RN-01 a RN-03, RN-05), `03-historias.md` (H-20, H-21, H-22, H-11, H-13), `04-modelo-de-dados.md` (seções 3.5 e 4), `05-arquitetura.md` (seção 6.3), protótipo (telas `#enquetes`, `#enquete/1`, `#enquete/2`, `#nova-enquete`) |
| **Criado em** | 13/10/2026 |
| **Plano** | `docs/superpowers/plans/m4-contrato.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m4.md` |
| **Decisão nova** | nenhuma ADR: as regras seguem o padrão das migrações 0002 a 0007 (regra importante garantida pelo banco, modelo seção 4) |

## 1. Objetivo

Deixar a base do M4 pronta para que **dois agentes trabalhem em paralelo**, sem tocar nos
mesmos arquivos nem criar migrações conflitantes:

| Épico | Histórias | Entrega |
|---|---|---|
| **A · Criar e gerir** | H-20 | formulário "Nova enquete" (pergunta, 2 a 10 opções, escolha única ou múltipla, término, destino, quando mostrar o resultado), aviso automático (H-13) com notificação, "Editar" enquanto ninguém votou (com a correção do aviso automático), histórico `enquete_criada` e `enquete_editada` |
| **B · Votar e resultado** | H-21, H-22 | lista "Abertas / Terminadas" com o selo "Seu apartamento ainda não votou", enquete aberta com votar e trocar o voto, resultado (votos por opção, participação), "só no fim", "Quais apartamentos votaram" para a gestão, item "Enquetes" no menu e o botão "Ir para a enquete" no aviso automático |

Esta onda **não implementa as histórias** e **não muda nada que o morador vê** (a versão do
`web/package.json` e o `novidades.ts` ficam como estão). Entrega: a migração 0008 com as três
regras do roadmap garantidas pelo banco (e testes que tentam burlar cada uma direto no banco), os
modelos, o contrato da API (este documento + esquemas Pydantic + tipos TypeScript + rotas dos
épicos que respondem 501), o campo `enquete` do aviso aberto (pronto), a correção do aviso sem
commit (`gravar_correcao`, para o épico A), as frases do histórico e os pontos de encaixe no
front.

## 2. Banco · migração 0008

Mesmo padrão da 0002 a 0007: SQL escrito à mão, roda como `dono`, permissões ao papel `app`
(nome trocável por `-x papel_app=`), funções de trigger com `set search_path = pg_catalog,
public, pg_temp` e nomes qualificados, datas carimbadas pelo banco, `upgrade → downgrade →
upgrade` testado (e o downgrade não deixa função para trás). Arquivo:
`api/migracoes/versions/0008_enquetes.py`; modelos em `api/app/modelos/enquetes.py`.

"Quando mostrar o resultado" é `text` com `CHECK`, não `enum` do Postgres (como a categoria do
aviso e do documento): o modelo de dados falava em `enum exibicao_resultado`; a coluna se chama
`mostrar_resultado` (dúvida 2).

### 2.1 `enquete` (H-20)

| Coluna | Regra |
|---|---|
| `id` | PK |
| `pergunta` | 1 a 200 caracteres, sem espaço só (`enquete_pergunta_tamanho`) |
| `multipla_escolha` | `false` = escolha única |
| `mostrar_resultado` | `durante` ou `so_no_fim` (`enquete_mostrar_resultado`) |
| `encerra_em` | no futuro e no máximo 366 dias à frente, ao criar e ao editar (`enquete_encerramento`, trigger); sempre depois de `criada_em` (`enquete_prazo`, `CHECK`) |
| `para_todos` | `false` = só os blocos em `enquete_bloco`. Não muda depois de criada |
| `criada_por` / `criada_em` | FK `unidade` / carimbada pelo banco |
| `editada_em` | nula até a primeira edição; carimbada pelo banco a cada edição |
| `aviso_id` | FK `aviso`, **única e obrigatória**: o aviso automático (H-13), criado na mesma transação. Não muda |

- **Completa no commit** (`enquete_completa`, trigger adiado como o do aviso): de 2 a 10 opções
  e, se não é para todos, pelo menos um bloco.
- **Nada muda depois do 1º voto** (`enquete_com_voto`): `UPDATE` em `enquete`, `INSERT` e
  `DELETE` em `enquete_opcao` são recusados se a enquete tem voto. A edição trava a linha da
  enquete e o voto pede a mesma linha em modo compartilhado (`for share`): editar e votar ao
  mesmo tempo não passam juntos; quem chega depois vê o que o outro gravou.
- **Nada muda depois do encerramento** (`enquete_encerrada`, RF-25), mesmo sem voto: uma
  enquete terminada não volta a ficar aberta mudando o `encerra_em`.
- O `app` só altera `pergunta`, `multipla_escolha`, `mostrar_resultado` e `encerra_em`
  (permissão por coluna); destino, autor e aviso não mudam. Não apaga nada (RN-05).

### 2.2 `enquete_opcao`

| Coluna | Regra |
|---|---|
| `id` | PK |
| `enquete_id` | FK `enquete` |
| `texto` | 1 a 100 caracteres, sem espaço só (`enquete_opcao_texto_tamanho`); único na enquete (`enquete_opcao_texto_unico`) |
| `ordem` | 1 a 10 (`enquete_opcao_ordem`); única na enquete (`enquete_opcao_ordem_unica`) |

Única também em (`enquete_id`, `id`), para a chave estrangeira composta de `voto_opcao` (uma
opção de outra enquete nunca entra num voto). Editar as opções é **apagar e inserir de novo**
(o `app` não tem `UPDATE` aqui), só enquanto não há voto e a enquete está aberta; no máximo 10
por enquete já na inserção (`enquete_opcoes`).

### 2.3 `enquete_bloco`

PK (`enquete_id`, `bloco_id`). Como `aviso_bloco`: enquete para todos não tem lista de blocos
(`enquete_bloco_destino`). O destino só entra **na transação que cria a enquete**
(`enquete_destino_fechado`: `enquete.criada_em = now()`): não muda depois, porque o aviso
automático (que tem o mesmo destino) também não muda.

### 2.4 `voto` (H-21, RN-01)

| Coluna | Regra |
|---|---|
| `enquete_id` + `unidade_id` | **PK composta: um voto por unidade (RN-01)** |
| `votado_em` | carimbada pelo banco; atualizada quando o voto é trocado |

- **Nada de voto depois do prazo** (`enquete_encerrada`): inserir ou trocar o voto com
  `clock_timestamp() >= encerra_em` é recusado (o relógio do banco na hora da gravação, não o
  início da transação).
- **Só quem está no destino vota** (`voto_fora_do_destino`): o modelo deixava isso para a
  aplicação; o banco também confere, porque é uma consulta só (dúvida 6).
- **Completo no commit** (`voto_completo`, trigger adiado): todo voto tem pelo menos uma opção;
  na escolha única, exatamente uma.
- O `app` insere e só altera `votado_em`. **Sem DELETE**: o voto não é retirado, só trocado
  (dúvida 7), e sobrevive ao reset da unidade (H-08).

### 2.5 `voto_opcao`

PK (`enquete_id`, `unidade_id`, `opcao_id`); FK (`enquete_id`, `unidade_id`) → `voto` e FK
(`enquete_id`, `opcao_id`) → `enquete_opcao` (`enquete_id`, `id`). Trocar o voto apaga as
linhas da unidade e insere as novas, na mesma transação (o conteúdo do voto anterior não é
guardado: modelo, seção 3.5). Inserir ou apagar aqui também exige a enquete aberta
(`enquete_encerrada`) e trava a linha do `voto` da unidade (`for no key update`), então duas
trocas da mesma unidade nunca misturam as opções.

### 2.6 Dois celulares da mesma unidade ao mesmo tempo

Critério de pronto do marco. O épico B grava o voto **sempre nesta ordem**, numa transação:

```sql
insert into voto (enquete_id, unidade_id) values (:e, :u)
    on conflict (enquete_id, unidade_id) do update set votado_em = excluded.votado_em;
delete from voto_opcao where enquete_id = :e and unidade_id = :u;
insert into voto_opcao (enquete_id, unidade_id, opcao_id) values (:e, :u, :o), ...;
```

O `on conflict do update` trava a linha do voto: o segundo celular espera o primeiro terminar,
e então troca o voto dele. Resultado: **um voto só**, com as opções de quem gravou por último
(H-21: "vale sempre o último"); nenhum dos dois recebe erro. Se algo fugir dessa ordem, o banco
ainda recusa no commit o voto com opções misturadas (`voto_completo`) e a API responde 409
`voto_mudou_agora` (nunca 500). Teste com duas conexões de verdade em
`api/testes/test_m4_banco.py`; o épico B repete pela API, com duas requisições em paralelo.

### 2.7 Permissões do `app`

| Tabela | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|
| `enquete` | sim | sim | só `pergunta`, `multipla_escolha`, `mostrar_resultado`, `encerra_em` (e só sem voto e aberta: trigger) | **não** |
| `enquete_opcao` | sim | sim | **não** | sim, só sem voto e aberta (trigger) |
| `enquete_bloco` | sim | sim (só na criação: trigger) | **não** | **não** |
| `voto` | sim | sim | só `votado_em` | **não** |
| `voto_opcao` | sim | sim | **não** | sim, só aberta (trigger) |

### 2.8 Testes que tentam burlar (critério do roadmap)

Em `api/testes/test_m4_banco.py`, com SQL direto, como `app` **e** como `dono` (as triggers
valem para os dois): segundo `INSERT` em `voto` da mesma unidade (chave primária); voto e troca
de voto depois do `encerra_em`, inclusive mexendo só em `voto_opcao`; `UPDATE` da pergunta, do
prazo, do tipo de escolha e do "mostrar resultado", `INSERT` e `DELETE` de opção depois do 1º
voto; editar e votar ao mesmo tempo (a edição espera o voto e é recusada); dois votos da mesma
unidade ao mesmo tempo (um voto só). E: `app` sem `DELETE` em `enquete` e `voto`, sem `UPDATE`
em destino, autor, aviso e datas.

## 3. Contrato da API

Convenções do M1 (spec do M1, seção 4): JSON em `snake_case`, datas ISO 8601 em UTC, erros
`{ "codigo", "mensagem" }`, toda alteração exige `X-Portal: 1`, id fora do `bigint` é 422.
Esquemas Pydantic em `app/esquemas/enquetes.py`, espelho em `web/src/enquetes/tipos.ts`,
conferidos pelo `api/testes/test_contrato.py`.

As rotas dos épicos respondem **501 `em_construcao`**, mas sessão, permissão, CSRF e validação
do corpo já são as de verdade. O que vale antes e depois dos épicos fica em
`api/testes/test_m4_rotas.py`; os testes de 501 ficam em `api/testes/test_m4_em_construcao.py`
(o épico troca o corpo da função e apaga a própria seção de lá). Um roteador por épico, com o
mesmo prefixo `/api/enquetes` (os caminhos não se cruzam): `app/rotas/enquetes.py` (B) e
`app/rotas/enquetes_gestao.py` (A).

### 3.1 Rotas

| Rota | Quem | Corpo | Resposta | Erros | Épico |
|---|---|---|---|---|---|
| `GET /api/enquetes` | `UnidadeLogada` | — | 200 `ListaEnquetes` | 401, 403 | B |
| `GET /api/enquetes/{enquete_id}` | `UnidadeLogada` | — | 200 `Enquete` | 404 `enquete_nao_encontrada` | B |
| `PUT /api/enquetes/{enquete_id}/voto` | `UnidadeLogada` | `Votar` | 200 `Enquete` | 404, 403 `fora_do_destino`, 409 `enquete_encerrada`, 409 `enquete_mudou`, 409 `voto_mudou_agora`, 422 | B |
| `GET /api/enquetes/{enquete_id}/votantes` | `Gestao` | — | 200 `Votantes` | 404 | B |
| `POST /api/enquetes` | `Gestao` | `NovaEnquete` | 201 `EnqueteGravada` | 422 (inclusive `bloco_inexistente`) | A |
| `PUT /api/enquetes/{enquete_id}` | `Gestao` | `EditarEnquete` | 200 `EnqueteGravada` | 404, 409 `enquete_com_voto`, 409 `enquete_encerrada`, 409 `sem_mudanca`, 422 | A |

- **Quem vê:** a unidade comum vê as enquetes para todos e as do bloco dela; fora disso, **404
  igual a enquete inexistente** (H-21: "unidade fora do destino não vê a enquete"). A gestão vê
  todas (como no mural), mas só vota se a unidade dela está no destino (`pode_votar`; senão 403
  `fora_do_destino`).
- **Resultado "só no fim"** (H-22): antes do encerramento, ninguém vê os votos por opção, **nem a
  gestão** (dúvida 4): `votos` de cada opção vem nulo e `resultado_visivel` falso. A
  participação (quantas unidades votaram) aparece sempre.
- **"Quais apartamentos votaram"** (H-22): só a gestão, a qualquer momento, sem dizer em quê.
- **Votar e trocar** são a mesma rota (`PUT`, idempotente): grava na ordem da seção 2.6. Opção
  que não é da enquete (a enquete foi editada depois que a tela abriu): 409 `enquete_mudou`.
- **Criar** (épico A): na **mesma transação**, `app.servicos.avisos.gravar_publicacao` com o
  aviso automático (mesmo destino da enquete, categoria `geral`), a enquete com `aviso_id`
  apontando para ele, as opções na ordem e os blocos; a rota chama `notificacoes.agendar` depois
  do commit, como a de documentos. Enquete e aviso nascem juntos ou nenhum dos dois. Título do
  aviso: "Enquete nova: <pergunta>" (cortado em 120 letras com "…"); o texto diz até quando vai
  e que é consulta sem valor legal. O aviso aberto mostra o botão para a enquete pelo campo
  `enquete` (seção 3.3), já preenchido nesta onda.
- **Editar** (épico A): só enquanto ninguém votou e a enquete está aberta; troca pergunta,
  opções (apaga e insere de novo, na ordem), tipo de escolha, término e quando mostrar o
  resultado. Destino não muda (dúvida 5). Corrige o aviso automático na mesma transação com
  `app.servicos.avisos.gravar_correcao` (versão nova, "Editado em"), sem notificar de novo.
  Os erros do banco viram 409 (`enquete_com_voto`, `enquete_encerrada`), nunca 500.
- **Histórico** (`Acao`, já criadas): `enquete_criada` (entidade `enquete`, `{"pergunta",
  "opcoes": n, "multipla_escolha", "mostrar_resultado", "para_todos", "blocos"}`),
  `enquete_editada` (os mesmos campos). O voto **não** vai para o histórico: a linha do `voto`
  já tem a data, e registrar cada troca criaria dado sobre o comportamento das pessoas (modelo,
  seção 3.5). "Enquete encerrada" não tem autor nem momento de gravação (é o relógio): a tela do
  histórico não ganha linha para isso (dúvida 8). As frases já existem em
  `web/src/administracao/frases.ts`.

### 3.2 Esquemas (`app/esquemas/enquetes.py`)

Requisições:

- `NovaEnquete`: `pergunta` (1 a 200, mesma regra de texto do título do aviso:
  `sem_invisivel_nenhum`; "Escreva a pergunta." / "A pergunta pode ter até 200 letras."),
  `opcoes: list[str]` (cada uma de 1 a 100, mesma regra; de 2 a 10; sem repetir, ignorando
  maiúsculas e espaços; "Escreva pelo menos 2 opções de resposta.", "O limite é de 10 opções.",
  "Cada opção pode ter até 100 letras.", "Duas opções estão iguais."; opções em branco são
  descartadas antes de contar, como o protótipo faz), `multipla_escolha` (padrão falso),
  `encerra_em` (com fuso; "A data de término já passou. Escolha uma data no futuro."; "A enquete
  pode durar até 1 ano."), `mostrar_resultado` (`MostrarResultado`, padrão `durante`),
  `para_todos`, `blocos` (como no `NovoAviso`: "Escolha pelo menos um bloco, ou Todos os
  blocos.").
- `EditarEnquete`: os mesmos campos, menos `para_todos` e `blocos`. Todos obrigatórios menos
  `multipla_escolha` e `mostrar_resultado` (padrões iguais aos da criação): o formulário manda
  tudo.
- `Votar`: `opcoes: list[IdBanco]`, de 1 a 10, sem repetir ("Escolha uma opção.", "A mesma
  opção foi escolhida duas vezes."). Mais de uma numa enquete de escolha única: 422 "Nesta
  enquete, escolha só uma opção." (a API confere, o banco também).

Respostas:

- `MostrarResultado`: `durante` | `so_no_fim`.
- `OpcaoEnquete`: `id`, `texto`, `votos: int | None` (nulo enquanto o resultado está escondido).
- `Participacao`: `votaram` (unidades que votaram), `total` (unidades ativas do destino, como o
  "Lido por X de Y" do aviso). A tela calcula a porcentagem.
- `EnqueteResumo`: `id`, `pergunta`, `multipla_escolha`, `mostrar_resultado`, `encerra_em`,
  `encerrada` (pelo relógio da API), `para_todos`, `blocos: list[int]` (números),
  `criada_em`, `editada_em`, `ja_votou` (a unidade logada).
- `Enquete` = resumo + `opcoes: list[OpcaoEnquete]` (na ordem), `meu_voto: list[int]` (ids das
  opções que a unidade marcou; `[]` se não votou), `votado_em`, `participacao`,
  `resultado_visivel`, `pode_votar` (aberta e a unidade no destino), `pode_editar` (gestão,
  aberta e sem voto nenhum), `aviso_id`.
- `ListaEnquetes`: `itens: list[EnqueteResumo]`, as abertas primeiro (a que termina antes no
  topo), depois as encerradas (a que terminou por último no topo); empate pelo `id` desc.
- `EnqueteGravada`: `id`, `aviso_id`. É a resposta de criar e editar: a tela vai para
  `/enquetes/{id}`, que carrega a `Enquete` (épico B). Assim o épico A não depende da montagem
  da `Enquete`, que é do B (dúvida 10).
- `Votantes` (H-22): `votaram`, `entraram_sem_votar`, `nao_entraram` (listas de `UnidadeRef`,
  das unidades ativas do destino, por login; quem votou e depois foi desativado continua em
  `votaram`). Sem o voto de ninguém.

### 3.3 No aviso (pronto nesta onda)

`AvisoCompleto` ganha `enquete: EnqueteDoAviso | None` (`id`, `pergunta` e, desde os ajustes do
M4, `encerra_em` e `encerrada`, para o cartão dizer "Terminou · ver o resultado"): a enquete que gerou
este aviso (H-13), para o botão "Ir para a enquete". Como o aviso e a enquete têm o mesmo
destino, quem vê o aviso vê a enquete. Serviço: `app/servicos/avisos.py`
(`_enquete_do_aviso`).

`app/servicos/avisos.py` ganha `gravar_correcao(db, logado, aviso_id, dados) -> int` (o
`corrigir` sem o commit; devolve a versão nova), como o `gravar_publicacao` do M3. O `corrigir`
passa a chamar `gravar_correcao` e fazer o commit; nada muda para quem chama.

## 4. Front

| Pasta / arquivo | Dono | Nesta onda |
|---|---|---|
| `web/src/enquetes/tipos.ts`, `api.ts`, `caminhos.ts`, `rotas.tsx` | comum | **pronto**: tipos, uma função por rota, os endereços das telas, e a junção das rotas dos dois épicos |
| `web/src/enquetes/gestao/**` | épico A | `rotas.tsx` com `rotasGestaoEnquetes = []` |
| `web/src/enquetes/votar/**` | épico B | `rotas.tsx` com `rotasVotar = []`, `menu.ts` (`itemEnquetes` devolve `null`: sem item no menu) e `EnqueteDoAviso.tsx` (não mostra nada) |
| `web/src/avisos/tipos.ts` | comum nesta onda | `AvisoCompleto.enquete` e `EnqueteDoAviso` |

Endereços (`caminhos.ts`), para um épico apontar para a tela do outro sem importar dele:
`/enquetes` (lista, B), `/enquetes/:id` (enquete aberta, B), `/enquetes/:id/votantes` (quais
votaram, B), `/enquetes/nova` (A), `/enquetes/:id/editar` (A). O botão "Nova enquete" da lista
(B) aponta para `/enquetes/nova`; o "Editar" da enquete aberta (B, quando `pode_editar`) aponta
para `/enquetes/:id/editar`. As rotas de gestão ficam atrás de `ExigeGestao`.

Pontos de encaixe já ligados (o épico troca só o corpo, do lado dele):

| Onde | Chama | Épico |
|---|---|---|
| `web/src/rotas.tsx` | `...rotasEnquetes` (de `enquetes/rotas.tsx`, que junta `rotasVotar` e `rotasGestaoEnquetes`) | A e B |
| `web/src/casca/menu.ts` | `itemEnquetes()` de `enquetes/votar/menu.ts`, depois de "Avisos" (hoje `null`) | B |
| `web/src/avisos/AvisoAberto.tsx` | `<EnqueteDoAviso enquete={aviso.enquete} />` depois do botão do documento (hoje `null`) | B |
| `web/src/administracao/frases.ts` | frases de `enquete_criada` e `enquete_editada` (prontas) | comum |

O protótipo é a referência das telas: "Abertas / Terminadas", o selo "Seu apartamento ainda não
votou", "O voto vale pelo apartamento X do Bloco Y. Dá para trocar até …", a confirmação no
lugar ("Seu apartamento já votou em …. Se escolher outra, vale a nova."), as barras do
resultado, "N de M apartamentos votaram (P%)", "Enquete é consulta. Não tem valor legal de
votação em assembleia." (RN-03, em toda enquete), e no formulário o alerta "Depois do primeiro
voto, a pergunta e as opções não podem mais mudar.". Celular e computador (RNF-02): votar em no
máximo 3 toques a partir da tela inicial (menu → enquete → opção e "Votar").

Teste dos encaixes e das funções de API: `web/src/m4contrato.test.ts`.

## 5. Posse dos arquivos

**Épico A · Criar e gerir** edita só: `api/app/rotas/enquetes_gestao.py`,
`api/app/servicos/enquetes_gestao.py` (novo), `api/testes/test_enquetes_gestao*.py` (novos),
`web/src/enquetes/gestao/**`, `docs/superpowers/duvidas-m4-gestao.md` (novo). Nos testes comuns,
só: apagar a seção "épico A" de `api/testes/test_m4_em_construcao.py`.

**Épico B · Votar e resultado** edita só: `api/app/rotas/enquetes.py`,
`api/app/servicos/enquetes.py` (novo), `api/testes/test_enquetes_voto*.py` e
`api/testes/test_enquetes_resultado*.py` (novos), `web/src/enquetes/votar/**`,
`docs/superpowers/duvidas-m4-votar.md` (novo). Nos testes comuns, só: apagar a seção "épico B"
de `api/testes/test_m4_em_construcao.py`.

**Comuns — nenhum épico edita** (se precisar, avisa o coordenador e explica no arquivo de
dúvidas do épico): `api/migracoes/**` (**nenhuma migração nova no M4 sem o coordenador**),
`api/app/modelos/**`, `api/app/esquemas/{enquetes,avisos,comum}.py`,
`api/app/servicos/{avisos,historico,notificacoes,visibilidade}.py`, `api/app/seguranca/**`,
`api/app/main.py`, `api/app/erros_api.py`, `api/testes/{conftest,apoio}.py` e os testes já
existentes (inclusive `test_m4_rotas.py`, `test_m4_banco.py`; as únicas exceções são as dos
parágrafos acima), `api/pyproject.toml`, `api/uv.lock`, `web/src/enquetes/{tipos,api,caminhos,
rotas}.ts*`, `web/src/{main.tsx,rotas.tsx,estilo.css}`,
`web/src/{api,arquivos,avisos,casca,acesso,administracao,documentos,notificacoes,recuperacao}/**`,
`web/package*.json`, `vercel.json`, `docs/0*.md`, `docs/adr/**`, este spec. A versão do
`web/package.json` e o `web/src/sobre/novidades.ts` mudam só no fechamento do marco
(coordenador). Um épico **pode** criar um CSS próprio (`web/src/enquetes/<pasta do
épico>/<nome>.css`).

Usar sem editar: `gravar_publicacao`, `gravar_correcao` (avisos), `agendar` (notificações),
`registrar` (histórico), `IdBanco`, `UnidadeRef`, `Tela`, `Icone`, `useSessao`, `useRecado`
(casca), as funções de `web/src/enquetes/api.ts` e os endereços de `caminhos.ts`.

Mudança no contrato (campo novo, rota nova) dentro do próprio épico é permitida nos arquivos do
épico, desde que `test_contrato.py` continue verde e a mudança fique registrada no arquivo de
dúvidas do épico. Banco de teste próprio: `PORTAL_TESTE_BANCO=portal_teste_m4_gestao` e
`portal_teste_m4_votar`, cada um num container (ou porta) só dele.

## 6. Fica de fora desta onda

Implementação das histórias; migração no Neon (produção e `previa`); qualquer execução na
Vercel ou no Neon. Fica de fora **do M4** (backlog, dúvidas 3, 7 e 9): retirar o voto, prorrogar
ou encerrar antes do prazo uma enquete que já tem voto, cancelar uma enquete criada por engano,
texto explicativo na enquete, notificação quando a enquete termina.
