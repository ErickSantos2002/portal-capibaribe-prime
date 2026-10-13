# Dúvidas e decisões do M3 · Épico A · Documentos

Decisões tomadas sem perguntar a ninguém durante o épico A. Cada item: a dúvida, o que foi
decidido e por quê. **[Erick]** marca o que só o Erick pode confirmar (regra do condomínio,
preferência dele); o resto é decisão técnica que pode ser revista na revisão do marco.

## 1. "Avisar os apartamentos" vem marcado · respondida
- **Dúvida:** a API tem `avisar_unidades = false` por padrão; o protótipo (testado com os
  vizinhos) mostra a caixa já marcada.
- **Decisão:** a tela segue o protótipo: marcada. Some quando "Quem pode ver" é "Só a gestão".
  Abaixo da caixa, a tela diz o que acontece ("sai um aviso no mural e a notificação para os
  apartamentos").
- **Por quê:** documento novo que as unidades podem ver quase sempre merece aviso (é o caso do
  RF-33), e o texto explica a consequência antes de publicar.
- **Confirmar:** se a Comissão prefere a caixa desmarcada (aí é trocar um `useState(true)`).
- **Resposta do Erick (12/10/2026):** fica assim: marcada no documento novo, desmarcada na
  versão nova (item 13).

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

## 6. Abrir o PDF: aba aberta antes do pedido · substituído pelo item 12 (revisão)
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

---

# Revisão independente (código e UX) · o que mudou e o que ficou para o coordenador

## 11. Título sem nenhum invisível (C3) · resolvido no fechamento
- **Decisão:** `validar_titulo` (e a linha do aviso) recusam, além da regra comum, as categorias
  Unicode Zl, Zp e Cf (U+2028, U+2029, U+061C, U+180E, U+00AD…) e os preenchimentos do Hangul
  (U+115F, U+1160, U+3164, U+FFA0). O ZWJ (U+200D) continua aceito, como na regra comum (emojis
  compostos).
- **Pendência do coordenador:** a mesma regra em `app/esquemas/comum.py` (`sem_invisiveis`),
  para o título do aviso, o nome do arquivo e o resto. O épico A não edita o comum.
- **Fechamento do M3 (coordenador, 12/10/2026):** a regra virou `sem_invisivel_nenhum` em `app/esquemas/comum.py` e vale
  para o título do documento e o do aviso (publicar e corrigir), com testes em
  `test_avisos_esquemas.py`. O nome do arquivo e o local do evento seguem a regra comum de antes
  (`sem_controle` + `sem_invisiveis`): o nome vem do aparelho e quase nunca é digitado.

## 12. "Abrir" e "Baixar" pelo Portal: rota nova `GET .../versoes/{versao}/abrir` (U7) · resolvido no fechamento
- **Mudança de contrato:** `GET /api/documentos/{documento_id}/versoes/{versao}/abrir?baixar=`
  responde **302** para um link assinado novo (confere quem vê a cada visita; sem sessão, só o
  público). Sem acesso ou inexistente: 302 para `/documentos/{id}` (a página diz "não achamos"
  ou pede para entrar). Arquivos desligados: 302 para `/documentos/{id}?erro=arquivos_desligados`.
  `no-store` vem do middleware comum. A tela usa `href` comum (abrir: `target="_blank"`, com
  "(abre em outra aba)" para o leitor de tela; baixar: na própria aba). O `GET .../link`
  (JSON) continua, como no contrato.
- **O que isto resolve e o que não resolve (conferido no navegador):** todo toque no Portal
  (inclusive numa página deixada aberta por horas), "abrir em nova aba" pelo toque longo e o
  link copiado ou compartilhado passam pela conferência e ganham link novo. Mas **recarregar a
  aba do PDF não**: depois do 302, o endereço da aba é o link assinado, e o navegador recarrega
  esse endereço; passados 5 minutos, aparece o erro do bucket. Resolver isso de vez pede
  validade maior no link de leitura (`VALIDADE_LEITURA`, em `app/servicos/armazenamento.py`,
  comum) ou servir o arquivo pela API (a Vercel limita a resposta a 4,5 MB). **Pendência do
  coordenador** (a decisão vale também para os anexos do épico B).
- **Fora do OpenAPI** (`include_in_schema=False`): é navegação do navegador, não JSON, e o teste
  comum `test_m3_rotas.py::test_rotas_do_m3_declaradas` compara a lista exata de rotas, que o
  épico não pode editar. **Pendência do coordenador:** decidir no merge se a rota entra no
  OpenAPI e no teste comum (o épico B recebeu a mesma sugestão para os anexos, com
  `GET /api/avisos/{id}/anexos/{arquivo_id}/abrir`: o formato é o mesmo).
- Some com isso a aba aberta antes do pedido (item 6): o `href` abre a aba no próprio toque.
- **Fechamento do M3 (coordenador, 12/10/2026):** as duas rotas `…/abrir` (esta e a do anexo) entraram no OpenAPI, em
  `test_m3_rotas.py`, `test_cache.py` (302/303 ou 404/503, com `no-store` também no
  redirecionamento) e no spec do contrato. O link de leitura passou a valer **1 hora**
  (`VALIDADE_LEITURA`; ADR-0011, "Revisões"): recarregar a aba do PDF dentro de 1 hora
  funciona; o link do Portal sempre gera um novo.

## 13. Aviso da versão nova sem o botão "Ver o documento" (U3) · movido para o roadmap
- **Decisão:** "Enviar nova versão" ganhou "Avisar os apartamentos" (**desmarcado**) e "O que
  mudou (se quiser)". O aviso sai com título "Documento atualizado: <título>" e o texto "Saiu
  a versão N de um documento do Portal: “<título>”." + a linha + "Ela fica guardada em
  Documentos, no menu do Portal: <endereço do documento>" (o endereço só quando
  `PORTAL_URL_BASE` existe; vira link no mural e no e-mail).
