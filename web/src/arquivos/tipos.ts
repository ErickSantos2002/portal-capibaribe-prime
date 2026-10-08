// Comum · Envio de arquivo: tipos do contrato (docs/superpowers/specs/m3-contrato.md, seção 5.1).
// Espelho de api/app/esquemas/arquivos.py: o teste api/testes/test_contrato.py confere os campos.
// Arquivo comum: os épicos usam, não editam.
import type { DataHora } from '../api/tipos'

export type TipoArquivo = 'application/pdf' | 'image/jpeg' | 'image/png' | 'image/webp'

/** Para onde vai o arquivo: decide o limite (10 MB no aviso, 20 MB no documento). */
export type Finalidade = 'aviso' | 'documento'

/** `POST /api/arquivos`. `tamanho_bytes` já é o do arquivo comprimido. */
export interface PedirEnvio {
  nome: string
  tipo: TipoArquivo
  finalidade: Finalidade
  tamanho_bytes: number
}

/** `PUT url` com `Content-Type: content_type` (entra na assinatura), sem cookie. */
export interface EnvioAutorizado {
  arquivo_id: number
  url: string
  content_type: string
  expira_em: DataHora
}

/** Arquivo conferido e publicado. `tipo` e `tamanho_bytes` são os de verdade. */
export interface ArquivoEnviado {
  id: number
  nome: string
  tipo: TipoArquivo
  tamanho_bytes: number
}

/** Link curto (5 minutos) para abrir ou baixar: pedir na hora do toque, nunca guardar. */
export interface LinkDoArquivo {
  url: string
  expira_em: DataHora
}
