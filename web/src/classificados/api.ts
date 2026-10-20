// Classificados · uma função por rota da API (spec, seção 8).
import { api } from '../api/cliente'
import type { AvisarGestao, CategoriaServico, ListaCategorias } from '../indicacoes/tipos'
import type {
  Anuncio,
  AnuncioCriado,
  FotoAutorizada,
  FotoEnviada,
  ListaCategoriasClassificado,
  ListaClassificados,
  MeusAnuncios,
  MotivoEncerramento,
  NovoAnuncio,
  PedirFoto,
  TipoAnuncio,
} from './tipos'

export const listarCategorias = () =>
  api.get<ListaCategoriasClassificado>('/api/classificados/categorias')

/** O mais recente primeiro. `com_aviso` só vale para a gestão. */
export const listarClassificados = (
  consulta: { tipo?: TipoAnuncio; categoria?: number; busca?: string; com_aviso?: boolean } = {},
) => api.get<ListaClassificados>('/api/classificados', consulta)

export const meusAnuncios = () => api.get<MeusAnuncios>('/api/classificados/meus')

export const anunciar = (dados: NovoAnuncio) => api.post<AnuncioCriado>('/api/classificados', dados)

export const abrirAnuncio = (id: number) => api.get<Anuncio>(`/api/classificados/${id}`)

export const editarAnuncio = (id: number, dados: NovoAnuncio) =>
  api.put<Anuncio>(`/api/classificados/${id}`, dados)

export const reservar = (id: number) => api.post<Anuncio>(`/api/classificados/${id}/reservar`)

export const liberar = (id: number) => api.post<Anuncio>(`/api/classificados/${id}/liberar`)

export const renovar = (id: number) => api.post<Anuncio>(`/api/classificados/${id}/renovar`)

export const encerrar = (id: number, motivo: MotivoEncerramento) =>
  api.post<Anuncio>(`/api/classificados/${id}/encerrar`, { motivo })

export const avisarGestao = (id: number, dados: AvisarGestao) =>
  api.post<void>(`/api/classificados/${id}/aviso`, dados)

// --- fotos (o envio do M3, com rotas próprias) ---

export const pedirFoto = (dados: PedirFoto) =>
  api.post<FotoAutorizada>('/api/classificados/fotos', dados)

export const confirmarFoto = (id: number) =>
  api.post<FotoEnviada>(`/api/classificados/fotos/${id}/confirmar`)

// --- gestão ---

export const esconderAnuncio = (id: number) => api.post<void>(`/api/classificados/${id}/esconder`)

export const resolverAviso = (id: number) =>
  api.post<void>(`/api/classificados/avisos/${id}/resolver`)

// --- administração (as mesmas formas das categorias das indicações) ---

export const listarCategoriasParaAdmin = () =>
  api.get<ListaCategorias>('/api/classificados/categorias')

export const criarCategoria = (nome: string) =>
  api.post<CategoriaServico>('/api/classificados/categorias', { nome })

export const renomearCategoria = (id: number, nome: string) =>
  api.put<CategoriaServico>(`/api/classificados/categorias/${id}`, { nome })
