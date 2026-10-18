// Indicações · uma função por rota da API (spec, seção 7).
import { api } from '../api/cliente'
import type {
  AvisarGestao,
  CategoriaServico,
  CorrigirPrestador,
  DarOpiniao,
  IndicacaoCriada,
  ListaCategorias,
  ListaIndicacoes,
  NovaIndicacao,
  Parecidos,
  Prestador,
} from './tipos'

export const listarCategorias = () => api.get<ListaCategorias>('/api/indicacoes/categorias')

/** Mais recomendados primeiro. `com_aviso` só vale para a gestão. */
export const listarIndicacoes = (consulta: { categoria?: number; busca?: string; com_aviso?: boolean } = {}) =>
  api.get<ListaIndicacoes>('/api/indicacoes', consulta)

/** Até 3 nomes parecidos, para o aviso de duplicado. */
export const parecidos = (nome: string) => api.get<Parecidos>('/api/indicacoes/parecidos', { nome })

export const indicar = (dados: NovaIndicacao) => api.post<IndicacaoCriada>('/api/indicacoes', dados)

export const abrirIndicacao = (id: number) => api.get<Prestador>(`/api/indicacoes/${id}`)

/** Dar e mudar a opinião são a mesma coisa. */
export const opinar = (id: number, dados: DarOpiniao) =>
  api.put<Prestador>(`/api/indicacoes/${id}/opiniao`, dados)

export const apagarOpiniao = (id: number) => api.delete<void>(`/api/indicacoes/${id}/opiniao`)

/** Quem indicou ou a gestão. */
export const corrigir = (id: number, dados: CorrigirPrestador) =>
  api.put<Prestador>(`/api/indicacoes/${id}`, dados)

export const avisarGestao = (id: number, dados: AvisarGestao) =>
  api.post<void>(`/api/indicacoes/${id}/aviso`, dados)

// --- gestão ---

export const esconderPrestador = (id: number) => api.post<void>(`/api/indicacoes/${id}/esconder`)

export const esconderOpiniao = (id: number) =>
  api.post<void>(`/api/indicacoes/opinioes/${id}/esconder`)

export const resolverAviso = (id: number) => api.post<void>(`/api/indicacoes/avisos/${id}/resolver`)

// --- administração ---

export const criarCategoria = (nome: string) =>
  api.post<CategoriaServico>('/api/indicacoes/categorias', { nome })

export const renomearCategoria = (id: number, nome: string) =>
  api.put<CategoriaServico>(`/api/indicacoes/categorias/${id}`, { nome })
