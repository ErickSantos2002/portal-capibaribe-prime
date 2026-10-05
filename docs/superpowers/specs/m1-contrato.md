# Spec · M1 Onda 1 · Contrato

| | |
|---|---|
| **Marco** | M1 · Acesso e mural (`docs/07-roadmap.md`, seção 4) |
| **Base** | `03-historias.md` (H-01, 02, 03, 06, 07, 08, 09, 11, 12, 14, 15, 16), `04-modelo-de-dados.md`, `05-arquitetura.md`, ADR-0001/0002/0003/0005, protótipo |
| **Criado em** | 05/10/2026 |
| **Plano** | `docs/superpowers/plans/m1-contrato.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m1.md` |

## 1. Objetivo

Deixar a base do M1 pronta para que **três agentes trabalhem em paralelo**, cada um num épico,
sem tocar nos mesmos arquivos nem criar migrações conflitantes:

| Épico | Histórias | Também |
|---|---|---|
| **A · Acesso** | H-01 primeiro acesso, H-02 entrar, H-03 bloqueio, H-06 minha unidade | layout e tema (já entregues aqui como casca), política de privacidade (RNF-11) |
| **B · Administração** | H-07 painel de ativação, H-08 resetar, H-09 papel de Comissão, H-11 histórico | |
| **C · Avisos (só texto)** | H-12 publicar, H-14 mural, H-15 corrigir/arquivar, H-16 quem leu | |

Esta onda **não implementa as histórias**. Entrega: a migração 0002 com tudo o que o M1 grava,
o contrato da API (este documento + schemas Pydantic + tipos TypeScript), as peças comuns
(sessão, dependências de permissão, CSRF, histórico, formato de erro) e a casca do front.

## 2. Banco · migração 0002

Mesmo padrão da 0001: SQL escrito à mão, roda como `dono`, permissões ao papel `app` (nome
trocável por `-x papel_app=`), funções de trigger com `set search_path = pg_catalog, public,
pg_temp` e nomes qualificados, `upgrade → downgrade → upgrade` testado. `aviso_anexo` e
`arquivo` ficam para o M3.

### 2.1 Tabelas novas (avisos sem anexo)

| Tabela | Colunas | Regras no banco |
|---|---|---|
| `aviso` | `id`, `publicado_por` → unidade, `publicado_como` (`papel`), `publicado_em`, `para_todos`, `fixado` (padrão `false`), `arquivado_em` | `publicado_em` carimbado com `now()`; `arquivado_em` carimbado com `now()` ao arquivar e não pode voltar a nulo |
| `aviso_versao` | PK (`aviso_id`, `versao`), `titulo` (1 a 120), `texto` (1 a 10.000), `criada_em`, `criada_por` → unidade | `versao` só pode ser a próxima (1, 2, 3…); `criada_em` carimbado |
| `aviso_bloco` | PK (`aviso_id`, `bloco_id`) | recusado se o aviso é `para_todos` |
| `aviso_leitura` | PK (`aviso_id`, `unidade_id`), `lido_em` | `lido_em` carimbado; primeira abertura conta (`on conflict do nothing`) |

`publicado_como` **não está no modelo de dados**: guarda com que papel o aviso foi assinado
("Publicado pela Comissão", H-12), porque o papel da unidade pode mudar depois. Ver dúvida 3.

Regra de consistência (trigger de restrição **adiada para o commit**): todo aviso tem a versão 1,
e aviso que não é `para_todos` tem pelo menos um bloco. Assim o banco não aceita aviso sem texto
nem aviso sem destino, mesmo que a aplicação erre a ordem dos INSERTs dentro da transação.

### 2.2 Mudanças em tabelas da 0001

| O quê | Por quê |
|---|---|
| Trigger `unidade_papel_regras`: retirar o último `admin` em vigor falha com `check_violation`, restrição `ultimo_admin` | H-09 ("o Portal não pode ficar sem administrador"); prometido para o M1 na dúvida 4 do M0. Trava as outras linhas de admin com `select … for update`: duas retiradas ao mesmo tempo dão recusa, erro de serialização ou impasse desfeito pelo Postgres, nunca zero admins (testado em READ COMMITTED e REPEATABLE READ) |
| Papel em vigor **só em unidade ativa e já ativada** (restrição `papel_em_unidade_ativada`); unidade com papel em vigor não é desativada nem volta a "não ativada" (restrição `unidade_com_papel`: o reset retira os papéis antes) | Uma conta de gestão com `mudar123` seria tomada por quem conhece o padrão (revisão do M1). Cobre também "desativar a única unidade admin" |
| Dados: a 0002 **retira os papéis em vigor de unidades não ativadas** (o `admin` que a carga do M0 deu), com registro `papel_retirado` (`origem: migracao_0002`) no histórico | Em produção, o admin volta pela sequência da seção 2.5 |
| `unidade_papel.concedido_em` e `retirado_em` carimbados com `now()`; retirado não volta a vigorar | O painel (H-07) e o histórico mostram essas datas como prova (dúvida 20 do M0) |
| `app` só altera `retirado_em` e `retirado_por` em `unidade_papel` (GRANT por coluna) | Um papel não vira outro: retira-se e concede-se de novo, com registro |
| `unidade`: CHECK "ativada tem responsável e celular"; celular só com 10 ou 11 dígitos; nome de 1 a 100 caracteres; e-mail com `@` e até 254 caracteres | RF-04 ("obrigatório após ativar") garantido no banco; formato único para o painel e a busca |
| `unidade.senha_trocada_em` (data do banco, muda sozinha quando `senha_hash` muda) e `sessao.criada_em` carimbada pelo banco | Sessão aberta antes da última troca de senha não vale (seção 2.4) |

