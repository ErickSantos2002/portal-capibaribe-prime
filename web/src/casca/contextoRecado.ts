// Recado de confirmação ("Aviso publicado."), numa região de status que o leitor de tela anuncia.
import { createContext, useContext } from 'react'

export const ContextoRecado = createContext<(mensagem: string) => void>(() => {})

/** `const recado = useRecado(); recado('Aviso publicado.')` */
export function useRecado(): (mensagem: string) => void {
  return useContext(ContextoRecado)
}
