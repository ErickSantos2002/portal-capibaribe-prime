# Dúvidas e decisões do M3 · Onda 1 (contrato)

Decisões tomadas sem perguntar a ninguém durante a onda do contrato do M3. Cada item: a dúvida,
o que foi decidido e por quê. **[Erick]** marca o que só o Erick pode confirmar ou fazer (regra
do condomínio, custo, conta, preferência dele); o resto é decisão técnica que pode ser revista na
revisão do marco.

Os agentes dos épicos registram as próprias dúvidas em `duvidas-m3-documentos.md` (épico A),
`duvidas-m3-anexos.md` (épico B) e `duvidas-m3-protecao.md` (épico C).

A seção **"Passo a passo do Erick"** no fim reúne tudo o que precisa ser feito à mão (R2,
GitHub, Vercel) antes do primeiro documento real.

## 1. Arquivos protegidos contra perda: trava no R2 e cópia cifrada · respondida (plano B)
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
- **Resposta do Erick (12/10/2026): plano B, sem Backblaze.** A cópia cifrada vai para a pasta
  `arquivos/` do bucket de backups que já existe (`portal-capibaribe-backups`, no R2). Uma conta
  a menos; o custo é a cópia ficar na mesma conta da Cloudflare (risco aceito, registrado na
  [ADR-0011](../adr/0011-arquivos-protegidos-contra-perda.md), seção "Revisões"). O passo a
  passo abaixo já está no plano B: sem a seção do Backblaze, com a trava também em `arquivos/`
  do bucket de backups (passo A.7), e os `COPIA_S3_*` com os mesmos valores dos `R2_*`. O
  `testar-ciclo.sh` ganhou o caso "cópia no bucket de backups" (a cópia não toca os dumps, a
  retenção não apaga as cópias, e a restauração volta tudo para um bucket novo).

## 2. Rotas dos épicos já existem, respondendo 501
- **Dúvida:** como deixar três agentes trabalharem em paralelo sem brigar pelo `main.py` e pelo
  contrato.
- **Decisão:** todas as rotas do M3 já estão declaradas, com sessão, permissão, CSRF e
  validação do corpo de verdade, e só o corpo da função responde `501 em_construcao`. O épico
  troca o corpo e apaga a própria seção de `api/testes/test_m3_em_construcao.py`.
- **Por quê:** o que vale antes e depois dos épicos (quem pode chamar o quê) fica testado
  desde já em `test_m3_rotas.py`, e nenhum épico edita arquivo comum.
- **Fechamento do M3 (12/10/2026):** os épicos trocaram todos os 501; o
  `test_m3_em_construcao.py` foi apagado no merge. As rotas `…/abrir` que os épicos A e B
  criaram fora do OpenAPI entraram no contrato (spec, seção 5, e as listas de
  `test_m3_rotas.py` e `test_cache.py`).

## 3. Categoria nova: "Orientação" · respondida
- **Dúvida:** o modelo de dados tinha `convencao`, `regimento`, `ata`, `contrato`, `obra` e
  `outro`; o protótipo tem documentos como "Orientações para a vistoria", que não cabem em
  nenhuma.
- **Decisão:** `orientacao` entra na lista. Categoria é `text` com `CHECK`, então acrescentar
  outra depois é uma migração pequena.
- **Confirmar:** se a lista de categorias é a que a Comissão usaria.
- **Resposta do Erick (12/10/2026):** mantidas as 7, com "Orientação".

## 4. Só a gestão envia arquivo, até 50 por dia por unidade
- **Decisão:** `POST /api/arquivos` é só da gestão (Comissão e administração); a unidade comum
  recebe 403. No banco, até 50 arquivos por unidade a cada 24 horas, contando os recusados
  (a linha do recusado é apagada, então o trigger soma os `arquivo_recusado` do `historico` do
  mesmo período; sem isso, 60 recusas seguidas ainda deixavam pedir o 61º). Corrigido na
  própria 0007, que ainda não foi aplicada em lugar nenhum (só nesta branch).
