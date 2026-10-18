// Indicações · sair de "Indicar alguém" com algo escrito pergunta antes (como nos avisos; a
// frase dos avisos fala de anexos, que aqui não existem). Dentro do Portal pelo bloqueio do
// roteador; ao fechar a aba, pela pergunta do navegador (`useAvisarAoSair`).
import { useEffect, useRef } from 'react'
import type { Blocker } from 'react-router'
import { Icone } from '../casca/Icone'

/** Por cima da tela, com o foco em "Continuar escrevendo" (o caminho seguro). */
export function PerguntaSairSemPublicar({ blocker }: { blocker: Blocker }) {
  const ficar = useRef<HTMLButtonElement>(null)
  const bloqueado = blocker.state === 'blocked'
  useEffect(() => {
    if (bloqueado) ficar.current?.focus()
  }, [bloqueado])
  if (!bloqueado) return null
  return (
    <div className="ind-sair-fundo">
      <div
        className="ind-sair"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="ind-sair-titulo"
        aria-describedby="ind-sair-texto"
        onKeyDown={(e) => {
          if (e.key === 'Escape') blocker.reset()
        }}
      >
        <Icone nome="alerta" tamanho={28} />
        <h2 id="ind-sair-titulo">Sair sem publicar?</h2>
        <p id="ind-sair-texto">O que você escreveu na indicação vai se perder.</p>
        <button ref={ficar} type="button" className="botao" onClick={() => blocker.reset()}>
          Continuar escrevendo
        </button>
        <button type="button" className="botao leve" onClick={() => blocker.proceed()}>
          Sair sem publicar
        </button>
      </div>
    </div>
  )
}
