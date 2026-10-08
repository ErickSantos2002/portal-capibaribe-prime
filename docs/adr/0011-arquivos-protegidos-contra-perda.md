# ADR-0011 · Arquivos protegidos contra perda: trava no bucket e cópia diária cifrada fora da Cloudflare

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 07/10/2026 |
| **Complementa** | [ADR-0004](0004-arquivos-r2.md) (arquivos no R2), [ADR-0007](0007-backup.md) e [ADR-0009](0009-backup-bucket-papel-e-chave.md) (backup do banco) |

## Contexto
O M3 traz documentos (convenção, atas, contratos, obra) e anexos de aviso, guardados no bucket
privado de arquivos do R2 (ADR-0004). O backup diário (ADR-0007, ADR-0009) cobre **só o
banco**: depois de um desastre, o banco volta com a lista dos documentos, mas sem os arquivos
nada abre. O roadmap (M3) exige decidir a proteção dos arquivos **antes do primeiro documento
real**.

Restrições: custo zero (RNF-20), nada da infraestrutura da empresa do autor, e o mínimo de
rotina manual (o que depende de alguém lembrar deixa de acontecer). Já existe o bucket
`portal-capibaribe-backups` (R2), com chave restrita a ele, usado pelo workflow `Backup`.

O que pode fazer um arquivo sumir, do mais provável ao menos provável:

1. **Um bug ou uma chave vazada da API** apaga ou sobrescreve objetos (a chave do app tem
   leitura e escrita no bucket de arquivos; o R2 não separa "escrever" de "apagar" na chave).
2. **Engano no painel** da Cloudflare (apagar objeto, pasta ou bucket).
3. **Perder a conta da Cloudflare** (acesso perdido, suspensão, cartão recusado), ou uma falha
   do próprio R2. Hoje isso levaria os arquivos **e** os backups do banco juntos; o banco em si
   sobreviveria, porque mora no Neon.

O volume é pequeno (1 a 3 GB em 2 anos, `04-modelo-de-dados.md`, seção 6) e **nada é apagado
de propósito**: RN-05 diz que o oficial não some (corrige-se com versão nova ou arquiva-se), e
a nova versão de documento guarda a anterior (RF-32). Arquivo do Portal, uma vez publicado, é
para sempre.

## Decisão
Duas camadas, cada uma contra um grupo de riscos.

### 1. No bucket de arquivos: nada publicado é apagado nem sobrescrito
- **Duas pastas.** O navegador envia para `envios/<chave>` (URL assinada de 10 minutos). A API
  confere o conteúdo e só então copia para `arquivos/<chave>` e apaga o envio. Tudo que o
  Portal mostra vem de `arquivos/`.
- **Chave nunca reaproveitada:** 32 caracteres hexadecimais aleatórios (128 bits), únicos no
  banco (`arquivo.chave`). Uma versão nova de documento é um arquivo novo, nunca o mesmo nome.
- **Trava do bucket (R2 *bucket lock*)** na pasta `arquivos/`, com retenção **indefinida**: o
  R2 recusa apagar ou sobrescrever qualquer objeto ali, venha a ordem de onde vier (bug, chave
  vazada da API, script). Só quem entra no painel com a conta do dono consegue tirar a regra.
- **Regra de ciclo de vida** na pasta `envios/`: o R2 apaga sozinho o que ficar lá mais de 1
  dia (envio abandonado no meio, ou arquivo recusado cuja remoção falhou).
- **A API nunca apaga fora de `envios/`**: a camada de armazenamento recusa (teste), e o
  armazenamento falso dos testes imita a trava.

Cobre o risco 1 inteiro e boa parte do 2.

### 2. Cópia diária, cifrada, num segundo provedor (Backblaze B2)
- O workflow `Backup` ganha um passo depois do `pg_dump`: lista `arquivos/` no bucket de
  arquivos (com uma **chave só de leitura** desse bucket, nova) e, para cada objeto que ainda
  não está na cópia, baixa, **cifra com `age`** (os mesmos destinatários de
  `scripts/backup/destinatarios.age`) e envia para `arquivos/<chave>.age` num bucket privado
  do **Backblaze B2** (plano grátis de 10 GB, API compatível com S3, o mesmo `boto3` do
  `s3.py`).
- **Incremental e só de inclusão:** como nada em `arquivos/` muda, basta copiar o que falta.
  A chave do B2 é criada **sem a permissão `deleteFiles`**: nem o workflow consegue apagar a
  cópia; e o bucket guarda todas as versões (padrão do B2), então reenviar um nome não perde o
  anterior.