- **Por quê:** na E1 só a gestão publica avisos e documentos. 50 cobre um dia de trabalho
  folgado (uma ata com 5 fotos é 6 envios) e segura um bug ou uma conta tomada que tentasse
  encher o bucket de 10 GB.

## 5. Título, categoria, data e acesso de documento não mudam · respondida
- **Dúvida:** H-19 fala de nova versão do arquivo; não fala de corrigir o título ou o nível.
- **Decisão:** o papel `app` não tem UPDATE nessas colunas. Publicou com o nível errado:
  arquivar e publicar de novo.
- **Por quê:** o nível decide quem vê; trocar o nível de um documento já publicado mudaria em
  silêncio quem já viu o quê. Arquivar deixa rastro no histórico.
- **Confirmar:** se a Comissão precisa corrigir título sem arquivar; se sim, é uma rota nova
  (e uma linha de permissão) no épico A.
- **Resposta do Erick (12/10/2026):** fica assim. Errou: arquivar e publicar de novo.

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

## 8. CSP com curinga `https://*.r2.cloudflarestorage.com` · respondida
- **Dúvida:** o endereço exato do bucket tem o ID da conta da Cloudflare
  (`<ACCOUNT_ID>.r2.cloudflarestorage.com`), e o repositório é público.
- **Decisão (provisória, mantida):** o curinga, só em `connect-src` e `img-src` (o teste de
  cabeçalhos garante que é o único endereço de terceiros e que não aparece em outra diretiva).
- **A troca, nos dois sentidos:**
  - **Curinga:** libera o navegador a falar com **qualquer** conta R2. Isso só importa se
    alguém já conseguiu rodar script no Portal (XSS, que a própria CSP dificulta: script só do
    próprio Portal); aí o script poderia mandar dados para um bucket R2 do atacante. Mas um
    script injetado já consegue tirar dados navegando para outro endereço, o que a CSP não
    bloqueia; o curinga quase não abre caminho novo.
  - **Host exato:** fecha esse caminho, mas põe o ID da conta da Cloudflare no repositório
    público. A Cloudflare não trata esse ID como segredo (ele aparece em URLs e no painel), mas
    é mais um dado da conta exposto para sempre no histórico do git.
- **Recomendação:** manter o curinga. Se preferir o host exato, é trocar o endereço em
  `vercel.json` e no teste `web/testes/cabecalhos.test.ts`.
- **Resposta do Erick (12/10/2026):** manter o curinga. Revisitar só se o Portal passar a
  guardar algo realmente sensível.
- **Nota:** abrir o PDF numa aba nova funciona com a CSP de hoje. **Embutir** o PDF na página
  (num `<iframe>` ou `<object>`) exigiria liberar o R2 também em `frame-src`/`object-src`;
  ninguém pediu isso, e o épico B mostra o PDF como botão.

## 9. Foto pequena vai com os metadados do celular · respondida
- **Dúvida:** a compressão (seção 4 da spec) regrava em WEBP só a foto com o lado maior acima
  de 1920 px (ou a menor que passa do limite do destino, desde a revisão do contrato).
  Regravar descarta os metadados (EXIF), inclusive a localização do GPS; a foto menor e leve
  vai como saiu do celular.
- **Decisão:** mantida como na spec. A maioria das fotos de celular passa de 1920 px e é
  regravada; print de tela e foto já reduzida pelo WhatsApp normalmente não têm GPS.
- **Por quê:** regravar toda foto pequena também troca o formato e pode aumentar o arquivo
  (PNG de print com texto fica pior em WEBP com perda).
- **Confirmar:** se prefere que toda foto seja regravada, para nunca levar localização. É uma
  linha em `web/src/arquivos/comprimir.ts` (o teste "foto pequena vai como está" muda junto).
