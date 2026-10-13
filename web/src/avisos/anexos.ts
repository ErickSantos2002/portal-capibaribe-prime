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

/** Enquanto algum arquivo escolhido agora está enviando: quantos já terminaram (prontos ou com
 *  erro) de quantos foram escolhidos. Os anexos que já eram do aviso não contam. */
export function progressoDoEnvio(
  itens: readonly ItemAnexo[],
): { feitos: number; total: number } | null {
  const desta = itens.filter((i) => !i.jaPublicado)
  const enviando = desta.filter((i) => i.situacao === 'enviando').length
  if (enviando === 0) return null
  return { feitos: desta.length - enviando, total: desta.length }
}

/** "a, b e c". */
function emLista(partes: string[]): string {
  if (partes.length < 2) return partes.join('')
  return `${partes.slice(0, -1).join(', ')} e ${partes.at(-1)}`
}

/** Os PDFs pelo nome e as fotos contadas ("2 fotos"): o nome da foto é técnico (U7). */
function descreverArquivos(arquivos: readonly ArquivoEnviado[]): string {
  const fotos = arquivos.filter((a) => ehFoto(a.tipo)).length
  const partes = arquivos.filter((a) => !ehFoto(a.tipo)).map((a) => a.nome)
  if (fotos > 0) partes.push(fotos === 1 ? '1 foto' : `${fotos} fotos`)
  return emLista(partes)
}

/** U6: o que a correção mudou nos anexos, numa frase, ou `null` se nada mudou. */
export function mudancaNosAnexos(
  antes: readonly ArquivoEnviado[],
  depois: readonly ArquivoEnviado[],
): string | null {
  const idsAntes = new Set(antes.map((a) => a.id))
  const idsDepois = new Set(depois.map((a) => a.id))
  const entraram = depois.filter((a) => !idsAntes.has(a.id))
  const sairam = antes.filter((a) => !idsDepois.has(a.id))
  const partes: string[] = []
  if (entraram.length > 0) {
    partes.push(`${entraram.length > 1 ? 'entraram' : 'entrou'} ${descreverArquivos(entraram)}`)
  }
  if (sairam.length > 0) {
    partes.push(`${sairam.length > 1 ? 'saíram' : 'saiu'} ${descreverArquivos(sairam)}`)
  }
  if (partes.length > 0) return `Anexos: ${partes.join('; ')}.`
  const mesmaOrdem = antes.every((a, i) => depois[i]?.id === a.id)
  return mesmaOrdem ? null : 'Anexos: mudou a ordem.'
}

/** Os ids que vão no aviso, na ordem da lista. */
export function idsProntos(itens: readonly ItemAnexo[]): number[] {
  return itens.flatMap((i) => (i.situacao === 'pronto' && i.arquivo ? [i.arquivo.id] : []))
}
