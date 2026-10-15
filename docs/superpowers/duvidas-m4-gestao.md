# Dúvidas e decisões do M4 · Épico A (criar e gerir enquetes)

Decisões tomadas sem perguntar a ninguém durante o épico A do M4 (H-20, com o aviso automático
do H-13). Mesmo formato de `duvidas-m4.md`: a dúvida, o que foi decidido e por quê. **[Erick]**
marca o que só o Erick pode confirmar; o resto é decisão técnica que pode ser revista na revisão
do marco. **[Coordenador]** marca o que precisa de um arquivo comum.

## 1. O teste comum `m4contrato.test.ts` exige as rotas do épico A vazias · [Coordenador]
- **Dúvida:** `web/src/m4contrato.test.ts` ("encaixes do M4 ainda não mostram nada → rotas
  vazias e sem item no menu") confere `expect(rotasGestaoEnquetes).toEqual([])`. É o mesmo papel
  do `test_m4_em_construcao.py` da API, mas o contrato (seção 5) só deixa o épico apagar a seção
  dele no arquivo da API; o do front é comum.
- **Decisão:** não mexi no arquivo comum. Com o épico pronto, **esse teste falha** (é a única
  falha da suíte do front nesta branch). O conserto, no fechamento: apagar a linha
  `expect(rotasGestaoEnquetes).toEqual([])` (e o `importActual` de `./enquetes/gestao/rotas`
  logo acima). O épico B vai bater no mesmo teste com `rotasVotar` e `itemEnquetes`.
- **Por quê:** a regra da onda é "comum, nenhum épico edita; se precisar, registra e contorna".
  Aqui não há contorno: o teste confere justamente que a tela não existe.

## 2. A tela de editar depende do `GET /api/enquetes/{id}` do épico B
- **Dúvida:** "Editar" precisa carregar a enquete gravada (pergunta, opções, término…). A única
  rota que devolve isso é `GET /api/enquetes/{id}`, do épico B; o contrato não tem rota de
  leitura no épico A (e `test_m4_rotas.py` confere a lista exata de rotas).
- **Decisão:** a tela usa `abrirEnquete` (de `enquetes/api.ts`, comum) e o `pode_editar` da
  `Enquete`. Até o épico B entrar, `/enquetes/{id}/editar` mostra a frase do 501 ("Esta parte do
  Portal ainda está sendo feita.") com "Tentar de novo". Os testes do front usam a resposta de
  mentira com o formato do contrato.
- **Por quê:** criar uma rota de leitura só para editar duplicaria a montagem da `Enquete` e
  mudaria um teste comum. Depois de publicar ou salvar, a tela vai para `/enquetes/{id}` (B),
  como o contrato manda (dúvida 10 do contrato).

## 3. O texto do aviso automático · [Erick]
- **Dúvida:** o contrato diz só "o texto diz até quando vai e que é consulta sem valor legal".
- **Decisão:** o aviso traz a pergunta, **a lista das opções**, até quando dá para votar (dia e
  hora de Recife), se é para marcar uma ou mais de uma, "Vale um voto por apartamento, e dá para
  trocar o voto até o fim", quando o resultado aparece, o destaque "Enquete é consulta. Não tem
  valor legal de votação em assembleia." e que o botão "Ir para a enquete" leva a ela. Texto
  exato no spec do épico, seção 1.2; a tela mostra a prévia com a mesma frase.
- **Por quê:** o aviso também vai por e-mail; quem lê lá entende a enquete inteira sem abrir o
  Portal, e a frase do RN-03 fica registrada no mural junto com a enquete.
- **Confirmar:** se a Comissão quer um texto mais curto (sem as opções, por exemplo).

## 4. Aviso automático arquivado: a enquete edita, o aviso não é corrigido
- **Dúvida:** se a gestão arquivou o aviso automático e depois edita a enquete (ainda sem voto),
  `gravar_correcao` recusa ("Aviso arquivado não pode ser corrigido.") e a edição inteira cairia.
- **Decisão:** edita a enquete e deixa o aviso arquivado como estava.
- **Por quê:** arquivar foi uma decisão da gestão (tirar do mural), e não há como desarquivar;
  recusar a edição prenderia a enquete com um erro de digitação para sempre. O aviso aberto
  continua mostrando a pergunta atual no botão (`enquete` do aviso é lido na hora).

## 5. A edição reescreve o texto do aviso, e a tela avisa
- **Dúvida:** se alguém corrigiu o aviso automático à mão (acrescentou uma linha), editar a
  enquete apaga essa linha?
- **Decisão (do coordenador, depois da revisão independente, ponto 3):** sim. A enquete é a
  fonte da verdade: a correção do aviso usa o texto gerado de novo (título e texto); categoria,
  evento e anexos ficam, e o texto manual continua nas versões anteriores do aviso. A tela de
  editar diz isso numa linha fixa, logo acima de "Salvar alterações": "Salvar reescreve o texto
  do aviso desta enquete."
- **Por quê:** o aviso precisa dizer a pergunta, as opções e o prazo novos, e juntar texto à mão
  com texto gerado não tem regra boa. Nada se perde (RN-05), e quem edita fica sabendo antes.

## 6. Mudança que não muda o aviso não gera versão nova dele
- **Dúvida:** `gravar_correcao` recusa com `sem_mudanca` quando título e texto ficam iguais. Isso
  acontece quando só os segundos do término mudam (o texto mostra até o minuto).
- **Decisão:** a edição confere antes e só corrige o aviso se o título ou o texto mudarem; a
  enquete é editada mesmo assim. Nada mudou na enquete inteira: 409 `sem_mudanca` "Nada mudou na
  enquete." (o término comparado como instante; opções com espaço sobrando contam como iguais,
  porque a API já tira os espaços).

## 7. Quando as opções são recriadas (ids novos)
- **Dúvida:** editar é "apagar e inserir de novo" as opções (contrato). E quando só a pergunta
  muda, ou só o tipo de escolha?
- **Decisão (revista depois da revisão independente, ponto 1):**
  - **A pergunta mudou:** recria **todas** as opções, com ids novos, mesmo que os textos sejam
    os mesmos. Um voto mandado de uma tela aberta antes (com os ids velhos) é recusado pelo
    banco (a opção não é mais da enquete) e não cai numa pergunta que o morador nunca viu
    ("Aprovar R$ 1.000?" virando "Aprovar R$ 10.000?" com o mesmo "Sim").
  - **Só as opções mudaram:** apaga e insere de novo, como antes.
  - **Pergunta e opções iguais** (mudou o término ou quando mostrar): as opções ficam, com os
    mesmos ids.
  - **O tipo de escolha mudou** (ajustes do M4, ponto 1): recria também. Com os mesmos ids, a
    tela aberta da múltipla que virou única mandava duas opções e recebia 422, sem saber que a
    enquete mudou; com ids novos, recebe 409 `enquete_mudou` e recarrega.
  - Em todos os casos a enquete recebe o `UPDATE`, para o banco carimbar `editada_em` e conferir
    de novo voto e prazo.
- **Por quê:** a primeira versão só recriava se o texto das opções mudasse, e a revisão mostrou
  o voto da tela velha valendo para a pergunta nova.

## 8. Editar trava a enquete e espera o voto em andamento
- **Dúvida:** foco de revisão 2 do contrato, agora pela API.
- **Decisão:** a edição faz `select … for update` na enquete antes de tudo: se um voto está
  gravando, espera; depois vê `primeiro_voto_em` preenchido e responde 409 `enquete_com_voto`.
  Teste com duas conexões de verdade (`test_editar_espera_o_voto_em_andamento_e_e_recusada`).

## 9. Duas pessoas da gestão editando ao mesmo tempo: a segunda recebe 409
- **Dúvida:** o aviso tem `versao_base` para não sobrescrever a correção de outra pessoa; a
  `EditarEnquete` do contrato não tinha campo parecido, e a primeira versão deixava valer a
  última edição (a revisão independente mostrou a segunda apagando as opções que a primeira
  tinha acrescentado, ponto 2).
- **Decisão (do coordenador):** `EditarEnquete` ganhou `editada_em_base: datetime | None`,
  **obrigatório** no corpo (`null` = a enquete nunca foi editada). A tela manda o `editada_em` da
  `Enquete` que carregou. Se não bate com o `editada_em` da linha travada, 409 `enquete_mudou`:
  "Outra pessoa editou esta enquete agora há pouco. Abra de novo para ver a versão nova antes de
  mudar." A tela mostra a frase e o botão "Abrir a versão nova", que carrega a enquete de novo e
  recomeça o formulário com ela.
- **Arquivo comum:** `api/app/esquemas/enquetes.py` e `web/src/enquetes/tipos.ts`, com o ok do
  coordenador. Para a `NovaEnquete` não herdar a `editada_em_base`, as duas classes (e as duas
  interfaces) foram escritas por inteiro; a `NovaEnquete` ficou com os mesmos campos de antes.

## 10. Término em dia e hora separados, hora padrão 20:00 · [Erick]
- **Dúvida:** o protótipo usa um campo só (`datetime-local`).
- **Decisão:** dois campos, "Dia do término" e "Hora do término" (como o evento do aviso), com a
  hora já em 20:00 e o dia em branco; sempre no horário de Recife (UTC-3, como a API).
- **Por quê:** o `datetime-local` é confuso no celular de quem tem mais idade (um seletor só
  para duas coisas) e muda de cara em cada navegador. 20:00 é o horário que a Comissão costuma
  usar para "até quinta à noite"; o dia em branco obriga a pensar no prazo.
- **Confirmar:** se 20:00 é um bom padrão.

## 11. Editar perto do fim do prazo
- **Dúvida:** o esquema pedia o término a pelo menos 1 hora de agora também na edição. Quem
  abria "Editar" a 40 minutos do fim, sem mexer no término, recebia "Escolha um término daqui a
  pelo menos 1 hora." e só conseguia corrigir a pergunta adiando o prazo (revisão independente,
  ponto 4).
