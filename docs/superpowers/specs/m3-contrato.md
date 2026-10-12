# Spec · M3 Onda 1 · Contrato

| | |
|---|---|
| **Marco** | M3 · Documentos e anexos (`docs/07-roadmap.md`, seção do M3) |
| **Base** | `02-requisitos.md` (RF-10, RF-30 a RF-33, RNF-20, RNF-22), `03-historias.md` (H-12 parte dos anexos, H-17, H-18, H-19), `04-modelo-de-dados.md` (seções 3.2 a 3.4), `05-arquitetura.md` (seções 1, 4 e 6.2), ADR-0004, ADR-0007, ADR-0009, protótipo (telas `#documentos`, `#publicos`, `#novo-documento`, `#aviso/2`, `#novo-aviso`) |
| **Criado em** | 07/10/2026 |
| **Plano** | `docs/superpowers/plans/m3-contrato.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m3.md` |
| **Decisão nova** | [ADR-0011](../../adr/0011-arquivos-protegidos-contra-perda.md) (arquivos protegidos contra perda) |

## 1. Objetivo

Deixar a base do M3 pronta para que **três agentes trabalhem em paralelo**, sem tocar nos
mesmos arquivos nem criar migrações conflitantes:

| Épico | Histórias | Entrega |
|---|---|---|
| **A · Documentos** | H-17 publicar, H-18 consultar (inclusive os públicos na tela de entrada), H-19 nova versão | lista por categoria com busca, documento aberto com "Versões anteriores", formulário "Novo documento" com o envio do arquivo, "Enviar nova versão", arquivar, "Avisar as unidades" (RF-33), link "Ver documentos públicos" na entrada |
| **B · Anexos nos avisos** | H-12 (anexos) | escolher até 5 PDFs ou fotos no formulário do aviso (publicar e corrigir), mostrar os anexos no aviso aberto (foto na própria tela, PDF como botão), marcador de anexo no mural, versão antiga mostra os anexos dela |
| **C · Proteção dos arquivos** | ADR-0011 | cópia diária cifrada de `arquivos/` para o Backblaze B2 no workflow `Backup`, conferência mensal na restauração de teste, passo a passo de restauração no README |

Esta onda **não implementa as histórias** e **não muda nada que o morador vê** (a versão do
`web/package.json` e o `novidades.ts` ficam como estão). Entrega: a migração 0007, a camada de
armazenamento (interface, R2 e falsa), o **envio de arquivo pronto e testado** (pedir URL
assinada, conferir o conteúdo, publicar no bucket), o contrato da API (este documento +
esquemas Pydantic + tipos TypeScript + rotas dos épicos que respondem 501), a configuração por
variável de ambiente, a CSP que deixa o navegador falar com o R2, as verificações do backup e
os pontos de encaixe no front.

## 2. Banco · migração 0007

Mesmo padrão da 0002 a 0006: SQL escrito à mão, roda como `dono`, permissões ao papel `app`
(nome trocável por `-x papel_app=`), funções de trigger com `set search_path = pg_catalog,
public, pg_temp` e nomes qualificados, datas carimbadas pelo banco, `upgrade → downgrade →
upgrade` testado (e o downgrade não deixa função para trás). Arquivo:
`api/migracoes/versions/0007_documentos_e_anexos.py`; modelos em
`api/app/modelos/arquivos.py` e `api/app/modelos/documentos.py`.

Categoria, nível de acesso, tipo e finalidade são `text` com `CHECK` (como a categoria do aviso
na 0004), não `enum` do Postgres: acrescentar um valor depois é trocar um `CHECK`, sem
`ALTER TYPE` fora de transação.

### 2.1 `arquivo` — o que foi enviado (RNF-22)

