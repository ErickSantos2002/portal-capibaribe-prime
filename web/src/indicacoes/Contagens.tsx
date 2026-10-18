// Indicações · as contagens do cartão e do prestador aberto. Zero recomendações não aparece
// verde com 👍 (diria o contrário do que é): fica só o "N não recomendam" ou, sem nenhuma
// opinião visível, o texto neutro.
import { naoRecomendamEmTexto, recomendamEmTexto } from './formatos'

interface Props {
  recomendam: number
  naoRecomendam: number
  /** No prestador aberto, o 👎 também vem antes do "não recomendam". */
  comPolegarNoNao?: boolean
}

export function Contagens({ recomendam, naoRecomendam, comPolegarNoNao = false }: Props) {
  if (recomendam === 0 && naoRecomendam === 0) {
    return <span className="ind-sem-opiniao">{recomendamEmTexto(0)}</span>
  }
  return (
    <>
      {recomendam > 0 && (
        <span className="ind-recomendam">
          <span aria-hidden="true">👍 </span>
          {recomendamEmTexto(recomendam)}
        </span>
      )}
      {naoRecomendam > 0 && (
        <span className="ind-nao-recomendam">
          {comPolegarNoNao && <span aria-hidden="true">👎 </span>}
          {naoRecomendamEmTexto(naoRecomendam)}
        </span>
      )}
    </>
  )
}
