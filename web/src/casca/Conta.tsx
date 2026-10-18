// A plaquinha com o número de não lidos: na aba da barra, no menu lateral e na folha do Menu.
import type { Lugar } from './menu'

export function Conta({ lugar, naoLidos }: { lugar: Lugar; naoLidos: number }) {
  if (lugar.contador !== 'nao-lidos' || naoLidos <= 0) return null
  return (
    <span className="conta" aria-label={`${naoLidos} não lidos`}>
      {naoLidos}
    </span>
  )
}
