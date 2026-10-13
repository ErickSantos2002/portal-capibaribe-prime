# Dúvidas e decisões do M3 · Épico B · Anexos nos avisos

Decisões tomadas sem perguntar a ninguém durante o épico B (spec
`docs/superpowers/specs/m3-anexos.md`). Cada item: a dúvida, o que foi decidido e por quê.
**[Erick]** marca o que só o Erick pode confirmar (preferência dele, regra do condomínio); o
resto é decisão técnica que pode ser revista na revisão do marco.

## 1. Histórico só ganha `anexos` quando há anexo
- **Dúvida:** registrar no histórico quantos anexos o aviso tem.
- **Decisão:** `"anexos": n` nos detalhes de `aviso_publicado` e `aviso_corrigido` só quando
  `n > 0`. As frases do histórico (`web/src/administracao/frases.ts`, comum) não mudam.
- **Por quê:** o aviso automático do épico A passa por `gravar_publicacao` sem anexo; se o
  detalhe mudasse sempre, um teste do épico A que compara o histórico inteiro quebraria no
  merge. Quais arquivos entraram está em `aviso_anexo`, que nunca muda.

## 2. Ícones do clipe, da foto e do "fechar" ficam no épico
- **Dúvida:** o `Icone` (`web/src/casca/Icone.tsx`) não tem clipe nem foto, e a casca é comum
  (seção 10 do contrato).
- **Decisão:** `web/src/avisos/IconesAnexo.tsx`, com o mesmo traço (2 px, 24×24, sempre
  decorativo ao lado de texto), em JSX (sem `innerHTML`).
- **Para o coordenador:** se o épico A também precisar de clipe/PDF, vale mover os desenhos para
  o `Icone` no fechamento do marco.

## 3. Envio sem porcentagem
- **Dúvida:** "progresso do envio" pede uma porcentagem, mas o `enviarArquivo` (comum) usa
  `fetch`, que não informa quanto já subiu.
- **Decisão:** cada arquivo mostra "Enviando…" com uma barra animada (sem número), um de cada
  vez, e a lista diz quantos faltam. Sem mexer no arquivo comum.
- **Se quiser porcentagem:** é trocar o PUT do `web/src/arquivos/enviar.ts` por
  `XMLHttpRequest` (que tem `upload.onprogress`) e aceitar um `aoProgredir`; arquivo comum,
  fica para o coordenador.

## 4. Ordem dos anexos é a da escolha
- **Dúvida:** o banco guarda a `ordem` (1 a 5); a tela poderia deixar reordenar.
- **Decisão:** sem reordenar. A ordem é a da escolha; para mudar, tira e escolhe de novo.
- **Por quê:** arrastar no celular é difícil para quem tem pouca prática, e com até 5 itens
  tirar e pôr de novo resolve. A API já aceita qualquer ordem, então reordenar depois é só tela.

## 5. PDF abre numa aba nova, sem "Baixar"
- **Dúvida:** a rota tem `?baixar=true`; a tela poderia ter dois botões por PDF.
- **Decisão:** um botão só, "abre em outra aba" (o leitor de PDF do celular e do computador já
  tem baixar e compartilhar). O `baixar` fica na API, pronto para o épico A ou para depois.
- **Por quê:** um botão por arquivo é mais simples para a Dona Socorro.

## 6. Arquivo tirado antes de publicar fica guardado
- Igual à dúvida 7 do contrato: "Tirar" só tira da lista. O arquivo já confirmado fica no
  bucket, travado, sem aparecer para ninguém.

## 7. Push e e-mail não falam do anexo
- **Dúvida:** o e-mail do aviso (M2) podia dizer "tem 2 anexos".
- **Decisão:** não muda (o envio é do `notificacoes`/e-mail, comuns). Quem abre o aviso vê os
  anexos; o link do anexo exige sessão de qualquer jeito.

## 8. Fotos primeiro, PDFs depois
- **Dúvida:** os anexos têm uma ordem (1 a 5); misturar foto e PDF na ordem exata quebraria a
  grade de fotos.
