// M3 · Épico B · Anexos nos avisos: a lógica sem tela (spec `m3-anexos.md`, seção 3.1).
import type { ArquivoEnviado } from '../arquivos/tipos'

/** No máximo 5 anexos por versão do aviso (o banco também confere). */
export const MAXIMO_DE_ANEXOS = 5

const MB = 1024 * 1024

/** Um arquivo na lista do formulário. `chave` só existe na tela (o id vem quando confirma). */
export interface ItemAnexo {
  chave: string
  nome: string
  tipo: string
  /** Miniatura local da foto escolhida (`blob:`), ou nulo (PDF, ou anexo que já existia). */
  previa: string | null
  situacao: 'enviando' | 'pronto' | 'erro'
  /** O arquivo conferido pela API, quando `pronto`. */
  arquivo?: ArquivoEnviado
  /** A mensagem para a pessoa, quando `erro`. */
  erro?: string
  /** O erro passa tentando de novo (rede, bucket fora do ar)? Arquivo recusado não passa. */
  podeTentar?: boolean
  /** Já era anexo da versão em vigor (formulário de correção). */
  jaPublicado?: boolean
}

/** "320 KB", "1,2 MB": o tamanho como a pessoa entende. */
export function tamanhoEmTexto(bytes: number): string {
  if (bytes < MB) return `${Math.max(1, Math.round(bytes / 1024)).toLocaleString('pt-BR')} KB`
  return `${(bytes / MB).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} MB`
}

export function ehFoto(tipo: string): boolean {
  return tipo.startsWith('image/')
}

/** "PDF, 320 KB" ou "Foto, 1,2 MB". */
export function descricaoDoAnexo(arquivo: ArquivoEnviado): string {
  return `${ehFoto(arquivo.tipo) ? 'Foto' : 'PDF'}, ${tamanhoEmTexto(arquivo.tamanho_bytes)}`
}

export function quantosAnexos(n: number): string {
  return n === 1 ? '1 anexo' : `${n} anexos`
}

/** Pode publicar com estes anexos? Se não, a frase da caixa de erro. */
export function situacaoDosAnexos(itens: readonly ItemAnexo[]): {
  pode: boolean
  mensagem: string
} {
  if (itens.some((i) => i.situacao === 'erro')) {
    return { pode: false, mensagem: 'Tire ou envie de novo o arquivo que deu erro.' }
  }
  if (itens.some((i) => i.situacao === 'enviando')) {
    return { pode: false, mensagem: 'Espere os arquivos terminarem de enviar.' }
  }
  return { pode: true, mensagem: '' }
}

/** Os ids que vão no aviso, na ordem da lista. */
export function idsProntos(itens: readonly ItemAnexo[]): number[] {
  return itens.flatMap((i) => (i.situacao === 'pronto' && i.arquivo ? [i.arquivo.id] : []))
}
