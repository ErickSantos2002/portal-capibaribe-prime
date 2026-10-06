# Dúvidas e decisões · Avisos com formatação, categoria e evento

Branch `avisos/visual`. Spec: `specs/2026-10-06-avisos-visual-design.md`; plano:
`plans/avisos-visual.md`. Decisões tomadas sem perguntar, registradas para o Erick conferir.

## Decisões de implementação

1. **O h1 continua no topo** (decisão U9 da revisão do M1: o assunto do aviso é o h1 e o título
   da aba). O cabeçalho do aviso aberto tem data em bloco, categoria e "Publicado pela Comissão em
   …, para …", sem repetir o título. O mockup punha "Aviso" no topo e o título no corpo.
2. **Categoria no banco é `text` com CHECK**, não um enum do Postgres (spec 3.2). Na API é um
   `StrEnum` (`Categoria`), conferido contra o TS pelo `test_contrato`.
3. **Correção sem categoria ou evento mantém os atuais** (revisão de código, achado 2). `evento:
   null` tira o evento. O formulário sempre manda os dois.
4. **Hora do evento é de Recife (−03:00 fixo)**: Recife não tem horário de verão desde 2020. Se
   voltar, `deRecife` (web/src/avisos/datas.ts) precisa olhar o fuso da data.
5. **Data do evento entre 2000 e 2100** (API, CHECK `aviso_versao_evento_quando_faixa` na 0004 e
   `min`/`max` no campo). Ano 9999 com fuso gravava e o mural de todos dava 500 (revisão).
6. **Resumo do mural**: primeiro parágrafo, sem marcas. Se o aviso começa com um `## ` seguido do
   texto sem linha em branco, o resumo junta os dois ("Como entrar Cada apartamento…").
7. **Texto antigo com linha começando por `- `, `1. `, `> ` ou `## ` passa a ser formatado.** É o
   esperado pela spec; o aviso de boas-vindas atual (com MAIÚSCULAS) não tem essas marcas.
8. **"Ver como fica" mostra só o texto renderizado** (o mesmo `TextoDoAviso` do aviso aberto); a
   prévia completa (cartão do mural + aviso aberto com cabeçalho e quadro) continua no "Ver prévia".
9. **Data em bloco:** a da publicação, ou o dia do evento quando o aviso é evento (dúvida A,
   decidida pelo Erick). O fixado não tem bloco e mantém a data na linha de detalhes.
10. **Evento em outro ano mostra o ano** ("Sáb, 09/10/27 · 9h", "Sábado, 9 de outubro de 2027,
    9h"), achado da revisão de UX.
11. **Barra: "Subtítulo, Negrito, Lista, Destaque"** (a spec dizia "Título"). Com dois "Título"
    na mesma tela, a Dona Socorro mexeria no texto achando que era o título do aviso.
12. **"É um evento?" logo depois da categoria**, antes do texto (quem marca Reunião já vê a
    pergunta). Não marquei sozinho ao escolher Reunião: aviso de reunião que já aconteceu (resumo,
    ata) não é evento.
13. **Enter no fim de um item continua a lista** (e a numerada, e o destaque); Enter num item vazio
    encerra. Shift+Enter é a quebra normal.
14. **Caracteres invisíveis**: título e local recusam os de direção e de largura zero (o ZWJ dos
    emojis vale); o texto recusa só os de direção (texto colado do WhatsApp às vezes traz U+200B).
15. **Ícones novos no `Icone.tsx`** no mesmo traço (2 px): geral (balão), obra, reunião,
    financeiro, calendário, local, e os da barra. Urgente usa o `alerta` que já existia.
16. **Histórico (`aviso_publicado`/`aviso_corrigido`) não guarda categoria nem evento**: os
    detalhes continuam os do M1 (a versão no banco já guarda tudo).
17. **Tokens `--cat-*`**: obra é terra `#9c4517` (o `#b4541f` do mockup dava 4,1:1 no fundo
    suave), reunião `#2f5d9e`, financeiro = mata, urgente = erro, geral = tinta-suave. O axe deu 0
    violações de contraste nas 54 telas conferidas (claro e escuro).

## Achados da revisão independente

### UX (persona Dona Socorro)

Corrigidos (com teste de regressão): 1 (ano do evento), 3 (Enter na lista), 5 (dois "Título"),
6 (erro some ao corrigir; caixa diz quantos erros), 7 ("É um evento?" sobe), 8 (ajuda cita a
numerada), 10 (ícone de Geral), 11 (✓ na categoria escolhida), 12 (verificação em pt-BR; ver
abaixo).

Descartados ou para o Erick:
- **2. O bloco de data é da publicação, e parece a data do evento.** Levado ao Erick (dúvida A),
  que decidiu: com evento, o bloco é o dia do evento. Implementado com teste.
- **4. "Ver como fica" e "Ver prévia" no mesmo formulário.** Nomes da spec e do M1; os dois
  fazem coisas diferentes (texto × aviso inteiro). Fica como está até o ensaio com vizinhos.
- **9. Negrito sem seleção insere "negrito" selecionado.** É de propósito: a palavra fica
  selecionada, e o que a pessoa digitar substitui. Inserir `****` vazio é pior (asteriscos soltos
  que não viram nada).

### Código e segurança

Corrigidos (com teste de regressão): 1 (ano fora da faixa derrubava o mural: API + CHECK +
campo), 2 (correção sem categoria/evento apagava os dois), 3 (resumo quadrático: corta em 2.000
antes de tirar marcas), 4 (negrito em várias linhas), 5 (dígitos só 0-9 e U+2028/U+2029 como
quebra, iguais na API e na tela), 6 (caracteres de direção e largura zero), 7 (Enter depois do
999).

Descartados:
- **4, segunda parte (negrito com a seleção dentro de um `**…**`).** Gera marcas a mais, mas a
  prévia mostra na hora e o "Ver como fica" deixa ver; desfazer é Ctrl+Z ou apagar. Custo de
  detectar pares parciais não compensa agora.
- **Vitest instável sob carga** (2 testes falharam uma vez com o pytest rodando junto). Não se
  repetiu em 6 rodadas minhas (269 verdes); registrado para observar.

## Dúvidas para o Erick

- **A. Data em bloco no aviso que é evento. DECIDIDA PELO ERICK (06/10):** quando o aviso é um
  evento, o bloco (no mural e no aviso aberto) mostra o dia do evento, com o ano se não for o
  corrente; a linha do cartão vira "Sáb, 9h · publicado 6/10" (ou "Já aconteceu · publicado
  6/10"); o leitor de tela ouve "Evento em …" ou "Publicado em …". A frase "Publicado pela … em …"
  do aviso aberto e o quadro Quando/Onde não mudam; a ordem do mural continua pela publicação.
  Spec §3.4 atualizada.
- **B. Dia e hora no Chrome headless saíram no formato dos EUA** (mm/dd/aaaa, AM) mesmo com
  `--lang=pt-BR` e `locale: 'pt-BR'`: o headless ignora o idioma nos campos `date`/`time`. Num
  celular em português aparecem dd/mm/aaaa e 24 h. Vale olhar num Android de verdade no ensaio.
- **C. Produção:** a 0004 tem de ir ao Neon (conexão direta do `dono`) **antes** do push (spec
  3.2), e o aviso de boas-vindas reescrito no formato novo depende do texto aprovado por você.
  Nada disso foi feito aqui.

## Fica de fora (spec 4)

`.ics` para a agenda, filtro do mural por categoria, imagens no texto, itálico, tabela e título de
nível 3.
