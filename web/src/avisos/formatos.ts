// Épico C · Avisos: textos na voz do morador e o texto puro do aviso. Pertence ao épico C.
import type { UnidadeRef } from '../api/tipos'

const MASCULINOS = new Set(['Síndico', 'Conselho'])

/** "Comissão" → "pela Comissão"; "Síndico" → "pelo Síndico" (H-12). */
export function assinatura(publicadoPor: string): string {
  return `${MASCULINOS.has(publicadoPor) ? 'pelo' : 'pela'} ${publicadoPor}`
}

function juntar(itens: (string | number)[]): string {
  if (itens.length < 2) return itens.join('')
  return `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`
}

/** [4] → "Bloco 4"; [1, 2] → "Blocos 1 e 2". */
export function blocosEmTexto(blocos: number[]): string {
  return `${blocos.length === 1 ? 'Bloco' : 'Blocos'} ${juntar(blocos)}`
}

/** Complemento de "para …": "todos os blocos", "o Bloco 4", "os Blocos 1 e 2". */
export function destinoEmTexto(aviso: { para_todos: boolean; blocos: number[] }): string {
  if (aviso.para_todos) return 'todos os blocos'
  return `${aviso.blocos.length === 1 ? 'o' : 'os'} ${blocosEmTexto(aviso.blocos)}`
}

/** Parágrafo = linha em branco (mesmo com espaços); a quebra simples fica dentro dele. */
export function paragrafos(texto: string): string[] {
  return texto
    .split(/\n[ \t]*\n/)
    .map((p) => p.replace(/^\n+|\n+$/g, ''))
    .filter((p) => p.trim() !== '')
}

export interface Parte {
  texto: string
  /** Só endereços http(s): nada de `javascript:` nem outro esquema. */
  link?: string
}

const ENDERECO = /https?:\/\/[^\s<>"]+/g
// Pontuação colada no fim do endereço é da frase, não do link.
const FIM_DE_FRASE = /[.,;:!?)\]}'"…]+$/

/** Separa uma linha em texto e links. Nada aqui vira HTML: a tela monta elementos do React. */
export function partesDaLinha(linha: string): Parte[] {
  const partes: Parte[] = []
  let resto = 0
  for (const achado of linha.matchAll(ENDERECO)) {
    const inicio = achado.index
    const endereco = achado[0].replace(FIM_DE_FRASE, '')
    if (endereco.length <= 'https://'.length) continue
    if (inicio > resto) partes.push({ texto: linha.slice(resto, inicio) })
    partes.push({ texto: endereco, link: endereco })
    resto = inicio + endereco.length
  }
  if (resto < linha.length) partes.push({ texto: linha.slice(resto) })
  return partes
}

/** Texto para colar no grupo do WhatsApp (H-16). */
function linhasPorBloco(unidades: UnidadeRef[]): string[] {
  const porBloco = new Map<number, string[]>()
  for (const u of unidades) porBloco.set(u.bloco, [...(porBloco.get(u.bloco) ?? []), u.apartamento])
  return [...porBloco].map(([bloco, aptos]) => `Bloco ${bloco}: ${aptos.join(', ')}`)
}

/** Texto para colar no grupo (H-16), em dois grupos (revisão do M1, U5): quem entrou e não leu
 *  primeiro, que é a quem a cobrança "abra o aviso" serve; depois quem nem entrou ainda. */
export function listaParaCopiar(
  titulo: string,
  naoEntraram: UnidadeRef[],
  entraramSemLer: UnidadeRef[],
): string {
  const partes = [`Ainda não leram o aviso “${titulo}”:`]
  if (entraramSemLer.length) {
    partes.push(
      ['Entraram no Portal, mas não leram:', ...linhasPorBloco(entraramSemLer)].join('\n'),
    )
  }
  if (naoEntraram.length) {
    partes.push(['Ainda não entraram no Portal:', ...linhasPorBloco(naoEntraram)].join('\n'))
  }
  return partes.join('\n\n')
}

/** A ordem da grade do admin: do 7º andar ao térreo, como o prédio visto de frente. */
export function ordemDaGrade(unidades: UnidadeRef[]): UnidadeRef[] {
  const andar = (u: UnidadeRef) => Math.floor(Number(u.apartamento) / 100)
  return [...unidades].sort(
    (a, b) => a.bloco - b.bloco || andar(b) - andar(a) || a.login.localeCompare(b.login),
  )
}
