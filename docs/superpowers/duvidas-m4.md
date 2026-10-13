# Dúvidas e decisões do M4 · Onda 1 (contrato)

Decisões tomadas sem perguntar a ninguém durante a onda do contrato do M4 (enquetes). Cada item:
a dúvida, o que foi decidido e por quê. **[Erick]** marca o que só o Erick pode confirmar (regra
do condomínio, preferência dele, o que a Comissão usaria); o resto é decisão técnica que pode ser
revista na revisão do marco.

Os agentes dos épicos registram as próprias dúvidas em `duvidas-m4-gestao.md` (épico A) e
`duvidas-m4-votar.md` (épico B).

## 1. Dois épicos, rotas já declaradas respondendo 501
- **Dúvida:** como deixar dois agentes trabalharem em paralelo sem brigar pelo roteador, pelo
  contrato e pela migração.
- **Decisão:** como no M3: todas as rotas do M4 declaradas com sessão, permissão, CSRF e
  validação de verdade, e só o corpo responde `501 em_construcao`. Um roteador por épico com o
  mesmo prefixo (`rotas/enquetes.py` do B, `rotas/enquetes_gestao.py` do A): os caminhos não se
  cruzam e nenhum épico edita o arquivo do outro. No front, `enquetes/gestao/` (A) e
  `enquetes/votar/` (B), com `tipos.ts`, `api.ts`, `caminhos.ts` e `rotas.tsx` comuns e prontos.
- **Por quê:** a divisão natural das histórias é "quem cria" (H-20) e "quem vota e vê" (H-21,
  H-22); as duas só se tocam pelo banco (pronto) e pelos endereços das telas (`caminhos.ts`).

## 2. "Mostrar resultado" é `text` com `CHECK`, e a coluna mudou de nome
- **Dúvida:** o modelo de dados falava em `resultado` do tipo `enum exibicao_resultado`.
- **Decisão:** coluna `mostrar_resultado`, `text` com `CHECK in ('durante', 'so_no_fim')`.
- **Por quê:** o padrão do repositório desde a 0004 (categoria do aviso, do documento) é `text` +
  `CHECK`: acrescentar um valor é trocar um `CHECK`, sem `ALTER TYPE`. E `resultado` como nome de
  coluna confundia com o resultado da votação (os votos), que aparece na mesma tela e na mesma
  resposta da API.

## 3. Depois do 1º voto, nada muda na enquete, nem o prazo · [Erick]
- **Dúvida:** H-20 diz que "pergunta e opções" não mudam depois do 1º voto. E o término, o tipo
  de escolha e o "mostrar resultado"? Prorrogar uma enquete com pouca participação é comum em
  condomínio; encerrar antes do prazo também aparece ("já deu maioria").
- **Decisão:** **nada** muda depois do 1º voto (a leitura estrita do roadmap: "nada de editar
  depois do 1º voto"), e nada muda depois do encerramento, mesmo sem voto (RF-25: uma enquete
  terminada não reabre mudando a data). Antes do 1º voto, tudo muda menos o destino (item 5).
- **Por quê:** mudar o prazo depois de ver os votos é a manipulação mais fácil (encerrar quando o
  resultado agrada). Com a regra no banco, nem a Comissão nem o administrador conseguem; se o
  grupo pedir prorrogação, é uma regra nova, com migração, e vale decidir com calma: "só
  prorrogar, nunca encurtar, e avisar todo mundo" seria o caminho.
- **Confirmar:** se a Comissão vai querer prorrogar (ou encerrar antes) enquetes já votadas.

## 4. "Só no fim" vale também para a gestão · [Erick]
- **Dúvida:** H-22 diz que, no "só no fim", antes do encerramento aparece apenas a
  participação. Isso vale para a Comissão também?
- **Decisão:** vale para todos, inclusive a gestão e o administrador: `votos` de cada opção vem
  nulo na API para todo mundo enquanto a enquete está aberta. A gestão continua vendo **quem**
  votou (nunca em quê), para cobrar participação.
