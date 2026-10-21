# ADR-0012 · Fotos dos classificados: descartáveis, numa pasta sem trava

| | |
|---|---|
| **Status** | Aceita (20/10/2026, classificados 1.9.0) |
| **Data** | 20/10/2026 |
| **Complementa** | [ADR-0011](0011-arquivos-protegidos-contra-perda.md) (arquivos protegidos contra perda) e [ADR-0004](0004-arquivos-r2.md) (arquivos no R2) |

## Contexto
Os classificados entre vizinhos (spec `docs/superpowers/specs/2026-10-20-classificados-design.md`)
deixam cada anúncio ter até 4 fotos. A ADR-0011 trava `arquivos/` no R2 para sempre e copia tudo
o que está lá para o bucket de backups, cifrado: certo para documento oficial, errado para a foto
de uma geladeira usada. O anúncio acaba em dias; a foto pode mostrar o interior do apartamento
(LGPD: minimização e retenção curta), e os 10 GB grátis do R2 já somam arquivos, cópia e dumps.

O que se quer: a foto **some de verdade** quando o anúncio acaba, sem ninguém precisar lembrar, e
o resto do bucket continua com a garantia da ADR-0011.

## Decisão

### 1. Pasta própria, sem trava
- As fotos moram em **`classificados/<chave>`**, no mesmo bucket de arquivos. A trava do R2 é por
  prefixo (`arquivos/`), então esta pasta **não** é travada. **Conferir no bucket real antes do
  push**, com um objeto de teste: enviar e apagar (o coordenador faz).
- A chave é a mesma da ADR-0011: 32 hexadecimais aleatórios (128 bits), nunca reaproveitados.
- O envio é o do M3 (`envios/<chave>` por URL assinada → conferência do tamanho e dos bytes do
  começo → cópia), com o destino em `classificados/` e só imagem (JPEG, PNG, WEBP; PDF é
  recusado). A compressão no navegador é a mesma, e **toda** foto é regravada, JPEG, PNG ou WEBP,
  mesmo pequena (sai o GPS e qualquer outro metadado; `comprimir(…, sempreRegravar)`, revisão
  M1). Os anexos do M3 continuam como eram.
- A leitura é por link assinado de 1 hora (`VALIDADE_LEITURA`), como os anexos; a capa da lista
  vem no mesmo formato.

### 2. Um único "apagar" novo, que só aceita `classificados/`
A camada de armazenamento (`api/app/servicos/armazenamento.py`) ganha `apagar_classificado(caminho)`,
que recusa (`ValueError`, antes de falar com o bucket) qualquer coisa que não seja exatamente
`classificados/<32 hexadecimais>`: `arquivos/…`, `envios/…`, caminho com `..`, maiúsculas, barra no
começo. O armazenamento falso dos testes imita. Teste: `api/testes/test_classificados_fotos.py`.
O `test_nao_existe_jeito_de_apagar_o_publicado` (M3) lista os métodos públicos e passa a conhecer
este.

### 3. Tabela própria, `anuncio_foto`, e não a `arquivo`
O `arquivo` confirmado é "para sempre": a trigger da 0007 recusa apagar, a cópia diária copia todo
`arquivos/`, e a conferência do dia 2 exige cópia de **todo** `arquivo` confirmado. Pôr a foto lá
pediria três exceções (na trigger, na finalidade e no `conferir-arquivos.sh`) e enfraqueceria a
regra simples "publicado = para sempre". A tabela própria (migração 0011) não pede nenhuma: o
`arquivo` e os scripts de backup continuam iguais.

A `anuncio_foto` guarda só a chave, o tipo, o tamanho e a ordem (a 0 é a capa). Estados:
pendente → pronta (confirmada, sem anúncio) → no anúncio → descartada. O banco garante: até 4 por
anúncio, da mesma unidade, só confirmada entra, só sai do anúncio descartada, descartada não volta,
40 fotos enviadas por unidade a cada 24 horas. O anúncio com foto presa **não** é apagado (chave
estrangeira sem cascata): quem apaga descarta as fotos antes, e o objeto nunca fica órfão no bucket.
Revisão de código (B1): a trigger também recusa apagar a linha de foto que não foi descartada, e
anúncio vencido não recebe foto nova.

