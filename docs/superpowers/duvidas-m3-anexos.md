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
