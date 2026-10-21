// Classificados entre vizinhos: tipos do contrato (docs/superpowers/specs/2026-10-20-classificados-design.md,
// seção 8). Espelho de api/app/esquemas/classificados.py: o teste api/testes/test_contrato.py
// confere os campos. Nas respostas, `null` nos campos da gestão quer dizer "não é para você". O
// aviso à gestão e as categorias usam os tipos das indicações (`AvisarGestao`, `AvisoRecebido`).
import type { DataHora, UnidadeRef } from '../api/tipos'
import type { AvisoRecebido } from '../indicacoes/tipos'

export type TipoAnuncio = 'venda' | 'troca' | 'doacao' | 'procura'

export type SituacaoAnuncio = 'ativo' | 'reservado' | 'encerrado'

export type MotivoEncerramento = 'vendi' | 'troquei' | 'doei' | 'desisti' | 'encontrei'

export type TipoFoto = 'image/jpeg' | 'image/png' | 'image/webp'

/** `POST /api/classificados` e `PUT /api/classificados/{id}`. `tipo` não tem padrão. */
export interface NovoAnuncio {
  tipo: TipoAnuncio
  categoria_id: number
  /** De 3 a 80 letras. */
  titulo: string
  /** Até 1000 letras; só espaço vira nulo. */
  descricao?: string | null
  /** Só na venda, em centavos, até 10.000.000; nulo = "a combinar". */
  preco_centavos?: number | null
  /** Com DDD; a API aceita máscara, espaço e +55 e guarda só os dígitos. */
  contato: string
  /** As ids na ordem (a primeira é a capa), até 4. */
  fotos?: number[]
}

/** `POST /api/classificados/{id}/encerrar` (o dono). */
export interface EncerrarAnuncio {
  motivo: MotivoEncerramento
}

/** `POST /api/classificados/fotos`. `tamanho_bytes` já é o da foto comprimida. */
export interface PedirFoto {
  tipo: TipoFoto
  tamanho_bytes: number
}

export interface CategoriaClassificado {
  id: number
  nome: string
}

export interface ListaCategoriasClassificado {
  itens: CategoriaClassificado[]
}

/** `PUT url` com `Content-Type: content_type` (entra na assinatura), sem cookie. */
export interface FotoAutorizada {
  foto_id: number
  url: string
  content_type: string
  expira_em: DataHora
}

/** A foto conferida e guardada: a id entra no anúncio. */
export interface FotoEnviada {
  id: number
}

/** `url`: link assinado de 1 hora. */
export interface FotoDoAnuncio {
  id: number
  url: string
}

/** Cartão da lista e de "Meus anúncios". */
export interface AnuncioResumo {
  id: number
  tipo: TipoAnuncio
  categoria: CategoriaClassificado
  titulo: string
  preco_centavos: number | null
  capa: string | null
  unidade: UnidadeRef
  /** A publicação ou a última renovação. */
  em: DataHora
  situacao: SituacaoAnuncio
  vencido: boolean
  escondido: boolean
  /** Até quando fica na lista. */
  vence_em: DataHora
  /** Só a gestão; nulo para o morador. */
  avisos_abertos: number | null
}

export interface ListaClassificados {
  itens: AnuncioResumo[]
  /** Só a gestão; nulo para o morador. */
  com_aviso: number | null
  /** Quantos anúncios a unidade logada tem (todos os estados). */
  meus: number
  /** Desses, os abertos (não encerrados nem vencidos). */
  meus_abertos: number
}

export interface MeusAnuncios {
  itens: AnuncioResumo[]
  /** A frase do limite que a unidade já bateu (5 por dia, 10 abertos), ou nulo. */
  limite: string | null
}

export interface Anuncio {
  id: number
  tipo: TipoAnuncio
  categoria: CategoriaClassificado
  titulo: string
  descricao: string | null
  preco_centavos: number | null
  /** Só os dígitos, com DDD. */
  contato: string
  /** 11 dígitos: sem isso, a tela mostra "Ligar". */
  celular: boolean
  unidade: UnidadeRef
  publicado_em: DataHora
  renovado_em: DataHora | null
  vence_em: DataHora
  situacao: SituacaoAnuncio
  motivo_encerramento: MotivoEncerramento | null
  vencido: boolean
  escondido: boolean
  fotos: FotoDoAnuncio[]
  meu: boolean
  pode_renovar: boolean
  ja_avisei: boolean
  /** Só a gestão; nulo para o morador. */
  avisos: AvisoRecebido[] | null
}

export interface AnuncioCriado {
  id: number
}

/** `GET /api/classificados/faxina` (Vercel Cron). */
export interface ResultadoDaFaxina {
  anuncios: number
  fotos: number
}
