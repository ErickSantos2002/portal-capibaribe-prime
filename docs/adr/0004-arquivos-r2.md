# ADR-0004 · Arquivos no Cloudflare R2, bucket privado com URLs assinadas

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 02/10/2026 |

## Contexto
Avisos e documentos têm PDFs e imagens: estimativa de 1 a 3 GB em 2 anos. Documentos de nível
"gestão" não podem vazar. A Vercel não aceita requisições acima de 4,5 MB.

## Decisão
Cloudflare R2, **um bucket privado**. Envio e download por **URLs assinadas** geradas pela API
depois de conferir a permissão: envio válido por 10 minutos, download por 5 minutos. O navegador
fala direto com o R2. Imagens são comprimidas no navegador antes do envio (lado maior até
1920 px, WEBP). Tipos aceitos: PDF, JPEG, PNG, WEBP, conferidos pelo conteúdo do arquivo.
O mesmo R2 guarda os backups do banco (ADR-0007), numa pasta separada.

## Consequências
- 10 GB grátis, sem custo de download (02/10/2026).
- O R2 pede **um cartão cadastrado** para ativar, como verificação. Só cobra acima da cota.
  Alerta de uso configurado em 70% da cota.
- API compatível com S3: dá para trocar de provedor sem reescrever.

## Alternativas consideradas
- **Vercel Blob:** sem cartão, mas só 1 GB grátis, e ao estourar os arquivos ficam inacessíveis
  por 30 dias. Com a estimativa de 1 a 3 GB, o risco é alto.
- **Guardar no Postgres:** estoura o 1 GB do Neon e deixa o banco lento. Descartado (RNF-22).
