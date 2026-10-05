// A placa do apartamento (o elemento-assinatura do protótipo): "Bloco 1 / 101", como a
// plaquinha da porta. Ensina o login sozinha: bloco + apartamento.
import type { UnidadeRef } from '../api/tipos'

interface Props {
  unidade: UnidadeRef
  grande?: boolean
  /** Contorno amarelo: a unidade tem papel de gestão. */
  gestao?: boolean
  /** Quando o mesmo texto já está escrito ao lado. */
  decorativa?: boolean
}

export function Placa({ unidade, grande, gestao, decorativa }: Props) {
  const classes = ['placa', grande && 'grande', gestao && 'gestao'].filter(Boolean).join(' ')
  const acessivel = decorativa
    ? { 'aria-hidden': true }
    : { role: 'img', 'aria-label': `Bloco ${unidade.bloco}, apartamento ${unidade.apartamento}` }
  return (
    <span className={classes} {...acessivel}>
      <small>Bloco {unidade.bloco}</small>
      <strong>{unidade.apartamento}</strong>
    </span>
  )
}

/** A marca do Portal na entrada: a placa sem número (número ali parecia apartamento escolhido). */
export function Marca() {
  return (
    <span className="placa grande marca" aria-hidden="true">
      <small>Capibaribe</small>
      <strong>PRIME</strong>
    </span>
  )
}
