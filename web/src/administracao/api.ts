// Épico B · Administração: uma função por rota do contrato (spec do M1, seção 4.3).
// Pertence ao épico B.
import { api } from '../api/cliente'
import type {
  PaginaHistorico,
  PainelAtivacao,
  PapelGerenciavel,
  Situacao,
  UnidadeAdmin,
} from './tipos'

const unidade = (login: string) => `/api/admin/unidades/${encodeURIComponent(login)}`

export const buscarPainel = (situacao: Situacao = 'todas') =>
  api.get<PainelAtivacao>('/api/admin/unidades', { situacao })

export const buscarUnidade = (login: string) => api.get<UnidadeAdmin>(unidade(login))

export const resetarUnidade = (login: string) =>
  api.post<UnidadeAdmin>(`${unidade(login)}/resetar`, { confirmo: true })

export const darPapel = (login: string, papel: PapelGerenciavel) =>
  api.put<UnidadeAdmin>(`${unidade(login)}/papeis/${papel}`)

export const retirarPapel = (login: string, papel: PapelGerenciavel) =>
  api.delete<UnidadeAdmin>(`${unidade(login)}/papeis/${papel}`)

/** Mais novo primeiro; para a próxima página, `antes_de` = `proximo` da anterior. */
export const buscarHistorico = (consulta: { antes_de?: number; limite?: number } = {}) =>
  api.get<PaginaHistorico>('/api/admin/historico', consulta)
