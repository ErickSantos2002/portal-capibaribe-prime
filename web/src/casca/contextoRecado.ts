// Recado de confirmação ("Aviso publicado."), numa região de status que o leitor de tela anuncia.
import { createContext, useContext } from 'react'

export const ContextoRecado = createContext<(mensagem: string) => void>(() => {})

/** `const recado = useRecado(); recado('Aviso publicado.')` */
export function useRecado(): (mensagem: string) => void {
  return useContext(ContextoRecado)
}

/** Onde a caixa do recado aparece: a tela registra o lugar dela (no topo), e o recado ocupa
 *  espaço ali, sem cobrir o conteúdo (ajustes do M4, ponto 8). Sem lugar, fica no fim. */
export const ContextoLugarDoRecado = createContext<(lugar: HTMLElement | null) => void>(() => {})