- **Por quê:** "só no fim" existe para o resultado parcial não influenciar o voto. Se a Comissão
  visse, ela poderia (sem querer) influenciar no grupo, e a desconfiança sobre quem organiza é
  o que o Portal quer evitar (visão, O2). E fica mais simples de explicar: "ninguém vê antes".
- **Confirmar:** se a Comissão precisa ver o parcial de uma enquete "só no fim".

## 5. Destino não muda depois de criada
- **Dúvida:** antes do 1º voto, dá para mudar o destino (todos ↔ blocos)?
- **Decisão:** não. O destino só entra na transação que cria a enquete
  (`enquete_destino_fechado`) e `para_todos` não está nas colunas que o `app` altera.
- **Por quê:** o aviso automático tem o mesmo destino, e o destino do aviso não muda (M1). Mudar
  só o da enquete deixaria gente vendo o aviso de uma enquete que não pode abrir (ou o
  contrário). Errou o destino antes de alguém votar: a Comissão cria outra (e o item 9 fala do
  cancelamento).

## 6. "Só vota quem está no destino" também no banco
- **Dúvida:** o modelo de dados deixava essa regra para a aplicação.
- **Decisão:** a aplicação confere (404 para quem não vê, 403 para a gestão fora do destino) e o
  banco também (`voto_fora_do_destino`).
- **Por quê:** é uma consulta só na trigger que já existe para o prazo; regra importante não
  depende só da API (RNF-13). O modelo de dados foi atualizado.

## 7. O voto não é retirado, só trocado · [Erick]
- **Dúvida:** a unidade que votou pode "desfazer" o voto (voltar a não ter votado)?
- **Decisão:** não. O `app` não tem DELETE em `voto`; dá para trocar até o prazo (H-21).
- **Por quê:** RN-05 (o que é oficial não some) e o modelo de dados já tiravam o DELETE de
  `voto`. Retirar o voto também mexeria na participação de um jeito difícil de explicar.
- **Confirmar:** se alguém do grupo vai sentir falta de "não quero mais votar".

## 8. "Enquete encerrada" não vira linha no histórico
- **Dúvida:** H-11 lista "enquete criada/encerrada" no histórico.
- **Decisão:** `enquete_criada` e `enquete_editada` existem (com as frases prontas); "encerrada"
  não: o encerramento é o relógio passando do `encerra_em`, sem autor e sem um momento em que
  alguma coisa seja gravada (o Portal não tem tarefa agendada). A data do encerramento está na
  própria enquete. O voto também não vai para o histórico (dado sobre o comportamento das
  pessoas, sem uso; modelo, seção 3.5).
- **Por quê:** gravar o encerramento pediria um agendador (Vercel Cron) só para isso. Se um dia
  houver "encerrar antes" (item 3), aí sim é uma ação com autor e entra no histórico.

## 9. Fica para depois: cancelar, texto explicativo, aviso de "terminou" · [Erick]
- **Dúvida:** três coisas que as histórias não pedem, mas que podem aparecer no uso real.
- **Decisão:** ficam fora do M4: (a) **cancelar** uma enquete criada por engano (hoje ela pode
  ser editada antes do 1º voto, mas não some; RN-05); (b) um **texto explicativo** além da
  pergunta (ex.: os orçamentos de cada opção); por ora, a Comissão publica um aviso com o
  detalhe, ou anexa no aviso; (c) **notificar quando a enquete termina** (pediria agendador,
  item 8).
- **Confirmar:** se alguma delas é necessária já para a primeira enquete real da Comissão.

## 10. Criar e editar respondem só o id (`EnqueteGravada`)
- **Dúvida:** no padrão do Portal, criar devolve o recurso inteiro (`Documento`,
  `AvisoCompleto`). A `Enquete` completa (resultado, participação, meu voto) é montada pelo
  épico B.