O celular é guardado **só com dígitos** (`81912345678`); a tela formata. Os dados fictícios
passam a seguir o formato (dúvida 6).

### 2.3 Permissões do `app` nas tabelas novas

| Tabela | SELECT | INSERT | UPDATE | DELETE | Por quê |
|---|---|---|---|---|---|
| `aviso` | sim | sim | só `fixado` e `arquivado_em` | **não** | RN-05: corrige-se ou arquiva-se, nunca se apaga |
| `aviso_versao` | sim | sim | **não** | **não** | Correção é versão nova; a anterior fica como estava (H-15) |
| `aviso_bloco` | sim | sim | **não** | **não** | O destino é parte do que foi publicado |
| `aviso_leitura` | sim | sim | **não** | **não** | Fato: a unidade abriu o aviso. Reset e "apagar meus dados" não apagam leitura (é da unidade, não da pessoa) |

### 2.4 Sessão

- **Sessão restrita** (ADR-0005) não é coluna: é `unidade.precisa_trocar_senha = true`, lida a
  cada requisição.
- **Troca de senha derruba as sessões anteriores** (revisão do M1): a sessão só vale se
  `sessao.criada_em >= unidade.senha_trocada_em`. Quem entrou com `mudar123` antes do morador
  guarda um cookie que **morre** quando o morador conclui o primeiro acesso; o reset e o "apagar
  meus dados" (que voltam a senha para `mudar123`) derrubam todos os aparelhos sozinhos. Por
  isso o primeiro acesso e a troca de senha **abrem uma sessão nova** para quem trocou
  (`trocar_senha_e_sessao`, seção 3.1).
- **Validade de 180 dias, renovada a cada uso:** a sessão vale enquanto
  `ultimo_uso_em > now() - 180 dias` e `encerrada_em is null`. `ultimo_uso_em` (e o cookie) são
  renovados no máximo uma vez por hora, para não gravar no banco a cada requisição.

### 2.5 O primeiro administrador (sequência de produção)

A carga inicial **não dá papel nenhum** (revisão do M1: o M0 dava `admin` a uma unidade com
`mudar123`). Em produção:

1. Deploy (migração 0002 aplicada; ela retira o papel que a carga do M0 tinha dado).
2. O Erick faz o primeiro acesso na unidade dele, pelo Portal (senha própria, contatos).
3. Roda-se, de `api/`, com a URL do `app`:
   `uv run python -m app.comandos.promover_admin <login>`. O comando recusa unidade que ainda
   não fez o primeiro acesso, é idempotente e registra `papel_concedido`
   (`origem: promover_admin`) no histórico. A unidade real só aparece na linha de comando,
   nunca no repositório.
4. Daí em diante, Comissão e outros admins pela tela de administração (H-09).

`PORTAL_ADMIN_UNIDADE` deixou de existir. Em desenvolvimento e teste, os dados fictícios dão
`admin` a uma unidade fictícia já ativada e `comissao` a duas; na prévia, nenhum papel.

## 3. Peças comuns da API (prontas e testadas nesta onda)

### 3.1 Sessão por cookie (`app/seguranca/sessoes.py`)

- Token: `secrets.token_urlsafe(32)` (32 bytes aleatórios). O banco guarda só
  `sha256(token)` em hexadecimal (`sessao.token_hash`).
- Cookie `__Host-sessao`: `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, sem `Domain`,
  `Max-Age` de 180 dias. O prefixo `__Host-` obriga o navegador a recusar o cookie se algum
  desses atributos faltar. Funciona em `http://localhost` (contexto seguro) e nos testes com
  `https://testserver`.
- `SameSite=Lax` (ADR-0005), e não `Strict`: dúvida 1.
- Funções: `criar_sessao(db, unidade_id, user_agent) -> str` (devolve o token),
  `buscar_sessao(db, token) -> Sessao | None`, `renovar(db, sessao) -> bool`,
  `encerrar_sessao(db, sessao_id)`, `encerrar_todas(db, unidade_id, exceto=None) -> int`,
  `trocar_senha_e_sessao(db, unidade_id, senha_nova, user_agent) -> str` (grava o hash novo,
  encerra **todas** as sessões da unidade e abre uma nova; a rota grava o cookie),
  `gravar_cookie(resposta, token)`, `apagar_cookie(resposta)`, `descrever_aparelho(user_agent) -> str` ("Android · Chrome").
- Nada aqui faz `commit`: quem chama decide (mesma regra da carga).

### 3.2 Dependências FastAPI (`app/seguranca/dependencias.py`)

