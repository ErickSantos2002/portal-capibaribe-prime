// Épico C · Avisos: tipos do contrato (spec do M1, seção 4.4). Pertence ao épico C.
// Espelho de api/app/esquemas/avisos.py: o teste api/testes/test_contrato.py confere os campos.
// O texto do aviso tem as marcas do Markdown restrito: quem interpreta é `formatacao.ts`, que
// nunca transforma texto em HTML.
import type { DataHora, UnidadeRef } from '../api/tipos'

/** Do que o aviso trata. `geral` é o padrão. */
export type Categoria = 'geral' | 'obra' | 'reuniao' | 'financeiro' | 'urgente'

/** "Quando / Onde" do aviso que é um evento. `quando` com fuso; `onde` é opcional. */
export interface Evento {
  quando: DataHora
  onde?: string | null
}

export interface CorrigirAviso {
  titulo: string
  texto: string
  categoria?: Categoria
  evento?: Evento | null
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
  /** Leu uma versão anterior e ainda não abriu a correção (revisão do M1, U1). */
  corrigido_desde_a_leitura: boolean
  categoria: Categoria
  /** Para a linha do evento no mural; nulo se não é evento. */
  evento_quando: DataHora | null
}

export interface VersaoAviso {
  versao: number
  titulo: string
  texto: string
  criada_em: DataHora
  categoria: Categoria
  evento: Evento | null
}

export interface ContagemLeitura {
  lidos: number
  total: number
}

export interface AvisoCompleto extends AvisoResumo {
  texto: string
  evento: Evento | null
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

export interface DestinoBloco {
  numero: number
  nome: string
}

/** Rota a mais do épico C: os blocos para os botões do formulário (são editáveis, H-10). */
export interface Destinos {
  blocos: DestinoBloco[]
}

export interface Leitura {
  lidos: number
  total: number
  /** Ainda não fizeram o primeiro acesso (revisão do M1, U5). */
  nao_entraram: UnidadeRef[]
  /** Já entraram no Portal, mas não abriram este aviso. */
  entraram_sem_ler: UnidadeRef[]
}
