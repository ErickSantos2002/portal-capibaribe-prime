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

## Revisão independente (pontos 1 a 7)

Cada ponto ganhou um teste de regressão que falhava antes da correção (API em
`test_enquetes_resultado.py` e `test_enquetes_voto.py`, seção "revisão do épico B"; front em
`votar/votar.test.tsx`, bloco "revisão do épico B").

### 16. No "durante", a lista de quem votou só sai no fim · [Erick]
- **O que a revisão provou:** no "durante", a gestão vê a contagem por opção ao vivo **e** a lista
  de quem votou. Basta olhar as duas antes e depois de um apartamento votar: o apartamento que
  entrou na lista é o mesmo voto que subiu numa opção. Com a enquete parada (pouca gente votando
  por vez, o normal num condomínio), isso diz em quê cada apartamento votou, o que o Portal
  promete não dizer ("quais votaram, nunca em quê", H-22).
- **Decisão (do coordenador, a confirmar com o Erick):** no "durante", enquanto aberta,
  `GET …/votantes` responde 409 `votantes_so_no_fim`, com a explicação e a saída ("crie a
  enquete com o resultado só no fim"). No "só no fim" (aberta ou terminada) e no "durante"
  terminado, a lista continua: no primeiro não há contagem para cruzar; no segundo, ninguém
  vota mais, e a contagem final não diz a ordem. Na tela, o cartão "Quais apartamentos votaram"
  dá lugar à mesma explicação; o link antigo da lista também a mostra (sem "Tentar de novo").
- **Confirmar:** se a Comissão aceita não cobrar participação nominal nas enquetes "durante"
  (o número de quem votou continua aparecendo sempre).
- **Recado ao coordenador (épico A):** o formulário "Nova enquete" deveria dizer isso na escolha
  "durante" (ex.: "Com o resultado durante a votação, a lista de quem votou só aparece no fim.").
  É arquivo do épico A; não editei.

### 17. Participação: a base é "ativas do destino ou que votaram"
- **O que a revisão provou:** `votaram` contava todo voto e `total` só as ativas; unidade que
  votou e foi desativada dava mais de 100% ou "1 de 1" (o admin, que não votou, sozinho na base).
- **Decisão:** as duas contas usam a mesma base: as unidades do destino que estão ativas agora
  **ou** que votaram nesta enquete. Quem votou e saiu continua contando no "votaram" e no total;
  quem saiu sem votar sai das duas. Assim `votaram <= total` sempre, os votos por opção de uma
  enquete terminada não mudam (RF-25; dúvida 13 do contrato) e a lista de votantes usa a mesma
  base: os três grupos somam o total, e quem votou e foi desativado aparece em "Votaram".
- **Por quê, e não "só ativas" como a revisão sugeriu:** com "só ativas" no `votaram`, o voto de
  quem saiu continuaria nas barras (o resultado não muda) mas não no "N de M votaram", e as
  porcentagens das opções (sobre quem votou, item 2) poderiam passar de 100%.

### 18. Banco recusa voto de unidade desativada (migração 0009)
- **Decisão:** a 0009 troca só a função `voto_conferir`: votar ou trocar o voto de unidade com
  `ativa = false` é recusado com a regra própria `voto_de_unidade_inativa`, que o
  `enquetes_banco` traduz para 403 `unidade_inativa` ("Este apartamento foi desativado no Portal
  e não vota mais. Fale com a administração."). A primeira versão reaproveitava
  `voto_fora_do_destino`, e a frase falava do bloco errado (revisão de integração; corrigido nos
  ajustes, item 25, com a 0009 ainda fora de produção). Unidade que não existe continua com a
  chave estrangeira. O downgrade devolve a função da 0008. Nenhuma tabela nova: as verificações
  do backup não mudam.
- **Aplicar:** `cd api && uv run --env-file .env alembic upgrade head` (a partir da 0008).

### 19. Troca que falha não diz "Voto registrado." e o foco fica no erro
- **Decisão:** enviar apaga o "Voto registrado." de antes; o erro recebe o foco (e o mantém
  quando a enquete recarrega depois de `enquete_mudou`). A confirmação só recebe o foco depois de
  um voto que deu certo.

### 20. Voto trocado em outro celular, com a tela parada
- **Decisão:** a enquete é buscada de novo quando a página volta a ficar visível
  (`visibilitychange`). Se o voto gravado mudou e não foi por esta tela, a escolha acompanha o
  voto de agora (o botão não fica "Trocar voto" para o que já está gravado) e aparece "O voto do
  seu apartamento foi trocado em outro aparelho.". Some quando a pessoa marca outra opção.

### 21. Id inválido no endereço
- **Decisão:** `/^[1-9]\d{0,14}$/`; `/enquetes/0`, `00`, 16 dígitos ou letras vão direto para
  "Enquete não encontrada", sem chamar a API. Se a API responder 422 a um id, a tela é a mesma.

### 22. Id da opção é inteiro estrito
- **Decisão:** `Votar.opcoes` é `list[Annotated[IdBanco, Strict()]]`: `true`, `"1"` e `1.0` dão
  422. Mexi só na classe `Votar` (e no import do `Strict`, na linha de import do pydantic).

### 23. Fora da lista da revisão (anotado, não corrigido)
- Os prints foram refeitos com a 0009 e a regra do item 16 (o 10 agora é de uma enquete "só no fim"; o 10b mostra o "durante" aberto).
- Durante a suíte do front, um teste de outro épico (`avisos/anexos-telas.test.tsx`, uma vez; e
  um do acesso, outra vez) falhou por tempo e passou nas duas rodadas seguintes: lentidão da
  máquina com outro agente rodando, não deste épico.

## Ajustes das revisões finais do M4 (integração A × B e usabilidade)

Cada ponto ganhou um teste de regressão que falhava antes da correção: API em
`api/testes/test_m4_ajustes.py`; front em `votar/ajustes.test.tsx`, `gestao/ajustes.test.tsx`,
`casca/ajustes-m4.test.tsx`; regras de CSS em `web/testes/estilo-m4.test.ts`.

### 24. "Quais apartamentos votaram" não promete sigilo que não tem · [Erick]
- **O que a revisão mostrou:** o cartão dizia "Sem mostrar o voto de ninguém", e a tela "nunca em
  quê". Quando todos escolhem a mesma opção (ou quase ninguém votou e o resultado aparece), a
  lista de quem votou somada ao resultado diz o voto de cada apartamento.
- **Decisão:** frase honesta. No cartão: "Mostra quem votou, não em quê. Quando todos escolhem a
  mesma opção, dá para saber."; na tela: "Mostra quem votou, não em quê. Mas, quando todos
  escolhem a mesma opção, dá para saber o voto de cada um."
- **Alternativa (não feita):** esconder a lista abaixo de um mínimo de votos (ex.: menos de 5),
  ou enquanto todos os votos estiverem numa opção só. Protege mais, mas a Comissão perde a
  cobrança nominal justamente no começo da enquete, quando ela mais ajuda.
- **Confirmar:** se a frase basta ou se vale o mínimo de votos.

### 25. Costura com o épico A
- **Trocar o tipo de escolha recria as opções** (ids novos), como a pergunta: a tela aberta da
  múltipla que virou única recebia 422 e ficava presa com caixas de marcar; agora recebe 409
  `enquete_mudou` e recarrega. E, por garantia, **todo 422 do voto também recarrega**.
- **A escolha de antes não sobrevive ao recarregar:** fica só com os ids que ainda existem; se
  não sobrar nenhum (ou sobrar mais de um numa única), volta ao voto gravado ou fica vazia, com o
  botão desligado e a dica.
- **`voto_mudou_agora`** não culpa mais "outro aparelho" (também acontece quando a gestão edita
  no meio do voto): "A enquete ou o voto do seu apartamento mudou agora há pouco. Confira e vote
  de novo."
- **`/enquetes/0/editar`** usa o `useIdDaEnquete` daqui; 404 e 422 vão para "Enquete não
  encontrada" (aqui também: 422 mostra a frase padrão, não "Confira os dados enviados.").

### 26. Telas (revisão de usabilidade)
- "Você ainda não trocou o voto. Toque em **Trocar voto** para valer." acima do botão, numa região
  `aria-live` educada que já existe (vazia, não ocupa espaço).
- Legenda depois do voto: "Quer trocar? Escolha outra opção." (única) / "Quer trocar? Marque ou
  desmarque e toque em Trocar voto." (múltipla); a dica do botão parado na múltipla: "Para trocar
  o voto, marque ou desmarque uma opção."
- Porcentagem maior que 0 e que arredonda para 0: "menos de 1%" (barras, `aria-valuetext` e
  participação, aqui e na tela de votantes). A largura da barra usa a conta exata.
- Na múltipla, com o resultado visível: "Cada apartamento pode marcar mais de uma opção, então a
  soma das porcentagens pode passar de 100%." ("pode": com um voto só, a soma dá 100).
- Terminada: selo de texto "Mais votada" (no empate, em todas), além da cor.
- Lista de quem falta em ordem crescente, por bloco e apartamento (na tela e no texto copiado;
  `ordemCrescente` daqui, o `ordemDaGrade` dos avisos ficou como estava). No computador, 8 por
  linha e cada andar começa a linha (`enq-andar-novo`).
- "Seu apartamento ainda não votou" em selo ipê (fundo ipê-suave, borda ipê, texto na tinta: o
  ipê puro como texto não chega a 4,5:1 no claro). O contador na aba ficou no backlog
  (`docs/07-roadmap.md`).
- Quem não vota (gestão fora do destino) vê "Vai até …".
- O cartão do aviso vem logo depois do cabeçalho (antes do "Corrigido em…" e do texto) e diz o
  estado: "Aberta · vai até …" / "Terminou · ver o resultado". Para isso, `EnqueteDoAviso`
  ganhou `encerra_em` e `encerrada` (esquema comum, com o `encerrada` pelo relógio da API).
- **Conferência visual:** o roteiro da revisão de usabilidade (Playwright próprio, Chrome
  headless, API 8168 e Vite 5168, banco `portal_dev` num container só dos ajustes), em 390 e
  1280 px, claro e escuro. Uma seleção está em `docs/superpowers/prints/m4-ajustes/`.
