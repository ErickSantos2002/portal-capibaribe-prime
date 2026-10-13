// M4 · Enquetes: tipos do contrato (docs/superpowers/specs/m4-contrato.md, seção 3.2). Comum aos
// dois épicos. Espelho de api/app/esquemas/enquetes.py: o teste api/testes/test_contrato.py
// confere os campos.
import type { DataHora, UnidadeRef } from '../api/tipos'

/** Quando o resultado aparece (RF-23). */
export type MostrarResultado = 'durante' | 'so_no_fim'

/** `PUT /api/enquetes/{id}` (épico A): só enquanto ninguém votou. Destino não muda. */
export interface EditarEnquete {
  pergunta: string
  /** De 2 a 10, na ordem; as em branco são descartadas pela API. */
  opcoes: string[]
  multipla_escolha?: boolean
  /** Com fuso; no futuro, até 1 ano. */
  encerra_em: DataHora
  mostrar_resultado?: MostrarResultado
}

/** `POST /api/enquetes` (H-20, épico A). */
export interface NovaEnquete extends EditarEnquete {
  para_todos: boolean
  /** Números dos blocos; só vale com `para_todos` falso. */
  blocos?: number[]
}

/** `PUT /api/enquetes/{id}/voto` (H-21, épico B): votar e trocar são a mesma coisa. */
export interface Votar {
  opcoes: number[]
}

export interface OpcaoEnquete {
  id: number
  texto: string
  /** Nulo enquanto o resultado está escondido ("só no fim" e ainda aberta). */
  votos: number | null
}

export interface Participacao {
  votaram: number
  /** Unidades ativas do destino. */
  total: number
}

export interface EnqueteResumo {
  id: number
  pergunta: string
  multipla_escolha: boolean
  mostrar_resultado: MostrarResultado
  encerra_em: DataHora
  encerrada: boolean
  para_todos: boolean
  blocos: number[]
  criada_em: DataHora
  editada_em: DataHora | null
  /** "Seu apartamento ainda não votou" quando falso e aberta. */
  ja_votou: boolean
}

export interface Enquete extends EnqueteResumo {
  opcoes: OpcaoEnquete[]
  /** Ids das opções que a unidade marcou; vazio se não votou. */
  meu_voto: number[]
  votado_em: DataHora | null
  participacao: Participacao
  resultado_visivel: boolean
  pode_votar: boolean
  pode_editar: boolean
  aviso_id: number
}

export interface ListaEnquetes {
  itens: EnqueteResumo[]
}

/** Resposta de criar e editar (épico A): a tela vai para `/enquetes/{id}`. */
export interface EnqueteGravada {
  id: number
  aviso_id: number
}

/** `GET /api/enquetes/{id}/votantes` (H-22, só a gestão): quem votou, nunca em quê. */
export interface Votantes {
  votaram: UnidadeRef[]
  entraram_sem_votar: UnidadeRef[]
  nao_entraram: UnidadeRef[]
}