- **Por que sem o botão:** `documento.aviso_id` guarda um aviso só (o da criação), único, e o
  `app` não tem UPDATE nele; o botão do aviso vem desse campo. Ligar mais avisos ao documento
  pede migração (uma coluna `aviso_id` em `documento_versao`, ou uma tabela), o que o épico não
  faz. O "o que mudou" também não aparece no documento, só no aviso, pelo mesmo motivo.
- **Fechamento do M3 (coordenador, 12/10/2026):** sem migração no M3; foi para o backlog sem data do roadmap (`07-roadmap.md`,
  "Backlog sem data (do M3)"), e o modelo de dados registra o limite (seção 3.4).

## 14. A resposta se perdeu: 409 `arquivo_em_uso` diz onde está (U1)
- **Mudança de contrato:** quando o arquivo (que a própria unidade enviou) já está num
  documento que ela vê, o 409 `arquivo_em_uso` traz `documento_id` e `versao`. A tela leva a
  pessoa até lá com "Já estava publicado: o primeiro envio tinha dado certo, e nada foi
  publicado em dobro." (ou "Já estava enviada", na versão nova). A conferência é feita antes
  de gravar qualquer coisa: o reenvio não cria aviso nem notificação de novo.
- **Por que assim, e não chave de idempotência:** o próprio id do arquivo já é a chave (ele é
  único por envio e só pode entrar em um documento), e não precisa de coluna nova.

## 15. Categoria do aviso automático (U13)
- **Decisão:** documento de Obra → aviso de Obra; Ata → Reunião; os outros → Geral. A gestão
  pode escrever uma linha para o aviso, e a tela mostra a prévia (categoria, título e texto,
  os mesmos que a API grava; os dois lados têm teste com o mesmo texto).

