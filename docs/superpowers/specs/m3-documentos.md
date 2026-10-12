# Spec · M3 · Épico A · Documentos

| | |
|---|---|
| **Marco** | M3 · Documentos e anexos (`docs/07-roadmap.md`, seção do M3) |
| **Histórias** | H-17 (publicar), H-18 (consultar, inclusive os públicos na entrada), H-19 (nova versão) |
| **Base** | contrato `m3-contrato.md` (seções 5.2, 5.4, 7 e 10), RF-30 a RF-33, ADR-0004, ADR-0011, `duvidas-m3.md`, protótipo (`#documentos`, `#publicos`, `#novo-documento`, `#entrar`) |
| **Criado em** | 12/10/2026 |
| **Plano** | `docs/superpowers/plans/m3-documentos.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m3-documentos.md` |

## 1. Objetivo

Trocar o 501 das rotas de documentos pelo comportamento do contrato e dar as telas: lista por
assunto com busca, documento aberto (abrir, baixar, versões anteriores), "Novo documento",
"Enviar nova versão", arquivar, documentos arquivados (gestão), os públicos para quem não
entrou e o botão "Abrir o documento" no aviso automático. **Sem migração nova** e sem tocar nos
arquivos comuns (contrato, seção 10).

## 2. API

### 2.1 Quem vê o quê (`app/servicos/documentos.py`)

