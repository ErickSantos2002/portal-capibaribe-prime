// Épico A do M3 · documentos na voz do morador: assuntos, quem vê, datas, tamanhos e a busca.
// Pertence ao épico A.
import { LIMITES, tipoAceito } from '../arquivos/limites'
import type { TipoArquivo } from '../arquivos/tipos'
import type { CategoriaDocumento, Data, DocumentoResumo, NivelAcesso } from './tipos'

export interface Assunto {
  valor: CategoriaDocumento
  /** No formulário ("Assunto: Ata"). */
  nome: string
  /** No título do grupo da lista ("Atas"). */
  grupo: string
}

/** A ordem é a do formulário do protótipo (e da API), `outro` por último. */
export const ASSUNTOS: readonly Assunto[] = [
  { valor: 'obra', nome: 'Obra', grupo: 'Obra' },
  { valor: 'convencao', nome: 'Convenção', grupo: 'Convenção' },
  { valor: 'regimento', nome: 'Regimento', grupo: 'Regimento' },
  { valor: 'ata', nome: 'Ata', grupo: 'Atas' },
  { valor: 'contrato', nome: 'Contrato', grupo: 'Contratos' },
  { valor: 'orientacao', nome: 'Orientação', grupo: 'Orientações' },
  { valor: 'outro', nome: 'Outro', grupo: 'Outros' },
]

export function assuntoDe(categoria: CategoriaDocumento): Assunto {
  return ASSUNTOS.find((a) => a.valor === categoria) ?? ASSUNTOS[ASSUNTOS.length - 1]
}

export interface Nivel {
  valor: NivelAcesso
  /** A opção de "Quem pode ver". */
  opcao: string
  /** Uma linha de explicação embaixo da opção. */
  explicacao: string
  /** No documento aberto: "Quem vê: …". */
  quemVe: string
}

/** RF-31. A primeira é a mais comum (e a escolhida de saída no formulário). */
export const NIVEIS: readonly Nivel[] = [
  {
    valor: 'compradores',
    opcao: 'Os apartamentos',
    explicacao: 'Quem já entrou no Portal com a conta do apartamento.',
    quemVe: 'os apartamentos que já entraram no Portal',
  },
  {
    valor: 'publico',
    opcao: 'Qualquer pessoa',
    explicacao: 'Aparece também na tela de entrada, para quem ainda não entrou.',
    quemVe: 'qualquer pessoa, mesmo sem entrar',
  },
  {
    valor: 'gestao',
    opcao: 'Só a gestão',
    explicacao: 'Comissão, síndico e conselho. Os apartamentos nem veem que existe.',
    quemVe: 'só a gestão (Comissão, síndico e conselho)',
  },
]

export function nivelDe(acesso: NivelAcesso): Nivel {
  return NIVEIS.find((n) => n.valor === acesso) ?? NIVEIS[0]
}

const MESES = [
  'janeiro',
  'fevereiro',
  'março',
  'abril',
  'maio',
  'junho',
  'julho',
  'agosto',
  'setembro',
  'outubro',
  'novembro',
  'dezembro',
]

/** "1 de outubro de 2026". A data do documento não tem hora: nada de fuso no meio. */
export function dataDoDocumento(data: Data): string {
  const [ano, mes, dia] = data.split('-').map(Number)
  return `${dia} de ${MESES[mes - 1]} de ${ano}`
}

/** Hoje, no horário de Recife, como `AAAA-MM-DD` (o padrão do campo de data). */
export function hojeEmRecife(agora: Date = new Date()): Data {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Recife' }).format(agora)
}

const dataPorExtenso = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'America/Recife',
})

/** "2 de outubro de 2026", no horário de Recife (para datas com hora: envio, arquivamento). */
export function diaPorExtenso(iso: string): string {
  return dataPorExtenso.format(new Date(iso))
}

/** O que o leitor de tela ouve depois de buscar. */
export function encontrados(n: number): string {
  if (n === 0) return 'Nenhum documento encontrado.'
  return n === 1 ? '1 documento encontrado.' : `${n} documentos encontrados.`
}

const KB = 1024
const MB = 1024 * KB

/** "340 KB", "2,4 MB": como a pessoa vê no celular. */
export function tamanhoEmTexto(bytes: number): string {
  if (bytes < MB) return `${Math.max(1, Math.round(bytes / KB))}\u00a0KB`
  const mb = Math.round((bytes / MB) * 10) / 10
  return `${mb.toLocaleString('pt-BR')}\u00a0MB`
}

export function tipoEmTexto(tipo: TipoArquivo): string {
  return tipo === 'application/pdf' ? 'PDF' : 'Foto'
}

// --- o aviso automático (prévia; o texto de verdade é o da API, `servicos/documentos.py`) -------

