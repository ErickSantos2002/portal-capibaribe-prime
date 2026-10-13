# Dúvidas e decisões do M3 · Épico C · Proteção dos arquivos

Decisões tomadas sem perguntar a ninguém durante o épico C ([ADR-0011](../adr/0011-arquivos-protegidos-contra-perda.md),
spec `specs/m3-protecao.md`). **[Erick]** marca o que só o Erick pode confirmar ou fazer; o resto
é decisão técnica, revisável na revisão do marco.

> **Fechamento do M3 (12/10/2026): plano B.** O Erick escolheu não criar a conta no Backblaze: a
> cópia vai para a pasta `arquivos/` do bucket de backups do R2 (item 14). O que este arquivo
> diz do B2 (região, chave sem `deleteFiles`, versões, tetos de gasto) vale para o dia em que a
> cópia for para lá; hoje, o item 14 manda. As seções do passo a passo de `duvidas-m3.md`
> mudaram de letra: os segredos do GitHub são a seção **B**, o fechamento a **D** e o envio de
> teste a **E**.

## 1. Nomes dos segredos: os da seção B (antes C) de `duvidas-m3.md`, sem mudança
- `ARQUIVOS_R2_ENDPOINT`, `ARQUIVOS_R2_ACCESS_KEY_ID`, `ARQUIVOS_R2_SECRET_ACCESS_KEY`,
  `ARQUIVOS_R2_BUCKET`, `COPIA_S3_ENDPOINT`, `COPIA_S3_ACCESS_KEY_ID`,
  `COPIA_S3_SECRET_ACCESS_KEY`, `COPIA_S3_BUCKET`, e o `BACKUP_AGE_KEY` que já existe.
- **Nenhum segredo novo no GitHub.** `DESTINO_S3_*` existe só para a restauração à mão (README),
  e as regiões (`*_REGIAO`) são opcionais (item 2).

## 2. Região do B2 tirada do endpoint
- **Dúvida:** o boto3 assina com a região; o R2 só aceita `auto`, o B2 espera a região dele
  (`us-east-005`, por exemplo), e a seção C não tem segredo de região.
- **Decisão:** se o endpoint é `https://s3.<região>.backblazeb2.com`, a região sai dele; senão,
  `auto`. `COPIA_S3_REGIAO` (ou `ARQUIVOS_R2_REGIAO`, `DESTINO_S3_REGIAO`) manda, se existir.
- **Por quê:** o endpoint que o Erick copia da página do bucket já tem a região; um segredo a
  mais só abriria espaço para os dois discordarem.

## 3. Sem os segredos (ou com só parte deles): avisa e não falha
- **Decisão:** faltando qualquer uma das 8 variáveis, o passo emite `::warning::`, escreve no
  resumo do run quais **nomes** faltam e sai com 0. Vale também para a configuração pela
  metade (leitura literal da spec: "sem os segredos, avisa e não falha").
- **Risco aceito:** um aviso amarelo não manda e-mail. A rede de segurança é a conferência do
  dia 2 (item 5): com arquivo confirmado no banco e sem a cópia configurada, ela **reprova**.
  No pior caso, o esquecimento dura até o próximo dia 2.

## 4. Cópia configurada que falha derruba o job (e-mail), mas não a restauração de teste
- **Decisão:** com as variáveis, um arquivo que não foi copiado faz o passo sair com 1 no fim
  (os outros são copiados mesmo assim). O job `restauracao` passou a rodar com
  `!cancelled() && objeto != '' && restaurar == 'true'`: se só a cópia falhou, o backup do banco
  existe e a restauração dele continua sendo testada.
- **Só se prova no Actions real:** que as `outputs` de um job que falhou chegam ao job seguinte
  (é o comportamento esperado, mas não conferi na documentação, e nenhum teste local cobre o
  YAML; o actionlint passa). Se não chegarem, a restauração só pula no dia em que a cópia falhou.