Um filtro só para lista, documento e link: `acesso in niveis_que_ve(logado)` e, se o documento
está arquivado, **só a gestão**. Tudo o que fica de fora responde **404
`documento_nao_encontrado`** ("Não achamos este documento. O link pode estar incompleto, ou ele
não está mais disponível."), igual ao inexistente: o de nível `gestao` não aparece nem abre por
link direto para a conta comum, nem para quem não entrou (critério do roadmap).

- `GET /api/documentos`: não arquivados que a unidade vê. `?arquivados=true`: só para a gestão
  (os arquivados); para a unidade comum, lista vazia (não revela que existem).
- `GET /api/documentos/publicos`: só `publico`, não arquivados, sem sessão.
- `GET /api/documentos/{id}`: o `Documento` (resumo + versões anteriores + `aviso_id`).
- Ordem da lista: `data_documento` desc, depois `id` desc. Uma consulta para os documentos e
  uma para as versões de todos eles (sem consulta por item).
- `GET .../versoes/{versao}/link?baixar=`: o documento passa pelo mesmo filtro e a versão tem
  de existir; senão 404. Depois `arquivos.link_do_arquivo` (503 `arquivos_desligados` sem
  bucket). Versão antiga também abre (H-19).

### 2.2 Publicar (H-17, RF-33)

1. `arquivo_utilizavel(db, logado, arquivo_id, "documento")`; `None` → 422 `arquivo_invalido`
   com o campo `arquivo_id` e a mensagem "Envie o arquivo de novo." (o formato de erro de
   campo que a tela já sabe mostrar).
2. Se `avisar_unidades`: `avisos.gravar_publicacao` com `NovoAviso(titulo="Documento novo:
   <título>", texto=..., categoria=geral, para_todos=True)`. O título do aviso é cortado em 120
   letras com "…" (o do documento já tem até 120). O texto não depende de onde é lido (mural ou
   e-mail): "Um documento novo foi publicado no Portal: “<título>”." + "Ele fica guardado em
   Documentos, no menu do Portal, e o botão “Abrir o documento” deste aviso leva direto a ele."
3. `documento` (com `aviso_id`) e `documento_versao` 1; histórico `documento_publicado`
   `{"versao": 1, "acesso", "categoria", "avisou"}`; **um commit só**: documento e aviso nascem
   juntos ou nenhum dos dois.
4. A rota chama `notificacoes.agendar(tarefas, aviso_id)` depois do commit, só quando avisou.
5. Restrições do banco viram resposta: `arquivo_em_uso` (e a única de `arquivo_id`) → 409
   `arquivo_em_uso` "Este arquivo já está em outro documento. Escolha o arquivo de novo.";
   `arquivo_nao_confirmado`/`arquivo_finalidade_errada` → o 422 do item 1.

### 2.3 Nova versão (H-19) e arquivar

- Nova versão: o documento é buscado **com trava** (`for update`), o que põe em fila duas
  versões ao mesmo tempo e o arquivar. Não existe → 404; arquivado → 409 `documento_arquivado`
  "Documento arquivado não recebe versão nova."; arquivo como no 2.2. Versão = maior + 1.
  Histórico `documento_versao_enviada` `{"versao": n}`. Resposta 201 `Documento`.
- Arquivar: com trava; não existe → 404; **já arquivado devolve o documento como está** (200,
  sem histórico repetido: o contrato só prevê 404, e o duplo toque não é erro). Senão
  `arquivado_em` (carimbado pelo banco) e histórico `documento_arquivado`. O aviso automático
  continua no mural, mas sem o botão (o campo `documento` do aviso já some, seção 5.3).

## 3. Front (`web/src/documentos/`)

| Rota | Quem | Tela |
|---|---|---|
| `/documentos` | unidade | busca + lista por assunto; "Novo documento" (flutuante) e "Ver os documentos arquivados" para a gestão |
| `/documentos/arquivados` | gestão | a mesma lista, só os arquivados |
| `/documentos/publicos` | qualquer um | os públicos, cada um com "Abrir" e "Baixar"; recado de que os outros aparecem depois de entrar |
| `/documentos/:id` | unidade | documento aberto: assunto, data, quem vê, "Abrir o documento", "Baixar", versão e "Versões anteriores"; para a gestão: "Enviar nova versão" e "Arquivar" (com confirmação) |
| `/documentos/novo` | gestão | título, assunto, data, arquivo, quem pode ver, "Avisar os apartamentos" |
| `/documentos/:id/nova-versao` | gestão | arquivo e "Enviar nova versão" |

- **Busca** na própria tela (a lista inteira já veio): cada palavra no título ou no nome do
  assunto, sem acento e sem maiúscula, como o protótipo. Grupos na ordem do formulário (Obra,
  Convenção, Regimento, Atas, Contratos, Orientações, Outros).
- **Abrir:** o link é pedido no toque. Para não cair no bloqueio de janela (o navegador só deixa
  abrir aba nova no próprio toque), a aba é aberta **antes** do pedido e recebe o endereço
  depois; se o navegador não abriu a aba, a própria tela vai para o arquivo. Erro: a aba é
  fechada e a mensagem aparece na tela. **Baixar:** o mesmo link com `baixar=true`, na própria
  aba (o `attachment` faz o navegador salvar sem sair do Portal).
- **Publicar:** `enviarArquivo(arquivo, 'documento')` ("Enviando o arquivo…") e depois
  `publicarDocumento` ("Publicando…"). Se o envio deu certo e a publicação falhou (um título
  vazio que escapou, a internet), o arquivo enviado é reaproveitado na próxima tentativa,
  enquanto a pessoa não trocar de arquivo; com "Envie o arquivo de novo." ou `arquivo_em_uso`,
  ele é esquecido. Sucesso: vai para o documento aberto com o recado "Documento publicado.".
- "Avisar os apartamentos" vem **marcado**, como no protótipo, e some quando "Quem pode ver" é
  "Só a gestão" (a API recusaria).
- **Encaixes:** `itemDocumentos` devolve o item "Documentos" para toda unidade; o
  `LinkDocumentosPublicos` é o "Ver documentos públicos" da entrada; o `DocumentoDoAviso` é um
  cartão-botão "Abrir o documento" com o título, que leva a `/documentos/:id`.
- CSS em `web/src/documentos/documentos.css`, só com os tokens de `estilo.css`. Ícones que a
  casca não tem (baixar, abrir em outra aba) são SVGs locais no mesmo traço (`Icone` é comum).
- O hook de carga e as caixas de erro/carregando são do próprio épico (os dos avisos são do
  épico B, que está mexendo neles).

## 4. Fora deste épico

Corrigir título ou nível de documento publicado (dúvida 5 do contrato); prévia do PDF embutida
na página (dúvida 8 do contrato); mostrar o documento como anexo no mural.