| Coluna | Regra |
|---|---|
| `id` | PK |
| `chave` | única; 32 caracteres hexadecimais (`^[0-9a-f]{32}$`), gerados pela API (`secrets.token_hex(16)`). O objeto mora em `envios/<chave>` até ser confirmado e em `arquivos/<chave>` depois. **Nunca reaproveitada** (ADR-0011) |
| `nome_original` | 1 a 200 caracteres, sem espaço nas pontas, sem `/`, `\` nem caractere de controle (`arquivo_nome`). Só um rótulo: o objeto nunca usa esse nome |
| `tipo` | `application/pdf`, `image/jpeg`, `image/png`, `image/webp` (`arquivo_tipo`) |
| `finalidade` | `aviso` ou `documento` (`arquivo_finalidade`) |
| `tamanho_bytes` | de 1 a 20 MB (20.971.520), e até 10 MB (10.485.760) quando `finalidade = 'aviso'` (`arquivo_tamanho`) |
| `enviado_por` / `enviado_em` | FK `unidade` / carimbada pelo banco |
| `confirmado_em` | nulo = **pendente** (URL de envio dada, conteúdo ainda não conferido); preenchido (pelo banco) quando a API conferiu o conteúdo e publicou em `arquivos/` |

- **Pendente** pode ter `tipo` e `tamanho_bytes` corrigidos pela API (o que o servidor achou
  no arquivo de verdade) e pode ser **apagado** (recusado, ou abandonado há mais de 1 dia).
- **Confirmado não muda nem é apagado** (`arquivo_confirmado`): `confirmado_em` não volta a
  nulo, e nenhuma coluna muda depois. O objeto em `arquivos/` está travado no bucket
  (ADR-0011); a linha que aponta para ele também.
- **Até 50 arquivos por unidade a cada 24 horas** (`arquivo_limite_dia`), contando os que ainda
  existem; o trigger trava a unidade (`for no key update`), então envios simultâneos contam uns
  com os outros. Só a gestão envia, e 50 cobre um dia de trabalho folgado.

### 2.2 `documento` (H-17, H-18)

| Coluna | Regra |
|---|---|
| `id` | PK |
| `titulo` | 1 a 120 caracteres (como o título do aviso) |
| `categoria` | `convencao`, `regimento`, `ata`, `contrato`, `obra`, `orientacao`, `outro` (dúvida 3) |
| `data_documento` | `date`, de 1990-01-01 a 2100-12-31: a data **do documento**, não do envio |
| `acesso` | `publico`, `compradores`, `gestao` (RF-31) |
| `criado_por` / `criado_em` | FK `unidade` / carimbada pelo banco |
| `aviso_id` | FK `aviso`, única, nula: o aviso automático de "Avisar as unidades" (RF-33). Gravada só na criação |
| `arquivado_em` | nulo = na lista. Carimbado pelo banco; arquivado não volta (`documento_arquivado`) |

- **Completo no commit** (`documento_completo`, trigger adiado como o do aviso): todo documento
  tem a versão 1.
- Título, categoria, data e acesso **não mudam** (o `app` não tem UPDATE neles). Publicou com o
  nível errado: arquivar e publicar de novo (dúvida 5).
- Aviso automático só para documento `publico` ou `compradores` (`documento_aviso_gestao`): um
  aviso para todos apontando para um documento só da gestão seria um botão que não abre.

### 2.3 `documento_versao` (H-19)

| Coluna | Regra |
|---|---|
| `documento_id` + `versao` | PK; versões em sequência (1, 2, 3…) como `aviso_versao` (`documento_versao_sequencia`). A maior é a atual |
| `arquivo_id` | FK `arquivo`, **única** |
| `enviada_por` / `enviada_em` | FK `unidade` / carimbada pelo banco |

O trigger confere que o arquivo está **confirmado**, é de `finalidade = 'documento'`
(`arquivo_finalidade_errada`) e não está em nenhum aviso (`arquivo_em_uso`); e que o
documento não está arquivado (`documento_arquivado`). Ele trava a linha do arquivo
(`for no key update`), então dois usos simultâneos do mesmo arquivo não passam juntos.

### 2.4 `aviso_anexo` (H-12)

| Coluna | Regra |
|---|---|
| `aviso_id` + `versao` | FK composta para `aviso_versao`: o anexo é **da versão** (modelo, seção 3.3) |
| `arquivo_id` | FK `arquivo` |
| `ordem` | 1 a 5: a ordem em que aparecem; **no máximo 5 anexos por versão** (`aviso_anexo_ordem` + única por versão) |

PK (`aviso_id`, `versao`, `arquivo_id`). O trigger confere: arquivo confirmado, de
`finalidade = 'aviso'`, nunca usado em documento nem em **outro** aviso (`arquivo_em_uso`; a
correção do mesmo aviso repete os anexos da versão anterior, e pode); e a versão foi criada
**nesta mesma transação** (`aviso_anexo_versao_fechada`: `aviso_versao.criada_em = now()`).
Assim uma versão publicada nunca ganha nem perde anexo depois: o que foi publicado fica como
foi (RN-05).

### 2.5 Permissões do `app`

| Tabela | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|
| `arquivo` | sim | sim | só `tipo`, `tamanho_bytes`, `confirmado_em` (e só enquanto pendente: trigger) | sim, **só pendente** (trigger) |
| `documento` | sim | sim | só `arquivado_em` | **não** |
| `documento_versao` | sim | sim | **não** | **não** |
| `aviso_anexo` | sim | sim | **não** | **não** |

## 3. Armazenamento

Arquivo comum: `api/app/servicos/armazenamento.py`. A API **nunca** recebe o conteúdo do
arquivo na requisição (a Vercel recusa corpo acima de 4,5 MB): o navegador envia e baixa
direto do R2, com URL assinada (ADR-0004).

```python
@dataclass(frozen=True)
class UrlAssinada:
    url: str
    expira_em: datetime

