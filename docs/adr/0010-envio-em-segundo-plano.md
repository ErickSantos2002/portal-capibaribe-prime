# ADR-0010 · Notificações depois da resposta, com `wait_until` e caixa de saída no banco

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 06/10/2026 |
| **Complementa** | [ADR-0002](0002-hospedagem-vercel.md) (Vercel) e [ADR-0006](0006-notificacoes.md) (push e e-mail) |

## Contexto
Publicar um aviso (H-12) dispara push para até ~1.000 aparelhos e cópia por e-mail para até
320 unidades (H-13). Pelo Gmail, uma mensagem por unidade leva de 0,3 a 1 s: até alguns
minutos. A Comissão não pode ficar esperando isso na tela de publicar, e o "esqueci a senha"
(H-04) não pode demorar mais quando a unidade tem e-mail do que quando não tem (o tempo
revelaria quem tem e-mail).

A API é uma função Python na Vercel (ADR-0002). Pergunta: o que roda depois da resposta?

- `BackgroundTasks` do FastAPI roda **dentro** da chamada ASGI, depois do corpo da resposta.
  A documentação da Vercel não diz se a invocação continua viva nesse intervalo. No código do
  runtime (`vercel-runtime`, `vc_init.py`), até a 0.22 havia um modo antigo que juntava a
  resposta inteira e só a devolvia quando a chamada ASGI terminava (o `BackgroundTasks`
  atrasaria a resposta); na **0.23.2** (conferida em 06/10/2026) esse ciclo saiu, e os dois
  caminhos passam pelo mesmo servidor ASGI, que manda a resposta antes. Mesmo assim, é o
  comportamento de hoje de um código interno, não um contrato documentado: pode mudar numa
  atualização sem aviso.
- O runtime Python 0.18 trouxe `wait_until` por invocação ("drained after the response is
  sent, bounded by the Function's maximum duration", changelog do `vercel-runtime`), exposto
  pelo SDK oficial: `from vercel.functions import wait_until`, que recebe um awaitable (trabalho
  síncrono vai como `asyncio.to_thread(...)`). Fora da Vercel ele **não roda nada**.
- Vercel Queues ou Workflow resolveriam com entrega garantida, mas são outro serviço, com
  cobrança própria, para ~3 avisos por semana.
- Cron do plano Hobby roda no máximo uma vez por dia: não serve para notificação.

## Decisão
1. **Caixa de saída no banco:** a publicação grava, na mesma transação do aviso, uma linha
   `pendente` em `notificacao_envio` por canal (`push`, `email`). Chave única (aviso, canal).
2. **Depois da resposta:** `app/servicos/segundo_plano.agendar` usa `wait_until` na Vercel
   (`VERCEL=1`) e `BackgroundTasks` fora dela (uvicorn local e testes).
3. **No máximo uma vez:** cada canal é reivindicado por um `UPDATE … where situacao =
   'pendente'`; só um processo ganha. Se a função morre no meio, o envio fica `interrompido`
   com as contagens até ali, e **não é repetido** (avisar duas vezes incomoda mais que uma
   notificação a menos; o mural continua sendo o registro oficial).
4. **Faxina a cada publicação:** `enviando` há mais de 10 minutos vira `interrompido`;
   `pendente` com mais de 24 horas também (aviso de ontem não vale notificação); `pendente`
   recente de outro aviso (trabalho que se perdeu) é enviado junto com o novo.
5. O "esqueci a senha" usa o mesmo `agendar`, com o pedido **inteiro** (consulta da unidade,
   cota, token, histórico) depois da resposta: a rota não abre o banco, e a resposta sai igual
   e no mesmo tempo, tenha ou não e-mail.
6. **Cabe no tempo da função** (revisão do contrato): os canais de um aviso rodam em paralelo
   (o e-mail, lento, não atrasa o push), com prazo comum de 240 s; o que não couber vira
   `pulados`, visível em `/envios`. As contagens vão para o banco aos poucos.
7. **A cota do Gmail é reservada antes de mandar**, com trava (`pg_advisory_xact_lock`) e
   gravada na hora (`notificacao_envio.reservados`): uma função que morre no meio continua
   contando na cota, e dois envios ao mesmo tempo não passam juntos do limite. Estourar o Gmail
   bloqueia a conta por até um dia, e com ela o "esqueci a senha".

## Consequências
- Publicar responde na hora; push e e-mail saem segundos depois, dentro dos 300 s da função
  (Hobby com Fluid compute). Push em paralelo cabe folgado; ~320 e-mails a 0,3-1 s cada podem
  não caber em 240 s, e o que sobrar fica `pulados` (medido, não perdido em silêncio).
- Dependência nova: o pacote `vercel` (SDK oficial). Se a Vercel não der o contexto do
  `wait_until` (runtime antigo), o trabalho se perde **em silêncio**, mas o envio fica
  `pendente` e sai na próxima publicação (passo 4). O link de recuperação não tem essa rede: a
  tela já diz "se não chegou, fale com a administração".
- `GET /api/avisos/{id}/envios` mostra para a gestão como foi cada canal (só contagens).
- Medir de verdade em produção, no portão do M2: publicar um aviso e conferir que a resposta
  volta antes de os e-mails terminarem e que o envio fica `concluido`.

## Alternativas consideradas
- **Mandar tudo dentro da requisição:** simples, mas a tela de publicar esperaria minutos e o
  "esqueci a senha" revelaria pelo tempo quem tem e-mail.
- **Só `BackgroundTasks`:** funciona pelo código de hoje do runtime (0.23.2), mas não é
  contrato documentado; até a 0.22, num dos modos, atrasava a resposta.
- **Vercel Queues:** entrega garantida e novas tentativas; custo e peça a mais para um volume
  pequeno. Reavaliar se a perda de envios aparecer nas contagens.
- **O próprio front chamar uma rota "notificar" depois de publicar:** depende do aparelho de
  quem publica continuar aberto e cria uma rota a mais para proteger.
