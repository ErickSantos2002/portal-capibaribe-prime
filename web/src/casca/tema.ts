// Tema claro/escuro (protótipo, seção 3.3). Começa no claro; o botão sol/lua alterna e a escolha
// fica no localStorage. O public/tema.js aplica a escolha antes do React, para não piscar.
import { useCallback, useState } from 'react'

export type Tema = 'claro' | 'escuro'
export const CHAVE_TEMA = 'portal-tema'

export function lerTema(): Tema {
  try {
    return localStorage.getItem(CHAVE_TEMA) === 'escuro' ? 'escuro' : 'claro'
  } catch {
    return 'claro'
  }
}

export function aplicarTema(tema: Tema): void {
  const raiz = document.documentElement
  if (tema === 'escuro') raiz.dataset.tema = 'escuro'
  else delete raiz.dataset.tema
  try {
    localStorage.setItem(CHAVE_TEMA, tema)
  } catch {
    // Navegação privada sem armazenamento: o tema vale só até fechar a página.
  }
}

export function useTema(): [Tema, () => void] {
  const [tema, setTema] = useState<Tema>(lerTema)
  const alternar = useCallback(() => {
    const novo: Tema = tema === 'escuro' ? 'claro' : 'escuro'
    aplicarTema(novo)
    setTema(novo)
  }, [tema])
  return [tema, alternar]
}
