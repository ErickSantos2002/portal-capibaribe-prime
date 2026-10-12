# Dúvidas e decisões do M3 · Onda 1 (contrato)

Decisões tomadas sem perguntar a ninguém durante a onda do contrato do M3. Cada item: a dúvida,
o que foi decidido e por quê. **[Erick]** marca o que só o Erick pode confirmar ou fazer (regra
do condomínio, custo, conta, preferência dele); o resto é decisão técnica que pode ser revista na
revisão do marco.

Os agentes dos épicos registram as próprias dúvidas em `duvidas-m3-documentos.md` (épico A),
`duvidas-m3-anexos.md` (épico B) e `duvidas-m3-protecao.md` (épico C).

A seção **"Passo a passo do Erick"** no fim reúne tudo o que precisa ser feito à mão (R2,
Backblaze B2, GitHub, Vercel) antes do primeiro documento real.

## 1. Arquivos protegidos contra perda: trava no R2 e cópia no Backblaze B2 **[Erick]**
- **Dúvida:** o roadmap pede decidir a proteção dos arquivos antes do primeiro documento real;
  o backup do banco não cobre o R2.
- **Decisão:** [ADR-0011](../adr/0011-arquivos-protegidos-contra-perda.md): trava do R2 em
  `arquivos/` (retenção indefinida), envio em `envios/` com ciclo de vida de 1 dia, e cópia
  diária cifrada com `age` num bucket privado do Backblaze B2 (épico C).
- **Por quê:** a trava sozinha não cobre perder a conta da Cloudflare; uma cópia no bucket de
  backups ficaria na mesma conta. O B2 é outra empresa, fala S3 (o mesmo `boto3`) e tem 10 GB
  grátis.
- **Custo zero, conferido em 12/10/2026:** a página de cadastro do B2
  (`backblaze.com/sign-up/cloud-storage`) diz "No credit card required", e a de preços
  (`backblaze.com/cloud-storage/pricing`) diz "First 10GB storage is always free". Guias de
  terceiros divergem sobre o cartão, então **confira na hora de criar a conta: se o cadastro
  pedir cartão, pare** e use o plano B da ADR-0011 (a cópia na pasta `arquivos/` do bucket de
  backups, só trocando variáveis). Acima de 10 GB o B2 cobra; o volume esperado é de 1 a 3 GB
  em 2 anos.

## 2. Rotas dos épicos já existem, respondendo 501
- **Dúvida:** como deixar três agentes trabalharem em paralelo sem brigar pelo `main.py` e pelo
  contrato.
- **Decisão:** todas as rotas do M3 já estão declaradas, com sessão, permissão, CSRF e
  validação do corpo de verdade, e só o corpo da função responde `501 em_construcao`. O épico
  troca o corpo e apaga a própria seção de `api/testes/test_m3_em_construcao.py`.
- **Por quê:** o que vale antes e depois dos épicos (quem pode chamar o quê) fica testado
  desde já em `test_m3_rotas.py`, e nenhum épico edita arquivo comum.

## 3. Categoria nova: "Orientação" **[Erick]**
- **Dúvida:** o modelo de dados tinha `convencao`, `regimento`, `ata`, `contrato`, `obra` e
  `outro`; o protótipo tem documentos como "Orientações para a vistoria", que não cabem em
  nenhuma.
- **Decisão:** `orientacao` entra na lista. Categoria é `text` com `CHECK`, então acrescentar
  outra depois é uma migração pequena.
- **Confirmar:** se a lista de categorias é a que a Comissão usaria.

## 4. Só a gestão envia arquivo, até 50 por dia por unidade
- **Decisão:** `POST /api/arquivos` é só da gestão (Comissão e administração); a unidade comum
  recebe 403. No banco, até 50 arquivos por unidade a cada 24 horas.
- **Por quê:** na E1 só a gestão publica avisos e documentos. 50 cobre um dia de trabalho
  folgado (uma ata com 5 fotos é 6 envios) e segura um bug ou uma conta tomada que tentasse
  encher o bucket de 10 GB.

