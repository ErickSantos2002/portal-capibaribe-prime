// Épico C · Avisos: tipos do contrato (spec do M1, seção 4.4). Pertence ao épico C.
// Espelho de api/app/esquemas/avisos.py: o teste api/testes/test_contrato.py confere os campos.
// O texto do aviso é texto puro: nunca renderizar como HTML.
import type { DataHora, UnidadeRef } from '../api/tipos'

export interface CorrigirAviso {
  titulo: string
  texto: string
}

export interface NovoAviso extends CorrigirAviso {
  para_todos: boolean
  blocos?: number[]
  fixado?: boolean
}

export interface MudarFixado {
  fixado: boolean
}

export interface AvisoResumo {
  id: number
  titulo: string
  resumo: string
  publicado_em: DataHora
  /** "Comissão", "Administração do Portal", "Síndico" ou "Conselho". */
  publicado_por: string
  editado_em: DataHora | null
  fixado: boolean
  para_todos: boolean
  blocos: number[]
  arquivado_em: DataHora | null
  lido: boolean
}

export interface VersaoAviso {
  versao: number
  titulo: string
  texto: string
  criada_em: DataHora
}

export interface ContagemLeitura {
  lidos: number
  total: number
}

export interface AvisoCompleto extends AvisoResumo {
  texto: string
  versoes_anteriores: VersaoAviso[]
  /** Só para a gestão. */
  leitura: ContagemLeitura | null
}

export interface ListaAvisos {
  itens: AvisoResumo[]
}

export interface ContagemNaoLidos {
  quantidade: number
}

export interface Alcance {
  unidades: number
}

export interface Leitura {
  lidos: number
  total: number
  nao_leram: UnidadeRef[]
}