### 4. Apagar de verdade: descartar e varrer
Tirar a foto na edição, encerrar ou ser escondido (depois de 7 dias, para o dono ainda ver em
"Meus anúncios"), vencer (depois de 30 dias), "apagar meus dados" (H-06) e o reset (H-08)
**descartam** a foto na transação. Depois do commit, `varrer` apaga o objeto no bucket (sempre os
dois lugares, `envios/<chave>` e `classificados/<chave>`: a cópia pode ter chegado ao bucket sem a
confirmação gravada, revisão M2) e a linha (a linha da
foto enviada há menos de 1 dia fica, descartada e sem o conteúdo, só para contar no limite do
dia; sem isso, mandar e tirar não teria fim). Se o bucket falhar, a foto continua descartada e a
faxina tenta de novo: nada quebra.

### 5. Faxina diária pelo Vercel Cron
- `vercel.json` ganha `crons`: `GET /api/classificados/faxina` às 07:00 UTC (04:00 em Recife). O
  plano Hobby permite 1 vez por dia, e a Vercel escolhe o minuto dentro da hora.
- A rota exige `Authorization: Bearer <CRON_SECRET>`, que a Vercel manda sozinha quando a variável
  `CRON_SECRET` existe no projeto. Sem a variável, responde 503 e não faz nada; com outro valor,
  401. Comparação em tempo constante.
- Cada rodada apaga o anúncio vencido há mais de 30 dias e o encerrado ou escondido pela gestão há
  mais de 7 (com os avisos e as fotos), descarta a foto enviada há mais de 1 dia e nunca posta num anúncio, e varre todas
  as descartadas. Quando apaga alguma coisa, registra `classificados_faxina` no histórico (só as
  contagens), o que deixa ver na tela do Histórico se o cron está rodando.
- **Falhar só atrasa:** a lista já esconde o vencido pela data (a consulta compara `vence_em` com
  o relógio do banco), e a rodada seguinte faz tudo o que ficou.

### 6. Fora da cópia diária
As fotos não entram na cópia cifrada da ADR-0011: o script só lista `arquivos/`. Depois de um
desastre, o banco volta com os anúncios, mas sem as fotos (aceito: são efêmeras, e o anúncio
continua com o texto e o contato).

## Consequências
- A foto some sem trabalho manual. Um anúncio vive no máximo 30 dias aberto (renovável) e mais 30
  vencido, ou 7 depois de encerrado.
- Uma chave vazada da API consegue apagar fotos de classificados (a pasta não tem trava), mas
  nunca um documento ou anexo: `arquivos/` continua travada no R2, e a camada da API nem tem como
  pedir isso.
- Espaço: no uso esperado, algumas centenas de MB, e a faxina segura o teto.
- Mais uma variável de ambiente na Vercel (`CRON_SECRET`, Production). Sem ela, a faxina fica
  desligada e os anúncios vencidos só saem da lista.

## Alternativas consideradas
- **Workflow diário do GitHub chamando a rota protegida** (como o `Backup`): daria e-mail do GitHub
  quando falhasse, mas pede um segredo a mais no GitHub, a URL de produção no workflow e mais uma
  peça entre os dois. O Vercel Cron mora no mesmo `vercel.json` e manda o segredo sozinho. Fica
  como plano B se o cron do Hobby mudar: a rota é a mesma.
- **Faxina "de passagem"** (rodar a limpeza quando alguém abre a lista): sem infraestrutura nova,
  mas o prazo prometido na Privacidade (7 e 30 dias) dependeria de alguém abrir os classificados.
- **Reaproveitar a tabela `arquivo` com uma finalidade nova:** três exceções na regra do
  "publicado = para sempre" (seção 3).
- **Guardar as fotos travadas, como os documentos:** contraria a minimização da LGPD e enche o R2
  grátis com coisa que ninguém mais vai abrir.
- **Ciclo de vida do R2 na pasta `classificados/`** (apagar depois de N dias): o anúncio renovado
  perderia as fotos, e o encerrado ficaria com elas até o prazo. Quem sabe quando a foto acaba é o
  banco.
