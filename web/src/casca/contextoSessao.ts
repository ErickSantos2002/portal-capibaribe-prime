// Quem está logado, para a casca e os épicos. Fonte: GET /api/acesso/eu.
import { createContext, useContext } from 'react'
import type { Eu } from '../api/tipos'

export type EstadoSessao =
  | { situacao: 'carregando' }
  | { situacao: 'pronta'; eu: Eu | null }
  | { situacao: 'sem_conexao'; mensagem: string }

export interface ValorSessao {
  estado: EstadoSessao
  /** Atalho: a unidade logada, ou nulo (sem sessão, carregando ou sem conexão). */
  eu: Eu | null
  /** Depois de entrar ou concluir o primeiro acesso, a rota do épico A passa o `Eu` recebido. */
  definir: (eu: Eu | null) => void
  /** Pergunta de novo à API (ex.: depois de um 403 `sem_permissao`, o papel pode ter mudado). */
  recarregar: () => Promise<void>
  /** Encerra a sessão deste aparelho (POST /api/acesso/sair). */
  sair: () => Promise<void>
}

export const ContextoSessao = createContext<ValorSessao | null>(null)

export function useSessao(): ValorSessao {
  const valor = useContext(ContextoSessao)
  if (!valor) throw new Error('useSessao fora do SessaoProvider')
  return valor
}