## 5. Título, categoria, data e acesso de documento não mudam **[Erick]**
- **Dúvida:** H-19 fala de nova versão do arquivo; não fala de corrigir o título ou o nível.
- **Decisão:** o papel `app` não tem UPDATE nessas colunas. Publicou com o nível errado:
  arquivar e publicar de novo.
- **Por quê:** o nível decide quem vê; trocar o nível de um documento já publicado mudaria em
  silêncio quem já viu o quê. Arquivar deixa rastro no histórico.
- **Confirmar:** se a Comissão precisa corrigir título sem arquivar; se sim, é uma rota nova
  (e uma linha de permissão) no épico A.

## 6. Foto PNG com nome `.jpg`: aceita, com o tipo de verdade
- **Decisão:** se os primeiros bytes são de outro tipo aceito, o arquivo é aceito e o `tipo`
  passa a ser o encontrado (o link de leitura usa esse tipo).
- **Por quê:** o celular escolhe o tipo pela extensão; quem erra a extensão não é quem envia, e
  o conteúdo é um tipo permitido. Recusar só faria a Comissão tentar de novo sem entender.

## 7. Arquivo enviado e nunca usado fica guardado
- **Dúvida:** a pessoa envia o arquivo e desiste do formulário.
- **Decisão:** o arquivo confirmado fica no banco e no bucket (travado), sem aparecer para
  ninguém. Só o pendente (nunca conferido) é apagado depois de 1 dia.
- **Por quê:** apagar exigiria tirar a trava do bucket, que é justamente o que a ADR-0011 não
  quer que o Portal consiga. O volume é pequeno. Se um dia for preciso apagar (LGPD), é o
  caminho manual da ADR-0011.

## 8. CSP com curinga `https://*.r2.cloudflarestorage.com`
- **Dúvida:** o endereço exato do bucket tem o número da conta da Cloudflare.
- **Decisão:** o curinga, só em `connect-src` e `img-src` (o teste de cabeçalhos garante que é
  o único endereço de terceiros e que não aparece em outra diretiva).
- **Por quê:** o repositório é público; o número da conta não precisa estar nele. O máximo que
  o curinga libera é um script injetado falar com algum bucket R2, o que ele já conseguiria
  navegando para lá. A CSP continua bloqueando script e estilo de fora.

## 9. Foto pequena vai com os metadados do celular **[Erick]**
- **Dúvida:** a compressão (seção 4 da spec) regrava em WEBP só a foto com o lado maior acima
  de 1920 px. Regravar descarta os metadados (EXIF), inclusive a localização do GPS; a foto
  menor vai como saiu do celular.
- **Decisão:** mantida como na spec. A maioria das fotos de celular passa de 1920 px e é
  regravada; print de tela e foto já reduzida pelo WhatsApp normalmente não têm GPS.
- **Por quê:** regravar toda foto pequena também troca o formato e pode aumentar o arquivo
  (PNG de print com texto fica pior em WEBP com perda).
- **Confirmar:** se prefere que toda foto seja regravada, para nunca levar localização. É uma
  linha em `web/src/arquivos/comprimir.ts` (o teste "foto pequena vai como está" muda junto).

## 10. Recusa na tela vira `ErroDaApi` `dados_invalidos`, campo `arquivo`
- **Decisão:** `enviarArquivo` recusa tipo fora da lista, arquivo vazio e tamanho acima do
  limite **antes** de chamar a API, com a mesma mensagem que a API daria, como `ErroDaApi(422,
  dados_invalidos)` apontando o campo `arquivo`. Falha do `PUT` (rede ou R2) vira
  `arquivo_nao_chegou`.
- **Por quê:** a tela trata todo erro do envio do mesmo jeito (`erro.mensagem`, ou
  `erro.doCampo('arquivo')` ao lado do botão). O tamanho é conferido **depois** de comprimir:
  uma foto de 30 MB que vira 2 MB passa.