| Dependência | Devolve | Recusa com |
|---|---|---|
| `sessao_qualquer` | `Logado` (inclusive sessão restrita) | 401 `sem_sessao` |
| `unidade_logada` | `Logado` com primeiro acesso concluído | 401 `sem_sessao`, 403 `primeiro_acesso_pendente` |
| `exige_gestao` | `Logado` com papel `admin`, `comissao`, `sindico` ou `conselho` em vigor | os de cima e 403 `sem_permissao` |
| `exige_admin` | `Logado` com papel `admin` em vigor | os de cima e 403 `sem_permissao` |
| `exige_cabecalho_portal` | nada | 403 `requisicao_recusada` se o método altera dados e falta `X-Portal: 1` |

`Logado` (dataclass congelada): `sessao_id`, `unidade_id`, `login`, `bloco` (int),
`apartamento` (str), `papeis` (frozenset de `Papel`), `precisa_trocar_senha`, e as
propriedades `gestao` e `admin`. Os papéis são lidos do banco **a cada requisição** (H-09:
"as opções somem imediatamente, mesmo com ela logada"). A unidade desativada (`ativa = false`)
não tem sessão válida. A dependência também guarda `request.state.unidade_id`, que o registro de
erros já usa.

Todas as rotas de gestão usam `exige_gestao` ou `exige_admin` (RNF-13). Cada épico tem um teste
por rota de gestão provando que uma unidade comum recebe 403 (portão do M1, issue #18).

### 3.3 CSRF

Os roteadores dos épicos e o de sessão nascem com `dependencies=[Depends(exige_cabecalho_portal)]`:
`POST`, `PUT`, `PATCH` e `DELETE` sem `X-Portal: 1` recebem 403. O cliente do front manda o
cabeçalho sempre. A rota de diagnóstico do M0 fica de fora de propósito (ela precisa responder
404 idêntico a uma rota inexistente).

### 3.4 Formato de erro (`app/erros_api.py`)

Todo erro previsto da API responde:

```json
{ "codigo": "credenciais_invalidas", "mensagem": "Bloco, apartamento ou senha incorretos. Confira e tente de novo." }
```

- `codigo`: identificador estável em `snake_case`, para o front decidir o que fazer.
- `mensagem`: texto pronto para mostrar ao morador, em português simples.
- Campos extras quando úteis (ex.: `bloqueada_ate`, `minutos_restantes`).
- Levantar: `raise ErroApi(status, codigo, mensagem, **extras)`.

Erro de validação (422) vira:

```json
{ "codigo": "dados_invalidos", "mensagem": "Confira os campos marcados.",
  "campos": [{ "campo": "senha_nova", "mensagem": "A senha nova precisa ter pelo menos 8 letras ou números." }] }
```

A mensagem de cada campo vem do validador (`ValueError("texto")` no Pydantic) ou de uma tradução
padrão por tipo ("Preencha este campo.", "Valor inválido."). **O valor digitado nunca volta na
resposta** (o padrão do FastAPI devolve o `input`, que pode ser uma senha). 401/403/404/405 do
Starlette fora das nossas rotas continuam no formato padrão (`{"detail": ...}`), para a rota de
diagnóstico do M0 continuar indistinguível de uma rota inexistente.

### 3.5 Histórico (`app/servicos/historico.py`)

```python
registrar(db, acao: Acao, *, unidade_id: int | None, entidade: str | None = None,
          entidade_id: int | None = None, detalhes: dict | None = None) -> None
```

`Acao` (StrEnum) lista as ações do M1: `carga_inicial`, `dados_ficticios`, `primeiro_acesso`,
`unidade_bloqueada`, `senha_trocada`, `dados_apagados`, `aparelho_desconectado`,
`unidade_resetada`, `papel_concedido`, `papel_retirado`, `aviso_publicado`, `aviso_corrigido`,
`aviso_arquivado`, `aviso_fixado`, `aviso_desafixado`. `unidade_id = None` é ação do sistema
(bloqueio automático). `detalhes` só aceita valores simples (texto, número, booleano, nulo ou
lista deles) e **recusa chaves de dado pessoal** (`senha`, `nome`, `responsavel_nome`, `celular`,
`email`, `token`…) com `ErroDoPortal`. Não faz commit.

### 3.6 Senhas (`app/seguranca/senhas.py`)

`gerar_hash(senha) -> str`, `senha_confere(hash, senha) -> bool` (nunca levanta),
`SENHA_INICIAL = "mudar123"`. Argon2id com os parâmetros padrão (ADR-0005); os testes trocam o
`hasher` do módulo por um de custo baixo (fixture `hasher_rapido`, automática).

## 4. Contrato da API

Convenções: JSON em `snake_case`; datas em ISO 8601 com fuso (UTC), a tela mostra em
`America/Recife`; unidade sempre identificada pelo `login` (`"1101"`) na URL, e mostrada como
`{ "login": "1101", "bloco": 1, "apartamento": "101" }` (`UnidadeRef`). Toda alteração exige
`X-Portal: 1` (seção 3.3). Erros no formato da seção 3.4; abaixo, só o `codigo`.

Schemas Pydantic: `api/app/esquemas/{comum,acesso,administracao,avisos}.py`. Tipos TypeScript
espelho: `web/src/api/tipos.ts` (comuns) e `web/src/{acesso,administracao,avisos}/tipos.ts`. Um
teste (`api/testes/test_contrato.py`) confere que cada schema tem um tipo TS com os mesmos campos.

### 4.1 Sessão (comum, já implementado nesta onda)

| Rota | Quem | Corpo | Resposta | Erros |
|---|---|---|---|---|
| `GET /api/acesso/eu` | sessão (inclusive restrita) | — | 200 `Eu` | 401 `sem_sessao` |
| `POST /api/acesso/sair` | qualquer um | — | 204, encerra a sessão e apaga o cookie (sem sessão também dá 204) | 403 `requisicao_recusada` |

`Eu`: `{ unidade: UnidadeRef, papeis: Papel[], gestao: bool, admin: bool,
precisa_trocar_senha: bool }`. É o que a casca do front usa para decidir rotas e menu.

### 4.2 Épico A · Acesso (`app/rotas/acesso.py`)

| Rota | Quem | Corpo | Resposta | Erros |
|---|---|---|---|---|
| `POST /api/acesso/entrar` | qualquer um | `Entrar` | 200 `Eu` + cookie | 401 `credenciais_invalidas`, 423 `unidade_bloqueada`, 422 |
| `POST /api/acesso/primeiro-acesso` | sessão restrita | `PrimeiroAcesso` | 200 `Eu` (já liberado) + cookie novo | 401, 409 `primeiro_acesso_ja_feito`, 422 |
| `GET /api/minha-unidade` | `unidade_logada` | — | 200 `MinhaUnidade` | 401, 403 |
| `PUT /api/minha-unidade/dados` | `unidade_logada` | `DadosDaUnidade` | 200 `MinhaUnidade` | 401, 403, 422 |
| `PUT /api/minha-unidade/senha` | `unidade_logada` | `TrocarSenha` | 204 + cookie novo | 400 `senha_atual_incorreta`, 401, 403, 422 |
| `DELETE /api/minha-unidade/aparelhos/{sessao_id}` | `unidade_logada` | — | 204 (se for o próprio aparelho, apaga o cookie) | 404 `aparelho_nao_encontrado` |
| `POST /api/minha-unidade/apagar-dados` | `unidade_logada` | `ApagarDados` | 204, apaga o cookie | 409 `unidade_com_papel_de_gestao`, 422 |

- `Entrar`: `login` (4 dígitos, `^[1-9][0-7][0-9]{2}$`; a tela monta a partir de bloco +
  apartamento), `senha` (1 a 200 caracteres).
  - Login inexistente, unidade desativada ou senha errada: **a mesma** resposta 401
    `credenciais_invalidas`, "Bloco, apartamento ou senha incorretos. Confira e tente de novo."
    (H-02). Login inexistente também passa por uma verificação de hash, para o tempo de resposta
    não diferenciar.
  - 5 erros seguidos: `bloqueada_ate = now() + 15 min`, `tentativas_falhas` volta a 0, histórico
    `unidade_bloqueada` (ação do sistema, `unidade_id` nulo, entidade `unidade`). Enquanto
    bloqueada, até a senha certa recebe 423 `unidade_bloqueada` com `bloqueada_ate` e
    `minutos_restantes`: "Entrada bloqueada por N minutos depois de várias senhas erradas. Se não
    foi você, avise a administração do Portal no grupo do WhatsApp." (H-03). Senha certa zera
    `tentativas_falhas`.
  - Unidade com `precisa_trocar_senha`: cria a sessão (restrita) e devolve `Eu` com
    `precisa_trocar_senha: true`; a tela vai para "Primeiro acesso" (H-01).
- `PrimeiroAcesso`: `senha_nova`, `senha_nova_repetida`, `responsavel_nome` (1 a 100, sem
  espaços nas pontas), `celular` (aceita máscara; guarda 10 ou 11 dígitos), `email` (opcional;
  vazio vira nulo; guardado em minúsculas). Mensagens:
  - "A senha nova precisa ter pelo menos 8 letras ou números." (menos de 8)
  - "Escolha uma senha diferente da inicial, que todo mundo conhece." (`mudar123`)
  - "As duas senhas estão diferentes. Escreva a mesma nas duas."
  - "Escreva o nome de quem responde pela unidade."
  - "Confira o celular: DDD e número, como (81) 9 1234-5678."
  - "Confira o e-mail, ou deixe em branco."

  Efeito: hash novo, `precisa_trocar_senha = false`, `ativada_em = now()`, contatos gravados,
  histórico `primeiro_acesso`. **Encerra todas as sessões da unidade e abre uma nova** para
  quem concluiu (`trocar_senha_e_sessao` + `gravar_cookie`): quem entrou com `mudar123` antes
  do morador perde o acesso. O banco garante isso mesmo se a rota esquecer (seção 2.4), mas a
  rota precisa devolver o cookie novo, senão o próprio morador cai para "sem sessão".
- `MinhaUnidade`: `unidade`, `responsavel_nome`, `celular`, `email`, `papeis`, `ativada_em`,
  `aparelhos: Aparelho[]`. `Aparelho`: `id`, `descricao`, `criada_em`, `ultimo_uso_em`,
  `este_aparelho`.
- `DadosDaUnidade`: `responsavel_nome`, `celular`, `email` (mesmas regras do primeiro acesso).
- `TrocarSenha`: `senha_atual`, `senha_nova`, `senha_nova_repetida`. Senha atual errada: 400
  "A senha atual não confere." Histórico `senha_trocada`. **Desconecta os outros aparelhos** e
  abre uma sessão nova para este (`trocar_senha_e_sessao`), como no primeiro acesso: na conta
  compartilhada, trocar a senha é o jeito de tirar quem não devia estar lá (dúvida 8, revista).
- `ApagarDados`: `{ "confirmo": true }` (qualquer outro valor: 422). Efeito (H-06): apaga
  responsável, celular e e-mail, senha volta a `mudar123`, `precisa_trocar_senha = true`,
  `ativada_em = null`, encerra **todas** as sessões, histórico `dados_apagados`. Votos e
  leituras ficam. Unidade com papel de gestão em vigor recebe 409: "Este apartamento tem papel
  de gestão. Peça à administração do Portal para retirar o papel antes." (dúvida 7).
- `DELETE …/aparelhos/{id}`: só sessões da própria unidade; de outra unidade, 404 (não revela que
  existe). Histórico `aparelho_desconectado`.

### 4.3 Épico B · Administração (`app/rotas/administracao.py`)

Todas com `exige_admin` (dúvida 9).

| Rota | Corpo / parâmetros | Resposta | Erros |
|---|---|---|---|
| `GET /api/admin/unidades` | `?situacao=todas\|ativadas\|nao_ativadas\|gestao` (padrão `todas`) | 200 `PainelAtivacao` | 401, 403, 422 |
| `GET /api/admin/unidades/{login}` | — | 200 `UnidadeAdmin` | 404 `unidade_nao_encontrada` |
| `POST /api/admin/unidades/{login}/resetar` | `ConfirmarReset` (`{ "confirmo": true }`) | 200 `UnidadeAdmin` | 404, 409 `ultimo_admin`, 422 |
| `PUT /api/admin/unidades/{login}/papeis/{papel}` | — (`papel`: `comissao` ou `admin`) | 200 `UnidadeAdmin` (idempotente) | 404, 409 `unidade_nao_ativada`, 422 |
| `DELETE /api/admin/unidades/{login}/papeis/{papel}` | — | 200 `UnidadeAdmin` (idempotente) | 404, 409 `ultimo_admin`, 422 |
| `GET /api/admin/historico` | `?antes_de=<id>&limite=<1..100, padrão 50>` | 200 `PaginaHistorico` | 401, 403, 422 |

- `PainelAtivacao`: `resumo: ResumoAtivacao` (`total`, `ativadas`, `percentual`, inteiro
  arredondado), `blocos: ResumoBloco[]` (`numero`, `nome`, `total`, `ativadas`, `percentual`),
  `unidades: UnidadePainel[]` (`unidade`, `andar`, `ativada`, `ativada_em`, `responsavel_nome`,
  `celular`, `papeis`). O resumo é sempre do prédio inteiro; o filtro só vale para `unidades`.
  Só unidades `ativa = true`.
- `UnidadeAdmin`: `unidade`, `andar`, `ativada`, `ativada_em`, `responsavel_nome`, `celular`,
  `email`, `papeis`, `bloqueada_ate`, `aparelhos_conectados` (contagem).
- Reset (H-08): senha `mudar123`, `precisa_trocar_senha = true`, `ativada_em = null`, contatos
  nulos, `tentativas_falhas = 0`, `bloqueada_ate = null`, encerra todas as sessões, retira todos
  os papéis em vigor (`retirado_por` = quem resetou). Votos e leituras ficam. Histórico
  `unidade_resetada` + um `papel_retirado` por papel. **Ordem:** retirar os papéis antes de
  voltar a unidade a "não ativada" (o banco recusa o contrário, restrição `unidade_com_papel`). Se a unidade for o último admin, o banco
  recusa e a rota responde 409 `ultimo_admin`: "Esta é a única unidade administradora. Dê o
  papel de administrador a outra unidade antes."
- Papel (H-09): conceder só a unidade ativada (409 `unidade_nao_ativada`: "Só dá para dar papel
  a um apartamento que já entrou no Portal."), porque uma conta com `mudar123` e poder de gestão
  seria tomada por quem conhece o padrão. O banco também garante (restrição
  `papel_em_unidade_ativada`); a rota traduz para o 409. Histórico `papel_concedido`/`papel_retirado` com
  `detalhes = {"papel": ...}`, só quando algo mudou.
- `PaginaHistorico`: `itens: ItemHistorico[]` (`id`, `ocorrido_em`, `unidade` (`UnidadeRef` ou
  nulo = "Portal"), `acao`, `entidade`, `entidade_id`, `detalhes`), `proximo` (o `id` para
  `antes_de` da próxima página, ou nulo). Mais novo primeiro.

### 4.4 Épico C · Avisos (`app/rotas/avisos.py`)

| Rota | Quem | Corpo / parâmetros | Resposta | Erros |
|---|---|---|---|---|
| `GET /api/avisos` | `unidade_logada` | `?busca=<até 100>&arquivados=false` | 200 `ListaAvisos` | 401, 403, 422 |
| `GET /api/avisos/nao-lidos` | `unidade_logada` | — | 200 `ContagemNaoLidos` | 401, 403 |
| `GET /api/avisos/alcance` | `exige_gestao` | `?blocos=1&blocos=3` (sem `blocos` = todos) | 200 `Alcance` | 422 `bloco_inexistente` |
| `GET /api/avisos/{id}` | `unidade_logada` | — | 200 `AvisoCompleto` (só lê) | 404 `aviso_nao_encontrado` |
| `POST /api/avisos/{id}/lido` | `unidade_logada` | — | 204, idempotente (a primeira vez conta) | 404 `aviso_nao_encontrado` |
| `POST /api/avisos` | `exige_gestao` | `NovoAviso` | 201 `AvisoCompleto` | 422 (inclui `bloco_inexistente`) |
| `PUT /api/avisos/{id}` | `exige_gestao` | `CorrigirAviso` | 200 `AvisoCompleto` (versão nova) | 404, 409 `aviso_arquivado`, 409 `sem_mudanca`, 422 |
| `POST /api/avisos/{id}/arquivar` | `exige_gestao` | — | 200 `AvisoCompleto` | 404, 409 `aviso_arquivado` |
| `PUT /api/avisos/{id}/fixado` | `exige_gestao` | `MudarFixado` | 200 `AvisoCompleto` | 404, 409 `aviso_arquivado` |
| `GET /api/avisos/{id}/leitura` | `exige_gestao` | — | 200 `Leitura` | 404 |

- Visibilidade (H-14): a unidade comum vê só avisos `para_todos` ou com o bloco dela em
  `aviso_bloco`; fora disso, 404 igual a aviso inexistente. A gestão vê todos (precisa corrigir
  aviso de qualquer bloco).
- `ListaAvisos`: `itens: AvisoResumo[]`, já na ordem do mural: fixados primeiro, depois do mais
  novo para o mais antigo. Sem paginação no M1 (cerca de 300 avisos em 2 anos). `arquivados=true`
  lista só os arquivados ("Avisos arquivados", H-15), também visíveis para a unidade comum do
  destino. `busca` procura no título e no texto da versão em vigor, sem diferenciar maiúsculas
  nem acentos ("fundacao" acha "Fundação").
- `AvisoResumo`: `id`, `titulo`, `resumo` (primeiro parágrafo, até 200 caracteres),
  `publicado_em`, `publicado_por` (`"Comissão"`, `"Administração do Portal"`, `"Síndico"` ou
  `"Conselho"`, de `publicado_como`), `editado_em` (data da versão em vigor se houver mais de
  uma, senão nulo), `fixado`, `para_todos`, `blocos` (números, vazio se `para_todos`),
  `arquivado_em`, `lido` (pela unidade logada).
- `AvisoCompleto`: tudo do resumo + `texto`, `versoes_anteriores: VersaoAviso[]` (`versao`,
  `titulo`, `texto`, `criada_em`; da mais nova para a mais antiga) e `leitura: ContagemLeitura | null`
  (`lidos`, `total`; só para a gestão, "Lido por X de Y unidades").
- `NovoAviso`: `titulo` (1 a 120, sem espaços nas pontas), `texto` (1 a 10.000; quebras de linha
  preservadas; **texto puro**, a tela nunca interpreta HTML), `para_todos`, `blocos` (números;
  obrigatório e sem repetição quando `para_todos = false`, ignorado quando `true`), `fixado`.
  Mensagens: "Escreva o título do aviso.", "O título pode ter até 120 letras.", "Escreva o texto
  do aviso.", "Escolha pelo menos um bloco, ou Todos os blocos.", bloco desconhecido: 422
  `bloco_inexistente` "O Bloco N não existe.". `publicado_como`: `comissao` se a unidade tem esse
  papel, senão `admin`, `sindico`, `conselho` (nessa ordem). Histórico `aviso_publicado`. A
  "prévia" de H-12 é só da tela; o número de unidades vem de `GET /api/avisos/alcance`.
- `Alcance`: `{ "unidades": N }` (unidades `ativa = true` dos blocos).
- `CorrigirAviso`: `titulo`, `texto` (mesmas regras). Cria a versão seguinte; igual à atual: 409
  `sem_mudanca` "Nada mudou no aviso.". Arquivado: 409 `aviso_arquivado` "Aviso arquivado não
  pode ser corrigido.". Histórico `aviso_corrigido` com `{"versao": n}`.
- Arquivar: `arquivado_em = now()`, sai do mural; histórico `aviso_arquivado`. Não existe rota de
  apagar (RN-05) e o banco nem deixaria.
- `MudarFixado`: `{ "fixado": bool }`; histórico `aviso_fixado`/`aviso_desafixado` só se mudou.
- Leitura (H-16): ao abrir o aviso, a tela chama `POST /api/avisos/{id}/lido` (204; repetir não
  muda nada, `on conflict do nothing`; aviso fora do destino da unidade comum: 404). `GET` nunca
  grava nada: com `SameSite=Lax`, uma navegação vinda de outro site leva o cookie e escaparia do
  `X-Portal` (revisão do M1).
- `ContagemNaoLidos`: `{ "quantidade": N }` (avisos visíveis, não arquivados, não lidos; para o
  número na aba "Avisos").
- `Leitura` (H-16): `lidos`, `total` (unidades `ativa = true` do destino), `nao_leram:
  UnidadeRef[]` (ordenado por login).

## 5. Casca do front

### 5.1 Bibliotecas novas

| Pacote | Por quê |
|---|---|
| `react-router` 8 | Endereço próprio para cada aviso (`/avisos/12`), que é o que a Comissão cola no grupo; botão voltar do celular; rotas protegidas. Escrever um roteador à mão seria refazer isso com menos testes. Uma dependência só (a v8 aboliu o `react-router-dom`). |
| `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/dom` (dev) | Testes de componente previstos na arquitetura (seção 8) e adiados no M0 (dúvida 16). Só desenvolvimento, não vão para o navegador. |

Nenhuma biblioteca de estado, de requisição ou de CSS: o estado é pouco (sessão e tema, em
contexto do React), o `fetch` basta, e o CSS é o do protótipo.

### 5.2 Estrutura

```
web/src/
  main.tsx              monta o roteador (comum)
  rotas.tsx             junta as rotas dos épicos dentro da casca (comum)
  estilo.css            tokens e componentes do protótipo (comum)
  api/cliente.ts        fetch tipado: X-Portal, cookies, ErroDaApi (comum)
  api/tipos.ts          tipos comuns: UnidadeRef, Papel, Eu, ErroResposta (comum)
  casca/                Tela, Topo, Navegacao, BotaoTema, Placa, Icone, Recado,
                        SessaoProvider + guardas, NaoEncontrado, SemPermissao (comum)
  acesso/               épico A: tipos.ts, api.ts, rotas.tsx, páginas
  administracao/        épico B: idem
  avisos/               épico C: idem
```

### 5.3 Rotas e guardas

| Caminho | Épico | Guarda | Página nesta onda |
|---|---|---|---|
| `/entrar` | A | só sem sessão (com sessão vai a `/avisos`) | marcação de lugar |
| `/primeiro-acesso` | A | sessão restrita | marcação de lugar |
| `/privacidade` | A | nenhuma (pública, RNF-11) | marcação de lugar |
| `/minha-unidade` | A | `ExigeUnidade` | marcação de lugar |
| `/avisos`, `/avisos/arquivados`, `/avisos/:id` | C | `ExigeUnidade` | marcação de lugar |
| `/avisos/novo`, `/avisos/:id/corrigir`, `/avisos/:id/leitura` | C | `ExigeGestao` | marcação de lugar |
| `/unidades`, `/unidades/:login`, `/historico` | B | `ExigeAdmin` | marcação de lugar |
| `/` | casca | vai para `/avisos` | — |
| `*` | casca | — | "Não encontrado" |

Guardas (`casca/guardas.tsx`): sem sessão → `/entrar`; sessão restrita → `/primeiro-acesso`;
sem papel → tela "Sem permissão". Cada épico exporta `rotas<Épico>: RouteObject[]` do próprio
`rotas.tsx`; o `web/src/rotas.tsx` comum só as junta.

### 5.4 Layout e tema (como no protótipo, `docs/06-prototipo.md`, seção 3)

- **Celular (< 900 px):** topo verde com título, placa da unidade e botão de tema; abas fixas
  embaixo (Avisos, Minha unidade, e Unidades para o admin). Tela de detalhe (`<Tela voltar=…>`)
  troca a placa pela seta de voltar e esconde as abas.
- **Computador (≥ 900 px):** menu lateral verde (marca no alto, placa e nome no rodapé),
  conteúdo numa coluna de até 720 px.
- **Tema:** começa **claro** (decisão do protótipo: o escuro do aparelho confundia quem testava);
  o botão sol/lua alterna e grava `portal-tema` (`claro`/`escuro`) no `localStorage`. Para não
  piscar claro antes do escuro, `public/tema.js` (arquivo próprio, a CSP proíbe script embutido)
  aplica `data-tema` no `<html>` antes do React.
- Tokens, fonte (Atkinson Hyperlegible local), alvos de 44 px, foco visível e
  `prefers-reduced-motion` iguais ao protótipo. Ícones SVG de traço 2 px do protótipo
  (`casca/Icone.tsx`).
- Nenhum `style=` em JSX nem `<style>`: a CSP (`default-src 'self'`) bloquearia.

### 5.5 Cliente de API

`pedir<T>(metodo, caminho, corpo?)`: `credentials: 'same-origin'`, `X-Portal: 1` em toda
requisição, JSON. Resposta não-2xx vira `ErroDaApi` (`status`, `codigo`, `mensagem`, `campos`,
`extras`); falha de rede vira `ErroDaApi` com `codigo: 'sem_conexao'` e "Sem conexão com o
Portal. Confira a internet e tente de novo.". 204 devolve `undefined`. Cada épico tem seu
`api.ts` com uma função tipada por rota, já escrita nesta onda.

## 6. Preview da Vercel

**Decisão: as prévias usam um único branch do Neon chamado `previa`, só com estrutura (sem
dados de produção) e preenchido com a carga inicial e os dados fictícios.** A variável
`DATABASE_URL` do ambiente *Preview* da Vercel aponta para o papel `app` desse branch.

Por quê:
- Sem banco, a prévia mostra só a tela de entrada: não serve para revisar o M1, que é login,
  mural e painel (o portão do M1 pede revisão independente e ensaio com vizinhos).
- Branch por prévia (integração Neon + Vercel) copia o branch de produção **com os dados
  pessoais**, o que contraria a arquitetura (seção 7: "sem dados pessoais") e a LGPD. O Neon
  tem branch só de estrutura, mas a integração automática cria branch com dados.
- Um branch só cabe folgado no plano grátis (10 branches, computação compartilhada) e não
  acumula branches esquecidos.

Como fazer (quem tiver acesso ao Neon e à Vercel; **nada disso foi executado nesta onda**):
1. No Neon, criar o branch `previa` **só com estrutura** (*schema-only*) a partir de `main`, ou
   vazio e rodar `alembic upgrade head` como `dono` do branch.
2. Rodar a carga e os dados fictícios com `PORTAL_AMBIENTE=previa` (valor aceito a partir
   desta onda). Na prévia, a semente **não dá papel nenhum**: quem revisa faz o primeiro
   acesso numa unidade não ativada e roda `promover_admin` nela, como em produção.
3. Na Vercel, `DATABASE_URL` só no ambiente *Preview*, com a URL do pooler do branch `previa`.
   Nunca a de produção. `PORTAL_DIAGNOSTICO_SEGREDO` fica vazio em prévia.
4. Migração nova no M1: rodar `alembic upgrade head` também no `previa` antes de abrir a prévia.

Risco aceito: prévias compartilham o mesmo banco fictício (um épico pode ver dados de outro).

**Condição para existir prévia com banco: a *Deployment Protection* da Vercel (Vercel
Authentication) ligada para as prévias.** As unidades fictícias ativadas entram com `mudar123`
sem troca obrigatória (para quem revisa entrar rápido); sem a proteção, qualquer pessoa com o
link entraria nelas. Por isso também a prévia não tem papel de gestão fictício (dúvida 28).
As prévias da Vercel ficam atrás da proteção de implantação padrão (login da Vercel).

## 7. Posse dos arquivos

**Épico A · Acesso** edita só: `api/app/rotas/acesso.py`, `api/app/esquemas/acesso.py`,
`api/app/servicos/acesso.py` (novo), `api/testes/test_acesso*.py` e
`api/testes/test_minha_unidade*.py` (novos), `web/src/acesso/**`,
`docs/superpowers/duvidas-m1-acesso.md` (novo).

**Épico B · Administração** edita só: `api/app/rotas/administracao.py`,
`api/app/esquemas/administracao.py`, `api/app/servicos/administracao.py` (novo),
`api/testes/test_administracao*.py` (novos), `web/src/administracao/**`,
`docs/superpowers/duvidas-m1-administracao.md` (novo).

**Épico C · Avisos** edita só: `api/app/rotas/avisos.py`, `api/app/esquemas/avisos.py`,
`api/app/servicos/avisos.py` (novo), `api/testes/test_avisos*.py` (novos), `web/src/avisos/**`,
`docs/superpowers/duvidas-m1-avisos.md` (novo).

**Comuns — nenhum épico edita** (se precisar, avisa o coordenador e explica no arquivo de
dúvidas do épico): `api/migracoes/**` (**nenhuma migração nova no M1 sem o coordenador**),
`api/app/modelos/**`, `api/app/main.py`, `api/app/banco.py`, `api/app/erros_api.py`,
`api/app/seguranca/**`, `api/app/servicos/{historico,erros,carga_inicial,dados_ficticios}.py`,
`api/app/esquemas/comum.py`, `api/app/rotas/{sessao,saude,diagnostico}.py`,
`api/testes/{conftest,apoio}.py` e os testes já existentes, `api/pyproject.toml`, `api/uv.lock`,
`web/src/{main.tsx,rotas.tsx,estilo.css}`, `web/src/api/**`, `web/src/casca/**`,
`web/index.html`, `web/public/**`, `web/package*.json`, `web/vite.config.ts`, `vercel.json`,
`.github/**`, `docs/0*.md`, `docs/adr/**`, este spec. Um épico **pode** criar um CSS próprio
(`web/src/<épico>/<épico>.css`) e importá-lo nas próprias páginas.

A casca usa `contarNaoLidos` de `web/src/avisos/api.ts` (número na aba "Avisos"): o épico C
não renomeia nem muda a assinatura dessa função. Recado depois de navegar:
`navigate(caminho, { state: { recado: 'Aviso publicado.' } })`; na mesma tela, `useRecado()`.
Testes da API: fixtures `predio` e `logar(login)` do `conftest.py` (ver dúvida 24).

Mudança no contrato (campo novo, rota nova) dentro do próprio épico é permitida nos arquivos do
épico, desde que o teste `test_contrato.py` continue verde (schema Python e tipo TS juntos) e a
mudança seja registrada no arquivo de dúvidas do épico.

## 8. Fica de fora desta onda

Implementação das histórias, regra de firewall, backup, e qualquer execução na Vercel ou no Neon.
