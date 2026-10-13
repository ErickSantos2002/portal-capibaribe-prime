// Épico C · Avisos: tipos do contrato (spec do M1, seção 4.4). Pertence ao épico C.
// Espelho de api/app/esquemas/avisos.py: o teste api/testes/test_contrato.py confere os campos.
// O texto do aviso tem as marcas do Markdown restrito: quem interpreta é `formatacao.ts`, que
// nunca transforma texto em HTML.
import type { DataHora, UnidadeRef } from '../api/tipos'
import type { ArquivoEnviado } from '../arquivos/tipos'

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
  /** M3: ids dos anexos (`enviarArquivo(…, 'aviso')`), na ordem. Na correção, omitido repete
   *  os da versão em vigor e `[]` tira todos; ao publicar, omitido é sem anexo. */
  anexos?: number[] | null
  /** M3 (revisão C2): a versão em vigor quando o formulário abriu; se outra pessoa corrigiu
   *  depois, 409 `aviso_corrigido_agora`. Só na correção. */
  versao_base?: number | null
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
  /** M3: quantos anexos a versão em vigor tem (o clipe no mural). */
  quantidade_anexos: number
}

export interface VersaoAviso {
  versao: number
  titulo: string
  texto: string
  criada_em: DataHora
  categoria: Categoria
  evento: Evento | null
  /** M3: os anexos daquela versão. */
  anexos: ArquivoEnviado[]
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
  /** M3: os anexos da versão em vigor, na ordem. */
  anexos: ArquivoEnviado[]
  /** M3 (RF-33): o documento que gerou este aviso, se a unidade pode vê-lo. */
  documento: DocumentoDoAviso | null
  /** M4 (H-13): a enquete que gerou este aviso, com a pergunta atual. */
  enquete: EnqueteDoAviso | null
}

/** O botão "Abrir o documento" do aviso automático (RF-33). */
export interface DocumentoDoAviso {
  id: number
  titulo: string
}

/** O botão "Ir para a enquete" do aviso automático (M4, H-13). */
export interface EnqueteDoAviso {
  id: number
  pergunta: string
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
