# Dúvidas e decisões do M1 · Épico C · Avisos (só texto)

Decisões tomadas sem perguntar a ninguém. **[Erick]** marca o que só o Erick pode confirmar
(regra do condomínio ou preferência dele); o resto é decisão técnica, revisável na revisão do
marco. Base: `duvidas-m1.md` (itens 3, 11 a 17, 22, 25 e 27 já valiam e foram seguidos).

## 1. Rota a mais: `GET /api/avisos/destinos`
- **Dúvida:** o formulário de H-12 precisa dos botões "Bloco 1…5", e o contrato não tinha rota
  que listasse os blocos.
- **Decisão:** `GET /api/avisos/destinos` (gestão) devolve os blocos ativos (`numero`, `nome`).
  Esquemas `Destinos`/`DestinoBloco` com espelho em `web/src/avisos/tipos.ts` (o
  `test_contrato.py` confere). A contagem "vai para N apartamentos" continua em `/alcance`.
- **Por quê:** os blocos são editáveis (H-10); números fixos na tela mentiriam no dia em que
  um bloco mudar.

## 2. Bloco inativo não é destino
- **Decisão:** publicar ou calcular o alcance com um bloco `ativo = false` dá o mesmo 422
  `bloco_inexistente` de um bloco que não existe, e ele some de `/destinos`. O erro traz também
  `campos: [{campo: "blocos", ...}]`, para a tela marcar o campo.

## 3. Quem publica já conta como quem leu
- **Decisão:** publicar grava a leitura da própria unidade (como no protótipo, `lido = {perfil}`).
  O aviso não aparece como "Novo" para quem o escreveu.
- **Consequência:** se quem publica é do destino, entra no "Lido por X de Y" (é verdade: leu).

## 4. "Lido por X de Y" só conta quem é do destino
- **Decisão:** X = leituras de unidades ativas do destino. A gestão pode abrir aviso de outro
  bloco (contrato, dúvida 14); a leitura é gravada, mas não entra na conta.
- **Por quê:** senão X poderia passar de Y.

## 5. Mural da gestão mostra todos os avisos
- **Decisão:** a gestão vê no mural (e no número de não lidos) todos os avisos, inclusive os de
  outros blocos, com "Bloco N" na linha de detalhes e "Fixado …, para os Blocos N" no fixado.
- **Por quê:** a gestão precisa achar qualquer aviso para corrigir, arquivar e conferir a
  leitura (contrato: "a gestão vê todos"). **[Erick]** se preferir que o mural da Comissão
  mostre só o bloco dela, é trocar o filtro de `_visivel` (a abertura por link continua).

## 6. Arquivar também desafixa
- **Decisão:** `POST …/arquivar` grava `arquivado_em` e `fixado = false` na mesma transação. O
  histórico registra só `aviso_arquivado`.
- **Por quê:** fixado só tem sentido no mural; um arquivado "fixado" confundiria se um dia
  existir desarquivar.

## 7. Correções ao mesmo tempo: 409, sem trava
- **Decisão:** corrigir não trava a linha do aviso. Se duas pessoas corrigem juntas, a segunda
  bate na chave (aviso, versão) e recebe 409 `aviso_corrigido_agora` ("Outra pessoa corrigiu
  este aviso agora há pouco. Abra de novo e confira."). Testado com duas transações de verdade.
- **Por quê:** com trava, a segunda esperaria e gravaria a versão 3 por cima da 2 sem ter visto
  o que a outra escreveu. Arquivar e fixar usam `select … for update` (não há o que perder).

## 8. Busca: cada palavra, em qualquer ordem, sem acento
- **Decisão:** a busca é feita em Python (dúvida 25 do M1) sobre os avisos visíveis: cada
  palavra digitada precisa aparecer no título ou no texto da versão em vigor, sem diferenciar
  maiúsculas nem acentos ("concluida bloco" acha "Fundação do Bloco 4 concluída"). O protótipo
  procurava a frase inteira; por palavra erra menos com quem digita fora de ordem.

## 9. Ordem dos arquivados
- **Decisão:** do mais novo para o mais antigo pela data de publicação, sem prioridade para
  fixado (o contrato só fixa a ordem do mural).

## 10. Texto do aviso: parágrafos, quebras e links
- **Decisão:** linha em branco separa parágrafos; quebra simples continua (`pre-line`). Só
  endereços `http://` e `https://` viram link, abrindo em outra aba com `rel="noopener
  noreferrer"`; a pontuação do fim da frase fica fora do link. Nada passa por
  `dangerouslySetInnerHTML` (testado com `<b>` e `<img onerror>` no texto). Endereço longo quebra
  a linha em vez de alargar a tela.

## 11. Textos que não prometem o que o M1 não faz
- **Decisão:** o protótipo dizia "vai para N apartamentos, com notificação, e por e-mail" e
  "Aviso publicado. As notificações foram enviadas.". Sem notificação no M1 (H-13 é do M2), a
  tela diz "Vai aparecer no mural de N apartamentos" e "Aviso publicado.". Voltar ao texto do
  protótipo quando o M2 ligar a notificação.

## 12. Prévia mostra o item do mural e o aviso aberto
- **Decisão:** H-12 pede "uma prévia de como vai aparecer". Além do item do mural (protótipo),
  a prévia mostra o aviso aberto, com os parágrafos e links como vão ficar.

## 13. "Para a Comissão" também para o admin
- **Decisão:** a seção de gestão do aviso aberto tem o título do protótipo, "Para a Comissão",
  mesmo para o administrador. **[Erick]** trocar por "Para a gestão" se achar melhor.

## 14. Histórico com o título
- **Decisão:** `aviso_publicado` guarda `titulo`, `para_todos`, `blocos` e `fixado`;
  `aviso_corrigido` guarda `versao` e `titulo`; todos com `entidade = "aviso"` e
  `entidade_id = aviso.id` (pedido do épico B, que mostra o título no histórico).

## 15. Teste no navegador sem a rota de entrar
- **Observação:** o épico A (entrar) não estava nesta branch. O teste com o Playwright abriu
  sessões direto no banco local e mandou o cookie pela interceptação de rede (o navegador do
  teste recusa cookie `Secure` em `http://localhost` posto à mão). Sem violação de CSP, sem
  rolagem horizontal em 390 e 1366 px, claro e escuro. O único aviso do console é o
  `bluetooth` do `Permissions-Policy` (dúvida 26 do M1).

## Pedidos de mudança no comum

Nenhum obrigatório. Observações para o coordenador:
- **Número da aba no computador:** a casca recalcula os não lidos a cada troca de caminho; ao
  abrir um aviso, o `POST …/lido` pode terminar depois, e o número no menu lateral só cai na
  próxima navegação. No celular a aba não aparece no aviso aberto. Se incomodar, a casca pode
  expor um "recontar" no contexto.
- **Recado sobre o botão flutuante:** no celular, o recado "Aviso publicado." aparece por cima
  do botão "Novo aviso" (ambos ficam acima das abas). É do CSS comum (`.recado`/`.flutuante`).