- Os números e as mensagens da tela são conferidos contra os da API em
  `api/testes/test_contrato.py` (`test_limites_do_envio_iguais_na_tela_e_na_api`).

## 11. `EnvioAutorizado` sem o campo `metodo`
- **Dúvida:** a seção 5.1 da spec listava `metodo` (`"PUT"`) na resposta; o esquema e o tipo
  TS feitos na Tarefa 4 não têm o campo.
- **Decisão:** sem o campo; a spec foi corrigida. O envio é sempre `PUT` (é o que a URL assinada
  permite), então o campo só repetiria uma constante.

## 12. Teste do mural não conhecia `quantidade_anexos`
- O commit da Tarefa 5 acrescentou o campo ao `AvisoResumo`, mas
  `api/testes/test_avisos_mural.py::test_item_do_mural` compara o item inteiro e ficou vermelho
  (a Tarefa 5 tinha rodado só os testes das áreas mudadas). Corrigido na retomada, com a suíte
  inteira verde.

## 13. Conteúdo trocado no meio da conferência: 409, não 422
- **Dúvida (revisão do contrato):** entre o HEAD, a leitura dos 16 bytes e a cópia, um 2º PUT
  na mesma URL (válida por 10 minutos) trocava o conteúdo publicado: um `.exe` de 25 MB saía
  como o PDF de 209 bytes conferido.
- **Decisão:** o ETag do HEAD vai como `If-Match` na leitura e como `CopySourceIfMatch` na
  cópia. ETag diferente responde 409 `arquivo_nao_chegou` ("envie de novo") e o arquivo
  continua pendente, sem apagar o envio nem registrar recusa. Tamanho real diferente do
  declarado (com o `Content-Length` na assinatura, só por fora da URL) recebe o mesmo 409.
- **Por quê:** não dá para saber o que estava certo, só que o objeto mudou; a próxima
  confirmação confere tudo de novo, atomicamente, contra o que estiver lá (um `.exe` aí é
  recusado normalmente). Quem usa a tela nunca faz dois PUTs; não vale um motivo novo no
  histórico nem uma frase nova para algo que só um ataque provoca.

---

## Passo a passo do Erick (antes do primeiro documento real) **[Erick]**

Nada disto foi feito pelos agentes (spec, seção 11). Ordem sugerida; cada passo pode ser
conferido antes do próximo. As chaves vão **só** para a Vercel e o GitHub, nunca para o
repositório nem para o chat.

### A. Cloudflare R2: o bucket de arquivos
1. **Criar o bucket** `portal-capibaribe-arquivos` (R2 → Create bucket), privado (sem domínio
   público, sem `r2.dev`). Nunca usar o `portal-capibaribe-backups` para isso: a API desliga os
   arquivos se o nome tiver "backup".
2. **Chave da API** (R2 → Manage API tokens → Create API token): permissão **Object Read &
   Write**, aplicada **só** ao bucket `portal-capibaribe-arquivos`. Guardar o Access Key ID, o
   Secret Access Key e o endpoint `https://<conta>.r2.cloudflarestorage.com`.
3. **Chave só de leitura** para o workflow de backup (mesma tela): **Object Read only**, só no
   bucket `portal-capibaribe-arquivos`. É a que copia os arquivos para o B2 (épico C).
4. **CORS** (bucket → Settings → CORS Policy → Add CORS policy, aba JSON). Só o `PUT` do envio
   precisa: a foto no `<img>` e o PDF numa aba nova não pedem CORS.
   ```json
   [
     {
       "AllowedOrigins": ["https://portal-capibaribe-prime.vercel.app"],
       "AllowedMethods": ["PUT"],
       "AllowedHeaders": ["Content-Type"],
       "MaxAgeSeconds": 3600
     }
   ]
   ```
5. **Ciclo de vida** (bucket → Settings → Object Lifecycle Rules → Add rule): prefixo
   `envios/`, apagar depois de **1 dia**. Ou pela linha de comando:
   `npx wrangler r2 bucket lifecycle add portal-capibaribe-arquivos envios-1-dia envios/ --expire-days 1`
