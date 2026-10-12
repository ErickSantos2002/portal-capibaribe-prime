# Spec · M3 · Épico B · Anexos nos avisos

| | |
|---|---|
| **Marco** | M3 · Documentos e anexos (`docs/07-roadmap.md`) |
| **História** | H-12 (a parte dos anexos: "imagens ou PDF, até 10 MB cada") |
| **Base** | [contrato do M3](m3-contrato.md) (seções 4, 5.1, 5.3, 7, 8 e 10), `02-requisitos.md` (RF-10), `04-modelo-de-dados.md` (seção 3.3, `aviso_anexo`), `05-arquitetura.md` (seção 6.2), ADR-0004, ADR-0011, protótipo (`#novo-aviso`, `#aviso/2`, mural) |
| **Criado em** | 12/10/2026 |
| **Plano** | `docs/superpowers/plans/m3-anexos.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m3-anexos.md` |

## 1. Objetivo

A Comissão anexa até 5 fotos ou PDFs a um aviso, ao publicar e ao corrigir. Quem vê o aviso vê
os anexos: a foto aparece na própria tela (toque abre grande) e o PDF é um botão com o nome e o
tamanho que abre numa aba nova. O mural mostra um clipe com "1 anexo" / "3 anexos". A versão
antiga ("Ver como era antes") mostra os anexos dela.

Fica de fora: banco (a 0007 já tem `aviso_anexo`; nenhuma migração nova), o envio do arquivo
em si (pronto no contrato: `enviarArquivo`), push e e-mail (não mencionam anexo), versão e
novidades (coordenador).

## 2. API

### 2.1 Publicar e corrigir com anexos (`app/servicos/avisos.py`)

`_anexos_conferidos(db, logado, ids, aviso_id=None) -> list[int]`, chamada antes de gravar:

1. Mais de 5: 422 `dados_invalidos` "Até 5 anexos por aviso." (campo `anexos`).
2. Repetido: 422 "O mesmo arquivo foi escolhido duas vezes." (campo `anexos`).
3. Cada id: `arquivo_utilizavel(db, logado, id, "aviso")` **e** ainda não usado em documento
   nem em outro aviso; **ou** (só na correção) já é anexo de alguma versão deste aviso. Senão
   422 "Envie o arquivo de novo." (campo `anexos`). Um arquivo de outra unidade, pendente, de
   finalidade `documento` ou inexistente recebe a mesma frase: não revela nada.
4. A restrição do banco `arquivo_em_uso` (dois avisos ao mesmo tempo com o mesmo arquivo)
   vira a mesma 422; `aviso_anexo_versao_fechada` nunca acontece pelo caminho da API (o anexo
   entra no mesmo flush da versão) e, se acontecer, é 500 (bug).

- **Publicar** (`gravar_publicacao`, também usada pelo épico A sem anexos): grava
  `aviso_anexo` (versão 1, `ordem` 1…n) na mesma transação do aviso. Omitido, nulo ou `[]`:
  nada muda em relação ao M1/M2.
- **Corrigir**: `anexos` omitido ou nulo repete os da versão em vigor (na mesma ordem); `[]`
  tira todos; lista = os da versão nova, na ordem dada. Trocar só os anexos (ou só a ordem) é
  mudança (versão nova); tudo igual continua 409 `sem_mudanca`.
- Histórico: `aviso_publicado` e `aviso_corrigido` ganham `"anexos": <quantidade>` nos
  detalhes **só quando há anexo** (aviso sem anexo registra exatamente o que registrava, e o
  aviso automático do épico A também); as frases do histórico, que são comuns, não mudam.

### 2.2 Ler (`abrir`, `listar`)

- `AvisoCompleto.anexos`: os da versão em vigor, na ordem; `VersaoAviso.anexos`: os de cada
  versão antiga. Uma consulta por aviso aberto (`aviso_anexo` + `arquivo`, por versão e ordem).
- `AvisoResumo.quantidade_anexos`: os da versão em vigor. Uma consulta agrupada para a lista
  inteira (contagem por aviso e versão; o Python pega a da versão em vigor).

### 2.3 Link do anexo (`GET /api/avisos/{aviso_id}/anexos/{arquivo_id}/link?baixar=`)

1. O aviso visível para a unidade (`_buscar`, a mesma regra do aviso aberto; arquivado
   continua visível para quem o via). Senão 404 `aviso_nao_encontrado`.
2. O arquivo é anexo de **alguma** versão deste aviso (a versão antiga também abre). Senão o
   mesmo 404, mesmo para a gestão: não diz se o arquivo existe.
3. `arquivos.link_do_arquivo(bucket, arquivo, baixar=baixar)`: sem bucket, 503
   `arquivos_desligados` (depois das conferências, para não revelar nada a quem não vê).

## 3. Front (`web/src/avisos/`)

### 3.1 Peças novas

| Arquivo | O quê |
|---|---|
| `anexos.ts` | lógica pura: `tamanhoEmTexto` ("320 KB", "2,4 MB"), `ehFoto`, `quantosAnexos` ("1 anexo", "3 anexos"), a fila de anexos do formulário (`ItemAnexo`: `enviando`, `pronto`, `erro`) e `situacaoDosAnexos` (pode publicar? qual a mensagem?) |
| `IconesAnexo.tsx` | clipe, foto, fechar e PDF em SVG de traço único, no estilo do `Icone` (o `Icone` é da casca, comum; dúvida 2) |
| `EscolherAnexos.tsx` | o campo "Fotos ou PDF, se tiver" do formulário |
| `AnexosDoAviso.tsx` | os anexos no aviso aberto, na prévia e na versão antiga; o visualizador da foto |
| `anexos.css` | estilos próprios, só com os tokens de `estilo.css` |