- **Decisão:** no aviso aberto, as fotos em grade e depois os PDFs, cada grupo na ordem dos
  anexos. No formulário, a lista segue a ordem exata.

## 9. "Enviar de novo" só quando pode dar certo
- **Decisão:** o arquivo recusado pela API (422: não é PDF nem foto, ou passou do limite) mostra
  só "Tirar"; erro de rede ou do bucket mostra "Enviar de novo" também. Achado na conferência
  visual: o botão para um `.pdf` falso só repetiria o mesmo erro.

## 10. Conferência visual com um navegador próprio
- **Dúvida:** o navegador do MCP do Playwright é um só para os três agentes do M3; no meio da
  conferência, a aba passou a mostrar a tela do épico A (`127.0.0.1:5191/documentos/5`).
- **Decisão:** a conferência rodou com um script do próprio Playwright (Chrome sem janela, um
  contexto por pessoa), contra a API (8182), o Vite (5192), o banco próprio e o `moto_server`
  (9182, com CORS do bucket). Prints em `docs/superpowers/prints/m3-anexos/`, só com dados
  fictícios (fotos desenhadas, PDF gerado).
- **O que não foi conferido:** tema escuro (o tema do Portal é escolhido no botão da casca,
  não pelo sistema, e o script não o trocou), um iPhone de verdade (o `window.open` antes do
  pedido é o caminho recomendado para o Safari, mas só foi testado no Chrome) e o R2 de verdade
  (CORS e CSP de produção).

## Revisão independente (código e UX)

## 11. Rota `…/anexos/{arquivo_id}/abrir` (U12): mudança de contrato dentro do épico
- **Dúvida:** o link de 5 minutos aberto numa aba nova vence; recarregar a aba mostrava o XML
  de erro do R2.
- **Decisão:** `GET /api/avisos/{aviso_id}/anexos/{arquivo_id}/abrir`, com a mesma regra do
  `…/link` (sessão da unidade, aviso visível, arquivo anexo de alguma versão), responde **302**
  para um link novo a cada pedido, com `no-store`. A tela usa essa rota como `href` do PDF
  (`<a target="_blank">`, que o Safari do iPhone não bloqueia) e como `src` da foto (a CSP já
  aceita `'self'` e o redirecionamento para o R2 em `img-src`). Erro (aviso que não vê, arquivo
  de outro aviso, bucket desligado) vira uma página HTML simples com a frase da API, não JSON.
  O cookie de sessão vai junto (navegação de topo no mesmo site, `SameSite=Lax`); GET não exige
  `X-Portal`. Sem sessão, a resposta continua a JSON 401 da dependência comum.
- **Limite, conferido no navegador:** depois do 302 a aba mostra o endereço assinado do R2;
  recarregar **essa aba** depois de 5 minutos ainda mostra o erro do R2. O que a rota resolve:
  a foto e o PDF abrem mesmo com a página do aviso aberta há horas (antes a tela pedia o link
  por JavaScript, e o Safari bloqueava a aba aberta depois da espera); tocar de novo no Portal
  sempre funciona. Resolver o recarregar da própria aba exigiria a API entregar o conteúdo do
  arquivo (a Vercel limita a resposta a 4,5 MB, ADR-0004) ou um link mais longo que 5 minutos
  (`armazenamento.py`, comum): fica para o coordenador decidir.
- **Fora do OpenAPI** (`include_in_schema=False`): as listas de rotas do contrato
  (`test_m3_rotas.py::test_rotas_do_m3_declaradas` e `test_cache.py`) são comuns e quebrariam
  com uma rota nova. **Para o coordenador:** ao fechar o marco, pôr a rota no esquema e nas duas
  listas (ela responde 302/404/503, sempre com `no-store`).
