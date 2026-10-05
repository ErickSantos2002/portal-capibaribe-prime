# Spec · M1 · Épico C · Avisos (só texto)

| | |
|---|---|
| **Marco** | M1 · Acesso e mural |
| **Histórias** | H-12 publicar (#10), H-14 mural (#11), H-15 corrigir ou arquivar (#12), H-16 quem leu (#13) |
| **Base** | `03-historias.md`, `02-requisitos.md` (RF-10, RF-12 a RF-15, RN-05, RNF-13, RNF-14), `04-modelo-de-dados.md` §3.3, contrato `specs/m1-contrato.md` §4.4, `duvidas-m1.md`, protótipo |
| **Plano** | `docs/superpowers/plans/m1-avisos.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m1-avisos.md` |
| **Fora** | Anexos (M3), notificação e e-mail (M2, H-13) |

## 1. O que entrega

A API das rotas da seção 4.4 do contrato e as telas do protótipo: mural, aviso aberto, novo
aviso (com prévia), corrigir aviso, avisos arquivados e "quem leu". Sem migração nova e sem
tocar em arquivo comum.

## 2. API

Regras de negócio em `app/servicos/avisos.py`; as rotas (`app/rotas/avisos.py`) só traduzem
HTTP. Cada rota de gestão usa `Gestao` (RNF-13); as de leitura, `UnidadeLogada`.

### 2.1 Visibilidade
- Unidade comum: aviso `para_todos` ou com o bloco dela em `aviso_bloco`. Fora disso, 404
  `aviso_nao_encontrado`, igual a aviso inexistente (inclusive em `POST …/lido`).
- Gestão: vê e abre todos (precisa corrigir e conferir qualquer aviso). O mural da gestão
  mostra todos os avisos, com os blocos de destino na linha de detalhes.

### 2.2 Mural e busca (H-14)
- Ordem: fixados primeiro, depois `publicado_em` do mais novo para o mais antigo (empate: `id`).
- `arquivados=false` (padrão): só não arquivados. `arquivados=true`: só arquivados, do mais
  novo para o mais antigo, sem dar prioridade a fixado.
- Busca (até 100 caracteres): no título e no texto da versão em vigor, sem diferenciar
  maiúsculas nem acentos; cada palavra digitada precisa aparecer (em qualquer ordem). Feita em
  Python sobre os avisos visíveis (cerca de 300 em 2 anos; dúvida 25 do M1).
- `lido`: a unidade logada já abriu o aviso. `resumo`: primeiro parágrafo, linhas juntadas por
  espaço, até 200 caracteres (cortado com "…").

### 2.3 Publicar (H-12)
- `publicado_como`: `comissao` se a unidade tem esse papel, senão `admin`, `sindico`,
  `conselho`. Mostrado como "Comissão", "Administração do Portal", "Síndico", "Conselho".
- Bloco desconhecido ou inativo: 422 `bloco_inexistente` "O Bloco N não existe." (com `campos`
  apontando `blocos`, para a tela marcar o campo).
- Quem publica conta como quem já leu (como no protótipo): não aparece "Novo" para ela.
- Histórico `aviso_publicado` com `para_todos`, `blocos`, `fixado` e `titulo`.
- Alcance (`GET /api/avisos/alcance`): unidades `ativa = true` dos blocos (sem blocos: todas).
- **Rota nova** `GET /api/avisos/destinos` (gestão): blocos ativos (`numero`, `nome`), para os
  botões "Bloco N" do formulário. Sem ela a tela teria os blocos 1 a 5 fixos no código, e os
  blocos são editáveis (H-10). Ver dúvida 1 do épico.

### 2.4 Corrigir, arquivar, fixar (H-15)
- Corrigir cria a versão `max + 1` (o banco confere). Igual à em vigor: 409 `sem_mudanca`.
  Arquivado: 409 `aviso_arquivado`. Duas correções ao mesmo tempo: a segunda bate na PK e vira
  409 `aviso_corrigido_agora` "Outra pessoa corrigiu este aviso agora há pouco. Abra de novo
  e confira." Histórico `aviso_corrigido` com `versao` e `titulo`.
- `editado_em` = `criada_em` da versão em vigor quando há mais de uma. `versoes_anteriores`
  da mais nova para a mais antiga.
- Arquivar: `arquivado_em` (banco carimba) e **desafixa** (fixado não tem sentido fora do
  mural). Já arquivado: 409 `aviso_arquivado` "Este aviso já está arquivado.". Histórico
  `aviso_arquivado`. Não existe rota de apagar.
- Fixar/desafixar: 409 se arquivado; histórico só se mudou.

### 2.5 Leitura (H-16)
- `POST …/lido`: `insert … on conflict do nothing`, 204.
- "Lido por X de Y": Y = unidades `ativa = true` do destino; X = dessas, as que têm leitura
  (gestão que abriu aviso de outro bloco não entra na conta). `nao_leram` por login.
- `leitura` em `AvisoCompleto` só para a gestão; `null` para a unidade comum.
- `nao-lidos`: avisos visíveis, não arquivados, sem leitura da unidade.

## 3. Telas (protótipo, `web/src/avisos/`)

| Caminho | Tela |
|---|---|
| `/avisos` | Mural: fixados em amarelo no topo, "Procurar nos avisos", folha contínua com "Novo" escrito, link "Avisos arquivados", botão flutuante "Novo aviso" (gestão) |
| `/avisos/arquivados` | Mesma lista, só arquivados, com busca |
| `/avisos/:id` | Aviso aberto: assinatura e destino, "Corrigido em" com "Ver como era antes", texto; marca como lido ao abrir. Gestão: "X de Y apartamentos leram", Corrigir, Fixar/Desafixar, Arquivar (com confirmação) |
| `/avisos/novo` | Título, texto, destino em botões, "Fixar no topo", quantos apartamentos recebem; 1º toque mostra a prévia, o 2º publica |
| `/avisos/:id/corrigir` | Título e texto preenchidos; a versão de antes fica guardada |
| `/avisos/:id/leitura` | Leram / ainda não, apartamentos que não leram por bloco, "Copiar a lista" |

- **Texto puro:** o texto vira parágrafos (linha em branco) com quebra simples preservada
  (`white-space: pre-line`). Endereços `http://` e `https://` viram links (abrem em outra aba,
  `rel="noopener noreferrer"`); nada é interpretado como HTML (sem `dangerouslySetInnerHTML`).
- Sem notificação no M1: os textos não prometem notificação nem e-mail.
- CSS próprio em `web/src/avisos/avisos.css`, sem `style=` (CSP).

## 4. Critérios de aceite → testes

Cada critério de `03-historias.md` vira teste em `api/testes/test_avisos*.py` (API) e
`web/src/avisos/*.test.tsx` (tela). A lista final está no plano.
