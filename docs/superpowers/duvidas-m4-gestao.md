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

## 5. A edição sobrescreve o texto do aviso
- **Dúvida:** se alguém corrigiu o aviso automático à mão (acrescentou uma linha), editar a
  enquete apaga essa linha?
- **Decisão:** sim: a correção do aviso usa o texto gerado de novo (título e texto); categoria,
  evento e anexos que a pessoa pôs ficam. A versão anterior continua em "versões anteriores".
- **Por quê:** o aviso precisa dizer a pergunta, as opções e o prazo novos, e juntar texto à mão
  com texto gerado não tem regra boa. Nada se perde (RN-05).

## 6. Mudança que não muda o aviso não gera versão nova dele
- **Dúvida:** `gravar_correcao` recusa com `sem_mudanca` quando título e texto ficam iguais. Isso
  acontece quando só os segundos do término mudam (o texto mostra até o minuto).
- **Decisão:** a edição confere antes e só corrige o aviso se o título ou o texto mudarem; a
  enquete é editada mesmo assim. Nada mudou na enquete inteira: 409 `sem_mudanca` "Nada mudou na
  enquete." (o término comparado como instante; opções com espaço sobrando contam como iguais,
  porque a API já tira os espaços).

## 7. Opções iguais mantêm os ids
- **Dúvida:** editar é "apagar e inserir de novo" as opções (contrato). E quando a pessoa só
  mudou a pergunta?
- **Decisão:** só apaga e insere se a lista de opções (textos, na ordem) mudou. Mas a enquete
  sempre recebe o `UPDATE` (mesmo quando só as opções mudam), para o banco carimbar `editada_em`
  e conferir de novo voto e prazo.
- **Por quê:** com os mesmos ids, a tela de quem está prestes a votar (B) não recebe
  `enquete_mudou` à toa.

## 8. Editar trava a enquete e espera o voto em andamento
- **Dúvida:** foco de revisão 2 do contrato, agora pela API.
- **Decisão:** a edição faz `select … for update` na enquete antes de tudo: se um voto está
  gravando, espera; depois vê `primeiro_voto_em` preenchido e responde 409 `enquete_com_voto`.
  Teste com duas conexões de verdade (`test_editar_espera_o_voto_em_andamento_e_e_recusada`).

## 9. Duas pessoas da gestão editando ao mesmo tempo: vale a última
- **Dúvida:** o aviso tem `versao_base` para não sobrescrever a correção de outra pessoa; a
  `EditarEnquete` do contrato não tem campo parecido.
- **Decisão:** vale a última edição (a trava põe as duas em fila; a segunda grava por cima).
- **Por quê:** a enquete só é editável antes do 1º voto, em geral minutos depois de criada, e
  pela mesma pessoa. Um campo novo mudaria o esquema comum. Se virar problema, o caminho é um
  `editada_em_base` no corpo, como o `versao_base` do aviso.

## 10. Término em dia e hora separados, hora padrão 20:00 · [Erick]
- **Dúvida:** o protótipo usa um campo só (`datetime-local`).
- **Decisão:** dois campos, "Dia do término" e "Hora do término" (como o evento do aviso), com a
  hora já em 20:00 e o dia em branco; sempre no horário de Recife (UTC-3, como a API).
- **Por quê:** o `datetime-local` é confuso no celular de quem tem mais idade (um seletor só
  para duas coisas) e muda de cara em cada navegador. 20:00 é o horário que a Comissão costuma
  usar para "até quinta à noite"; o dia em branco obriga a pensar no prazo.
- **Confirmar:** se 20:00 é um bom padrão.

## 11. Editar dentro da última hora antes do término
- **Dúvida:** o esquema comum pede o término a pelo menos 1 hora de agora. Quem abre "Editar" a
  40 minutos do fim, sem mexer no término, recebe "Escolha um término daqui a pelo menos 1 hora."
- **Decisão:** fica assim (é o esquema comum, e o caso é raro: editar uma enquete sem voto
  nenhum a menos de 1 hora do fim).

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