@dataclass(frozen=True)
class EnvioRecebido:
    tamanho: int   # o real
    etag: str      # a identidade deste conteúdo

class Armazenamento(Protocol):
    def url_de_envio(self, chave: str, tipo: str, tamanho: int) -> UrlAssinada: ...
        # PUT em envios/<chave>, assinado com o Content-Type e o Content-Length, 10 minutos
    def url_de_leitura(self, chave: str, *, tipo: str, nome: str, baixar: bool) -> UrlAssinada: ...
        # GET em arquivos/<chave>, vale 5 minutos; força Content-Type e Content-Disposition
    def envio_recebido(self, chave: str) -> EnvioRecebido | None: ...  # HEAD; None = não chegou
    def inicio_do_envio(self, chave: str, n: int = 16, *, etag: str) -> bytes: ...
        # GET com Range e If-Match; ETag diferente → EnvioMudou
    def publicar(self, chave: str, tipo: str, *, etag: str) -> None: ...
        # copia envios/<chave> → arquivos/<chave> (com o tipo conferido) só se o envio ainda
        # tem este ETag (CopySourceIfMatch; senão EnvioMudou). Idempotente: arquivos/<chave>
        # já publicado com o mesmo ETag conta como publicado; com outro, ObjetoTravado
    def descartar_envio(self, chave: str) -> None: ...          # apaga envios/<chave>
```

- **A interface só recebe a chave**, nunca o caminho: não existe jeito de apagar nada em
  `arquivos/` por ela (ADR-0011). `ArmazenamentoS3` (boto3, `signature_version="s3v4"`,
  checksums só quando exigidos, como no `scripts/backup/s3.py`) fala com o R2;
  `ArmazenamentoFalso` guarda em memória, imita a trava (publicar por cima de `arquivos/`
  falha) e tem `receber(chave, conteudo, tipo)` para o teste fazer o papel do navegador
  (recusa, como o R2, o PUT de tamanho diferente do assinado) e `gravar_por_fora(...)` para
  simular um objeto que chegou sem passar pela URL assinada.
- **O que é publicado é exatamente o que foi conferido:** o ETag do HEAD vai como `If-Match`
  na leitura do começo e como `CopySourceIfMatch` na cópia. Um 2º PUT na mesma URL no meio da
  conferência (o mesmo tamanho, outro conteúdo) faz a confirmação responder 409
  `arquivo_nao_chegou` e o arquivo continua pendente; confirmar de novo confere o conteúdo que
  estiver lá (dúvida 13). O `moto` ignora o `CopySourceIfMatch`: o teste confere que a cópia o
  pede, e o falso imita a recusa.
- **Erros do bucket:** o `ArmazenamentoS3` traduz os do boto3 em `ObjetoAusente`,
  `EnvioMudou` ou `FalhaNoArmazenamento`; nenhum `ClientError` cru chega à rota. A
  confirmação responde 503 `armazenamento_indisponivel` à `FalhaNoArmazenamento` (o arquivo
  continua pendente) e 409 `arquivo_nao_chegou` ao `ObjetoTravado`.
- **Apagar o envio é faxina:** a API apaga `envios/<chave>` depois do commit (publicado) ou na
  recusa, e uma falha aí só vai para o log; a regra de ciclo de vida do R2 apaga o resto.
- **O tamanho declarado entra na assinatura do PUT** (`ContentLength`): o R2 recusa o envio de
  outro tamanho. Sem isso, a mesma URL aceitaria gigabytes declarando 209 bytes.
- `obter_armazenamento()` é dependência FastAPI: `ArmazenamentoS3` com a configuração da seção
  6, ou `None` (arquivos desligados). Os testes trocam pelo falso
  (`app.dependency_overrides`, fixture `armazenamento` do `conftest.py`). **Nenhum teste fala
  com o R2**; o `ArmazenamentoS3` é testado contra o `moto` (S3 falso, em processo).
- Leitura: `ResponseContentType` = o tipo conferido; `ResponseContentDisposition` =
  `inline` (abrir no celular) ou `attachment` (baixar), com `filename*=UTF-8''…` e um nome
  ASCII de reserva, com a extensão do tipo se faltar; `ResponseCacheControl: private,
  max-age=300`.

## 4. Envio de arquivo (pronto nesta onda)

```
tela                          API                                   R2
 │ comprime (se imagem)        │                                     │
 │ POST /api/arquivos ───────► │ confere papel, tipo e tamanho        │
 │                             │ INSERT arquivo (pendente)            │
 │ ◄──── url de envio (10 min) │                                     │
 │ PUT url (Content-Type) ──────────────────────────────────────────► │ envios/<chave>
 │ POST /api/arquivos/{id}/confirmar ► HEAD + 16 primeiros bytes ───► │
 │                             │ tamanho e assinatura batem?          │
 │                             │   outro tamanho que o declarado, ou o ETag mudou → 409
 │                             │   não → apaga o envio, apaga a linha, histórico, 422
 │                             │   sim → copia para arquivos/<chave>, apaga o envio,
 │ ◄──── ArquivoEnviado        │         confirmado_em = now()        │
 │ (usa o id no documento ou no aviso)                                │