- **Decisão (do coordenador):** na edição, "pelo menos 1 hora" só vale **se o término mudou**
  (comparado como instante). Término igual passa, desde que a enquete ainda esteja aberta (o
  serviço confere `encerra_em` pelo relógio do banco, e o banco confere de novo). Na criação,
  continua valendo sempre. Na API: `EditarEnquete.encerra_em` só confere fuso, futuro e 1 ano; o
  serviço confere a 1 hora quando mudou (422 no campo `encerra_em`). No front: `conferir` recebe
  o dia e a hora gravados e não confere o término se forem os mesmos.

## 12. A pergunta é uma caixa de 2 linhas, sem Enter
- **Dúvida:** o protótipo usa um campo de uma linha; com 200 letras, a pergunta some no celular.
- **Decisão:** caixa de 2 linhas; Enter não quebra a linha e quebras coladas viram espaço.
- **Por quê:** quem escreve precisa ler a pergunta inteira antes de publicar, e a pergunta é uma
  frase só.

## 13. "Tirar" opção e o limite de 10 na tela
- **Dúvida:** o protótipo só tem "Adicionar opção".
- **Decisão:** a partir da 3ª caixa, cada uma tem "Tirar"; "Adicionar opção" some na 10ª, com "O
  limite é de 10 opções." no lugar da ajuda. A marca de cada opção (bolinha ou quadradinho)
  acompanha o "Pode marcar mais de uma opção", para quem cria ver a cédula como o morador vai ver.

