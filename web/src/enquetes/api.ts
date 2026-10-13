// M4 · Enquetes: uma função por rota do contrato (docs/superpowers/specs/m4-contrato.md, 3.1).
// Comum aos dois épicos: nenhum deles edita este arquivo.
import { api } from '../api/cliente'
import type {
  EditarEnquete,
  Enquete,
  EnqueteGravada,
  ListaEnquetes,
  NovaEnquete,
  Votantes,
  Votar,
} from './tipos'

/** Abertas primeiro, depois as encerradas (épico B). */
export const listarEnquetes = () => api.get<ListaEnquetes>('/api/enquetes')

/** Fora do destino, 404 igual a inexistente (épico B). */
export const abrirEnquete = (id: number) => api.get<Enquete>(`/api/enquetes/${id}`)

/** H-21: votar e trocar o voto são a mesma chamada; vale o último (épico B). */
export const votar = (id: number, dados: Votar) => api.put<Enquete>(`/api/enquetes/${id}/voto`, dados)

/** H-22: quais unidades votaram, nunca em quê; só a gestão (épico B). */
export const votantes = (id: number) => api.get<Votantes>(`/api/enquetes/${id}/votantes`)

/** H-20 (épico A): cria a enquete e o aviso automático. */
export const criarEnquete = (dados: NovaEnquete) => api.post<EnqueteGravada>('/api/enquetes', dados)

/** Só enquanto ninguém votou (épico A). */
export const editarEnquete = (id: number, dados: EditarEnquete) =>
  api.put<EnqueteGravada>(`/api/enquetes/${id}`, dados)