```

- **Tipos aceitos:** PDF, JPEG, PNG, WEBP (ADR-0004). **Limites:** 10 MB por anexo de aviso
  (H-12), 20 MB por documento (H-17). Conferidos quatro vezes: na tela (antes de mandar), no
  pedido (o tamanho declarado), no PUT (o R2 só aceita o tamanho declarado, que está na
  assinatura) e na confirmação (o tamanho **real**, pelo HEAD).
- **Conteúdo conferido pelo servidor, depois do envio:** os primeiros bytes do objeto têm de
  ser a assinatura de um dos quatro tipos (`app/servicos/arquivos.py`, `tipo_pelo_conteudo`):
  PDF `%PDF-`; JPEG `FF D8 FF`; PNG `89 50 4E 47 0D 0A 1A 0A`; WEBP `RIFF` + 4 bytes +
  `WEBP`. **Um `.exe` renomeado para `.pdf` é recusado e apagado** (critério do roadmap): 422
  `arquivo_recusado`, o objeto sai de `envios/`, a linha sai do banco e o histórico ganha
  `arquivo_recusado` `{"motivo": "conteudo" | "tamanho", "tipo_declarado", "tipo_encontrado",
  "tamanho_bytes"}` (sem o nome do arquivo, que pode ter nome de gente).
- **Tamanho real diferente do declarado** (só acontece se o objeto chegou por fora da URL
  assinada, que tem o tamanho): 409 `arquivo_nao_chegou`, continua pendente. Acima do limite
  continua sendo 422 `arquivo_recusado` (o limite é conferido antes).
- Assinatura de **outro tipo aceito** (uma foto PNG com nome `.jpg`): aceita, e o `tipo` passa
  a ser o encontrado (dúvida 6). O navegador escolhe o tipo pela extensão; quem paga o erro da
  extensão não pode ser a Dona Socorro.
- **Só quem pediu confirma** (outra unidade: 404 igual a inexistente). Confirmar de novo um
  arquivo já confirmado devolve o mesmo resultado (idempotente). Pendente há mais de 1 dia é
  apagado na hora de qualquer pedido novo; o objeto dele some sozinho pela regra de ciclo de
  vida do R2 (ADR-0011).
- **Arquivo confirmado e nunca usado** (a pessoa desistiu do formulário) fica no banco e no
  bucket (travado). É pouco e não aparece para ninguém; aceito (dúvida 7).
- **Compressão no navegador** (`web/src/arquivos/comprimir.ts`, ADR-0004): imagem com o lado
  maior acima de 1920 px é reduzida para 1920 px e regravada em WEBP (qualidade 0,82; se o
  navegador não grava WEBP, JPEG 0,85); se o resultado ficar maior que o original, vai o
  original. PDF vai como está. A compressão acontece **antes** do pedido (o tamanho declarado
  já é o comprimido) e troca a extensão do nome (`foto.jpg` → `foto.webp`).

## 5. Contrato da API

Convenções do M1 (spec do M1, seção 4): JSON em `snake_case`, datas ISO 8601 em UTC (a
`data_documento` é `AAAA-MM-DD`), erros `{ "codigo", "mensagem" }`, toda alteração exige
`X-Portal: 1`. Esquemas Pydantic e espelhos TypeScript conferidos pelo
`api/testes/test_contrato.py`:

| Python | TypeScript | Dono |
|---|---|---|
| `app/esquemas/arquivos.py` | `web/src/arquivos/tipos.ts` | comum (pronto) |
| `app/esquemas/documentos.py` | `web/src/documentos/tipos.ts` | épico A |
| `app/esquemas/avisos.py` (campos novos da seção 5.3) | `web/src/avisos/tipos.ts` | épico B |

As rotas dos épicos respondem **501 `em_construcao`**, mas sessão, permissão, CSRF e validação
do corpo já são as de verdade. O que vale antes e depois dos épicos fica em
`api/testes/test_m3_rotas.py`; os testes de 501 ficam em `api/testes/test_m3_em_construcao.py`
(o épico troca o corpo da função e apaga a própria seção de lá).

### 5.1 Comum · Envio de arquivo (`app/rotas/arquivos.py`, pronto)

| Rota | Quem | Corpo | Resposta | Erros |
|---|---|---|---|---|
| `POST /api/arquivos` | `Gestao` | `PedirEnvio` | 201 `EnvioAutorizado` | 422, 409 `muitos_arquivos`, 503 `arquivos_desligados`, 401, 403 |
| `POST /api/arquivos/{arquivo_id}/confirmar` | `Gestao` | — | 200 `ArquivoEnviado` | 404 `arquivo_nao_encontrado`, 409 `arquivo_nao_chegou`, 422 `arquivo_recusado`, 503 `arquivos_desligados` ou `armazenamento_indisponivel`, 401, 403 |

- `PedirEnvio`: `nome` (o nome do arquivo no aparelho; sem controle nem caracteres de direção),
  `tipo` (`TipoArquivo`), `tamanho_bytes` (≥ 1), `finalidade` (`Finalidade`). Mensagens: "O
  Portal aceita PDF e fotos (JPEG, PNG ou WEBP)."; "O arquivo pode ter até 10 MB." (aviso) ou
  "até 20 MB." (documento).
- `EnvioAutorizado`: `arquivo_id`, `url`, `content_type` (o envio é sempre `PUT`; mandar
  exatamente este `Content-Type` no PUT, ou o R2 recusa a assinatura), `expira_em`.
- `ArquivoEnviado`: `id`, `nome`, `tipo`, `tamanho_bytes` (o real). É também como o arquivo
  aparece no documento e no aviso.
- Mensagens dos erros: `arquivo_nao_chegou` "O arquivo não chegou ao Portal. Confira a internet
  e envie de novo."; `arquivo_recusado` "Este arquivo não é um PDF nem uma foto (JPEG, PNG ou
  WEBP). Escolha outro." (conteúdo) ou a do limite (tamanho); `muitos_arquivos` "Muitos
  arquivos enviados hoje. Tente de novo amanhã."; `arquivos_desligados` "O envio de arquivos
  ainda não está ligado no Portal."; `armazenamento_indisponivel` "Não deu para guardar o
  arquivo agora. Tente de novo em alguns minutos.".

### 5.2 Épico A · Documentos (`app/rotas/documentos.py`)

| Rota | Quem | Corpo | Resposta | Erros |
|---|---|---|---|---|
| `GET /api/documentos?arquivados=` | `UnidadeLogada` | — | 200 `ListaDocumentos` | 401, 403 |
| `GET /api/documentos/publicos` | ninguém (sem sessão) | — | 200 `ListaDocumentos` | — |
| `GET /api/documentos/{documento_id}` | `UnidadeLogada` | — | 200 `Documento` | 404 `documento_nao_encontrado` |
| `POST /api/documentos` | `Gestao` | `NovoDocumento` | 201 `Documento` | 422, 409 `arquivo_em_uso` |
| `POST /api/documentos/{documento_id}/versoes` | `Gestao` | `NovaVersaoDocumento` | 201 `Documento` | 404, 409 `documento_arquivado`, 409 `arquivo_em_uso`, 422 |
| `POST /api/documentos/{documento_id}/arquivar` | `Gestao` | — | 200 `Documento` | 404 |
| `GET /api/documentos/{documento_id}/versoes/{versao}/link?baixar=` | sessão opcional | — | 200 `LinkDoArquivo` | 404 `documento_nao_encontrado`, 503 |

- **Quem vê o quê** (`app/servicos/visibilidade.py`, `niveis_que_ve(logado)`, pronto): sem
  sessão (ou com a sessão restrita do primeiro acesso), só `publico`; unidade comum, `publico`
  e `compradores`; gestão, os três. Arquivado: só a gestão (em `?arquivados=true`). Fora
  disso, **404 igual a documento inexistente**, na lista, no documento e no link: "documento de
  nível gestão não aparece nem baixa por link direto para conta comum" (critério do roadmap,
  testado pelo épico).
- `NovoDocumento`: `titulo`, `categoria` (`CategoriaDocumento`), `data_documento`, `acesso`
  (`NivelAcesso`), `arquivo_id`, `avisar_unidades` (padrão falso; com `acesso = gestao`: 422 "Só
  dá para avisar as unidades de documento que elas podem ver."). O arquivo precisa ser
  confirmado, de finalidade `documento` e **enviado pela própria unidade** (senão 422 "Envie o
  arquivo de novo."). `NovaVersaoDocumento`: `arquivo_id`, mesma regra.
- "Avisar as unidades" (RF-33): na **mesma transação**,
  `app.servicos.avisos.gravar_publicacao` (o `publicar` sem o commit, separado nesta onda)
  com um aviso para todos (título "Documento novo: <título>", categoria `geral`, texto curto
  dizendo onde achar), e `documento.aviso_id` aponta para ele; a rota chama
  `notificacoes.agendar` depois do commit, como a de avisos. Documento e aviso nascem juntos
  ou nenhum dos dois. O aviso aberto mostra o botão para o
  documento pelo campo `documento` (seção 5.3), já preenchido nesta onda.
- `DocumentoResumo`: `id`, `titulo`, `categoria`, `data_documento`, `acesso`, `versao` (a
  atual), `atualizado_em` (envio da versão atual), `arquivo` (`ArquivoEnviado` da versão
  atual), `arquivado_em`. `Documento` = resumo + `versoes_anteriores: VersaoDocumento[]` (da
  mais nova para a mais antiga, sem a atual) + `aviso_id`. `VersaoDocumento`: `versao`,
  `enviada_em`, `arquivo`. `ListaDocumentos`: `itens`, na ordem `data_documento` desc, depois
  `id` desc (a tela agrupa por categoria e busca pelo título, como o protótipo).
- `LinkDoArquivo`: `url`, `expira_em` (5 minutos). A tela abre a `url` (nova aba) ou baixa
  (`baixar=true`). O link é pedido **na hora do toque**, nunca guardado.
- Histórico (`Acao`, já criadas): `documento_publicado` (entidade `documento`, `{"versao": 1,
  "acesso", "categoria", "avisou": bool}`), `documento_versao_enviada` (`{"versao": n}`),
  `documento_arquivado`. As frases do histórico já existem em
  `web/src/administracao/frases.ts`.

### 5.3 Épico B · Anexos nos avisos (`app/rotas/avisos.py`, `app/servicos/avisos.py`)

Campos novos (já no contrato; preenchidos pelo épico B, menos `documento`):

| Esquema | Campo | Nesta onda |
|---|---|---|
| `CorrigirAviso` | `anexos: list[int] \| None = None` — os anexos da versão nova, na ordem; **omitido = repete os da versão em vigor**; `[]` tira todos | só `None`/`[]`; com ids: 501 |
| `NovoAviso` | herda `anexos`: omitido, nulo ou `[]` é sem anexo | só sem anexo; com ids: 501 |
| `AvisoResumo` | `quantidade_anexos: int` (o clipe no mural) | `0` |
| `AvisoCompleto` | `anexos: list[ArquivoEnviado]` (da versão em vigor, na ordem) | `[]` |
| `VersaoAviso` | `anexos: list[ArquivoEnviado]` | `[]` |
| `AvisoCompleto` | `documento: DocumentoDoAviso \| None` (`id`, `titulo`): o documento que gerou este aviso (RF-33), se a unidade pode vê-lo e ele não está arquivado | **pronto** |

| Rota | Quem | Resposta | Erros |
|---|---|---|---|
| `GET /api/avisos/{aviso_id}/anexos/{arquivo_id}/link?baixar=` | `UnidadeLogada` | 200 `LinkDoArquivo` | 404 `aviso_nao_encontrado` (aviso que a unidade não vê, ou arquivo que não é anexo de nenhuma versão dele), 503 |

- Regras do épico: no máximo 5 anexos, sem repetir (422 "Até 5 anexos por aviso." e "O mesmo
  arquivo foi escolhido duas vezes."); cada id é um arquivo confirmado, de finalidade `aviso`,
  enviado pela própria unidade **ou** já anexo de uma versão deste aviso (a correção feita por
  outro membro da gestão repete os anexos); senão 422 "Envie o arquivo de novo.". As
  restrições do banco (`arquivo_em_uso`, `aviso_anexo_versao_fechada`) são a última linha.
- O link de um anexo de versão antiga também abre (o "ver como era antes" mostra os anexos
  daquela versão).
- Foto: a tela mostra com `<img>` usando o link (CSP, seção 8); PDF: botão com o nome e o
  tamanho, que pede o link e abre.

### 5.4 Erros e o 503

Sem configuração de arquivos (seção 6), toda rota que gera URL responde **503
`arquivos_desligados`**: a lista de documentos e os avisos funcionam igual, só não abrem nem
enviam arquivo. É o mesmo princípio do M2: o Portal sobe antes de o bucket existir.

## 6. Configuração (variáveis de ambiente)

| Variável | Para quê | Sem ela |
|---|---|---|
| `PORTAL_ARQUIVOS_ENDPOINT` | `https://<conta>.r2.cloudflarestorage.com` (ou `http://127.0.0.1:<porta>` de um S3 falso em desenvolvimento) | arquivos desligados |
| `PORTAL_ARQUIVOS_BUCKET` | o bucket **de arquivos** (`portal-capibaribe-arquivos`) | arquivos desligados |
| `PORTAL_ARQUIVOS_CHAVE_ID`, `PORTAL_ARQUIVOS_CHAVE_SECRETA` | a chave S3 **própria** da API, "Object Read & Write" **só** desse bucket | arquivos desligados |
| `PORTAL_ARQUIVOS_REGIAO` | opcional; padrão `auto` (o R2 aceita só isso) | padrão |

