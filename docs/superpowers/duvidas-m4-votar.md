# Dúvidas e decisões do M4 · Épico B · Votar e resultado

Decisões tomadas sem perguntar a ninguém durante o épico B (H-21, H-22). Cada item: a dúvida, o
que foi decidido e por quê. **[Erick]** marca o que só o Erick pode confirmar; o resto é decisão
técnica ou de tela que pode ser revista na revisão do marco. Spec: `specs/m4-votar.md`.

## 1. Dois testes comuns do front foram ajustados (fora da lista do épico)
- **Dúvida:** `web/src/m4contrato.test.ts` exigia os encaixes do B vazios ("ainda não mostram
  nada") e `web/src/m3contrato.test.ts` exigia o menu sem "Enquetes". Com o épico pronto, os dois
  ficam vermelhos, e nenhum deles está na lista de arquivos do B.
- **Decisão:** como fez o épico A do M3 (dúvidas dele, item 8): no `m4contrato.test.ts`, o bloco
  "ainda não mostram nada" ficou só com a parte do épico A (rotas de gestão vazias, num `it`
  próprio, para o A apagar sem conflito) e a parte do B virou "encaixes do épico B mostram o que
  devem". No `m3contrato.test.ts`, só a ordem esperada do menu: "Avisos, Enquetes, Documentos,
  Minha unidade" (a ordem que o contrato do M4 definiu). Nada mais nos comuns.
- **Por quê:** é o equivalente no front de apagar a seção do épico em `test_m4_em_construcao.py`.
  **Para o coordenador:** no merge com o A, o `m4contrato.test.ts` deve ficar sem o bloco "ainda
  não mostram nada" (o A apaga o `it` dele).

## 2. Porcentagem de cada opção: sobre os apartamentos que votaram · [Erick]
- **Dúvida:** "88 votos, 46%" é 46% de quê? O protótipo dividia pela soma dos votos.
- **Decisão:** pelos apartamentos que votaram (`participacao.votaram`). Na escolha única dá o
  mesmo que a soma dos votos; na múltipla, cada opção diz "quantos apartamentos querem isto"
  (a soma passa de 100%). A participação continua sendo sobre o destino inteiro.
- **Por quê:** na múltipla, dividir pela soma dos votos esconde a força de cada opção ("Prazo de
  entrega" marcado por 80% dos apartamentos viraria 35%).
- **Confirmar:** se a Comissão espera as porcentagens somando 100 também na múltipla.

## 3. "Durante": quem ainda não votou já vê o parcial · [Erick]
- **Dúvida:** no "durante", mostrar o parcial antes de a unidade votar pode influenciar o voto.
- **Decisão:** mostra (como o protótipo e o contrato: `votos` só é nulo no "só no fim").
- **Por quê:** quem não quer influência escolhe "só no fim" no formulário (RF-23). Esconder até a
  unidade votar seria uma terceira regra, que a Comissão não escolheu.
- **Confirmar:** se "durante" deveria esconder o parcial de quem ainda não votou.

## 4. O próprio voto aparece mesmo no "só no fim"
- **Dúvida:** no "só no fim", a unidade vê o que ela mesma marcou?
- **Decisão:** sim: `meu_voto` vem sempre, a confirmação diz em que o apartamento votou, e no
  resultado aberto a opção ganha "seu voto". Só os números dos outros ficam escondidos.
- **Por quê:** é o dado da própria unidade (H-21: "vê o voto da unidade e pode trocá-lo"); sem
  isso, o outro celular da mesma casa não sabe o que foi votado.

## 5. Ordem das conferências do voto na API
- **Decisão:** 404 (não vê) → 409 `enquete_encerrada` → 403 `fora_do_destino` → 409
  `enquete_mudou` (opção que não é desta enquete agora) → 422 "Nesta enquete, escolha só uma
  opção." → grava. O banco confere tudo de novo e as recusas dele passam por
  `enquetes_banco.traduzir` (nunca 500 numa regra conhecida).
- **Por quê:** a mensagem mais útil primeiro: de nada adianta dizer "escolha só uma" numa
  enquete que já terminou ou cujas opções mudaram.

## 6. Botão parado diz por quê
- **Dúvida:** o botão "Votar" sem escolha (ou "Trocar voto" com a mesma escolha de antes) fica
  desativado; a Dona Socorro toca e nada acontece.
- **Decisão:** abaixo dele, uma linha diz o que falta: "Escolha uma opção para votar.", "Marque
  pelo menos uma opção para votar." ou "Para trocar o voto, escolha outra opção.". Enquanto
  grava: "Gravando o voto…".
- **Por quê:** voto difícil de errar: não dá para mandar vazio nem "trocar" para a mesma coisa,
  e a tela explica.

## 7. Confirmação no lugar, sem `role="status"`
- **Decisão:** a confirmação ("Voto registrado. Seu apartamento já votou em …. Se escolher
  outra, vale a nova.") fica em cima das opções, como no protótipo, numa região "Seu voto" que
  recebe o foco depois de votar.
- **Por quê:** a casca já tem a região de status (o recado); duas regiões vivas se atropelam no
  leitor de tela. O foco na confirmação faz o leitor ler o que mudou.

## 8. Quando o voto falha, a escolha fica
- **Decisão:** o erro aparece acima do botão (`role="alert"`) e a escolha continua marcada. Em
  `enquete_mudou`, `enquete_encerrada` e `voto_mudou_agora`, a enquete é recarregada (a tela
  mostra as opções, o prazo ou o voto de agora) e a mensagem continua; em `enquete_mudou` a
  escolha é limpa (as opções de antes podem não existir mais).

## 9. Selo, "já votou" e destino na lista
- **Decisão:** o selo "Seu apartamento ainda não votou" só aparece na aberta **e** se o bloco da
  unidade está no destino (a gestão de outro bloco não vota, então não "falta"). Na aberta já
  votada, "Seu apartamento já votou" (o protótipo não tinha; ajuda a conferir sem abrir). Para a
  gestão, as enquetes só de alguns blocos dizem "Para o Bloco X". Terminadas não têm selo.
- **Por quê:** o selo é um pedido de ação; só faz sentido para quem pode agir.

## 10. Terminada: a mais votada em ipê
- **Decisão:** na enquete terminada, a barra da opção mais votada fica na cor ipê (empate: todas
  as empatadas); aberta, todas em verde-mata. "Seu apartamento votou em …" aparece em cima.
- **Por quê:** a pergunta de quem abre uma terminada é "o que ficou decidido?"; a cor responde
  sem precisar comparar números. Enquanto aberta, destacar a primeira colocada seria empurrar
  voto.

## 11. "Quais apartamentos votaram"
- **Decisão:** número em cima ("69 de 320 apartamentos votaram (22%)."), "Copiar a lista de quem
  falta" (texto para o grupo, como o "Quem leu" do aviso: primeiro quem entrou e não votou,
  depois quem nem entrou) e três grupos por bloco: "Votaram", "Entrou, mas não votou", "Ainda não
  entrou no Portal". O administrador toca no apartamento e vai para a unidade (como no "Quem
  leu"). Nunca em quê: a API nem manda.
- **Por quê:** o uso é cobrar participação no grupo; a lista copiável é o que a Comissão cola.

## 12. "Para a Comissão" também para o administrador · [Erick]
- **Decisão:** a seção da gestão na enquete se chama "Para a Comissão" (como no protótipo),
  mesmo quando quem vê é o administrador ou o síndico. O aviso aberto usa "Para a gestão".
- **Confirmar:** se prefere "Para a gestão" também aqui (é uma palavra).

## 13. Mensagem do 404
- **Decisão:** "Não achamos esta enquete. O link pode estar incompleto, ou ela é de outro
  bloco." para a inexistente e para a de outro bloco (a mesma resposta, H-21). O
  `enquetes_banco` comum tem uma mais curta ("Enquete não encontrada."), que só aparece se o banco
  recusar uma enquete apagada no meio do voto (não acontece: o `app` não apaga enquete).

## 14. Teste de dois celulares pela API
- **Como:** duas sessões da mesma unidade (dois `TestClient`), uma barreira, e a primeira a
  gravar demora 0,4 s entre o voto e as opções (`_trocar_opcoes` trocado no teste), para a
  segunda chegar no meio. Três rodadas na múltipla escolha e uma na única: as duas respostas são
  200, fica um voto só, com as opções inteiras de um dos dois.
- **Conferido por mutação:** com o `delete` das opções antes do `insert … on conflict` (fora da
  ordem do contrato), o teste falha (`voto_mudou_agora` numa das duas).

## 15. Conferência visual
- **Como:** banco `portal_dev_m4_votar` no container do épico, carga + dados fictícios, quatro
  enquetes fictícias (aberta com votos, "só no fim" múltipla, só do Bloco 2, terminada), API na
  8162, Vite na 5192, Chrome headless próprio (puppeteer-core, não o MCP). 390 px e 1280 px,
  morador e gestão, claro e escuro. Prints em `docs/superpowers/prints/m4-votar/`.
- **Corrigido pelo que se viu:** "seu voto" quebrando em duas linhas e colando no texto da
  opção; link da pergunta em azul padrão na tela de votantes; botão desativado sem explicação
  (item 6).