- **Resposta do Erick (12/10/2026):** regravar **todo JPEG**, mesmo pequeno e dentro do limite,
  com as mesmas dimensões, só para tirar os metadados (inclusive o GPS). PNG e WEBP seguem a
  regra de antes (só se grande ou acima do limite). **Feito no fechamento do M3**
  (`comprimir.ts` e testes em `web/src/arquivos/arquivos.test.ts`): o JPEG regravado vai mesmo
  se ficar maior que o original; se passar do limite, a tela recusa pelo tamanho, como qualquer
  arquivo. Se o navegador não conseguir regravar (raro), o original vai como está. Celular que
  fotografa em HEIC: o Portal não aceita HEIC (só PDF, JPEG, PNG e WEBP); o iPhone costuma converter para
  JPEG ao escolher a foto no navegador, e aí ela passa por esta regra.

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

## 14. Endpoint com o nome do bucket no fim; `/api/saude` não muda
- **Dúvida (revisão do contrato):** a página do bucket no painel da Cloudflare mostra
  `https://<conta>.r2.cloudflarestorage.com/portal-capibaribe-arquivos`. Colado assim, o
  endpoint era recusado e a API ficava em 503 com só um aviso no log.
- **Decisão:** se o caminho do endpoint é exatamente `/<bucket configurado>` (com ou sem barra
  no fim), ele é tirado; qualquer outro caminho continua desligando os arquivos.
