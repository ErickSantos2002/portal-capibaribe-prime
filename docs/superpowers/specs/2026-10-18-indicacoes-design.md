# Indicações de serviços (design)

Estado: **no ar (1.8.0, 18/10/2026), aguardando retorno dos moradores** · Data: 18/10/2026 · Versão alvo: **1.8.0** (novidade = minor) · Migração nova: **0010**
Origem: votação no grupo de WhatsApp em 18/10/2026 (a opção 1, "Indicações de serviços", foi a
mais pedida) e brainstorming com o Erick. Ele aprovou o desenho **sem mudanças**:
`.superpowers/brainstorm/525159-1792347030/content/indicacoes.html` (fora do git; três telas e as
regras embaixo).

## 1. Por quê

Perto da entrega, o grupo vai se encher de "alguém indica um marceneiro?", e a resposta se perde
nas mensagens. Depois da mudança, o assunto vira eletricista, encanador e diarista. As indicações
ficam guardadas no Portal, organizadas, e **os próprios moradores alimentam**.

Dois critérios do Erick valem para toda função nova:
- **Ninguém precisa ficar alimentando.** Nem ele, nem a Comissão.
- **Continua útil depois da obra**, quando o Portal vira o sistema do condomínio.

## 2. Objetivos, não-objetivos, anti-objetivos

**Objetivos**
- Qualquer unidade ativa indica um prestador (com a primeira opinião) e dá a sua opinião
  (recomendo ou não recomendo, com comentário opcional) sobre um que já está na lista.
- A lista é fácil de achar: busca, categorias e os mais recomendados primeiro.
- Botão direto para o WhatsApp do prestador.
- O mesmo prestador não aparece duas vezes.
- A gestão consegue esconder o que estiver errado, sem precisar acompanhar nada no dia a dia.

**Não-objetivos**
- Nota de 1 a 5 estrelas, foto do serviço, preço, orçamento ou agenda.
- Notificação de indicação nova (seria spam).
- Página pública. Nada aparece fora do login.
- Classificados e "conheça seus vizinhos": são as outras opções da votação, e cada uma é outro
  projeto.

**Anti-objetivos (fracasso, mesmo funcionando)**
- O mesmo apartamento inflar um prestador. Por isso há **uma opinião por unidade e prestador**,
  garantida pelo banco.
- Lista poluída de duplicados ("Marcenaria X" e "marcenaria x ltda" com o mesmo telefone).
- A gestão ter trabalho de rotina: moderar só quando alguém avisa.
- Dado pessoal novo sem entrar no inventário da LGPD e na página de privacidade.

## 3. Telas (aprovadas, ver o desenho)

### 3.1 Lista: `/indicacoes`
- Título "Indicações". Busca "Procurar: nome ou serviço" (nome do prestador, categoria e texto
  das opiniões, sem diferenciar acento nem maiúscula).