- **Decisão:** `POST` e `PUT /api/enquetes…` devolvem `EnqueteGravada` (`id`, `aviso_id`), e a
  tela vai para `/enquetes/{id}`, que carrega a `Enquete`.
- **Por quê:** assim o épico A não depende do código do B, e os dois rodam em paralelo de
  verdade. Custa uma requisição a mais depois de publicar, que a gestão faz poucas vezes por mês.

## 11. Limites: pergunta até 200 letras, opção até 100, término em até 1 ano · [Erick]
- **Dúvida:** as histórias não dão tamanhos.
- **Decisão:** pergunta de 1 a 200 caracteres (o título do aviso tem 120; uma pergunta
  costuma ser mais longa), opção de 1 a 100, término no futuro e em até 1 ano (366 dias no
  banco, por causa do ano bissexto). Opções em branco são descartadas antes de contar (como o
  protótipo); opções iguais (ignorando maiúsculas e espaços) são recusadas.
- **Por quê:** valores folgados para o uso normal e que cabem na tela do celular; o limite do
  prazo evita enquete esquecida aberta e datas que o driver não lê de volta (achado 1 do M1).
- **Confirmar:** se 200/100 letras e 1 ano bastam para o que a Comissão pergunta.

## 12. O aviso automático é sempre criado · [Erick]
- **Dúvida:** H-20 diz "publicar a enquete gera aviso automático". Opcional, como o "Avisar as
  unidades" do documento?
- **Decisão:** sempre: `enquete.aviso_id` é obrigatório no banco. Título "Enquete nova:
  <pergunta>" (cortado em 120 letras), mesmo destino, notificação como qualquer aviso. Editar a
  enquete corrige o aviso (versão nova, sem notificar de novo), com o `gravar_correcao` que esta
  onda separou do `corrigir`.
- **Por quê:** enquete que ninguém fica sabendo não tem participação, e participação é o
  critério de sucesso do roadmap (30% do destino). O aviso no mural também é o registro de que a
  enquete existiu.
- **Confirmar:** se a Comissão vai querer, alguma vez, criar enquete "em silêncio".

## 13. A participação é contada na hora, sobre as unidades ativas do destino
- **Dúvida:** "% das unidades do destino" (H-22): o total é o de quando a enquete foi criada ou
  o de agora?
- **Decisão:** o de agora: unidades ativas (`unidade.ativa`) dos blocos do destino, como o "Lido
  por X de Y" do aviso. Os votos de uma unidade desativada depois continuam contando.
- **Por quê:** a lista de unidades só muda pelo H-10 (M5), raramente; guardar o total na
  enquete seria mais uma coluna para manter certa. Se o H-10 desativar unidades com enquete
  encerrada, a porcentagem antiga muda um pouco; os votos, não (RF-25).

## 14. A gestão vê todas as enquetes, mas só vota no destino
- **Dúvida:** uma Comissão do Bloco 2 vê a enquete só do Bloco 1?
- **Decisão:** vê (como o mural: a gestão vê todos os avisos), com `pode_votar` falso; votar dá
  403 `fora_do_destino` (e o banco recusa). A unidade comum fora do destino recebe 404, igual a
  enquete inexistente (H-21).
- **Por quê:** quem cria precisa acompanhar a enquete que criou, mesmo que não seja do bloco
  dela.

## 15. Prazo pelo relógio do banco na hora da gravação
- **Dúvida:** `now()` no Postgres é o início da transação; um voto que começou às 19:59:59 e
  gravou às 20:00:01 passa?
- **Decisão:** não: as triggers do voto usam `clock_timestamp()` (a hora de verdade da
  gravação). A criação e a edição usam `now()` (o prazo precisa estar no futuro, com folga de
  sobra).
- **Por quê:** "nada de voto depois do prazo" sem exceção de milissegundos; fica fácil de
  explicar e de testar.