- `config_arquivos() -> ConfigArquivos | None` em `app/configuracao.py`. **Nunca o bucket de
  backups:** nome com `backup` desliga os arquivos com aviso no log (a chave da API não pode
  enxergar os backups, ADR-0009). Endereço fora de `https://` (ou da máquina local) também.
- Nada de `R2_*`: esses nomes são do workflow de backup, com outra chave e outro bucket.
- Segredo com `field(repr=False)`; aviso no log nunca mostra valor; exemplo comentado em
  `api/.env.example`. A prévia da Vercel fica sem estas variáveis (arquivos desligados), como
  ficou sem SMTP no M2.

## 7. Front

| Pasta / arquivo | Dono | Nesta onda |
|---|---|---|
| `web/src/arquivos/` (`tipos.ts`, `api.ts`, `limites.ts`, `comprimir.ts`, `enviar.ts`) | comum | **pronto**: `enviarArquivo(arquivo, finalidade)` faz conferir na tela → comprimir → pedir → PUT no R2 → confirmar, e devolve `ArquivoEnviado` (ou lança `ErroDaApi` com a mensagem pronta) |
| `web/src/documentos/` (`tipos.ts`, `api.ts`, `rotas.tsx`, `menu.ts`, `LinkDocumentosPublicos.tsx`, `DocumentoDoAviso.tsx`) | épico A | tipos, funções de API, `rotasDocumentos = []`, encaixes que não mostram nada |
| `web/src/avisos/**` | épico B | tipos com os campos novos; o resto é do épico |