## 5. A conferência é mais rígida que "tem assinatura"
- **Decisão:** para **toda** cópia de arquivo confirmado:
  - existe `arquivos/<chave>.age`;
  - o tamanho (da listagem, sem baixar nada) é **exatamente** o de um `age` daquele arquivo:
    carga de `16 + t + 16 × blocos de 64 KiB` (mínimo 1 bloco) mais cabeçalho de
    `70 + 98 × destinatários X25519` (1 a 20). Conferido contra o `age` de verdade nos testes de
    unidade, para 1 e 2 destinatários e nos limites do bloco;
  - o começo é `age-encryption.org/v1` (GET parcial de 22 bytes) em até 200 cópias por
    conferência (todas, enquanto forem até 200; acima disso, 200 ao acaso).
  E o sorteado decifra com **o tamanho e o tipo registrados no banco**. Sem `COPIA_S3_*` e com
  arquivo confirmado: reprova. Sem nenhum confirmado (hoje): passa com aviso.
- **Revisão independente:** antes só "cópia menor ou igual ao original" reprovava, e lixo de 300
  bytes passava em 6 de 10 rodadas (só o sorteado era decifrado).
- **Custo:** a listagem é classe C do B2 (1 por 1.000 objetos); o GET parcial é classe B, com
  2.500 grátis por dia. O teto de 200 deixa folga mesmo com milhares de arquivos, e com o teto de
  gasto em US$ 0 (passo B.1b) passar do grátis faria o B2 recusar, não cobrar.
- **Limite:** destinatário que não seja X25519 (chave SSH, por exemplo) tem outro tamanho de
  cabeçalho e reprovaria a conferência. Hoje `destinatarios.age` só tem `age1...`; quem trocar
  por outro tipo ajusta `CABECALHO_FIXO`/`POR_DESTINATARIO` em `arquivos.py`.
- Só chave, tipo e tamanho saem do banco; o nome original do arquivo nunca entra no log.

## 6. Nada de nome fora do padrão no log
- **Decisão:** a cópia só considera `arquivos/<32 hexadecimais>` (o que a API cria). Outro
  objeto em `arquivos/` (posto à mão no painel, por exemplo) é ignorado e **só contado** no
  aviso, sem o nome: o log de um repositório público é público, e um nome à mão pode ter dado
  pessoal. As chaves hexadecimais aparecem no log: sozinhas não abrem nada (bucket privado).
- **[Erick]** se um dia puser algo à mão em `arquivos/`, ele não vai para a cópia.

## 7. O conteúdo em claro não toca o disco na cópia nem na conferência
- **Decisão:** a cópia passa o download direto para a entrada do `age` (só o cifrado vai para
  um diretório temporário 700, apagado a cada arquivo e no fim); a conferência baixa o cifrado e
  lê a saída do `age` em memória, guardando só os 16 primeiros bytes e a contagem.
- Na **restauração** o claro passa por um diretório temporário 700, apagado logo depois de cada
  envio: é o caminho mais simples para enviar com o tamanho conferido, e o destino é o bucket
  de arquivos, que guarda o claro de qualquer jeito.

## 8. "Nunca sobrescrever" sem `If-None-Match`
- **Dúvida:** o S3 tem PUT condicional (`If-None-Match: *`), mas não achei confirmação de que o
  B2 aceita pela API S3.
- **Decisão:** a garantia vem de três coisas: só se envia o nome que a listagem diz que não está
  lá; o workflow nunca roda dois ao mesmo tempo (`concurrency`); e o bucket do B2 guarda todas
  as versões (passo B.2), então nem um envio repetido perderia a anterior. O teste confere que
  `arquivos.py` não tem nenhuma chamada de apagar, copiar por cima ou mexer em bucket.
- Nunca **esconde** nada. Um arquivo escondido à mão some da listagem e seria copiado de novo
  (uma versão nova, sem perder a antiga).

## 9. Restauração: pula o que já está no destino, sem baixar
- **Decisão:** objeto que já existe no bucket novo é pulado sem conferir o tamanho. O PUT do S3
  é atômico (um envio interrompido não deixa objeto pela metade), então existir basta; e assim
  rodar de novo depois de uma queda não baixa tudo outra vez. Content-Type pela assinatura;
  conteúdo desconhecido volta como `application/octet-stream`, com aviso. Destino com "backup"
  no nome é recusado (a API recusaria esse bucket).
- **Destino que é a própria cópia** (revisão independente): `DESTINO_S3_*` igual a `COPIA_S3_*`
  gravava os arquivos **em claro** no B2. Agora é recusado comparando bucket e endpoint
  normalizado (esquema e host sem caixa, porta padrão explícita, sem barra no fim), e também é
  recusado qualquer destino que já tenha `.age` em `arquivos/`. Não recuso "destino = bucket de
  arquivos de origem": restaurar é justamente para um bucket novo, e o script não conhece o
  bucket de origem (não usa `ARQUIVOS_R2_*`).

