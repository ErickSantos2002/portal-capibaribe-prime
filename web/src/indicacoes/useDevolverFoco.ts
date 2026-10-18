// Indicações · quando um formulário ou uma pergunta que abre na própria tela fecha (Cancelar,
// Manter, salvou), o foco volta ao botão que a abriu. Sem isso, ele caía no body e quem usa
// teclado ou leitor de tela recomeçava do topo (revisão das indicações).
import { useEffect, useRef } from 'react'

/** O `ref` vai no botão que abre; `aberto` é o estado do que ele abre. */
export function useDevolverFoco<T extends HTMLElement>(aberto: boolean) {
  const botao = useRef<T>(null)
  const estavaAberto = useRef(aberto)
  useEffect(() => {
    if (estavaAberto.current && !aberto) botao.current?.focus()
    estavaAberto.current = aberto
  }, [aberto])
  return botao
}