`enviarArquivo` faz o PUT com `fetch` direto para a URL assinada: **sem** `X-Portal`, **sem**
cookie (`credentials: 'omit'`) e com o `Content-Type` devolvido pela API. Erro do R2 ou da rede
no PUT vira `ErroDaApi` `arquivo_nao_chegou`.

Pontos de encaixe já ligados (o épico troca só o corpo, do lado dele):

| Onde | Chama | Épico |
|---|---|---|
| `web/src/rotas.tsx` | `...rotasDocumentos` | A |
| `web/src/casca/menu.ts` | `itemDocumentos()` de `documentos/menu.ts` (hoje `null`: sem item no menu) | A |
| `web/src/acesso/Entrar.tsx` | `<LinkDocumentosPublicos />` depois do "Esqueci minha senha" (hoje `null`) | A |
| `web/src/avisos/AvisoAberto.tsx` | `<DocumentoDoAviso documento={aviso.documento} />` depois do corpo do aviso (hoje `null`) | A |
| `web/src/administracao/frases.ts` | frases de `documento_publicado`, `documento_versao_enviada`, `documento_arquivado`, `arquivo_recusado` (prontas) | comum |

Teste dos encaixes e das funções de API: `web/src/m3contrato.test.ts`; do envio:
`web/src/arquivos/arquivos.test.ts`.

