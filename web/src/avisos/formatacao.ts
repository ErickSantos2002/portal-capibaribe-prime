// O Markdown restrito do aviso (spec dos avisos com formatação, seção 3.1). Funções puras:
// texto → blocos → trechos. Quem desenha é `TextoDoAviso` (componentes.tsx), sempre com elementos
// do React e texto: nenhum caminho daqui transforma texto em HTML, e nada de biblioteca de
// Markdown. Só estas marcas valem; todo o resto é texto literal.
//
//   ## título de seção      - item de lista      1. item numerado      > caixa de destaque
//   **negrito** dentro da linha      linha em branco separa parágrafos      http(s):// vira link
//
// As mesmas marcas de linha são tiradas do resumo do mural pela API (`resumir`, em
// api/app/servicos/avisos.py): mudou aqui, mude lá.
import { partesDaLinha } from './formatos'

export type Bloco =
  | { tipo: 'paragrafo'; linhas: string[] }
  | { tipo: 'titulo'; texto: string }
  | { tipo: 'lista'; itens: string[] }
  | { tipo: 'numerada'; inicio: number; itens: string[] }
  | { tipo: 'destaque'; linhas: string[] }

export interface Trecho {
  texto: string
  negrito?: true
  /** Só endereços http(s) (de `partesDaLinha`). */
  link?: string
}

// A marca vale só com espaço depois e texto em seguida: "##Título", "- " sozinho e "  - recuado"
// ficam como estão.
const TITULO = /^## (?=\S)(.*)$/
const ITEM = /^- (?=\S)(.*)$/
const NUMERADO = /^(\d{1,3})\. (?=\S)(.*)$/
const DESTAQUE = /^> (?=\S)(.*)$/
const EM_BRANCO = /^[ \t]*$/
// `**trecho**` sem espaço colado por dentro das marcas ("2 ** 3" não é negrito).
const NEGRITO = /\*\*(\S(?:.*?\S)??)\*\*/g

/** Separa o texto em blocos, linha a linha. */
export function analisar(texto: string): Bloco[] {
  const blocos: Bloco[] = []
  const ultimo = () => blocos[blocos.length - 1]
  let separado = true // a próxima linha começa bloco novo (início ou depois de linha em branco)

  for (const linha of texto.replace(/\r\n?/g, '\n').split('\n')) {
    if (EM_BRANCO.test(linha)) {
      separado = true
      continue
    }
    const anterior = separado ? undefined : ultimo()
    separado = false
    let achado: RegExpMatchArray | null
    if ((achado = linha.match(TITULO))) {
      blocos.push({ tipo: 'titulo', texto: achado[1].trimEnd() })
      separado = true // título é uma linha só
    } else if ((achado = linha.match(ITEM))) {
      if (anterior?.tipo === 'lista') anterior.itens.push(achado[1])
      else blocos.push({ tipo: 'lista', itens: [achado[1]] })
    } else if ((achado = linha.match(NUMERADO))) {
      if (anterior?.tipo === 'numerada') anterior.itens.push(achado[2])
      else blocos.push({ tipo: 'numerada', inicio: Number(achado[1]), itens: [achado[2]] })
    } else if ((achado = linha.match(DESTAQUE))) {
      if (anterior?.tipo === 'destaque') anterior.linhas.push(achado[1])
      else blocos.push({ tipo: 'destaque', linhas: [achado[1]] })
    } else if (anterior?.tipo === 'paragrafo') {
      anterior.linhas.push(linha)
    } else {
      blocos.push({ tipo: 'paragrafo', linhas: [linha] })
    }
  }
  return blocos
}

function comLinks(texto: string, negrito: boolean): Trecho[] {
  return partesDaLinha(texto).map((parte) => ({
    texto: parte.texto,
    ...(parte.link ? { link: parte.link } : {}),
    ...(negrito ? { negrito: true as const } : {}),
  }))
}

/** Separa uma linha em texto, negrito e links. */
export function trechos(linha: string): Trecho[] {
  const resultado: Trecho[] = []
  let resto = 0
  for (const achado of linha.matchAll(NEGRITO)) {
    if (achado.index > resto) resultado.push(...comLinks(linha.slice(resto, achado.index), false))
    resultado.push(...comLinks(achado[1], true))
    resto = achado.index + achado[0].length
  }
  if (resto < linha.length) resultado.push(...comLinks(linha.slice(resto), false))
  return resultado
}
