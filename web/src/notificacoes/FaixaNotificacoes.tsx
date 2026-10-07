// Faixa "Falta um passo" no mural (revisão do épico A): quem instalou o Portal no iPhone, ou o
// segundo celular da casa, nunca passa pela oferta do primeiro acesso. Aqui o convite aparece
// onde a pessoa já está, com o botão que ativa direto (o pedido de permissão sai do toque).
//
// Só aparece quando dá para ativar de verdade: servidor com push ligado, aparelho que recebe
// (no iPhone, aberto pelo ícone), permissão não negada e este aparelho ainda sem inscrição.
// "Agora não" esconde por 30 dias neste aparelho: o convite volta, mas raramente.
import { useState } from 'react'
import { CaixaDeErro } from '../acesso/CaixaDeErro'
import { Icone } from '../casca/Icone'
import { useNotificacoes } from './useNotificacoes'
import './notificacoes.css'

/** `localStorage`: até quando (ms desde 1970) a faixa fica escondida neste aparelho. */
export const CHAVE_FAIXA = 'portal-faixa-avisos-ate'
const ESCONDIDA_POR_MS = 30 * 24 * 60 * 60 * 1000

function escondida(): boolean {
  try {
    return Number(localStorage.getItem(CHAVE_FAIXA) ?? 0) > Date.now()
  } catch {
    return false
  }
}

function esconder(): void {
  try {
    localStorage.setItem(CHAVE_FAIXA, String(Date.now() + ESCONDIDA_POR_MS))
  } catch {
    // Sem localStorage, some só até a próxima abertura do mural.
  }
}

export function FaixaNotificacoes() {
  const n = useNotificacoes()
  const [dispensada, setDispensada] = useState(escondida)
  // Ativou por aqui: a faixa confirma no lugar, em vez de sumir sem dizer nada.
  const [ativouAqui, setAtivouAqui] = useState(false)
  if (n.situacao === 'ativa' && ativouAqui) {
    return (
      <section className="notif-faixa ligada" aria-label="Notificações">
        <p className="notif-situacao ligada" role="status">
          <Icone nome="certo" />
          <span>Pronto. Os avisos vão chegar neste aparelho.</span>
        </p>
      </section>
    )
  }
  if (n.situacao !== 'inativa' || dispensada) return null

  return (
    <section className="notif-faixa" aria-label="Notificações">
      <p className="notif-faixa-texto">
        <Icone nome="sino" />
        <span>Falta um passo: ative as notificações para saber dos avisos na hora.</span>
      </p>
      {n.problema && (
        <CaixaDeErro vez={n.problema.vez}>
          <p>{n.problema.mensagem}</p>
        </CaixaDeErro>
      )}
      {n.dica && <p className="ajuda">{n.dica}</p>}
      <div className="notif-faixa-acoes">
        <button
          type="button"
          className="botao"
          disabled={n.ocupado}
          onClick={() => {
            setAtivouAqui(true)
            n.aoAtivar()
          }}
        >
          {n.ocupado ? 'Ativando…' : 'Ativar'}
        </button>
        <button
          type="button"
          className="botao leve"
          onClick={() => {
            esconder()
            setDispensada(true)
          }}
        >
          Agora não
        </button>
      </div>
    </section>
  )
}