## 8. CSP (`vercel.json`)

Antes: `default-src 'self'` cobria tudo. Com o navegador falando direto com o R2:

- `connect-src 'self' https://*.r2.cloudflarestorage.com`: o PUT do envio.
- `img-src 'self' blob: https://*.r2.cloudflarestorage.com`: a foto do anexo (URL assinada) e a
  prévia da foto escolhida antes de enviar (`URL.createObjectURL`).

Nada mais muda (`default-src 'self'` continua sendo o recuo do resto, e o service worker e o
manifest do M2 seguem valendo). Abrir um PDF é navegação (nova aba), que a CSP não restringe.
O curinga `*.r2.cloudflarestorage.com` evita pôr o número da conta da Cloudflare no
repositório público; o máximo que ele libera é falar com algum bucket R2, o que um script
injetado já conseguiria navegando (dúvida 8). O teste `web/testes/cabecalhos.test.ts` confere
que **só** esse endereço de terceiros aparece, e só nessas duas diretivas.

## 9. Proteção dos arquivos (épico C, ADR-0011)

Fora do código da API. O épico C edita só: `scripts/backup/**` (novo
`scripts/backup/arquivos.py` ou comando novo no `s3.py`; o teste local
`scripts/backup/testes/testar-ciclo.sh` ganha a cópia com dois S3 falsos), o
`.github/workflows/backup.yml`, a seção "Backup" do `README.md` e
`docs/superpowers/duvidas-m3-protecao.md`.

1. **Copiar** (todo dia, depois do `pg_dump`): listar `arquivos/` do bucket de arquivos (chave só
   de leitura, segredos `ARQUIVOS_R2_ENDPOINT`, `ARQUIVOS_R2_ACCESS_KEY_ID`,
   `ARQUIVOS_R2_SECRET_ACCESS_KEY`, `ARQUIVOS_R2_BUCKET`), listar `arquivos/` da cópia (segredos
   `COPIA_S3_ENDPOINT`, `COPIA_S3_ACCESS_KEY_ID`, `COPIA_S3_SECRET_ACCESS_KEY`,
   `COPIA_S3_BUCKET`), e para cada chave que falta: baixar, `age -R destinatarios.age`, enviar
   `arquivos/<chave>.age`. Nunca apagar nada na cópia. Sem os segredos da cópia: o passo avisa
   e não falha o backup do banco (o banco é mais importante que a cópia de hoje).
