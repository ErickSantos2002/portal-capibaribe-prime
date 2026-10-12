// Comum · Limites do envio de arquivo, conferidos na tela antes de mandar (spec do M3, seção 4).
// Os mesmos de `api/app/modelos/arquivos.py` e `api/app/esquemas/arquivos.py`: o teste
// `api/testes/test_contrato.py` confere os números e as mensagens. Arquivo comum: os épicos usam,
// não editam.
import type { Finalidade, TipoArquivo } from './tipos'

const MB = 1024 * 1024

/** PDF e fotos (ADR-0004). */
export const TIPOS_ACEITOS: readonly TipoArquivo[] = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/webp',
]

/** Para o `accept` do `<input type="file">`. */
export const ACEITAR = TIPOS_ACEITOS.join(',')

/** Por arquivo: 10 MB no anexo de aviso (H-12), 20 MB no documento (H-17). */
export const LIMITES: Readonly<Record<Finalidade, number>> = { aviso: 10 * MB, documento: 20 * MB }

export const MSG_TIPO = 'O Portal aceita PDF e fotos (JPEG, PNG ou WEBP).'
const MSG_VAZIO = 'O arquivo está vazio. Escolha outro.'

export function mensagemDoLimite(finalidade: Finalidade): string {
  return `O arquivo pode ter até ${LIMITES[finalidade] / MB} MB.`
}

export function tipoAceito(tipo: string): tipo is TipoArquivo {
  return (TIPOS_ACEITOS as readonly string[]).includes(tipo)
}

/** O que impede o envio, na voz do morador, ou `null` se pode mandar. */
export function problemaNaTela(
  arquivo: Pick<File, 'type' | 'size'>,
  finalidade: Finalidade,
): string | null {
  if (!tipoAceito(arquivo.type)) return MSG_TIPO
  if (arquivo.size < 1) return MSG_VAZIO
  if (arquivo.size > LIMITES[finalidade]) return mensagemDoLimite(finalidade)
  return null
}
