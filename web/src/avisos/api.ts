// Épico C · Avisos: uma função por rota do contrato (spec do M1, seção 4.4). Pertence ao épico C.
import { api } from '../api/cliente'
import type {
  Alcance,
  AvisoCompleto,
  ContagemNaoLidos,
  CorrigirAviso,
  Leitura,
  ListaAvisos,
  NovoAviso,
} from './tipos'

export const listarAvisos = (consulta: { busca?: string; arquivados?: boolean } = {}) =>
  api.get<ListaAvisos>('/api/avisos', consulta)

/** Usada pela casca no número da aba "Avisos". */
export const contarNaoLidos = () => api.get<ContagemNaoLidos>('/api/avisos/nao-lidos')

/** Sem blocos = todos. */
export const calcularAlcance = (blocos: number[] = []) =>
  api.get<Alcance>('/api/avisos/alcance', { blocos })

/** Abrir o aviso conta como leitura (H-16). */
export const abrirAviso = (id: number) => api.get<AvisoCompleto>(`/api/avisos/${id}`)

export const publicarAviso = (dados: NovoAviso) => api.post<AvisoCompleto>('/api/avisos', dados)

export const corrigirAviso = (id: number, dados: CorrigirAviso) =>
  api.put<AvisoCompleto>(`/api/avisos/${id}`, dados)

export const arquivarAviso = (id: number) => api.post<AvisoCompleto>(`/api/avisos/${id}/arquivar`)

export const mudarFixado = (id: number, fixado: boolean) =>
  api.put<AvisoCompleto>(`/api/avisos/${id}/fixado`, { fixado })

export const buscarLeitura = (id: number) => api.get<Leitura>(`/api/avisos/${id}/leitura`)
