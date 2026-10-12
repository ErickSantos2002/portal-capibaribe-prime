// Épico A do M3 · Documentos: uma função por rota do contrato (spec do M3, seção 5.2).
// Pertence ao épico A. O arquivo vem antes, de `enviarArquivo(…, 'documento')`.
import { api } from '../api/cliente'
import type { LinkDoArquivo } from '../arquivos/tipos'
import type { Documento, ListaDocumentos, NovaVersaoDocumento, NovoDocumento } from './tipos'

/** H-18. `arquivados` só vale para a gestão. */
export const listarDocumentos = (consulta: { arquivados?: boolean } = {}) =>
  api.get<ListaDocumentos>('/api/documentos', consulta)

/** Os de nível público, sem sessão (o link da tela de entrada). */
export const listarDocumentosPublicos = () => api.get<ListaDocumentos>('/api/documentos/publicos')

export const abrirDocumento = (id: number) => api.get<Documento>(`/api/documentos/${id}`)

/** H-17. */
export const publicarDocumento = (dados: NovoDocumento) =>
  api.post<Documento>('/api/documentos', dados)

/** H-19. */
export const enviarNovaVersao = (id: number, dados: NovaVersaoDocumento) =>
  api.post<Documento>(`/api/documentos/${id}/versoes`, dados)

export const arquivarDocumento = (id: number) =>
  api.post<Documento>(`/api/documentos/${id}/arquivar`)

/** Link de 5 minutos: pedir na hora do toque, nunca guardar. Funciona sem sessão para `publico`. */
export const linkDaVersao = (id: number, versao: number, baixar = false) =>
  api.get<LinkDoArquivo>(`/api/documentos/${id}/versoes/${versao}/link`, {
    baixar: baixar || undefined,
  })
