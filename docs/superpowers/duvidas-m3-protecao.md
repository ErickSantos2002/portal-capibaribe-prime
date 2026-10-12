# Dúvidas e decisões do M3 · Épico C · Proteção dos arquivos

Decisões tomadas sem perguntar a ninguém durante o épico C ([ADR-0011](../adr/0011-arquivos-protegidos-contra-perda.md),
spec `specs/m3-protecao.md`). **[Erick]** marca o que só o Erick pode confirmar ou fazer; o resto
é decisão técnica, revisável na revisão do marco.

## 1. Nomes dos segredos: os da seção C de `duvidas-m3.md`, sem mudança
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
- **Decisão:** além de existir `arquivos/<chave>.age` para todo confirmado, a cópia precisa ser
  **maior** que o original (o `age` só acrescenta; menor ou igual é cópia truncada), e o
  sorteado precisa decifrar com **o tamanho e o tipo registrados no banco** (não só "algum dos
  quatro tipos"). Sem `COPIA_S3_*` e com arquivo confirmado: reprova. Sem nenhum confirmado
  (hoje): passa com aviso, mesmo sem as variáveis.
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

## 10. Python do épico com trava de dependências (`--frozen`)
- **Decisão:** `arquivos.py` e o ajudante de teste `testes/s3_teste.py` são scripts `uv` com
  `*.py.lock` ao lado e rodam com `uv run --frozen --script`. O `s3.py` do M1 roda com
  `uv run --script` sem trava; não mexi (fora do escopo), mas dá para alinhar com
  `uv lock --script scripts/backup/s3.py` e `--frozen` em `comum.sh`.
- O `moto` do teste continua como no M1 (`uv run --with 'moto[server]==5.2.3'`).

## 11. Tempo do job
- **Decisão:** o `timeout-minutes: 20` do job `backup` ficou. A cópia é incremental (no dia a
  dia, poucos arquivos novos) e o volume esperado é 1 a 3 GB em 2 anos. Se a primeira cópia
  depois de configurar estourar o tempo, o próximo run continua de onde parou (só copia o que
  falta). Subir para 30 é uma linha.

## 12. O teste local continua fora do CI
- Mesmo motivo do M1 (`duvidas-m1-backup.md`, item 10): o `testar-ciclo.sh` precisa de Docker,
  `age` e dois `moto`, e o workflow mensal é a prova contínua. 37 verificações hoje (19 do M1 +
  18 da proteção).

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