## 14. Peças comuns usadas sem editar
- `avisos/api.ts` (`listarDestinos`, `calcularAlcance`) para os botões de destino e o "vai para
  N apartamentos"; `avisos/componentes.tsx` (`TextoDoAviso`, `Carregando`, `FalhaAoCarregar`) e
  `avisos/avisos.css` para a prévia; `documentos/carregar.ts` (`useCarga`, `comoErroDaApi`);
  `servicos/email.FUSO_DE_RECIFE` na API. O aviso de "Sair sem publicar?" foi refeito no épico
  (`gestao/SairSemSalvar.tsx`), porque o do aviso fala em anexos.

## 15. Unicode: NFC, texto sem letra, contagem por letra (revisão independente, pontos 6 a 8)
- **Dúvida:** "Café" (é pronto) e "Café" (e + acento solto) apareciam iguais na tela e passavam
  como opções diferentes; uma opção só de acentos soltos (ou só "?!") não aparece; o front
  contava o emoji como 2 letras (UTF-16) e cortava o título do aviso no meio dele; o
  `toLowerCase` do front não é o `casefold` da API ("Straße" × "STRASSE").
- **Decisão:**
  - API e front normalizam para **NFC** antes de comparar, contar e gravar (pergunta e opções).
  - Pergunta ou opção **sem nenhuma letra ou número** é recusada: "Escreva a pergunta com letras
    ou números." / "Cada opção precisa ter letras ou números." (categorias Unicode L e N; no
    front, `/[\p{L}\p{N}]/u`).
  - O front conta e corta **por code point** (`Array.from`), como o `len` do Python, no título
    do aviso e nos limites de 200 (pergunta) e 100 (opção). Os campos perderam o `maxLength` do
    HTML, que conta diferente (um emoji valeria 2); a conferência da tela avisa no lugar.
  - A comparação do front é NFC + `toLocaleLowerCase('pt-BR')` + "ß" → "ss" + espaços juntados.
    **Diferença que sobra:** o `casefold` também dobra letras raras (ligaduras como "ﬁ", o "ς"
    final do grego e outras); nesses casos a tela deixa passar e a API recusa com "Duas opções
    estão iguais.", que a tela mostra no campo. A API é a palavra final.