### 3.2 Formulário (novo e corrigir)

- Depois do texto, antes de "Para quem" (onde o protótipo põe "Anexo, se tiver"): rótulo
  **"Fotos ou PDF, se tiver"**, ajuda "Até 5 arquivos, de até 10 MB cada. Fotos grandes são
  reduzidas antes de enviar.", e o botão **"Anexar foto ou PDF"** (um `<label>` de 48 px que
  aciona o `<input type="file" multiple accept=…>` escondido visualmente, mas focável).
- Escolheu: cada arquivo entra na lista na hora e é enviado (`enviarArquivo(arquivo, 'aviso')`),
  um de cada vez, na ordem escolhida. Cada linha: miniatura (foto: `URL.createObjectURL`, que a
  CSP permite com `blob:`; PDF: ícone), nome, situação e o botão **"Tirar"** (44 px).
  - `enviando`: "Enviando…" com uma barra animada (o `enviarArquivo` não informa o progresso;
    dúvida 3); `aria-live` anuncia.
  - `pronto`: "PDF, 320 KB" / "Foto, 1,2 MB" (tamanho **real**, o devolvido pela API).
  - `erro`: a mensagem do `ErroDaApi` (já na voz do morador) e **"Enviar de novo"**, só
    quando tentar de novo pode dar certo (rede, bucket fora do ar); arquivo recusado (422: não
    é PDF nem foto, ou grande demais) fica só com "Tirar".
- Escolher mais que as vagas: entram os primeiros até 5, e a caixa diz "Até 5 anexos por aviso.
  Ficaram de fora: <nomes>.". Com 5, o botão some e fica "Já são 5 anexos, o máximo.".
- **Tirar** antes de publicar só tira da lista (o arquivo confirmado fica guardado sem aparecer,
  dúvida 7 do contrato). Tirar um que ainda está enviando cancela o uso dele (o envio termina e
  é ignorado).
- **Publicar / Salvar correção** espera: com algum `enviando`, o botão diz "Espere os arquivos
  terminarem de enviar." (caixa de erro, sem enviar); com algum `erro`, "Tire ou envie de novo o
  arquivo que deu erro.". A prévia mostra os anexos prontos (fotos pela miniatura local).
- Corrigir começa com os anexos da versão em vigor (`pronto`, foto pela miniatura do link) e
  manda sempre a lista explícita (`anexos: [ids]`). Erro 422 da API com campo `anexos` aparece
  embaixo do campo.
- A ordem é a da escolha (sem reordenar; dúvida 4).

### 3.3 Aviso aberto

Depois do texto e antes do `<DocumentoDoAviso />` (encaixe do épico A, intacto). As fotos
vêm primeiro, em grade, e os PDFs depois, cada grupo na ordem dos anexos:

- **Fotos**: grade de miniaturas (uma só: largura toda, 16:10; várias: 2 colunas no celular,
  3 no computador, 4:3), `object-fit: cover`. Cada uma é um `<button>` "Ver a foto <nome> em
  tamanho grande". O link é pedido quando a miniatura aparece (a `<img>` precisa dele) e de novo
  se a imagem falhar (o link vale 5 minutos); falhou de novo: "Não deu para mostrar a foto." +
  "Tentar de novo".
- **Visualizador**: camada por cima da tela (`role="dialog"`, `aria-modal`, foco no "Fechar",
  Esc fecha, o foco volta à miniatura), a foto inteira (`object-fit: contain`), o nome e o
  botão "Fechar" de 48 px. Sem gesto de zoom próprio: o do navegador continua valendo.
- **PDFs**: um botão por PDF, como o `.arquivo` do protótipo: ícone, nome sublinhado e "PDF,
  320 KB · abre em outra aba". O toque pede o link e abre numa aba nova. A aba é aberta **antes**
  do pedido (`window.open('', '_blank')`, depois `location` = link), senão o Safari do iPhone
  bloqueia a janela que não nasce do toque; sem aba (bloqueada), abre na mesma. Erro: caixa com
  a mensagem da API embaixo do botão. A CSP não deixa embutir PDF (contrato, seção 8).
- Versões antigas: o mesmo bloco dentro de cada versão em "Ver como era antes".

### 3.4 Mural

`ItemAviso` e `AvisoFixado` (pela `Meta`) ganham, quando `quantidade_anexos > 0`, o clipe com
"1 anexo" / "3 anexos" na linha de detalhes (como o protótipo: "📎 anexo").

## 4. Testes

- API (`api/testes/test_anexos*.py`): publicar com 1 e 5 anexos; 6, repetido, de outra unidade,
  pendente, de documento, já usado em outro aviso; corrigir omitido/nulo/`[]`/lista, só trocar
  anexos é mudança, outro membro da gestão repete os anexos; versão antiga mantém os dela;
  quantidade no mural; link: visível, versão antiga, aviso de outro bloco (404), arquivo de
  outro aviso (404), sem bucket (503), `baixar`; corrida no banco (`arquivo_em_uso`) vira 422.
- Front (Vitest): `anexos.test.ts` (lógica) e `anexos-telas.test.tsx` (formulário com
  `enviarArquivo` falso: enviando/pronto/erro/tirar/limite/bloqueio; aviso aberto com foto e
  PDF; visualizador; mural com o clipe; correção manda a lista).
- Conferência local com Playwright: gestão publicando com foto e PDF, morador abrindo, em
  390 px e 1280 px; prints em `docs/superpowers/prints/m3-anexos/`.
