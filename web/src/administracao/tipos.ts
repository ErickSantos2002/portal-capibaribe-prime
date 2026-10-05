// Épico B · Administração: tipos do contrato (spec do M1, seção 4.3). Pertence ao épico B.
// Espelho de api/app/esquemas/administracao.py: api/testes/test_contrato.py confere os campos.
import type { DataHora, Papel, UnidadeRef } from '../api/tipos'

export type Situacao = 'todas' | 'ativadas' | 'nao_ativadas' | 'gestao'
export type PapelGerenciavel = 'comissao' | 'admin'

export interface ConfirmarReset {
  // A API recusa qualquer valor diferente de true (422).
  confirmo: boolean
}

export interface ResumoAtivacao {
  total: number
  ativadas: number
  percentual: number
}

export interface ResumoBloco {
  numero: number
  nome: string
  total: number
  ativadas: number
  percentual: number
}

export interface UnidadePainel {
  unidade: UnidadeRef
  andar: number
  ativada: boolean
  ativada_em: DataHora | null
  responsavel_nome: string | null
  celular: string | null
  papeis: Papel[]
}

export interface PainelAtivacao {
  resumo: ResumoAtivacao
  blocos: ResumoBloco[]
  unidades: UnidadePainel[]
}

export interface UnidadeAdmin {
  unidade: UnidadeRef
  andar: number
  ativada: boolean
  ativada_em: DataHora | null
  responsavel_nome: string | null
  celular: string | null
  email: string | null
  papeis: Papel[]
  bloqueada_ate: DataHora | null
  aparelhos_conectados: number
}

export interface ItemHistorico {
  id: number
  ocorrido_em: DataHora
  /** Nulo = ação do próprio Portal (ex.: bloqueio automático). */
  unidade: UnidadeRef | null
  acao: string
  entidade: string | null
  entidade_id: number | null
  detalhes: Record<string, unknown>
}

export interface PaginaHistorico {
  itens: ItemHistorico[]
  proximo: number | null
}