- Filtro **"Categoria"**: lista de escolher nativa (`<select>` com rótulo visível), da largura
  da coluna, com "Todos" primeiro. Escolher filtra; "Todos" tira só a categoria (o filtro "com
  aviso" da gestão liga e desliga pelo botão dele; "Ver todas" tira os dois). *Até a 1.9.0 era
  uma faixa de chips que rolava para o lado; virou lista de escolher na 1.9.1, a pedido do Erick
  (a rolagem não dava sinal nenhum no celular).*
- Cartão: categoria (em caixa alta, ipê-forte), nome, "👍 N vizinhos recomendam" (verde) e, se
  houver, "N não recomenda(m)" (cor de alerta), mais o trecho da opinião mais recente com
  comentário e o bloco de quem escreveu.
- Ordem: mais recomendações primeiro; no empate, a opinião mais recente.
- Botão fixo embaixo "＋ Indicar alguém" (ipê). Fica acima da barra do celular e não cobre o
  último cartão.
- Lista vazia: "Ainda não tem indicação aqui. Seja o primeiro a indicar alguém." e o botão.

### 3.2 Prestador aberto: `/indicacoes/:id`
- Categoria, nome, total de recomendações e não recomendações.
- Botão **"WhatsApp: (81) 9 0000-0000"** (link `https://wa.me/55<dígitos>`) e um "Ligar"
  (`tel:`) se o número não for celular. Instagram opcional, como link.
- Botão **"Dar a minha opinião"**, que vira **"Mudar a minha opinião"** se a unidade já opinou
  (abre o mesmo formulário com o que ela escreveu e a opção "Apagar a minha opinião").
- "O que os vizinhos disseram": cada opinião com a **placa da unidade** (bloco e apartamento,
  decisão do Erick), 👍/👎, data e comentário. Mais recente primeiro.
- Link discreto **"Tem algo errado aqui? Avisar a gestão"**, que abre uma confirmação com um
  motivo opcional (até 300 caracteres).
- Quem indicou o prestador (ou a gestão) pode **corrigir o nome, a categoria e os contatos**.
- Para a gestão, uma seção "Para a gestão" (o nome já usado em avisos, documentos e enquetes),
  com os avisos recebidos, "Esconder este prestador" e "Esconder esta opinião" em cada opinião.

### 3.3 Indicar alguém: `/indicacoes/nova`
- Campos: **Que serviço?** (categoria, lista), **Nome do prestador ou da empresa** (2–80),
  **WhatsApp ou telefone** (obrigatório, só números brasileiros com DDD, 10 ou 11 dígitos),
  **Instagram** (opcional, `@usuario`), **Você recomenda?** (👍 Recomendo / 👎 Não recomendo,
  sem padrão marcado), **Conte como foi (opcional)** (até 500 caracteres).
- **Duplicado:** enquanto a pessoa digita o nome, o Portal busca nomes parecidos e mostra "Já tem
  uma **X** na lista. É a mesma? Dar minha opinião lá". Se o telefone já existe, a API recusa
  (409 `prestador_ja_existe`, com o id) e a tela leva para o prestador existente com o formulário
  de opinião aberto.
- "Publicar indicação" cria o prestador **e** a primeira opinião numa transação.
- Sair com coisa escrita pergunta "Sair sem publicar?", como nos avisos.

### 3.4 Menu
Lugar novo na lista única (`casca/menu.ts`): **"Indicações"**, frase "Serviços que os vizinhos
recomendam", grupo "Dia a dia", **fora da barra** (fica na folha do Menu e no menu lateral). É o
primeiro teste real de "lugar novo = uma entrada".

## 4. Regras

| Regra | Onde é garantida |
|---|---|
| Só unidade **ativa e logada** vê e escreve | Rotas (sessão) e trigger, como no voto (0009) |
| **Uma opinião por unidade e prestador** | `unique (prestador_id, unidade_id)` |
| Telefone único entre **todos** os prestadores, escondidos inclusive (minha escolha: esconder não libera o número, então quem pediu para sair não volta no dia seguinte) | Índice único sobre os dígitos |
| Prestador nasce com a primeira opinião | Serviço (transação). Prestador sem nenhuma opinião visível **sai da lista**, mas a página dele continua abrindo (é para lá que o 409 leva), e uma opinião nova o traz de volta |
| Corrigir prestador: quem indicou ou a gestão | Rota. O banco guarda `criado_por` |
| Apagar opinião: a própria unidade | Rota. Apagar de verdade, não esconder |
| Esconder (prestador ou opinião) e resolver aviso: **a gestão** (dependência `Gestao`: Comissão, administração), com registro no histórico | Rota + `historico` |
| Opinião escondida fica **travada**: continua ocupando a vaga da unidade, que vê "A gestão escondeu a sua opinião" e não edita nem apaga (409 `opiniao_escondida`). Só "apagar meus dados" e o reset a removem | Rota + trigger |
| Telefone de prestador escondido: o 409 diz que o prestador não está disponível no Portal, **sem link** | Rota |
| Limite: **10 indicações novas e 30 opiniões por unidade por dia**, contando só **linhas inseridas** (a primeira opinião, criada com o prestador, conta; mudar a opinião não conta) | Trigger, no padrão do limite de arquivos da 0007 |
| Avisar a gestão: **1 aviso aberto por unidade e prestador** | `unique` parcial |
| Comentário ≤ 500, nome 2–80, motivo ≤ 300, sem caracteres invisíveis (NFC) | Pydantic + `check` |
| Categorias fixas, gerenciáveis pela gestão | Tabela `categoria_servico` com carga inicial |

Categorias iniciais, nesta ordem: Móveis planejados · Ar-condicionado · Cortinas e persianas ·
Mudança · Eletricista · Encanador · Pintura · Gesso · Vidraçaria e box · Diarista · Outros.
"Gerenciável" nesta versão = **acrescentar** e **renomear**, **só a administração** (`Admin`), com
uma tela mínima dentro da administração. Apagar categoria não existe.

## 5. Dados (migração 0010)

Proposta. Os nomes seguem o padrão das tabelas existentes, e o builder ajusta tipos e índices.
- `categoria_servico (id, nome unique, ordem, criada_em)`.
- `prestador (id, categoria_id, nome, nome_busca (normalizado, sem acento, minúsculo), telefone
  (só dígitos, único), instagram null, criado_por → unidade **null** (vira nulo em "apagar meus
  dados"/reset, para o próximo morador do apê não herdar o direito de corrigir), criado_em, editado_em, escondido_em null,
  escondido_por null)`.
- `opiniao_servico (id, prestador_id, unidade_id, recomenda boolean, comentario null, criada_em,
  editada_em, escondida_em null, escondida_por null)`, com `unique (prestador_id, unidade_id)`.
- `aviso_servico (id, prestador_id, unidade_id, motivo null, criado_em, resolvido_em null,
  resolvido_por null)`.
- Grants para `app` no mesmo padrão da 0007/0008 (só as colunas que a aplicação escreve), mais
  verificações em `verificacoes.sql`, se o padrão existir.
- **Aplicar no Neon ANTES do push** (regra do backup: a restauração reprova se o código pedir uma
  tabela que o banco não tem).

## 6. Privacidade (LGPD)

- **Dado novo de terceiro:** o nome e o telefone do prestador, que pode ser pessoa física. Ele é
  indicado como contato profissional, e o uso é só mostrar para os moradores logados.
- **Dado novo da unidade:** as opiniões, que aparecem com a placa (bloco e apartamento) para
  todos os logados, por decisão do Erick. A placa sozinha não é dado pessoal (`04`, seção 5), e o
  nome do responsável **nunca** aparece.
- **"Apagar meus dados" (H-06)** apaga de verdade as opiniões (inclusive escondidas) e os avisos
  da unidade, e põe `criado_por = null` nos prestadores que ela indicou. O prestador **não** é
  apagado: sem opinião visível, ele só sai da lista (seção 4). O **reset da gestão (H-08)** faz o
  mesmo.
- **O prestador pode pedir para sair:** a gestão esconde o prestador (o que já existe atende).
- Atualizar o inventário (`docs/04-modelo-de-dados.md`, seção 5) e a página **Privacidade** do
  Portal, no mesmo commit, com o texto na voz do morador.

## 7. API (proposta)

Prefixo `/api/indicacoes`, sessão obrigatória, `X-Portal: 1` em escrita (padrão do Portal).
- `GET /categorias`
- `GET /?categoria=&busca=`: lista ordenada (seção 3.1).
- `GET /parecidos?nome=`: até 3 nomes parecidos para o aviso de duplicado.
- `POST /`: prestador + primeira opinião. 409 `prestador_ja_existe` com o `id`.
- `GET /{id}`: prestador, opiniões e a minha opinião. A gestão recebe também os avisos.
- `PUT /{id}`: corrigir (quem indicou ou a gestão).
- `PUT /{id}/opiniao` e `DELETE /{id}/opiniao`: a minha opinião.
- `POST /{id}/aviso`: avisar a gestão.
- Gestão: `POST /{id}/esconder`, `POST /opinioes/{id}/esconder`, `POST /avisos/{id}/resolver`,
  `POST /categorias` e `PUT /categorias/{id}`.
- Erros na mesma forma de `erros_api.py`. `IdBanco` com 422 para id fora da faixa, como no resto.

## 8. Gestão sem rotina

Ninguém precisa abrir as indicações para moderar. Quando chega o **primeiro aviso aberto** de um
prestador, as unidades com papel **admin** recebem **um e-mail** (só a administração, minha
escolha: a Comissão também pode esconder, mas não é acordada por isso) (o mesmo envio dos avisos, em segundo plano,
ADR-0010) com o link. Na lista, a gestão vê no topo "N indicações com aviso da vizinhança", que
filtra. Esconder ou resolver tira dali.

## 9. Pronto quando

- Testes da API (pytest) cobrindo cada regra da seção 4 **tentando burlar direto no banco**
  (padrão do M4): segunda opinião da mesma unidade, telefone duplicado, unidade inativa, limite
  do dia, prestador escondido fora da lista e "apagar meus dados".
- Testes do front (vitest): as três telas, o duplicado (parecidos e 409), mudar e apagar a minha
  opinião, avisar a gestão, a seção da gestão e o lugar novo no menu.
- Conferência visual headless (script do M5, telas novas `indicacoes`, `indicacao`,
  `nova-indicacao`) a 320/360/412/1280 × 16/24/32 × claro/escuro, sem problema novo. **Nenhuma
  janela de navegador visível.**
- Revisão independente de código e de UX, com as correções e teste de regressão.
- Migração 0010 aplicada no Neon antes do push. Versão **1.8.0** com item em `novidades.ts`.
  Privacidade e inventário atualizados.

## 10. O que fica com o builder

Medidas, componentes e nomes de arquivo. Como normalizar o nome (unaccent em SQL ou em Python).
O algoritmo de "parecidos" (prefixo ou trigram, se `pg_trgm` existir no Neon free; senão,
`ilike` no `nome_busca`). A formatação do telefone na tela. Os textos de erro, no tom do Portal.
O ícone do lugar no menu (traço único, no estilo de `Icone.tsx`).