2. **Conferir** (na restauração de teste do dia 2): toda `arquivo.chave` com `confirmado_em`
   no banco restaurado tem `arquivos/<chave>.age` na cópia; um deles, ao acaso, é baixado,
   decifrado com `BACKUP_AGE_KEY` e tem a assinatura de PDF/JPEG/PNG/WEBP. Faltou: falha.
3. **Restaurar** (README): decifrar a cópia inteira para um bucket novo em `arquivos/`, trocar
   `PORTAL_ARQUIVOS_*` na Vercel. Script próprio, testado no `testar-ciclo.sh`.

## 10. Posse dos arquivos

**Épico A · Documentos** edita só: `api/app/rotas/documentos.py`,
`api/app/esquemas/documentos.py`, `api/app/servicos/documentos.py` (novo),
`api/testes/test_documentos*.py` (novos), `web/src/documentos/**`,
`docs/superpowers/duvidas-m3-documentos.md` (novo). Nos testes comuns, só: apagar a seção "épico
A" de `api/testes/test_m3_em_construcao.py` e tirar as rotas `/api/documentos…` de
`EM_CONSTRUCAO` em `api/testes/test_cache.py`.

**Épico B · Anexos** edita só: `api/app/rotas/avisos.py`, `api/app/esquemas/avisos.py`,
`api/app/servicos/avisos.py` (mantendo o campo `documento` como está),
`api/testes/test_avisos*.py` e `api/testes/test_anexos*.py` (novos), `web/src/avisos/**`
(mantendo o encaixe `<DocumentoDoAviso />`), `docs/superpowers/duvidas-m3-anexos.md` (novo). Nos
testes comuns, só: apagar a seção "épico B" de `api/testes/test_m3_em_construcao.py` e tirar a
rota do link do anexo de `EM_CONSTRUCAO` em `api/testes/test_cache.py`.

**Épico C · Proteção** edita só o que está na seção 9.

**Comuns — nenhum épico edita** (se precisar, avisa o coordenador e explica no arquivo de
dúvidas do épico): `api/migracoes/**` (**nenhuma migração nova no M3 sem o coordenador**),
`api/app/modelos/**`, `api/app/configuracao.py`,
`api/app/servicos/{armazenamento,arquivos,visibilidade,historico,notificacoes}.py`,
`api/app/rotas/arquivos.py`, `api/app/esquemas/{arquivos,comum}.py`, `api/app/seguranca/**`,
`api/app/main.py`, `api/app/erros_api.py`, `api/testes/{conftest,apoio}.py` e os testes já
existentes (inclusive `test_m3_rotas.py`, `test_m3_banco.py`, `test_m3_arquivos.py`,
`test_m3_armazenamento.py`; as únicas exceções são as dos parágrafos acima),
`api/pyproject.toml`, `api/uv.lock` (o `boto3` e o `moto` já estão), `api/.env.example`,
`web/src/arquivos/**`, `web/src/{main.tsx,rotas.tsx,estilo.css}`,
`web/src/{api,casca,acesso,administracao,notificacoes,recuperacao}/**`, `web/package*.json`,
`vercel.json`, `docs/0*.md`, `docs/adr/**`, este spec. A versão do `web/package.json` e o
`web/src/sobre/novidades.ts` mudam só no fechamento do marco (coordenador). Um épico **pode**
criar um CSS próprio (`web/src/<pasta do épico>/<nome>.css`).

Usar sem editar: `obter_armazenamento`, `ArmazenamentoFalso` (testes), `niveis_que_ve`,
`arquivo_utilizavel` (`app/servicos/arquivos.py`: o arquivo existe, está confirmado, tem a
finalidade certa e foi enviado pela unidade), `link_do_arquivo` (`app/servicos/arquivos.py`:
o `LinkDoArquivo` de um arquivo confirmado), `registrar` (histórico), `gravar_publicacao` e
`agendar` (avisos e notificações, épico A), `enviarArquivo` e `LIMITES` (`web/src/arquivos/`), `Tela`,
`Icone`, `useSessao`, `useRecado` (casca).

Mudança no contrato (campo novo, rota nova) dentro do próprio épico é permitida nos arquivos do
épico, desde que `test_contrato.py` continue verde e a mudança fique registrada no arquivo de
dúvidas do épico. Banco de teste próprio: `PORTAL_TESTE_BANCO=portal_teste_m3_documentos` e
`portal_teste_m3_anexos`.

## 11. Fica de fora desta onda

Implementação das histórias; criar o bucket de arquivos, a chave, o CORS, a trava e a regra de
ciclo de vida no R2; a conta e o bucket do B2; variáveis na Vercel e segredos no GitHub;
migração no Neon (produção e `previa`); qualquer execução na Vercel, no Neon ou no R2.
