# Classificados entre vizinhos (design)

Estado: **em construção** · Data: 20/10/2026 · Versão alvo: **1.9.0** (novidade = minor) · Migração nova: **0011**
Origem: votação no grupo de WhatsApp em 18/10/2026 (opção 2, "Classificados entre vizinhos": "um
espaço pra vender, trocar ou doar entre nós: o móvel que não coube, a sobra de piso, o
eletrodoméstico que vai ser trocado"). O Erick pediu para construir com autonomia e deixar as
perguntas para o fim; este desenho foi fechado pelo coordenador, seguindo o das **Indicações**
(`2026-10-18-indicacoes-design.md`, 1.8.0), que ele aprovou sem mudanças. As escolhas que são
dele ficam em `docs/superpowers/duvidas-classificados.md`, para perguntar uma por vez no fim.

## 1. Por quê

Na entrega das chaves, cada apartamento vai ter sobra: piso, porcelanato, rejunte, o sofá que não
coube, a geladeira velha que vai ser trocada. No grupo do WhatsApp a oferta se perde em minutos.
Depois da mudança, continua: móvel que sai, coisa de criança que ficou pequena. Os próprios
moradores alimentam, e o anúncio **some sozinho** quando vence.

Os dois critérios do Erick para toda função nova:
- **Ninguém precisa ficar alimentando.** Nem ele, nem a Comissão. Anúncio velho sai sozinho.
- **Continua útil depois da obra.**

## 2. Objetivos, não-objetivos, anti-objetivos

**Objetivos**
- Qualquer unidade ativa anuncia algo para **vender, trocar ou doar**, ou diz o que **procura**
  (entrou por resposta do Erick em 20/10/2026), com até **4 fotos**.
- Quem se interessa fala direto com o dono pelo **WhatsApp**, com a mensagem já escrita.
- O dono marca **"Reservado"** e depois **"Encerrar"** (vendido, trocado, doado ou desistiu).
- Anúncio **vence em 30 dias** e sai da lista sozinho; o dono renova com um toque.
- A gestão esconde o que estiver errado, sem precisar acompanhar nada no dia a dia.

**Não-objetivos (nesta versão)**
- Pagamento, chat dentro do Portal, oferta/lance, frete.
- Notificação de anúncio novo (seria spam). Notificação de vencimento.
- Página pública. Nada aparece fora do login.

**Anti-objetivos (fracasso, mesmo funcionando)**
- Lista cheia de anúncio velho de coisa que já foi vendida. Por isso o vencimento automático.
- Foto de móvel guardada **para sempre** no bucket travado. Foto de classificado é descartável:
  mora numa pasta própria, sem trava, e é apagada de verdade (seção 6, ADR-0012).
- Expor o celular de alguém sem ele escolher. O contato é digitado (ou confirmado) **em cada
  anúncio**.
- Virar loja: limite de anúncios por apartamento.
- Dado pessoal novo sem entrar no inventário da LGPD e na página de privacidade.

## 3. Telas

### 3.1 Lista: `/classificados`
- Título "Classificados". Busca "Procurar: o que você quer?" (título, descrição e categoria, sem
  diferenciar acento nem maiúscula).
- Filtro de **tipo** (Tudo · Vende · Troca · Doa · Procura; quebra em linha, nunca esconde um) e faixa de **categorias** ("Todas" primeiro),
  no mesmo padrão da faixa das Indicações (rola dentro, inclusive com letra grande).
- Cartão: foto de capa (quadrada, ou um marcador sem foto), tipo (selo: "Vende R$ 350",
  "Troca", "Doa"; venda sem preço = "Vende · a combinar"), título, categoria, placa da unidade e
  há quanto tempo foi publicado. **Reservado** aparece como selo e o cartão continua na lista.
- Ordem: mais recente primeiro (publicação ou renovação).
- Botão fixo embaixo "＋ Anunciar" (ipê), no mesmo padrão do "Indicar alguém".
- Entrada **"Meus anúncios"** no topo da lista quando a unidade tem algum (ativos, vencidos e
  encerrados recentes).
- Lista vazia: "Ainda não tem anúncio aqui. Que tal anunciar o que sobrou da obra?" e o botão.

### 3.2 Anúncio aberto: `/classificados/:id`
- Fotos (a primeira grande; toque abre a foto inteira, com anterior/próxima), tipo e preço,
  título, categoria, descrição, placa da unidade, data.
- Botão **"Chamar no WhatsApp"** (`https://wa.me/55<dígitos>?text=<mensagem>`), mensagem pronta:
  "Oi! Vi seu anúncio "<título>" no Portal Capibaribe Prime. Ainda está disponível?".
  Fixo sem WhatsApp → "Ligar" (`tel:`), mesma regra do telefone das Indicações: "Ligar" é o
  principal e o WhatsApp continua como botão leve (fixo pode ter WhatsApp Business), com a mesma
  mensagem pronta (confirmado na revisão de UX, item 13).
  No "Procura", a mensagem é de quem tem o que é procurado: "Oi! Vi no Portal Capibaribe Prime
  que você procura "<título>". Tenho um que pode te interessar."
- Para o dono: **Editar**, **Marcar como reservado / Tirar a reserva** (não no "Procura": quem
  procura não reserva), **Renovar** (quando vencido ou a menos de 7 dias de vencer), **Encerrar**
  (confirmação com o motivo: Vendi · Troquei · Doei · Desisti; no "Procura", Encontrei ·
  Desisti). Encerrado não volta (anuncia de novo, se quiser).
- Link discreto **"Tem algo errado aqui? Avisar a gestão"**, igual ao das Indicações.
- Para a gestão, a seção "Para a gestão": avisos recebidos, "Esconder este anúncio",
  "Resolver aviso".

### 3.3 Anunciar: `/classificados/novo` (e editar: `/classificados/:id/editar`)
- **O que você quer fazer?** Vender · Trocar · Doar · Procurar (sem padrão marcado). No
  "Procurar", sem preço; fotos opcionais, como nos outros (pode ser uma foto de referência).
- **Categoria** (lista). **Título** (3–80). **Descrição (opcional)** (até 1000).
- **Preço** (só em Vender; opcional; em reais, até R$ 100.000; vazio = "a combinar").
- **Fotos (até 4)**: o mesmo envio do M3 (compressão no navegador, conferência do conteúdo,
  JPEG regravado para tirar o GPS), só imagens (JPEG, PNG, WEBP). Reordenar não precisa: a
  primeira enviada é a capa; tirar e pôr de novo resolve.
- **WhatsApp ou telefone para contato** (obrigatório), **pré-preenchido** com o celular da
  unidade (Minha unidade), editável, com a frase "Aparece para os vizinhos logados neste
  anúncio.". Mesma validação e normalização das Indicações (nono dígito).
- "Publicar anúncio". Sair com coisa escrita pergunta "Sair sem publicar?".

### 3.4 Menu
Lugar novo na lista única (`casca/menu.ts`): **"Classificados"**, frase "Vender, trocar, doar ou
procurar entre vizinhos", grupo "Dia a dia", **fora da barra** (folha do Menu e menu lateral), ao lado de
"Indicações".

## 4. Regras

| Regra | Onde é garantida |
|---|---|
| Só unidade **ativa e logada** vê e escreve | Rotas (sessão) e trigger, como nas Indicações |
| Tipo ∈ {venda, troca, doacao, procura}; preço só em venda, ≥ 0 e ≤ 10.000.000 centavos | `check` |
| Situação: `ativo` → `reservado` ↔ `ativo` → `encerrado` (com motivo). Encerrado é final. "Procura" nunca fica reservado | Trigger |
| Motivo do encerramento: Encontrei só no "Procura"; Vendi, Troquei e Doei só nos outros; Desisti em todos | `check` |
| Vence em **30 dias** depois de publicar ou renovar (`vence_em`). Vencido sai da lista, sem job: a consulta filtra por data | Consulta + coluna |
| Renovar: só o dono, só ativo/reservado, só vencido ou a menos de 7 dias de vencer | Rota + trigger |
| Editar, reservar, renovar, encerrar: **só o dono** (a unidade que anunciou). A gestão só esconde | Rota |
| Anúncio escondido fica travado: o dono vê "A gestão escondeu este anúncio" e só pode encerrar | Rota + trigger |
| Limites: **5 anúncios novos por unidade por dia** e **10 abertos** (ativo/reservado, não vencidos) | Trigger, no padrão da 0007/0010 |
| Até **4 fotos** por anúncio, só imagem | Trigger + conferência do envio |
| Avisar a gestão: **1 aviso aberto por unidade e anúncio**, 10 avisos por unidade a cada 24 h | `unique` parcial + trigger |
| Título 3–80, descrição ≤ 1000, motivo ≤ 300, sem caracteres invisíveis (NFC) | Pydantic + `check` |
| Categorias gerenciáveis pela administração (acrescentar, renomear) | Tabela + tela mínima, como nas Indicações |

Categorias iniciais, nesta ordem: Móveis · Eletrodomésticos · Eletrônicos · Material de obra e
acabamento · Decoração · Utilidades domésticas · Infantil · Outros.

## 5. Dados (migração 0011)

Proposta; o builder ajusta tipos e índices no padrão das tabelas existentes.
- `categoria_classificado (id, nome unique, ordem, criada_em)`.
- `anuncio (id, unidade_id → unidade, categoria_id, tipo, titulo, titulo_busca, descricao,
  descricao_busca, preco_centavos null, contato (só dígitos), situacao, motivo_encerramento null,
  publicado_em, renovado_em, vence_em, editado_em, encerrado_em null, escondido_em null,
  escondido_por null)`.
  `unidade_id` **não** fica nulo: o anúncio é da unidade e some com "apagar meus dados".
- `anuncio_foto (id, anuncio_id on delete cascade, chave unique, ordem, largura, altura, bytes,
  criada_em)` (ou reaproveitar `arquivo` com uma coluna de pasta: o builder escolhe o que dá menos
  exceção na camada de arquivos, justificando na ADR-0012).
- `aviso_anuncio (id, anuncio_id, unidade_id, motivo null, criado_em, resolvido_em null,
  resolvido_por null)`.
- Grants para `app` só nas colunas que a aplicação escreve; `delete` só onde o Portal apaga de
  verdade (anúncio e foto, no "apagar meus dados", no reset e na faxina). Verificações em
  `verificacoes.sql`.
- **Aplicar no Neon ANTES do push** (regra do backup).

## 6. Fotos: descartáveis, numa pasta sem trava (ADR-0012, nova)

A ADR-0011 trava `arquivos/` para sempre, e a camada de armazenamento só apaga em `envios/`. Isso
é certo para documento oficial e errado para foto de geladeira usada: o anúncio acaba, a foto
tem que ir embora (minimização da LGPD e espaço no R2 grátis).

Decisão (escrever como **ADR-0012**, complementando a 0011):
- Pasta nova **`classificados/<chave>`** no mesmo bucket de arquivos. A trava do R2 é por
  prefixo (`arquivos/`), então esta pasta **não** é travada; **conferir** isso no bucket real
  antes do push com um objeto de teste (o coordenador faz).
- O envio é o mesmo do M3 (`envios/` → conferência → cópia), mas o destino é `classificados/`.
- A camada de armazenamento ganha **um** "apagar" novo, que só aceita `classificados/<chave>`
  (teste: recusa `arquivos/` e qualquer outra coisa). O falso dos testes imita.
- **Não entra na cópia diária** dos arquivos (backup): depois de um desastre, os anúncios voltam
  sem as fotos (aceito; são efêmeros).
- **Apaga de verdade** as fotos: ao tirar a foto na edição, ao encerrar (depois de 7 dias, para
  o dono ainda ver o encerrado em "Meus anúncios"), no "apagar meus dados", no reset e na faxina.
- **Faxina diária**: anúncio vencido há mais de 30 dias, ou encerrado ou escondido pela gestão há
  mais de 7 dias, é apagado (linha e fotos). O escondido entrou na revisão de código (M3, decisão
  do coordenador): sem isso, a foto de um anúncio escondido ficava até 60 dias. Rodar pelo que o repo já tem (Vercel Cron do plano Hobby, 1×/dia, ou o
  workflow diário do GitHub chamando uma rota protegida): o builder escolhe e justifica. Falha
  da faxina não quebra nada (só atrasa).
- Leitura: link assinado curto, como os anexos; a capa da lista vem no mesmo formato.

## 7. Privacidade (LGPD)

- **Dado novo da unidade:** o anúncio (com a placa visível para os logados, como nas Indicações)
  e o **contato**, que a pessoa escolhe por anúncio. O nome do responsável **nunca** aparece.
- **Fotos** podem mostrar o interior do apartamento: a tela de anunciar lembra "Evite fotos com
  pessoas ou documentos." e o GPS sai de todo JPEG.
- Retenção curta e automática (seção 6): encerrado some em 7 dias, vencido em 30.
- **"Apagar meus dados" (H-06)** e **reset (H-08)** apagam de verdade os anúncios, as fotos e os
  avisos da unidade.
- Atualizar o inventário (`docs/04-modelo-de-dados.md`, seção 5) e a página **Privacidade** do
  Portal, no mesmo commit, na voz do morador.

## 8. API (proposta)

Prefixo `/api/classificados`, sessão obrigatória, `X-Portal: 1` em escrita.
- `GET /categorias`
- `GET /?tipo=&categoria=&busca=`: lista (ativos e reservados, não vencidos, não escondidos).
- `GET /meus`: os da unidade (todos os estados, enquanto existirem).
- `POST /`: cria (com as fotos já enviadas pelo fluxo de envio do M3).
- `GET /{id}`: anúncio; a gestão recebe também os avisos. Vencido/encerrado abre para o dono e a
  gestão; para os outros, 404 com a frase "Este anúncio não está mais disponível."
- `PUT /{id}`: editar (dono). `POST /{id}/reservar`, `/{id}/liberar`, `/{id}/renovar`,
  `/{id}/encerrar` (dono).
- `POST /{id}/aviso`: avisar a gestão.
- Gestão: `POST /{id}/esconder`, `POST /avisos/{id}/resolver`, `POST /categorias`,
  `PUT /categorias/{id}`.
- Faxina: o que o builder escolher na seção 6, protegido.
- Erros na forma de `erros_api.py`; `IdBanco` com 422 para id fora da faixa.

## 9. Gestão sem rotina

Igual às Indicações: no **primeiro aviso aberto** de um anúncio, as unidades **admin** recebem
um e-mail (envio em segundo plano, cota do Gmail reservada no `historico`, ADR-0010), sem o
motivo e sem a placa de quem avisou. Na lista, a gestão vê "N anúncios com aviso da vizinhança",
que filtra.

## 10. Pronto quando

- pytest cobrindo cada regra da seção 4 **tentando burlar direto no banco** (padrão do M4):
  limite do dia e de abertos, 5ª foto, preço em doação, encerrado que volta, renovar fora da
  janela, unidade inativa, escondido travado, "apagar meus dados" apagando fotos no armazenamento
  falso, apagar fora de `classificados/` recusado, faxina.
- vitest: as telas, o filtro, o fluxo do dono (reservar, renovar, encerrar), avisar a gestão, a
  seção da gestão, o lugar novo no menu, a mensagem pronta do WhatsApp.
- Conferência visual headless (script do M5, telas novas `classificados`, `classificado`,
  `novo-classificado`, `meus-classificados`) a 320/360/412/1280 × 16/24/32 × claro/escuro, sem
  problema novo. **Nenhuma janela de navegador visível.**
- Revisão independente de código e de UX, com correções e teste de regressão.
- Migração 0011 no Neon antes do push. Versão **1.9.0** com item em `novidades.ts`. Privacidade,
  inventário, ADR-0012 e roadmap atualizados.

## 11. O que fica com o builder

Medidas, componentes, nomes de arquivo, o visor de fotos, como reaproveitar o envio do M3, o
mecanismo da faxina, os textos de erro no tom do Portal, o ícone do menu (traço único, estilo
`Icone.tsx`). Toda escolha que muda o que o morador vê vai para `duvidas-classificados.md`.
