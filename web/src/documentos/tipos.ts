// Épico A do M3 · Documentos: tipos do contrato (docs/superpowers/specs/m3-contrato.md, 5.2).
// Pertence ao épico A. Espelho de api/app/esquemas/documentos.py: o teste
// api/testes/test_contrato.py confere os campos.
import type { DataHora } from '../api/tipos'
import type { ArquivoEnviado } from '../arquivos/tipos'

/** Assunto; a ordem é a das opções do formulário. */
export type CategoriaDocumento = 'obra' | 'convencao' | 'regimento' | 'ata' | 'contrato' | 'orientacao' | 'outro'

/** Quem vê (RF-31). */
export type NivelAcesso = 'publico' | 'compradores' | 'gestao'

/** Data sem hora, `AAAA-MM-DD` (a data do documento, não a do envio). */
export type Data = string

/** `POST /api/documentos` (H-17). `arquivo_id` vem de `enviarArquivo(…, 'documento')`. */
export interface NovoDocumento {
  titulo: string
  categoria: CategoriaDocumento
  data_documento: Data
  acesso: NivelAcesso
  arquivo_id: number
  /** RF-33: cria o aviso automático (não vale para `gestao`). */
  avisar_unidades?: boolean
}

/** `POST /api/documentos/{id}/versoes` (H-19). */
export interface NovaVersaoDocumento {
  arquivo_id: number
}

export interface VersaoDocumento {
  versao: number
  enviada_em: DataHora
  arquivo: ArquivoEnviado
}

/** Item da lista (H-18): `versao`, `atualizado_em` e `arquivo` são da versão atual. */
export interface DocumentoResumo {
  id: number
  titulo: string
  categoria: CategoriaDocumento
  data_documento: Data
  acesso: NivelAcesso
  versao: number
  atualizado_em: DataHora
  arquivo: ArquivoEnviado
  arquivado_em: DataHora | null
}

export interface Documento extends DocumentoResumo {
  /** Da mais nova para a mais antiga, sem a atual. */
  versoes_anteriores: VersaoDocumento[]
  aviso_id: number | null
}

export interface ListaDocumentos {
  itens: DocumentoResumo[]
}
