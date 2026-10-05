// Caixa de erro em cima do formulário (como no protótipo): o leitor de tela anuncia
// (role="alert"). O foco vai para o campo com problema, se houver; senão, para a caixa.
import { useEffect, useRef, type ReactNode } from 'react'
import { Icone, type NomeDoIcone } from '../casca/Icone'

interface Props {
  children: ReactNode
  icone?: NomeDoIcone
  /** Muda a cada erro novo, para o foco voltar mesmo com a mesma mensagem. */
  vez?: number
  /** `id` do campo que recebe o foco; sem ele, a própria caixa recebe. */
  focar?: string
}

export function CaixaDeErro({ children, icone = 'alerta', vez, focar }: Props) {
  const caixa = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const campo = focar ? document.getElementById(focar) : null
    ;(campo ?? caixa.current)?.focus()
  }, [vez, focar])
  return (
    <div ref={caixa} className="aviso-caixa erro" role="alert" tabIndex={-1}>
      <Icone nome={icone} />
      <div>{children}</div>
    </div>
  )
}