## 16. Recado que some e fonte em px (U9, U18) · U9 resolvido, U18 no roadmap
- **U9:** o recado da casca (`useRecado`, comum) some em 2,6 s; não mexi. No documento, depois
  de publicar ou enviar versão, fica uma confirmação fixa ("Pronto: o documento foi publicado.
  Ele já aparece em Documentos. O aviso saiu no mural."), até sair da tela.
- **U18:** as fontes do Portal inteiro estão em px (`estilo.css`, comum); a CSS do épico seguiu
  o padrão. Trocar por `rem` é decisão do coordenador para o Portal todo.
- **Fechamento do M3 (coordenador, 12/10/2026):** **U9:** o recado da casca não some mais sozinho: fica até a pessoa tocar
  em "Fechar" (44 px, fora da região de status) ou trocar de tela, para sucesso e erro, anunciado
  pelo `aria-live` (`casca/RecadoProvider.tsx`, testes em `casca/recado.test.tsx`). **U18:** não
  convertido agora; está no backlog do roadmap (fontes em `rem` no Portal todo).

## 17. Outras decisões da revisão
- **C1/C2:** número fora do tipo do banco (versão acima de 32767, id acima de bigint, zero)
  responde **422** `dados_invalidos`, não 404 nem 500, nas rotas e no `arquivo_id` do épico. O
  mesmo ajuste nas rotas de avisos e arquivos é do coordenador. **Fechamento do M3 (coordenador, 12/10/2026):** tipo comum `IdBanco`
  (`esquemas/comum.py`) em todo id de caminho, query e corpo do Portal; teste que varre o
  OpenAPI (`test_ids_do_banco.py`).
- **C4:** a resposta de "Enviar nova versão" é o documento como ficou **na versão que o pedido
  criou** (versões até ela), mesmo que outra tenha chegado logo depois.
- **Histórico:** `documento_versao_enviada` passou a ter `{"versao": n, "avisou": bool}` (a
  frase de `frases.ts` só usa a versão; nada muda nela).
- **U2:** o link de um documento **público** aberto sem entrar mostra a página dele (com Abrir,
  Baixar e "Entrar"); a tela acha o documento na lista dos públicos (a API não tem o documento
  aberto sem sessão). Não é público: vai para "Entrar" e volta para o documento depois.
- **U4:** cada versão antiga diz "Substituída pela versão N em <data>"; o botão é discreto
  (link). Para o morador, as versões ficam recolhidas em "Ver versões anteriores (N)"; a gestão
  as vê abertas.
- **U5:** sair de "Novo documento" ou "Enviar nova versão" com algo escrito, arquivo escolhido
  ou no meio do envio pergunta antes (`window.confirm`, a pergunta nativa, que o leitor de tela
  e o celular conhecem) e, ao fechar a aba, o `beforeunload`. Solução do próprio épico
  (`documentos/confirmarSaida.ts`); o épico B fez a dele no aviso: vale unificar depois (no
  backlog do roadmap desde o fechamento).
- **U6:** a ajuda do arquivo diz "Se o documento tem várias páginas, junte num PDF antes de
  enviar.". Várias fotos num documento só não foi feito (fica para quando a Comissão pedir; no
  backlog do roadmap).
- **U10:** o arquivo é conferido na hora de escolher, com o que fazer: Word ("salve como PDF"),
  outro tipo, vazio, PDF acima de 20 MB (com o tamanho e como reduzir). Foto grande passa,
  porque é reduzida antes de enviar. Trocar o arquivo limpa o erro de antes.
- **U11, U12, U14 a U17:** "Documentos públicos" sem o convite para entrar quando já se entrou
  (e com "Entrar" para o visitante); "Quem vê" só na parte da gestão; o assunto começa em
  "Escolha…" e é obrigatório; selo "qualquer pessoa vê" na lista da gestão; arquivados com a
  data em que foram arquivados; título do topo em até 2 linhas, com o título inteiro na folha.
