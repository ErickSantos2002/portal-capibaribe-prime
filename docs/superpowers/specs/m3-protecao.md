# Spec · M3 · Épico C · Proteção dos arquivos

| | |
|---|---|
| **Marco** | M3 · Documentos e anexos |
| **Base** | [ADR-0011](../../adr/0011-arquivos-protegidos-contra-perda.md), ADR-0007, ADR-0009, `m3-contrato.md` (seções 9 e 10), `duvidas-m3.md` (seção C do passo a passo) |
| **Criado em** | 12/10/2026 |
| **Plano** | `docs/superpowers/plans/m3-protecao.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m3-protecao.md` |

## 1. Objetivo

A segunda camada da ADR-0011: uma cópia diária, cifrada com `age`, de tudo o que está em
`arquivos/` no bucket de arquivos (R2), num bucket do Backblaze B2; a conferência dessa cópia
na restauração de teste do dia 2; e um script para trazer os arquivos de volta depois de um
desastre. Nada na API nem no front muda.

## 2. Peças

| Arquivo | O que faz |
|---|---|
| `scripts/backup/arquivos.py` | Script `uv` (Python 3.12, `boto3` fixado, `arquivos.py.lock`), roda com `uv run --frozen --script`. Comandos `copiar`, `conferir`, `restaurar` |
| `scripts/backup/arquivos.py.lock` | Trava as dependências do script (com hash) para o `--frozen` |
| `scripts/backup/copiar-arquivos.sh` | Passo do workflow depois do `pg_dump`: confere os segredos, chama `copiar`, escreve o resumo |
| `scripts/backup/conferir-arquivos.sh` | Passo da restauração de teste: lê do banco restaurado as chaves confirmadas e chama `conferir` |
| `scripts/backup/restaurar-arquivos.sh` | Desastre: decifra a cópia inteira para um bucket novo |
| `scripts/backup/testes/testar-ciclo.sh` | Ganha a cópia, a conferência e a restauração, com dois S3 falsos (`moto`) |
| `.github/workflows/backup.yml` | Passo da cópia no job `backup`; passo da conferência no job `restauracao` |
| `README.md`, seção "Backup" | O que a cópia faz e o passo a passo para restaurar os arquivos |

## 3. Variáveis (segredos do GitHub)

Os nomes são os da seção C de `duvidas-m3.md` e da seção 9 do contrato:

| Grupo | Variáveis | Quem usa |
|---|---|---|
| Bucket de arquivos (R2, chave **só de leitura**) | `ARQUIVOS_R2_ENDPOINT`, `ARQUIVOS_R2_ACCESS_KEY_ID`, `ARQUIVOS_R2_SECRET_ACCESS_KEY`, `ARQUIVOS_R2_BUCKET` | `copiar` |
| Cópia (B2, chave sem `deleteFiles`) | `COPIA_S3_ENDPOINT`, `COPIA_S3_ACCESS_KEY_ID`, `COPIA_S3_SECRET_ACCESS_KEY`, `COPIA_S3_BUCKET` | `copiar`, `conferir`, `restaurar` |
| Chave privada do `age` | `BACKUP_AGE_KEY` (ou `BACKUP_AGE_KEY_FILE`) | `conferir`, `restaurar` |
| Bucket novo do desastre (só à mão) | `DESTINO_S3_ENDPOINT`, `DESTINO_S3_ACCESS_KEY_ID`, `DESTINO_S3_SECRET_ACCESS_KEY`, `DESTINO_S3_BUCKET` | `restaurar` |

Opcionais: `ARQUIVOS_R2_REGIAO` (padrão `auto`), `COPIA_S3_REGIAO` e `DESTINO_S3_REGIAO` (padrão:
a região tirada de `s3.<região>.backblazeb2.com`, se o endpoint for do B2; senão `auto`).
Nenhum valor é impresso; mensagens de erro citam só o **nome** da variável.

## 4. Copiar (todo dia, depois do `pg_dump`)

1. Sem nenhuma das 8 variáveis (`ARQUIVOS_R2_*` e `COPIA_S3_*`): aviso (`::warning::` e uma
   linha no resumo do job, com os **nomes** que faltam) e sai com 0. O backup do banco já
   subiu no passo anterior e nada muda nele.