6. **Trava** (bucket → Settings → Bucket lock rules → Add rule): prefixo `arquivos/`,
   retenção **indefinida**. Se o painel não oferecer "indefinida":
   `npx wrangler r2 bucket lock add portal-capibaribe-arquivos arquivos-para-sempre arquivos/ --retention-indefinite`.
   A regra **não pode** cobrir `envios/` (aí nem o recusado seria apagado). Depois dela, nem o
   painel apaga o que está em `arquivos/` sem antes tirar a regra.
7. **Conferir** com um envio de teste depois do deploy do M3: o arquivo aparece em
   `arquivos/<chave>` e nada fica em `envios/`; um `.exe` renomeado para `.pdf` é recusado e
   não sobra nada em `envios/`.

### B. Backblaze B2: a cópia cifrada
1. **Criar a conta** em `backblaze.com/sign-up/cloud-storage`, com o e-mail do Portal.
   **Se pedir cartão, parar** (item 1: plano B).
2. **Criar o bucket** privado, por exemplo `portal-capibaribe-copia-arquivos` (o nome do B2 é
   global; se estiver ocupado, acrescente um sufixo). Manter o padrão "Keep all versions".
   Anotar o endpoint S3 mostrado na página do bucket (`https://s3.<região>.backblazeb2.com`).
3. **Chave sem poder de apagar.** A tela de chaves do site só oferece "Read and Write", "Read
   Only" e "Write Only", e não deixa tirar só o `deleteFiles`. Por isso, pela linha de comando
   oficial (`uv tool run --from b2 b2`, autenticando com a chave mestra só nesta hora):
   ```sh
   b2 account authorize            # pede o keyID e a chave mestra (não salvar em arquivo)
   b2 key create --bucket portal-capibaribe-copia-arquivos copia-arquivos-portal \
     listBuckets,listFiles,readFiles,writeFiles
   ```
   Guardar o `keyID` e a `applicationKey` que o comando imprime (aparecem uma vez só). Conferir
   que `deleteFiles` **não** está na lista. Por fim, `b2 account clear`: a CLI guarda a chave
   mestra em disco depois do `authorize`.

### C. GitHub: segredos do workflow `Backup` (épico C)
Em Settings → Secrets and variables → Actions:

| Segredo | Valor |
|---|---|
| `ARQUIVOS_R2_ENDPOINT` | o endpoint do R2 (A.2) |
| `ARQUIVOS_R2_ACCESS_KEY_ID`, `ARQUIVOS_R2_SECRET_ACCESS_KEY` | a chave **só de leitura** (A.3) |
| `ARQUIVOS_R2_BUCKET` | `portal-capibaribe-arquivos` |
| `COPIA_S3_ENDPOINT` | o endpoint S3 do B2 (B.2) |
| `COPIA_S3_ACCESS_KEY_ID`, `COPIA_S3_SECRET_ACCESS_KEY` | a chave do B2 sem `deleteFiles` (B.3) |
| `COPIA_S3_BUCKET` | o bucket do B2 (B.2) |

Sem os `COPIA_S3_*`, o passo da cópia avisa e não derruba o backup do banco.

### D. Vercel: variáveis da API (só Production, como sensíveis)
`PORTAL_ARQUIVOS_ENDPOINT`, `PORTAL_ARQUIVOS_BUCKET` (`portal-capibaribe-arquivos`),
`PORTAL_ARQUIVOS_CHAVE_ID`, `PORTAL_ARQUIVOS_CHAVE_SECRETA` (a chave de A.2). A prévia fica sem
elas (arquivos desligados), como ficou sem SMTP no M2.

### E. No fechamento do marco (coordenador)
Migração 0007 no Neon (produção e `previa`), deploy, o envio de teste de A.7 e um backup manual
(`gh workflow run backup.yml -f restaurar=true`) conferindo a cópia no B2.
