// M3 · Épico B (revisão de UX, U1): a pergunta "Sair sem publicar?" (`useAvisarAoSair`).
import { useEffect, useRef } from 'react'
import type { Blocker } from 'react-router'
import { Icone } from '../casca/Icone'

/** A pergunta, por cima da tela, com o foco em "Continuar escrevendo" (o caminho seguro). */
export function PerguntaSairSemPublicar({ blocker }: { blocker: Blocker }) {
  const ficar = useRef<HTMLButtonElement>(null)
  const bloqueado = blocker.state === 'blocked'
  useEffect(() => {
    if (bloqueado) ficar.current?.focus()
  }, [bloqueado])
  if (!bloqueado) return null
  return (
    <div className="sair-fundo">
      <div
        className="sair-pergunta"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="sair-titulo"
        aria-describedby="sair-texto"
        onKeyDown={(e) => {
          if (e.key === 'Escape') blocker.reset()
        }}
      >
        <Icone nome="alerta" tamanho={28} />
        <h2 id="sair-titulo">Sair sem publicar?</h2>
        <p id="sair-texto">O que você escreveu e os anexos vão se perder.</p>
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
