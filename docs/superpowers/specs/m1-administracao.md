# Spec · M1 · Épico B · Administração

| | |
|---|---|
| **Marco** | M1 · Acesso e mural |
| **Histórias** | H-07 painel de ativação (#6), H-08 resetar uma unidade (#7), H-09 papel de Comissão (#8), H-11 histórico (#9) |
| **Base** | `docs/03-historias.md`, `docs/02-requisitos.md` (RF-06, RF-07, RF-09, RNF-13, RNF-14), `docs/04-modelo-de-dados.md` §5, ADR-0005, contrato `specs/m1-contrato.md` §4.3, dúvidas `duvidas-m1.md` (9, 10, 18, 24) |
| **Plano** | `docs/superpowers/plans/m1-administracao.md` |
| **Dúvidas do épico** | `docs/superpowers/duvidas-m1-administracao.md` |

## 1. Objetivo

O administrador do Portal (hoje, só o Erick) consegue: medir a adesão e perceber conta tomada
(painel), devolver uma unidade ao estado inicial (reset), dar e retirar os papéis de Comissão e de
administrador, e ler o histórico de ações. Tudo só para o admin (dúvida 9 do M1), conferido no
servidor (RNF-13).

## 2. API (`app/rotas/administracao.py` → `app/servicos/administracao.py`)

A rota só traduz HTTP; a regra mora no serviço, que não faz commit (quem chama decide, como no
resto do projeto). Todas as rotas com `Admin` (`exige_admin`) e o roteador com
`exige_cabecalho_portal`.

| Rota | Comportamento |
|---|---|
| `GET /api/admin/unidades?situacao=` | `PainelAtivacao`. Só unidades `ativa = true`, em ordem de login. Resumo geral e por bloco sempre do prédio inteiro; `situacao` filtra só `unidades` (`ativadas` = `ativada_em` preenchida; `nao_ativadas`; `gestao` = algum papel em vigor). Percentual arredondado para o inteiro mais próximo (meio para cima); prédio sem unidade dá 0. |
| `GET /api/admin/unidades/{login}` | `UnidadeAdmin`. Login inexistente, fora do padrão ou unidade desativada: 404 `unidade_nao_encontrada`. `aparelhos_conectados` conta só sessões válidas (mesma regra de `buscar_sessao`). |
| `POST …/{login}/resetar` | Corpo `{"confirmo": true}`. Trava a linha da unidade; retira cada papel em vigor (`retirado_por` = admin) com `papel_retirado` (`{"papel", "origem": "reset"}`); depois senha `mudar123`, `precisa_trocar_senha`, `ativada_em`/contatos nulos, `tentativas_falhas = 0`, `bloqueada_ate` nulo, encerra todas as sessões; registra `unidade_resetada` (`{"papeis_retirados": [...]}`). Último admin: 409 `ultimo_admin` e nada muda. Vale também para unidade não ativada (tira o bloqueio e derruba quem entrou com `mudar123`). |
| `PUT …/{login}/papeis/{papel}` | `papel` ∈ {`comissao`, `admin`} (outro: 422). Unidade não ativada: 409 `unidade_nao_ativada` (a regra também está no banco: `papel_em_unidade_ativada` vira o mesmo 409). Já tem: 200 sem registro novo. Senão insere e registra `papel_concedido` `{"papel"}`. Dois pedidos iguais ao mesmo tempo: o segundo bate no índice único e vira 200 idempotente. |
| `DELETE …/{login}/papeis/{papel}` | Não tem: 200 sem registro. Senão retira (`retirado_por`) e registra `papel_retirado` `{"papel"}`. Último admin: 409 `ultimo_admin`. |
| `GET /api/admin/historico?antes_de=&limite=` | `PaginaHistorico`, mais novo primeiro (por `id`, que cresce com o tempo). `limite` 1..100 (padrão 50), `antes_de` ≥ 1. Busca `limite + 1` para saber se há próxima página. |

Histórico de admin (`entidade = "unidade"`, `entidade_id` = a unidade afetada, `unidade_id` = o
admin que fez). Nenhum detalhe leva nome, celular ou e-mail (`registrar` já recusa).

### 2.1 Mudança no contrato do épico: o item afetado no histórico

H-11 pede "o item afetado", e `entidade_id` é um número interno que a tela não sabe traduzir. O
protótipo mostra "resetou o Bloco 1, 106" e "publicou o aviso “Vistoria…”". `ItemHistorico`
ganha dois campos (esquema Python e tipo TS juntos):

- `unidade_afetada: UnidadeRef | null`: quando `entidade = "unidade"`.
- `aviso_titulo: string | null`: quando `entidade = "aviso"`, o título da versão em vigor
  (título de aviso é público dentro do Portal; não é dado pessoal).

Só leitura nas tabelas de avisos (épico C), nada é escrito nelas.

### 2.2 Dados pessoais (modelo §5)

- Painel: responsável e celular, que H-07 pede e que a gestão pode ver. E-mail só na ficha da
  unidade. Nenhuma descrição de aparelho (só a própria unidade vê): a ficha mostra a contagem.
- Histórico: só `UnidadeRef` (apartamento), ação, item e detalhes sem dado pessoal.
- Respostas com `Cache-Control: no-store` (painel, ficha e histórico têm dado pessoal ou de
  segurança e não devem ficar em cache do navegador ou de proxy).

## 3. Telas (`web/src/administracao/`)

Seguem o protótipo (`telaAdmin`, `telaUnidade`, `telaHistorico`), com as classes já em
`estilo.css` (`resumo`, `grade`, `legenda`, `ficha`, `folha`, `item`, `chips`, `aviso-caixa`).
CSS novo só em `administracao.css`, sem `style=` (CSP).

- **`/unidades` (H-07):** resumo (já entraram · ainda não · adesão %), filtros em chips (Todas,
  Já entraram, Ainda não, Com papel), e por bloco: "Bloco N: X de Y (Z%)". Com "Todas", a grade
  do protótipo (8 colunas, do 7º andar ao térreo; já entrou = verde; papel = faixa amarela). Com
  outro filtro, ou ao tocar em "Ver como lista", a lista do bloco: placa, responsável, celular e
  "entrou em …". Cada unidade abre a ficha. Link para o histórico no fim.
- **`/unidades/:login` (H-08, H-09):** placa grande, ficha (situação, primeiro acesso,
  responsável, celular, e-mail, papel, aparelhos conectados, bloqueio). Resetar: botão perigo →
  caixa de confirmação no lugar (padrão do protótipo), listando o que vai acontecer, com
  "Sim, resetar" e "Cancelar". Papéis: "Dar papel de Comissão" / "Tirar papel de Comissão" e o
  mesmo para administrador (retirar admin também confirma). Unidade não ativada: explica que só
  dá papel depois do primeiro acesso. Erros da API numa caixa de erro; sucesso por `useRecado`.
  Se o admin mexeu na própria unidade (reset ou retirou o próprio admin), a sessão é relida
  (`recarregar`) e as guardas levam para onde couber.
- **`/historico` (H-11):** "Só o administrador vê. Ninguém consegue apagar."; lista com quem fez
  (placa pequena ou "Portal"), a frase da ação e a data/hora de Recife; "Carregar mais" com
  `proximo`.

## 4. Testes

- Um teste por critério de aceite (lista no plano).
- **Portão (issue #18):** um teste percorre `app.routes` e acha **todas** as rotas `/api/admin/**`
  (não uma lista escrita à mão), e prova a recusa para conta comum, Comissão, sessão restrita de
  primeiro acesso e sem sessão, e que nada foi gravado. Alteração sem `X-Portal` também recusada.
- Front: testes de componente (vitest) do painel, da ficha (confirmação de reset, papéis, erro
  409) e do histórico (frases e paginação), com `fetch` de mentira.
- Navegador (Playwright) contra API e banco locais: 390 px e 1366 px, claro e escuro, sem
  violação de CSP.
