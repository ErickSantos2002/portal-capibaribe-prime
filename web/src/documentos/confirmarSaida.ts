// Épico A do M3 · revisão UX, U5: sair de "Novo documento" ou "Enviar nova versão" com algo
// escrito (ou no meio do envio) pergunta antes. Pertence ao épico A (o épico B faz o mesmo no
// formulário do aviso, com a solução dele).
//
// Duas saídas: dentro do Portal (voltar, menu, link), pelo bloqueio do roteador; fechar a aba
// ou recarregar, pelo `beforeunload` (o navegador mostra a pergunta dele). Depois de publicar,
// `liberar()` deixa a tela ir para o documento sem perguntar.
import { useCallback, useEffect, useRef } from 'react'
import { useBlocker } from 'react-router'

const PERGUNTA = 'Sair sem publicar? O que você escreveu e o arquivo escolhido vão se perder.'

export function useConfirmarSaida(temAlgo: boolean): { liberar: () => void } {
  const liberado = useRef(false)
  const bloqueio = useBlocker(
    useCallback(
      ({ currentLocation, nextLocation }) =>
        temAlgo && !liberado.current && currentLocation.pathname !== nextLocation.pathname,
      [temAlgo],
    ),
  )

  useEffect(() => {
    if (bloqueio.state !== 'blocked') return
    if (window.confirm(PERGUNTA)) bloqueio.proceed()
    else bloqueio.reset()
  }, [bloqueio])

  useEffect(() => {
    if (!temAlgo) return
    function aoSair(evento: BeforeUnloadEvent) {
      if (liberado.current) return
      evento.preventDefault()
      // Navegadores antigos só perguntam com `returnValue` preenchido.
      evento.returnValue = ''
    }
    window.addEventListener('beforeunload', aoSair)
    return () => window.removeEventListener('beforeunload', aoSair)
  }, [temAlgo])

  return {
    liberar: useCallback(() => {
      liberado.current = true
    }, []),
  }
}
