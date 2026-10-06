// Épico A do M2 · uma função por rota do contrato (spec do M2, seção 4.2). Pertence ao épico A.
import { api } from '../api/cliente'
import type { EstadoNotificacoes, InscricaoPush } from './tipos'

export const lerEstadoDasNotificacoes = () => api.get<EstadoNotificacoes>('/api/notificacoes')

export const inscreverEsteAparelho = (dados: InscricaoPush) =>
  api.put<void>('/api/notificacoes/este-aparelho', dados)

export const removerEsteAparelho = () => api.delete<void>('/api/notificacoes/este-aparelho')
