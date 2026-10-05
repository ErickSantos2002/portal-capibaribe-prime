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
export function listaParaCopiar(titulo: string, naoLeram: UnidadeRef[]): string {
  const porBloco = new Map<number, string[]>()
  for (const u of naoLeram) porBloco.set(u.bloco, [...(porBloco.get(u.bloco) ?? []), u.apartamento])
  const linhas = [...porBloco].map(([bloco, aptos]) => `Bloco ${bloco}: ${aptos.join(', ')}`)
  return [`Ainda não leram o aviso “${titulo}”:`, ...linhas].join('\n')
}