- **Testado todo mês:** a restauração de teste do dia 2 (ADR-0009) passa a conferir que todo
  arquivo confirmado no banco restaurado tem a cópia `arquivos/<chave>.age` no B2, e decifra
  um deles escolhido ao acaso, conferindo a assinatura do conteúdo (os mesmos bytes mágicos da
  validação do envio). Falhou, o GitHub manda e-mail.
- **Restaurar:** o banco volta como hoje; os arquivos voltam decifrando a cópia para um bucket
  novo (`arquivos/<chave>`), sem precisar do banco para achar os nomes. Passo a passo no README
  quando o passo do workflow existir.

Cobre o risco 3 e o resto do 2. Implementação: épico C do M3 (spec `m3-contrato.md`, seção 9),
**portão do primeiro documento real**.

## Consequências
- Um arquivo publicado precisa de **duas** falhas independentes para sumir: a trava do R2 (ou a
  conta da Cloudflare) **e** a cópia no B2 (outra empresa, outra senha, chave sem poder de
  apagar).
- **Apagar de verdade passa a ser trabalho manual do dono**, nos dois provedores (tirar a
  trava, apagar o objeto; no B2, com uma chave que tenha `deleteFiles`). É o que se quer para
  documento oficial. Se um dia for preciso tirar um arquivo por obrigação (ex.: pedido de
  exclusão pela LGPD de uma foto com pessoas), o caminho é: arquivar no Portal na hora, e
  apagar os objetos à mão depois. Registrar no histórico do Portal é responsabilidade de quem
  faz.
- Espaço: os arquivos ocupam o R2 uma vez só (a cópia vai para o B2), então a folga do R2
  continua a da arquitetura (1 a 3 GB de arquivos + ~1 GB de backups do banco, de 10 GB). O
  B2 guarda 1 a 3 GB dos seus 10 GB grátis. A cópia cifrada tem o mesmo tamanho do original
  (o `age` não comprime).
- Mais um provedor e mais segredos para cuidar: uma conta no Backblaze (sem cartão no plano
  grátis, em 07/10/2026; conferir ao criar) e os segredos do workflow (chave só de leitura do
  bucket de arquivos, chave do B2). Itens **[Erick]** em `docs/superpowers/duvidas-m3.md`.
- Perda máxima: o que foi publicado depois da última cópia e antes do desastre (até ~24 h),
  **e só no risco 3**; nos riscos 1 e 2 a trava não deixa perder nada.
- O backup do banco continua no R2. Na perda da conta da Cloudflare, o banco segue vivo no
  Neon e os arquivos voltam do B2; o histórico de backups do banco se perde (aceito: é o mesmo
  risco já aceito na ADR-0009).

## Alternativas consideradas
- **Só a trava do bucket:** resolve bug e chave vazada, de graça e sem rotina. Não protege da
  perda da conta, e o arquivo só existe num lugar. Fica como a primeira camada, não como a
  decisão inteira.
- **Cópia no bucket de backups que já existe (`portal-capibaribe-backups`, pasta
  `arquivos/`):** nenhuma conta nova, o workflow já tem a chave. Mas os arquivos ficariam
  **duas vezes na mesma conta da Cloudflare**: perder a conta leva o original e a cópia
  juntos, que é justamente o risco que a trava não cobre. E a cópia ocuparia o mesmo limite de
  10 GB do R2 (até ~7 GB no pior caso). **É o plano B** se o B2 grátis deixar de existir ou
  pedir cartão: o script é o mesmo, só mudam as variáveis.
- **Versionamento de objetos no R2:** o R2 não tem versionamento de objetos (07/10/2026); a
  trava cumpre o papel de "não perder a versão anterior".
- **Google Drive da conta do Portal (15 GB):** grátis e fora da Cloudflare, mas o acesso de um
  robô pede um app OAuth no Google Cloud, consentimento e token que vence se o app ficar "em
  teste": mais peças e mais chance de parar sem ninguém ver. O B2 fala S3, como o resto.
- **Repositório privado no GitHub (Releases ou LFS):** usa o GitHub como depósito de arquivos,
  fora do que ele se propõe; o LFS grátis tem 1 GB.
- **Guardar os arquivos no banco:** descartado na ADR-0004 (1 GB do Neon, banco lento).
- **Não fazer nada até ter volume:** a decisão precisa estar pronta antes do primeiro documento
  real (roadmap); depois, o primeiro desastre seria a descoberta.
