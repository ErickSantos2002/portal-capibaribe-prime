// Épico A do M3 · documentos na voz do morador: assuntos, quem vê, datas, tamanhos e a busca.
// Pertence ao épico A.
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
