// Espera a pessoa parar de digitar antes de perguntar à API (como a busca do mural).
import { useEffect, useState } from 'react'

export function useAtrasado<T>(valor: T, ms: number): T {
  const [atrasado, setAtrasado] = useState(valor)
  useEffect(() => {
    const relogio = window.setTimeout(() => setAtrasado(valor), ms)
    return () => window.clearTimeout(relogio)
  }, [valor, ms])
  return atrasado
}