- **Para o épico A (mesmo formato):** `GET /api/documentos/{id}/versoes/{versao}/abrir` →
  `servico.link…` dentro de `try`, `RedirectResponse(link.url, 302)`; `ErroApi` →
  `_pagina_de_erro(erro)` (HTML com `html.escape` na mensagem). O `…/link` fica para quem quer
  o JSON (`baixar=true`).

## 12. `versao_base` na correção (C2): mudança de contrato dentro do épico
- `CorrigirAviso.versao_base: int | None` (1 a 32.767; espelho em `web/src/avisos/tipos.ts`,
  `test_contrato.py` verde). Diferente da versão em vigor: 409 `aviso_corrigido_agora` (o código
  e a frase que a correção simultânea já usava). Omitida, não confere (cliente antigo). A tela
  manda sempre (`versoes_anteriores.length + 1`) e, no 409, mostra a frase e o botão "Abrir a
  versão nova", que recarrega o formulário com a versão nova (o que a pessoa escreveu se perde;
  ela foi avisada pela frase).

## 13. Sair no meio: pergunta, mas não guarda rascunho (U1)
- **Decisão:** `useBlocker` (o roteador é de dados: `createBrowserRouter`) pergunta "Sair sem
  publicar?" ao sair por dentro do Portal; `beforeunload` faz o navegador perguntar ao recarregar
  ou fechar. Formulário sem nada escrito sai sem perguntar.
- **Não feito:** guardar o texto em `sessionStorage`. Os anexos não dá para guardar (o arquivo
  escolhido não sobrevive a recarregar), e meio rascunho confunde mais do que ajuda. Se a
  Comissão pedir, é um efeito no `Formularios.tsx`.
- A pergunta é um `alertdialog` com o foco em "Continuar escrevendo" e Esc para ficar; a página
  de trás não fica `inert` (a pergunta só aparece por um instante e cobre a tela).

## 14. Correção que tira anexos não tem prévia (U13)
- Só registrado: a correção salva direto, como antes do M3. O aviso aberto diz depois o que
  mudou nos anexos ("Anexos: saiu 1 foto.", U6), e a versão antiga guarda os anexos dela.

## 15. Botão do PDF desabilitado enquanto abre (C7): deixou de existir
- Com a rota `…/abrir` (dúvida 11), o PDF virou um link comum: não há espera nem janela aberta
  por script. Tocar duas vezes abre duas abas, cada uma com um link válido.

## 16. Recusados continuam contando nas 5 vagas (U10)
- **Decisão:** a frase muda: com 5 na lista e algum com erro, "Já são 5 arquivos. Tire os que
  deram erro para anexar outros.". Tirar libera a vaga na hora (e o foco vai para o próximo item
  ou para "Anexar foto ou PDF", U5).

## 17. Foto sem nome para o morador (U7)
- No aviso aberto e no visualizador a foto é "Foto 1 de 2" (rótulo e texto alternativo); o
  nome do arquivo só aparece no formulário da gestão. O PDF mantém o nome como foi enviado.

## 18. Conferência visual da revisão
- Mesmo arranjo da dúvida 10 (Chrome próprio sem janela, banco, API, Vite e `moto_server`
  locais; sem o MCP compartilhado). Prints novos em `docs/superpowers/prints/m3-anexos/`:
  botão "Esperando os arquivos…", formulário pronto, "Sair sem publicar?" (pelo voltar do
  navegador), aviso aberto com "Ampliar", visualizador com "Anterior"/"Próxima", correção que
  trocou anexos no computador ("Anexos: entrou …; saiu 1 foto.", "Assim era antes", "Como está
  agora:") e o mural. O PDF abriu pela rota `…/abrir` e recarregar a aba dentro dos 5 minutos
  deu 200. Achado e corrigido na conferência: no computador, uma foto só ocupava a largura
  toda; agora vai até 520 px.
- **Não conferido:** tema escuro, iPhone de verdade (zoom de dois dedos e a aba do PDF), R2 de
  verdade, e o recarregar da aba do PDF depois de 5 minutos (limite descrito na dúvida 11).