const LIMITE_TITULO_AVISO = 120
// A categoria do aviso que combina com o assunto do documento (revisão UX, U13).
const CATEGORIA_DO_AVISO: Partial<Record<CategoriaDocumento, string>> = {
  obra: 'Obra',
  ata: 'Reunião',
}

export interface PreviaDoAviso {
  titulo: string
  categoria: string
  texto: string
}

function cortar(prefixo: string, titulo: string): string {
  const completo = prefixo + titulo
  if (completo.length <= LIMITE_TITULO_AVISO) return completo
  return completo.slice(0, LIMITE_TITULO_AVISO - 1).trimEnd() + '…'
}

function paragrafos(...partes: string[]): string {
  return partes.filter(Boolean).join('\n\n')
}

/** A linha da gestão como a API grava: uma linha só, sem espaços sobrando. */
export function linhaDoAviso(nota: string): string {
  return nota.split(/\s+/).filter(Boolean).join(' ')
}

export function avisoDoDocumentoNovo(
  titulo: string,
  categoria: CategoriaDocumento,
  nota: string,
): PreviaDoAviso {
  return {
    titulo: cortar('Documento novo: ', titulo),
    categoria: CATEGORIA_DO_AVISO[categoria] ?? 'Geral',
    texto: paragrafos(
      `Um documento novo foi publicado no Portal: “${titulo}”.`,
      linhaDoAviso(nota),
      'Ele fica guardado em Documentos, no menu do Portal, e o botão “Ver o documento”' +
        ' deste aviso leva direto a ele.',
    ),
  }
}

export function avisoDaVersao(
  titulo: string,
  categoria: CategoriaDocumento,
  versao: number,
  nota: string,
): PreviaDoAviso {
  return {
    titulo: cortar('Documento atualizado: ', titulo),
    categoria: CATEGORIA_DO_AVISO[categoria] ?? 'Geral',
    texto: paragrafos(
      `Saiu a versão ${versao} de um documento do Portal: “${titulo}”.`,
      linhaDoAviso(nota),
      'Ela fica guardada em Documentos, no menu do Portal.',
    ),
  }
}

// --- o arquivo, na hora de escolher (revisão UX, U10) ------------------------------------------

const PALAVRA = /\.(docx?|odt|rtf)$/i

/** O que impede o arquivo escolhido, com o que fazer, ou `null`. A foto pode passar do limite
 *  aqui: ela é reduzida antes de enviar, e `enviarArquivo` confere o tamanho depois. */
export function problemaAoEscolher(arquivo: Pick<File, 'type' | 'size' | 'name'>): string | null {
  const ehPalavra = PALAVRA.test(arquivo.name) || /word|opendocument\.text/.test(arquivo.type)
  if (ehPalavra) {
    return 'Arquivo do Word: salve como PDF (no Word, “Salvar como” e escolha PDF) e escolha o PDF aqui.'
  }
  if (!tipoAceito(arquivo.type)) {
    return 'O Portal aceita PDF e fotos (JPEG, PNG ou WEBP). Se for outro tipo, salve como PDF antes.'
  }
  if (arquivo.size < 1) return 'O arquivo está vazio. Escolha outro.'
  if (arquivo.type === 'application/pdf' && arquivo.size > LIMITES.documento) {
    return (
      `Este PDF tem ${Math.ceil(arquivo.size / MB)} MB e o limite é ${LIMITES.documento / MB} MB. ` +
      'Para reduzir, salve de novo com qualidade menor (“reduzir tamanho” no app de PDF) ou ' +
      'divida em partes.'
    )
  }
  return null
}

/** Tira acentos e maiúsculas, para a busca: "Convenção" → "convencao". */
export function semAcento(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/\p{Mn}/gu, '')
    .toLocaleLowerCase('pt-BR')
}

/** H-18: cada palavra da busca no título ou no nome do assunto, em qualquer ordem. */
export function filtrar<T extends DocumentoResumo>(itens: readonly T[], busca: string): T[] {
  const palavras = semAcento(busca).split(/\s+/).filter(Boolean)
  return itens.filter((item) => {
    const assunto = assuntoDe(item.categoria)
    const alvo = semAcento(`${item.titulo} ${assunto.nome} ${assunto.grupo}`)
    return palavras.every((p) => alvo.includes(p))
  })
}

export interface Grupo<T> {
  assunto: Assunto
  itens: T[]
}

/** Grupos na ordem dos assuntos; dentro de cada um, a ordem da API (do mais novo). */
export function agrupar<T extends DocumentoResumo>(itens: readonly T[]): Grupo<T>[] {
  return ASSUNTOS.map((assunto) => ({
    assunto,
    itens: itens.filter((i) => i.categoria === assunto.valor),
  })).filter((g) => g.itens.length > 0)
}
