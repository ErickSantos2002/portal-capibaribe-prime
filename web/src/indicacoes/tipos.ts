// Indicações de serviços: tipos do contrato (docs/superpowers/specs/2026-10-18-indicacoes-design.md,
// seção 7). Espelho de api/app/esquemas/indicacoes.py: o teste api/testes/test_contrato.py
// confere os campos. Nas respostas, `null` nos campos da gestão quer dizer "não é para você".
import type { DataHora, UnidadeRef } from '../api/tipos'

/** `POST /api/indicacoes`: o prestador e a primeira opinião. `recomenda` não tem padrão. */
export interface NovaIndicacao {
  categoria_id: number
  /** De 2 a 80 letras. */
  nome: string
  /** Com DDD; a API aceita máscara, espaço e +55 e guarda só os dígitos. */
  telefone: string
  /** `@usuario` ou `usuario`; em branco vira nulo. */
  instagram?: string | null
  recomenda: boolean
  /** Até 500 letras; só espaço vira nulo. */
  comentario?: string | null
}

/** `PUT /api/indicacoes/{id}`: quem indicou ou a gestão. */
export interface CorrigirPrestador {
  categoria_id: number
  nome: string
  telefone: string
  instagram?: string | null
}

/** `PUT /api/indicacoes/{id}/opiniao`: dar e mudar são a mesma coisa. */
export interface DarOpiniao {
  recomenda: boolean
  comentario?: string | null
}

/** `POST /api/indicacoes/{id}/aviso`: "Tem algo errado aqui?". Motivo até 300 letras. */
export interface AvisarGestao {
  motivo?: string | null
}

/** `POST /api/indicacoes/categorias` (administração). */
export interface NovaCategoria {
  nome: string
}

/** `PUT /api/indicacoes/categorias/{id}` (administração). */
export interface RenomearCategoria {
  nome: string
}

export interface CategoriaServico {
  id: number
  nome: string
}

export interface ListaCategorias {
  itens: CategoriaServico[]
}

/** A opinião visível mais recente com comentário, no cartão da lista. */
export interface OpiniaoTrecho {
  unidade: UnidadeRef
  comentario: string
  em: DataHora
}

export interface PrestadorResumo {
  id: number
  categoria: CategoriaServico
  nome: string
  recomendam: number
  nao_recomendam: number
  trecho: OpiniaoTrecho | null
  /** Só a gestão. */
  avisos_abertos: number | null
}

export interface ListaIndicacoes {
  itens: PrestadorResumo[]
  /** Quantos prestadores têm aviso aberto (só a gestão). */
  com_aviso: number | null
}

export interface PrestadorRef {
  id: number
  nome: string
  categoria: CategoriaServico
}

/** `GET /api/indicacoes/parecidos?nome=`: até 3. */
export interface Parecidos {
  itens: PrestadorRef[]
}

export interface Opiniao {
  id: number
  unidade: UnidadeRef
  recomenda: boolean
  comentario: string | null
  em: DataHora
  /** É a opinião da unidade logada. */
  minha: boolean
}

/** O que a unidade logada escreveu. `escondida`: a gestão escondeu e ela não muda mais. */
export interface MinhaOpiniao {
  recomenda: boolean
  comentario: string | null
  escondida: boolean
}

/** Aviso aberto, para a gestão. Sem a placa de quem avisou. */
export interface AvisoRecebido {
  id: number
  motivo: string | null
  em: DataHora
}

export interface Prestador {
  id: number
  categoria: CategoriaServico
  nome: string
  /** Só os dígitos, com DDD. */
  telefone: string
  /** Falso: o número é fixo e a tela mostra também o "Ligar". */
  celular: boolean
  instagram: string | null
  recomendam: number
  nao_recomendam: number
  /** Visíveis, da mais recente para a mais antiga. */
  opinioes: Opiniao[]
  minha_opiniao: MinhaOpiniao | null
  pode_corrigir: boolean
  ja_avisei: boolean
  /** Só a gestão vê um escondido. */
  escondido: boolean
  /** Avisos abertos (só a gestão). */
  avisos: AvisoRecebido[] | null
}

/** Resposta de indicar: a tela vai para `/indicacoes/{id}`. */
export interface IndicacaoCriada {
  id: number
}
