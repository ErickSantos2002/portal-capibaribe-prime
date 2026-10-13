// M3 · Épico B (revisão de UX, U1): sair do formulário do aviso no meio pede confirmação.
// Dentro do Portal (seta do topo, menu, voltar do navegador) pelo `useBlocker` do roteador; ao
// recarregar ou fechar a aba, pelo aviso do próprio navegador (`beforeunload`). A pergunta é
// `PerguntaSairSemPublicar`.
import { useEffect, useRef } from 'react'
import { useBlocker } from 'react-router'

/** `sujo`: há texto ou anexos que se perderiam. `liberar()` antes de navegar de propósito
 *  (depois de publicar ou salvar), para a pergunta não aparecer. */
export function useAvisarAoSair(sujo: boolean) {
  const liberado = useRef(false)
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      sujo && !liberado.current && currentLocation.pathname !== nextLocation.pathname,
  )
  useEffect(() => {
    if (!sujo) return
    function avisar(evento: BeforeUnloadEvent) {
      evento.preventDefault()
      // Navegadores antigos só perguntam com `returnValue` preenchido.
      evento.returnValue = ''
    }
    window.addEventListener('beforeunload', avisar)
    return () => window.removeEventListener('beforeunload', avisar)
  }, [sujo])
  return {
    blocker,
    liberar() {
      liberado.current = true
    },
  }
}