2. Lista `arquivos/` no bucket de arquivos e `arquivos/` na cópia (paginado).
3. Só entra chave no formato `arquivos/<32 hexadecimais>` (as que a API cria). Outra chave em
   `arquivos/` é ignorada, contada no aviso, **sem o nome** (o log de repositório público é
   público e um nome assim poderia ser qualquer coisa).
4. Para cada chave que falta na cópia (`arquivos/<chave>.age`): baixa em fluxo, passa pelo
   `age --encrypt --recipients-file destinatarios.age` (o conteúdo em claro nunca vai para o
   disco: vai do download direto para a entrada do `age`), grava o cifrado num diretório
   temporário 700 apagado no fim, envia e confere o tamanho no destino. O tamanho baixado tem
   de bater com o da listagem.
5. Nunca apaga, nunca sobrescreve, nunca esconde: só envia o nome que **não** está na cópia.
   Uma chave que já está lá não é baixada de novo.
6. Uma falha num arquivo não para os outros; no fim, se algum falhou, sai com 1 (o GitHub manda
   e-mail) listando as chaves.
7. Resumo do job: quantos copiados agora, quantos já estavam, quantos ignorados.

## 5. Conferir (restauração de teste do dia 2, e `workflow_dispatch` com `restaurar`)

Depois do `restaurar.sh`, no banco restaurado:

1. `select chave, tipo, tamanho_bytes from arquivo where confirmado_em is not null`.
2. Nenhuma linha (a situação de hoje): passa com aviso.
3. Com linhas e sem `COPIA_S3_*`: **falha** (há arquivos publicados e não dá para provar que
   estão protegidos).
4. Toda chave tem `arquivos/<chave>.age` na cópia, maior que o tamanho original (o `age` só
   acrescenta). Faltou ou é menor: falha, listando as chaves.
5. Uma chave ao acaso (`secrets.SystemRandom`) é baixada, decifrada com `BACKUP_AGE_KEY` (em
   fluxo, sem gravar o claro) e tem: o tamanho de `tamanho_bytes` e a assinatura do `tipo`
   registrado (os mesmos bytes mágicos de `api/app/servicos/arquivos.py`). Senão, falha.

## 6. Restaurar (desastre, à mão)

`restaurar-arquivos.sh` decifra **toda** a cópia (`arquivos/<chave>.age`) para
`arquivos/<chave>` num bucket novo (`DESTINO_S3_*`), sem precisar do banco:

- o `Content-Type` vem da assinatura do conteúdo (`application/octet-stream` se não for nenhum
  dos quatro; contado no aviso);
- o arquivo decifrado fica num diretório temporário 700, apagado a cada arquivo e no fim;
- objeto que já está no destino com o mesmo tamanho é pulado (dá para rodar de novo depois de
  uma queda); com outro tamanho é falha (nunca sobrescreve);
- recusa destino com `backup` no nome (a API também recusa esse bucket);
- tamanho enviado conferido com HEAD.

## 7. Testes (`testar-ciclo.sh`)

Dois `moto` em processo: um faz o papel da Cloudflare (bucket de backups, bucket de arquivos e
o bucket novo do desastre) e outro o do B2. Chave `age` gerada no teste. Casos:

- sem as variáveis: avisa e sai 0, com os nomes e sem valor nenhum na saída;
- copia PDF, JPEG, PNG e WEBP; ignora `envios/` e chave fora do padrão; o objeto na cópia é
  `age` e decifra para os mesmos bytes;
- rodar de novo não copia nada e não muda os objetos da cópia;
- nenhum `delete`/`copy_object` no `arquivos.py` (a chave do B2 nem deixaria);
- conferência: passa com os arquivos; passa com aviso sem arquivo confirmado (backup antigo);
  falha se falta a cópia de um, com a chave errada, sem `COPIA_S3_*` havendo arquivos, e com
  conteúdo de assinatura errada;
- restauração para bucket novo: mesmos bytes, `Content-Type` certo, segunda rodada não refaz
  nada, destino com `backup` no nome é recusado.

## 8. Fora do escopo

Criar a conta e o bucket do B2, as chaves e os segredos (passo a passo do Erick, seções B e C);
rodar o workflow de verdade; qualquer mudança na API.
