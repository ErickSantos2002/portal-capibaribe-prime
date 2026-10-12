# Dúvidas e decisões do M3 · Épico A · Documentos

Decisões tomadas sem perguntar a ninguém durante o épico A. Cada item: a dúvida, o que foi
decidido e por quê. **[Erick]** marca o que só o Erick pode confirmar (regra do condomínio,
preferência dele); o resto é decisão técnica que pode ser revista na revisão do marco.

## 1. "Avisar os apartamentos" vem marcado **[Erick]**
- **Dúvida:** a API tem `avisar_unidades = false` por padrão; o protótipo (testado com os
  vizinhos) mostra a caixa já marcada.
- **Decisão:** a tela segue o protótipo: marcada. Some quando "Quem pode ver" é "Só a gestão".
  Abaixo da caixa, a tela diz o que acontece ("sai um aviso no mural e a notificação para os
  apartamentos").
- **Por quê:** documento novo que as unidades podem ver quase sempre merece aviso (é o caso do
  RF-33), e o texto explica a consequência antes de publicar.
- **Confirmar:** se a Comissão prefere a caixa desmarcada (aí é trocar um `useState(true)`).

## 2. Texto do aviso automático
- **Decisão:** título "Documento novo: <título>" (cortado em 120 letras com "…"), categoria
  Geral, para todos, sem fixar; texto: "Um documento novo foi publicado no Portal: “<título>”."
  e "Ele fica guardado em Documentos, no menu do Portal, e o botão “Abrir o documento” deste
  aviso leva direto a ele."
- **Por quê:** o mesmo texto vai no e-mail (M2), que leva ao aviso, e no aviso aberto, que já tem
  o botão logo abaixo. A primeira versão ("abra este aviso no Portal e toque…") ficou estranha
  na conferência visual, para quem já estava com o aviso aberto.

## 3. Arquivar de novo não é erro
- **Decisão:** arquivar um documento já arquivado devolve 200 com o documento como está, sem
  registro repetido no histórico (o contrato só prevê 404; o aviso responde 409 no mesmo caso).
- **Por quê:** o duplo toque (ou duas pessoas da Comissão ao mesmo tempo) chega ao mesmo
  resultado; não há o que corrigir.

## 4. `?arquivados=true` para a unidade comum: lista vazia
- **Decisão:** a unidade comum que pede os arquivados recebe `itens: []` (200), não 403.
- **Por quê:** o contrato põe a rota para `UnidadeLogada`; lista vazia não revela se há
  arquivados, como o 404 igual ao inexistente.

## 5. "Envie o arquivo de novo." como erro de campo
- **Decisão:** arquivo que não é utilizável (de outra unidade, pendente, de aviso, inexistente)
  responde 422 com o código **`arquivo_invalido`** e a lista `campos` apontando `arquivo_id`
  (o mesmo formato do erro de validação). Arquivo já usado em outro documento: 409
  `arquivo_em_uso`.
- **Por quê:** a tela já mostra erro por campo ao lado do botão do arquivo; o contrato só fixou
  a mensagem. O código não pode ser `dados_invalidos`: o teste comum `test_m3_rotas.py`
  (`..._passam_da_validacao`) exige que o arquivo inexistente dê "outro erro, nunca o de
  validação". **Código novo no contrato** (permitido dentro do épico, contrato seção 10); o
  épico B pode querer o mesmo código para os anexos.

## 6. Abrir o PDF: aba aberta antes do pedido
- **Dúvida:** o link é pedido na hora do toque (vale 5 minutos), mas o navegador do celular só
  abre aba nova **no próprio toque**; depois de esperar a API, o `window.open` é bloqueado.
- **Decisão:** abre a aba vazia no toque e põe o endereço nela quando o link chega; se o
  navegador não deu a aba, a própria tela vai para o arquivo (o "voltar" traz de volta ao
  Portal). "Baixar" sempre na própria aba (o arquivo vem como anexo e o Portal não sai da tela).

## 7. Ícones e peças de tela próprios do épico
- **Dúvida:** a casca não tem ícone de "baixar"/"abrir em outra aba" (e `casca/` é comum), e o
  `useCarga`/`FalhaAoCarregar` moram em `avisos/`, que o épico B está mexendo.
- **Decisão:** `documentos/` tem os próprios: dois SVGs no mesmo traço do `Icone` e um
  `carregar.ts` pequeno. Na revisão do marco dá para subir os ícones para a casca.

## 8. Teste de encaixe do front
- **Decisão:** o bloco "encaixes do épico A ainda não mostram nada" de
  `web/src/m3contrato.test.ts` foi trocado por "encaixes do épico A mostram o que devem" (o
  arquivo não está na lista de comuns do contrato; é o equivalente no front de apagar a seção
  do épico em `test_m3_em_construcao.py`). Os outros blocos ficaram como estavam.

## 9. Conferência visual (390 px e 1280 px, morador e gestão)
- **Como:** banco `portal_dev_m3_documentos`, S3 falso (`moto_server`, com CORS), API na 8181,
  Vite na 5191, Playwright. Unidades e PDFs fictícios. Prints em
  `docs/superpowers/prints/m3-documentos/`.
- **Conferido de ponta a ponta:** públicos sem entrar (abre em aba nova com o link assinado);
  lista do morador sem o documento da gestão; `/documentos/<id da ata>` direto como morador →
  "Não achamos este documento" e o link da API → 404; documento aberto com versões anteriores;
  "Baixar" salva o arquivo e a tela fica no Portal; aviso automático com o botão; gestão
  publicando (envio do arquivo pelo navegador até o S3 falso), enviando nova versão e
  arquivando; documentos arquivados; tema escuro.
- **Corrigido pelo que se viu:** texto do aviso automático (item 2); "1 KB" quebrando a linha
  (espaço que não quebra entre número e unidade); "Quem vê" sumiu do documento arquivado (só a
  gestão vê, a caixa de cima já diz); botão "Trocar o arquivo" (o texto longo quebrava no
  celular); linhas da versão anterior separadas (sem o "·").
- **Não conferido:** celular de verdade (Android e iPhone), em especial o "Abrir o documento" no
  Safari do iPhone (a aba aberta antes do pedido, item 6) e o PDF abrindo no visualizador do
  aparelho. **[Erick]** testar no aparelho junto com o teste do M2, depois do R2 de verdade.

## 10. O texto "Avisar os apartamentos" fala em notificação
- **Decisão:** "Sai um aviso no mural, com o botão para abrir o documento, e ele chega no
  celular de quem ativou as notificações." O aviso automático entra no mesmo envio de push e
  e-mail de qualquer aviso (M2); quem marca a caixa precisa saber que vai tocar no celular de
  muita gente.
