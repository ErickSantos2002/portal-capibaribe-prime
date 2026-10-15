# Spec · M4 · Épico B · Votar e resultado

| | |
|---|---|
| **Marco** | M4 · Enquetes |
| **Histórias** | H-21 (votar), H-22 (ver resultado), H-13 (botão no aviso automático) |
| **Contrato** | `docs/superpowers/specs/m4-contrato.md` (seções 2.6, 3 e 4): este spec só detalha o que o contrato deixou para o épico |
| **Plano** | `docs/superpowers/plans/m4-votar.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m4-votar.md` |

## 1. API (`app/servicos/enquetes.py`, rotas em `app/rotas/enquetes.py`)

As rotas só traduzem HTTP; as regras ficam no serviço. Nada de migração, modelo ou esquema novo.

- **Quem vê** (`_visivel`): a gestão vê todas; a unidade comum, as para todos e as do bloco dela.
  Fora disso, `404 enquete_nao_encontrada`, com a mesma mensagem da enquete que não existe.
- **Encerrada**: `encerra_em <= agora` pelo relógio da API (o banco confere de novo pelo dele,
  na hora da gravação).
- **Lista**: abertas primeiro (a que termina antes no topo), depois as encerradas (a que terminou
  por último no topo); empate pelo `id` desc. `ja_votou` da unidade logada.
- **Enquete**: opções na ordem; `votos` contados no banco (`count` por opção) e nulos para todos
  (inclusive a gestão) enquanto é "só no fim" e está aberta; participação sobre uma base só:
  as unidades do destino ativas agora ou que votaram (`votaram <= total`; revisão, dúvida 17); `pode_votar` = aberta e o bloco da unidade no destino; `pode_editar` = gestão,
  aberta e `primeiro_voto_em` nulo.
- **Votar** (`PUT …/voto`), nesta ordem: enquete visível (404) → aberta (409
  `enquete_encerrada`) → no destino (403 `fora_do_destino`) → todas as opções são desta enquete
  agora (409 `enquete_mudou`) → escolha única com mais de uma (422, campo `opcoes`, "Nesta
  enquete, escolha só uma opção.") → grava na ordem da seção 2.6 do contrato (`insert … on
  conflict do update`, `delete`, `insert`), `commit`. Erro do banco: `rollback` e
  `enquetes_banco.traduzir` (nunca 500 numa regra conhecida). Responde a `Enquete` relida
  depois do commit.
- **Votantes** (só gestão; no "durante", só depois do fim: 409 `votantes_so_no_fim`, dúvida 16):
  sobre a mesma base da participação, `votaram` (por login), e as que não votaram, separadas em `entraram_sem_votar` (`ativada_em` preenchida) e
  `nao_entraram`. Nunca em quê.

## 2. Front (`web/src/enquetes/votar/**`)

| Arquivo | O quê |
|---|---|
| `menu.ts` | "Enquetes" para toda unidade, logo depois de "Avisos" |
| `rotas.tsx` | `/enquetes` e `/enquetes/:id` atrás de `ExigeUnidade`; `/enquetes/:id/votantes` atrás de `ExigeGestao` |
| `Lista.tsx` | "Abertas" e "Terminadas"; selo "Seu apartamento ainda não votou" na cor de atenção (ipê), aberta e `ja_votou` falso, se a unidade está no destino; "Vai até …" / "Terminou em …"; botão flutuante "Nova enquete" (gestão) para `/enquetes/nova` |
| `EnqueteAberta.tsx` | pergunta; "O voto vale pelo apartamento X do Bloco Y. Dá para trocar até …"; confirmação no lugar ("Seu apartamento já votou em …. Se escolher outra, vale a nova."); opções grandes (rádio na escolha única, caixa na múltipla); "Votar" / "Trocar voto"; resultado em barras com "N votos, P%"; "só no fim": só a participação e quando o resultado aparece; terminada: "Terminou em …. O resultado não muda mais."; RN-03 em toda enquete; para a gestão: "Quais apartamentos votaram" e, se `pode_editar`, "Editar" (`/enquetes/:id/editar`) |
| `Votantes.tsx` | "N de M apartamentos votaram (P%)", e os grupos "Votaram", "Entrou, mas não votou", "Ainda não entrou no Portal", por bloco, em ordem crescente (no computador, 8 por linha e cada andar começa a linha), com "Copiar a lista" de quem falta (na mesma ordem) |
| `EnqueteDoAviso.tsx` | o cartão "Ir para a enquete" com a pergunta e o estado ("Aberta · vai até …" / "Terminou · ver o resultado"), logo depois do cabeçalho do aviso automático, antes do texto |
| `formatos.ts` | datas na voz do morador ("10 de novembro, às 20h"), porcentagem, ordem da lista |
| `enquetes.css` | barras, opções e cartões; tokens do `estilo.css` (mata, ipê) |

Voto óbvio e difícil de errar: o botão só fica ativo com a escolha feita (na troca, só se a
escolha mudou); erro do servidor aparece no lugar, acima do botão, e a escolha não se perde.
Depois de votar, a tela troca pela `Enquete` da resposta e o foco vai para a confirmação.

Ajustes das revisões finais do M4 (dúvidas do B, itens 24 a 26): um 422 do voto também recarrega
a enquete; ao recarregar, a escolha fica só com as opções que ainda existem (senão, o voto
gravado); escolha diferente do voto gravado mostra "Você ainda não trocou o voto. Toque em
**Trocar voto** para valer." (`aria-live` educado); depois do voto, a legenda vira "Quer trocar?
…"; quem não vota vê "Vai até …"; porcentagem entre 0 e 1 é "menos de 1%"; na múltipla, uma
linha explica a soma acima de 100%; terminada, a mais votada ganha o selo "Mais votada".

## 3. Testes

- API: `test_enquetes_voto.py` (votar, trocar, regras, concorrência pela API com duas
  requisições em paralelo da mesma unidade) e `test_enquetes_resultado.py` (lista, resultado,
  "só no fim", participação, votantes).
- Front: `votar/votar.test.tsx` (telas pela API falsa) e `votar/formatos.test.ts`.