## 9b. Restauração pelas versões do B2
- **Dúvida (revisão independente):** a restauração só via a versão mais nova
  (`list_objects_v2`); uma cópia escondida ou com a versão mais nova estragada não voltava.
- **Decisão:** a restauração lista por `list_object_versions`. Uma cópia escondida (no S3, um
  marcador de remoção por cima) volta pela versão anterior a ele; se a versão mais nova não
  decifra, tenta as anteriores, da mais nova para a mais velha, antes de desistir. O resumo
  conta "de versão anterior" e "estavam escondidos". Testado no `moto` com versionamento ligado
  (como o "Keep all versions" do B2).
- A **conferência** e a **cópia** continuam olhando só a versão mais nova, de propósito: uma
  versão nova estragada ou um arquivo escondido têm de dar alarme (a conferência reprova), e a
  cópia reenvia o escondido como versão nova.
- **Só se prova no B2 real:** que o `ListObjectVersions` e o GET com `VersionId` da API S3 do
  B2 se comportam como o `moto` (a chave Read Only do passo 4 do README tem `listFiles` e
  `readFiles`, que é o que essas chamadas pedem).

## 9c. Trocar a chave do `age`
- **Dúvida (revisão independente):** as cópias de arquivo são permanentes e cifradas para os
  destinatários do dia em que foram feitas.
- **Decisão:** documentado no README ("Trocar a chave do `age`"): a chave privada antiga nunca
  pode ser descartada enquanto houver cópia para ela; na troca, `BACKUP_AGE_KEY` passa a ter as
  duas chaves privadas (uma por linha; o teste confere que a conferência passa assim). Recifrar
  as cópias antigas (caso de chave vazada) fica fora: exige script novo e apagar versões à mão
  no B2. Nenhuma ação agora; só vale no dia de uma troca.

## 10. Python do épico com trava de dependências (`--frozen`)
- **Decisão:** `arquivos.py` e o ajudante de teste `testes/s3_teste.py` são scripts `uv` com
  `*.py.lock` ao lado e rodam com `uv run --frozen --script`. O `s3.py` do M1 roda com
  `uv run --script` sem trava; não mexi (fora do escopo), mas dá para alinhar com
  `uv lock --script scripts/backup/s3.py` e `--frozen` em `comum.sh`.
- O `moto` do teste continua como no M1 (`uv run --with 'moto[server]==5.2.3'`).

## 11. Tempo do job e da cópia
- **Decisão (revista na revisão independente):** o passo da cópia tem `timeout-minutes: 12`,
  menor que os 20 do job. Uma primeira cópia longa para no meio como falha **do passo** (e-mail),
  o job termina, a restauração de teste do dia ainda roda (item 4), e o próximo run continua de
  onde parou (só copia o que falta; o PUT é atômico). No dia a dia a cópia é de poucos arquivos.
- **A cópia só roda se o backup do banco passou** (o padrão do Actions, mantido de propósito):
  sem o dump de hoje, a falha dele já manda e-mail, e a cópia de amanhã pega o que faltou.

## 11b. Erros sem traceback nem endereço
- **Decisão (revisão independente):** erro de conexão ou de listagem saía como traceback do
  Python, com a URL do bucket, num log público. Agora todo erro passa por `descrever()`: só o
  código e a operação (`o bucket respondeu NoSuchBucket em ListObjectsV2`) ou o tipo do erro
  (`EndpointConnectionError`), nunca endpoint nem nome de bucket. Testado com um bucket fora do
  ar e um inexistente.

## 11c. Padrão das chaves com `fullmatch`
- **Decisão (revisão independente):** o `$` do `re` aceitava `arquivos/<chave>\n`, que é outro
  objeto. Os padrões passaram a `fullmatch` (teste de unidade com o `\n` e outros casos).

## 12. O teste local continua fora do CI
- Mesmo motivo do M1 (`duvidas-m1-backup.md`, item 10): o `testar-ciclo.sh` precisa de Docker,
  `age` e dois `moto`, e o workflow mensal é a prova contínua. 46 verificações hoje (19 do M1 +
  27 da proteção), mais os testes de unidade de `testes/testar_arquivos_unidade.py`, rodados
  por ele.

