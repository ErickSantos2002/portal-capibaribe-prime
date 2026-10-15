// Épico A do M4 · sair do formulário da enquete com algo escrito pergunta antes (como o "Novo
// aviso"). Dentro do Portal pelo bloqueio do roteador; ao fechar ou recarregar a aba, pela
// pergunta do próprio navegador (`useAvisarAoSair.ts`).
import { useEffect, useRef } from 'react'
import type { Blocker } from 'react-router'
import { Icone } from '../../casca/Icone'

/** Por cima da tela, com o foco em "Continuar escrevendo" (o caminho seguro). */
export function PerguntaSairSemSalvar({ blocker, titulo }: { blocker: Blocker; titulo: string }) {
  const ficar = useRef<HTMLButtonElement>(null)
  const bloqueado = blocker.state === 'blocked'
  useEffect(() => {
    if (bloqueado) ficar.current?.focus()
  }, [bloqueado])
  if (!bloqueado) return null
  return (
    <div className="enq-sair-fundo">
      <div
        className="enq-sair"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="enq-sair-titulo"
        aria-describedby="enq-sair-texto"
        onKeyDown={(e) => {
          if (e.key === 'Escape') blocker.reset()
        }}
      >
        <Icone nome="alerta" tamanho={28} />
        <h2 id="enq-sair-titulo">{titulo}</h2>
        <p id="enq-sair-texto">O que você escreveu na enquete vai se perder.</p>
        <button ref={ficar} type="button" className="botao" onClick={() => blocker.reset()}>
          Continuar escrevendo
        </button>
        <button type="button" className="botao leve" onClick={() => blocker.proceed()}>
          {titulo.replace('?', '')}
        </button>
      </div>
    </div>
  )
}
