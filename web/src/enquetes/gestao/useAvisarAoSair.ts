// Épico A do M4 · sair do formulário da enquete com algo escrito pergunta antes. Dentro do Portal
// pelo bloqueio do roteador; ao fechar ou recarregar a aba, pela pergunta do navegador. A
// pergunta é `PerguntaSairSemSalvar`. `liberar()` antes de navegar de propósito (depois de salvar).
import { useEffect, useRef } from 'react'
import { useBlocker } from 'react-router'

export function useAvisarAoSair(sujo: boolean) {
  const liberado = useRef(false)
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      sujo && !liberado.current && currentLocation.pathname !== nextLocation.pathname,
  )
  useEffect(() => {
    if (!sujo) return
    function avisar(evento: BeforeUnloadEvent) {
      if (liberado.current) return
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