## 13. O que só o Actions de verdade prova **[Erick]**
- Assinatura e envio no **B2 real** (região, envio em partes acima de 8 MB, checksums só
  quando exigidos) e a chave B.3 com `listBuckets,listFiles,readFiles,writeFiles` bastando
  para listar, HEAD e enviar.
- A chave **Object Read only** do R2 (A.3) listando `arquivos/`.
- O aviso amarelo e o resumo do run, e o item 4 (outputs de job que falhou).
- **Como provar:** no fechamento do marco (passo E de `duvidas-m3.md`), depois de criar os
  segredos da seção C: `gh workflow run backup.yml -f restaurar=true` e conferir no resumo do
  run as seções "Cópia dos arquivos" dos dois jobs. Antes do primeiro documento real, o
  esperado é "copiados agora: 0" e "nenhum arquivo confirmado"; depois do envio de teste
  (passo F), rodar de novo e ver "copiados agora: 1" e a conferência decifrando o PDF.
- **Ensaio da restauração dos arquivos** (README, "Restaurar os arquivos num desastre"): vale
  fazer uma vez com um bucket de ensaio, depois do envio de teste, para o passo a passo não ser
  lido pela primeira vez no dia do desastre. Apague o bucket de ensaio depois (ele não tem
  trava).

## 14. Plano B: a cópia no bucket de backups (fechamento do M3, resposta do Erick)
- **Decisão (Erick, 12/10/2026):** sem Backblaze. Os quatro `COPIA_S3_*` recebem os mesmos
  valores dos `R2_*` do backup do banco; a cópia fica em `arquivos/` do bucket
  `portal-capibaribe-backups`, ao lado dos dumps. ADR-0011, seção "Revisões".
- **Conferido no código e no teste:**
  - origem e cópia na **mesma conta** (o mesmo endpoint, buckets diferentes): nada no script
    depende de endpoints diferentes; `mesmo_bucket` compara endpoint **e** bucket;
  - a cópia **no mesmo bucket dos dumps**: o script só lista e escreve em `arquivos/`, e só
    considera `arquivos/<32 hex>.age`; a retenção (`s3.py reter`) só lista `diarios/` e
    `mensais/` e só apaga nomes no padrão dos dumps;
  - a restauração recusa destino com "backup" no nome (o bucket de backups nunca é destino) e
    destino igual à cópia.
  - `testar-ciclo.sh` ganhou a seção 8 (3 verificações, 49 no total): a cópia no bucket de
    backups não muda nenhum objeto de `diarios/`, `mensais/` nem de outra pasta; a retenção
    rodada logo depois não apaga nenhuma cópia; e a restauração a partir dele devolve os
    arquivos iguais num bucket novo.
- **O R2 não tem versões de objeto:** o `ListObjectVersions` não aparece na lista de operações
  do R2 (a de `PutBucketVersioning` diz "não implementado"; documentação da Cloudflare,
  12/10/2026). A restauração listava por versões (item 9b) e falharia no R2. Agora, se o bucket
  responde `NotImplemented` (ou `MethodNotAllowed`) a essa listagem, ela usa a listagem comum e
  baixa sem `VersionId`; outro erro continua aparecendo (testes de unidade
  `versoes_num_bucket_sem_versionamento`, `versoes_com_outro_erro_do_bucket_nao_esconde_o_erro`
  e `restaurar_um_sem_versao_baixa_sem_version_id`). **Só o R2 de verdade prova** o código que
  ele devolve; o `moto` aceita a listagem por versões mesmo sem versionamento, por isso o caso
  fica no teste de unidade. Se o R2 responder outro código, a restauração falha com a mensagem
  curta do `descrever()`, e o ajuste é acrescentar o código em `SEM_VERSOES`.
- **Trava:** a chave `R2_*` pode apagar (a retenção usa), então o passo A.7 de `duvidas-m3.md`
  põe uma trava indefinida só no prefixo `arquivos/` do bucket de backups. Com ela, "nunca
  sobrescrever" (item 8) fica garantido pelo próprio R2, e não só pelo script.
- **Itens que mudam de sentido:** o 2 (região: o endpoint do R2 dá `auto`), o 5 (custo: a
  listagem e o GET parcial são operações do R2, dentro do grátis; não há teto de gasto como no
  B2), o 9b (versões: ver acima) e o 13 (o que só o Actions prova: agora é a chave `R2_*` na
  cópia e a chave só de leitura do bucket de arquivos).
