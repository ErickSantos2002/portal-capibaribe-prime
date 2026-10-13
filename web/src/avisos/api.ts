// Épico C · Avisos: uma função por rota do contrato (spec do M1, seção 4.4). Pertence ao épico C.
import { api } from '../api/cliente'
import type { LinkDoArquivo } from '../arquivos/tipos'
import type {
  Alcance,
  AvisoCompleto,
  ContagemNaoLidos,
  CorrigirAviso,
  Destinos,
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

/** Blocos que podem ser destino de um aviso (botões do formulário). */
export const listarDestinos = () => api.get<Destinos>('/api/avisos/destinos')

/** Só lê: GET não altera nada. Ao abrir o aviso, a tela chama também `marcarLido`. */
export const abrirAviso = (id: number) => api.get<AvisoCompleto>(`/api/avisos/${id}`)

/** A unidade abriu o aviso (H-16). Idempotente: só a primeira vez conta. */
export const marcarLido = (id: number) => api.post<void>(`/api/avisos/${id}/lido`)

export const publicarAviso = (dados: NovoAviso) => api.post<AvisoCompleto>('/api/avisos', dados)

export const corrigirAviso = (id: number, dados: CorrigirAviso) =>
  api.put<AvisoCompleto>(`/api/avisos/${id}`, dados)

export const arquivarAviso = (id: number) => api.post<AvisoCompleto>(`/api/avisos/${id}/arquivar`)

export const mudarFixado = (id: number, fixado: boolean) =>
  api.put<AvisoCompleto>(`/api/avisos/${id}/fixado`, { fixado })

export const buscarLeitura = (id: number) => api.get<Leitura>(`/api/avisos/${id}/leitura`)

/** M3 (épico B, revisão U12): o endereço do Portal que abre o anexo. A API confere a sessão
 *  e redireciona para um link novo (de 1 hora) a cada pedido: serve de `src` da foto e de
 *  `href` do PDF: cada toque pede um link novo, mesmo com a página aberta há horas. */
export const enderecoDoAnexo = (avisoId: number, arquivoId: number) =>
  `/api/avisos/${avisoId}/anexos/${arquivoId}/abrir`

/** M3 (épico B): link de 1 hora de um anexo, de qualquer versão do aviso. Pedir na hora do
 *  toque, nunca guardar. */
export const linkDoAnexo = (avisoId: number, arquivoId: number, baixar = false) =>
  api.get<LinkDoArquivo>(`/api/avisos/${avisoId}/anexos/${arquivoId}/link`, {
    baixar: baixar || undefined,
  })