- **`/api/saude` não ganhou o estado dos arquivos.** Ela é a prova de vida da API e do banco, é
  pública, e não mostra o push nem o e-mail, que seguem a mesma regra ("sem configuração,
  desligado"). Mostrar só os arquivos seria incoerente, e mostrar os três diz a qualquer um
  quais canais estão sem configuração. A conferência depois do deploy é o aviso
  "arquivos desligados" nos logs da Vercel (passo C) ou o 503 `arquivos_desligados` no
  primeiro envio.

---

## Passo a passo do Erick (antes do primeiro documento real) **[Erick]**

Nada disto foi feito pelos agentes (spec, seção 11). Ordem sugerida; cada passo diz onde
conferir antes do próximo. Caminhos de tela conferidos na documentação oficial em 12/10/2026
(o painel muda de vez em quando: se um nome não bater, procure o mais parecido e anote).

**Plano B (resposta do Erick, item 1):** sem Backblaze. A cópia dos arquivos fica na pasta
`arquivos/` do bucket de backups que já existe; por isso não há mais seção do B2, e o passo A.7
trava essa pasta.

**As chaves vão só para a Vercel e o GitHub**, nunca para o repositório, o chat ou um arquivo
de texto. **Clipboard:** o `cliphist` grava em disco tudo o que é copiado. No fim de tudo
(seção F): apagar do histórico as entradas das chaves (⊞+SHIFT+V, selecionar e apagar) ou
`cliphist wipe`, e fechar o terminal onde alguma chave apareceu.

### A. Cloudflare R2: o bucket de arquivos (e a trava da cópia no bucket de backups)
1. **Criar o bucket** (R2 → Create bucket): nome `portal-capibaribe-arquivos`; Location
   **Automatic** (sem jurisdição); Default storage class **Standard** (o Infrequent Access não
   tem plano grátis e cobra leitura e cópia). Privado: sem domínio público e sem `r2.dev`. Nunca
   usar o `portal-capibaribe-backups` para isso: a API desliga os arquivos se o nome tiver
   "backup".
2. **Chave da API** (R2 → Overview → Account Details → API Tokens → **Manage** → Create
   **Account API token**): permissão **Object Read & Write**, aplicada **só** ao bucket
   `portal-capibaribe-arquivos`; TTL **Forever**; filtro de IP **vazio** (os IPs da Vercel e do
   GitHub Actions mudam). Na tela final, copiar o **Access Key ID**, a **Secret Access Key**
   (aparece **uma vez só**: se perder, crie outra chave) e o endpoint
   `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`. Copie o endpoint **desta** tela: o da
   página do bucket vem com `/portal-capibaribe-arquivos` no fim (a API aceita assim também,
   mas o workflow de backup não foi testado com ele).
3. **Chave só de leitura** para o workflow de backup (mesmo caminho, outro Account API token):
   **Object Read only**, só no bucket `portal-capibaribe-arquivos`, TTL Forever, sem filtro de
   IP. É a que lê os arquivos para a cópia cifrada (épico C).
4. **CORS** (bucket → aba **Settings** → CORS Policy → Add CORS policy, aba JSON) e **Save**.
   Só o `PUT` do envio precisa: a foto no `<img>` e o PDF numa aba nova não pedem CORS. Pode
   levar até 30 segundos para valer. Conferir: a política aparece na aba Settings do bucket.
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
5. **Ciclo de vida** (bucket → aba **Settings** → Object Lifecycle Rules → Add rule): prefixo
   `envios/`, apagar depois de **1 dia**, e **Save changes**. O R2 apaga "tipicamente em até
   24 horas" depois de vencer, então uma sobra em `envios/` pode durar uns 2 dias (é normal).
   Conferir: a regra aparece na aba Settings do bucket.
6. **Trava** (bucket → aba **Settings** → Bucket lock rules → Add rule): prefixo `arquivos/`,
   retenção **Indefinite**, e **Save changes**. A regra **não pode** cobrir `envios/` (aí nem
   o recusado seria apagado). Depois dela, nem o painel apaga o que está em `arquivos/` sem
   antes tirar a regra. Conferir: a regra aparece na aba Settings do bucket.

7. **Trava no bucket de backups** (bucket `portal-capibaribe-backups` → aba **Settings** →
   Bucket lock rules → Add rule): prefixo `arquivos/`, retenção **Indefinite**, e **Save
   changes**. É onde fica a cópia cifrada dos arquivos (plano B), e a chave `R2_*` do backup
   pode apagar (a retenção dos dumps usa). A regra cobre **só** `arquivos/`: se pegar
   `diarios/` ou `mensais/` (ou o bucket inteiro), a retenção de 30 diários + 12 mensais para de
   funcionar e o bucket cresce sem parar. Conferir: a regra aparece na aba Settings do bucket
   de backups, com o prefixo `arquivos/`.

Alternativa pela linha de comando (só se preferir; o painel basta). Primeiro
`npx wrangler login` (abre o navegador). Para criar:
`npx wrangler r2 bucket lifecycle add portal-capibaribe-arquivos envios-1-dia envios/ --expire-days 1`
, `npx wrangler r2 bucket lock add portal-capibaribe-arquivos arquivos-para-sempre arquivos/ --retention-indefinite`
e `npx wrangler r2 bucket lock add portal-capibaribe-backups copia-para-sempre arquivos/ --retention-indefinite`.
Para conferir (vale também depois do painel):
`npx wrangler r2 bucket lock list portal-capibaribe-arquivos`,
`npx wrangler r2 bucket lock list portal-capibaribe-backups` e
`npx wrangler r2 bucket lifecycle list portal-capibaribe-arquivos`.

### B. GitHub: segredos do workflow `Backup` (épico C, já na `main`)
Caminho: repositório → Settings → Secrets and variables → Actions → aba **Secrets** → **New
repository secret** (de repositório, não de environment). Depois, conferir os nomes na lista
(o valor não aparece mais).

**Os quatro `COPIA_S3_*` recebem os mesmos valores dos `R2_*` que já existem** (os do backup do
banco: endpoint, Access Key ID, Secret Access Key e o bucket `portal-capibaribe-backups`). O
GitHub não mostra o valor de um segredo salvo, então copie de onde você guardou a chave do
backup (ou, se não tiver mais, crie no R2 outra chave **Object Read & Write** só do bucket de
backups e use nos `COPIA_S3_*`). Por que repetir, em vez de o workflow usar os `R2_*`: os
nomes separados deixam trocar a cópia de lugar depois (para o B2, ADR-0011) mexendo só nos
segredos, e cada passo do workflow diz com clareza de onde lê e para onde escreve.

| Segredo | Valor |
|---|---|
| `ARQUIVOS_R2_ENDPOINT` | o endpoint do R2 (A.2): o mesmo valor do `R2_ENDPOINT` que já existe |
| `ARQUIVOS_R2_ACCESS_KEY_ID`, `ARQUIVOS_R2_SECRET_ACCESS_KEY` | a chave **só de leitura** (A.3) |
| `ARQUIVOS_R2_BUCKET` | `portal-capibaribe-arquivos` |
| `COPIA_S3_ENDPOINT` | o mesmo valor do `R2_ENDPOINT` |
| `COPIA_S3_ACCESS_KEY_ID`, `COPIA_S3_SECRET_ACCESS_KEY` | os mesmos do `R2_ACCESS_KEY_ID` e do `R2_SECRET_ACCESS_KEY` |
| `COPIA_S3_BUCKET` | `portal-capibaribe-backups` (o mesmo do `R2_BUCKET`) |

Sem os `COPIA_S3_*`, o passo da cópia avisa e não derruba o backup do banco.

### C. Vercel: variáveis da API (só Production)
Project → Settings → Environment Variables. Marcar **só Production** (a prévia fica sem elas,
arquivos desligados, como ficou sem SMTP no M2). **Confira a grafia antes de salvar**: o nome
de uma variável Secret não se edita depois.

| Variável | Valor | Type |
|---|---|---|
| `PORTAL_ARQUIVOS_ENDPOINT` | o endpoint do R2 (A.2) | Config ou Secret |
| `PORTAL_ARQUIVOS_BUCKET` | `portal-capibaribe-arquivos` | Config ou Secret |
| `PORTAL_ARQUIVOS_CHAVE_ID` | o Access Key ID de A.2 | **Secret** |
| `PORTAL_ARQUIVOS_CHAVE_SECRETA` | a Secret Access Key de A.2 | **Secret** |

`PORTAL_ARQUIVOS_REGIAO`: **não criar** (o padrão `auto` é o certo para o R2). Variável nova só
vale depois de um **redeploy** de produção (Deployments → o último de produção → Redeploy). Para
conferir: nos logs da Vercel, **não** pode aparecer "arquivos desligados" depois do redeploy
(se aparecer, a mensagem diz qual variável está faltando ou inválida, sem mostrar o valor).

### D. No fechamento do marco (coordenador)
Migração 0007 no Neon (produção e `previa`), deploy, e um backup manual
(`gh workflow run backup.yml -f restaurar=true`) conferindo a cópia em `arquivos/` do bucket de
backups.

### E. Envio de teste (depois do D: deploy e migração feitos)
- **O arquivo de teste fica para sempre:** em `arquivos/` ele está travado, vai para a cópia
  cifrada (também travada) e cria uma linha no banco de produção. Use um **PDF inofensivo, pensado para ficar** (por
  exemplo, um "Teste do envio de arquivos" de uma página), nada pessoal.
- Conferir: o arquivo aparece em `arquivos/<chave>` e nada fica em `envios/` (ou some em até
  uns 2 dias, pelo ciclo de vida).
- Um `.exe` renomeado para `.pdf` é **recusado**: não chega a `arquivos/`, e o que foi para
  `envios/` é apagado (ou some pelo ciclo de vida).

### F. No fim: limpar o rastro das chaves
- Apagar do histórico do clipboard as entradas com chaves (⊞+SHIFT+V) ou `cliphist wipe`.
- Fechar o terminal onde alguma chave apareceu.
- Não salvar nenhuma chave em arquivo de texto (o lugar delas é a Vercel e o GitHub).