## 16. Editar exige todos os campos; criar mantém os padrões (revisão independente, ponto 9)
- **Dúvida:** com `multipla_escolha` e `mostrar_resultado` com padrão também na edição, um corpo
  sem eles voltava a enquete para "escolha única" e "durante" em silêncio.
- **Decisão:** em `EditarEnquete`, os dois são **obrigatórios**, sem padrão (422 se faltarem).
  Em `NovaEnquete`, os padrões ficam (`false` e `durante`, como no contrato): na criação não há
  valor anterior para apagar sem querer, e o formulário manda os dois de qualquer jeito.

## 17. Testes comuns ajustados por causa da revisão · [Coordenador]
- **Dúvida:** os pontos 2 e 9 deixam `editada_em_base`, `multipla_escolha` e `mostrar_resultado`
  obrigatórios na edição, e dois testes comuns montavam o corpo de editar sem eles (um deles
  quebrava o `tsc` e, com ele, o pre-commit).
- **Decisão:** edição mínima, só acrescentando os campos novos ao corpo de editar:
  `api/testes/test_m4_esquemas.py` (`test_editar_nao_tem_destino`) e `web/src/m4contrato.test.ts`
  (`criar é POST e editar é PUT`). Nada mais nesses arquivos. O item 1 (o teste das rotas
  vazias) continua como estava.
- **Também comuns, com o ok do coordenador:** `_FIM_DE_FRASE` em `api/app/servicos/email.py` e o
  espelho `FIM_DE_FRASE` em `web/src/avisos/formatos.ts` ganharam `”’»` (ponto 5: o link da
  pergunta entre aspas curvas levava o `”` junto). Testes dos dois lados nos arquivos do épico
  (`test_enquetes_gestao_revisao.py`, `gestao/links.test.ts`).

## 18. "Quando mostrar o resultado" explica a lista de quem votou · [Erick]
- **Dúvida:** a revisão do épico B mostrou que, no "durante", a gestão deduzia em quê cada
  apartamento votou cruzando a contagem ao vivo com a lista "Quais apartamentos votaram".
- **Decisão (do coordenador, vinda da revisão do épico B):** no "durante", enquanto a enquete
  está aberta, a lista de quem votou não aparece (só quando termina); no "só no fim", aparece o
  tempo todo. O formulário (nova e editar) explica isso junto de cada escolha:
  - **Durante a votação:** "Todos veem a contagem enquanto votam. A lista de quais apartamentos
    votaram só aparece quando a enquete terminar."
  - **Só quando terminar:** "Ninguém vê a contagem antes do fim, nem a Comissão. Enquanto isso, a
    Comissão acompanha quais apartamentos ainda faltam votar."
- O texto do aviso automático continua coerente ("O resultado aparece durante a votação." / "O
  resultado só aparece quando a enquete terminar."): ele fala do resultado, não da lista, que é
  só da gestão. Não mudou.
- **Confirmar:** se a Comissão aceita não ver quem votou no "durante" até o fim (para cobrar
  participação, a escolha é o "só no fim").

## 19. Ajustes das revisões finais do M4
- **Data do aviso automático por extenso** ("Dá para votar até 16 de outubro, às 20h (horário de
  Recife)."; com minutos, "às 19h30"; em outro ano, com o ano), igual à tela da enquete. API:
  `quando_em_texto` (o ano de referência é o de quando o aviso é gerado); prévia do formulário:
  `textoDoAviso(rascunho, agora)` usa o `quandoTermina` do épico B. Teste dos dois lados.
- **Id do endereço:** `/enquetes/0/editar` e companhia vão para "Enquete não encontrada" sem
  chamar a API (o `useIdDaEnquete` do épico B); 404 e 422 da API também.
- **Erro geral** guarda os campos que o causaram e some quando todos forem corrigidos; o da API
  sem campo (ex.: `tente_de_novo`) continua até o próximo envio.
- **Espaço entre o dia e a hora** no celular (`gap` de 18 px entre as linhas) e antes de "Quando
  mostrar o resultado".
- **Não mudou (decisões):** "Corrigido" no aviso de uma enquete editada antes do 1º voto (regra
  de transparência dos avisos); encerrar/cancelar (dúvida [Erick] do contrato, item 9);
  `navigate replace` depois de salvar.
