// A barra Título · Negrito · Lista · Destaque do formulário (spec dos avisos com formatação,
// seção 3.4): função pura que devolve o texto novo e a seleção que o campo deve mostrar.
export type Marca = 'titulo' | 'negrito' | 'lista' | 'destaque'

export interface ComSelecao {
  texto: string
  inicio: number
  fim: number
}

const PREFIXOS: Record<Exclude<Marca, 'negrito'>, string> = {
  titulo: '## ',
  lista: '- ',
  destaque: '> ',
}
// Qualquer marca de linha que já esteja lá: trocar de uma para outra não empilha.
const MARCA_DE_LINHA = /^(?:## |- |\d{1,3}\. |> )/
const EXEMPLO_DO_NEGRITO = 'negrito'

function negrito(texto: string, inicio: number, fim: number): ComSelecao {
  // Espaço nas pontas fica fora: "** palavra **" não seria negrito.
  while (inicio < fim && /\s/.test(texto[inicio])) inicio++
  while (fim > inicio && /\s/.test(texto[fim - 1])) fim--
  if (inicio === fim) {
    const novo = texto.slice(0, inicio) + `**${EXEMPLO_DO_NEGRITO}**` + texto.slice(fim)
    return { texto: novo, inicio: inicio + 2, fim: inicio + 2 + EXEMPLO_DO_NEGRITO.length }
  }
  if (texto.slice(inicio - 2, inicio) === '**' && texto.slice(fim, fim + 2) === '**') {
    const novo = texto.slice(0, inicio - 2) + texto.slice(inicio, fim) + texto.slice(fim + 2)
    return { texto: novo, inicio: inicio - 2, fim: fim - 2 }
  }
  const novo = texto.slice(0, inicio) + '**' + texto.slice(inicio, fim) + '**' + texto.slice(fim)
  return { texto: novo, inicio: inicio + 2, fim: fim + 2 }
}

function deLinha(texto: string, inicio: number, fim: number, prefixo: string): ComSelecao {
  const comeco = texto.lastIndexOf('\n', inicio - 1) + 1
  // Seleção que acaba logo depois de uma quebra de linha não inclui a linha seguinte.
  const ate = fim > inicio && texto[fim - 1] === '\n' ? fim - 1 : fim
  const quebra = texto.indexOf('\n', ate)
  const final = quebra === -1 ? texto.length : quebra
  const linhas = texto.slice(comeco, final).split('\n')
  const preenchidas = linhas.filter((l) => l.trim() !== '')
  const tirar = preenchidas.length > 0 && preenchidas.every((l) => l.startsWith(prefixo))
  const novas = linhas.map((linha) => {
    if (tirar) return linha.slice(prefixo.length)
    if (linha.trim() === '' && linhas.length > 1) return linha
    return prefixo + linha.replace(MARCA_DE_LINHA, '')
  })
  const trecho = novas.join('\n')
  const novo = texto.slice(0, comeco) + trecho + texto.slice(final)
  if (inicio === fim) {
    const cursor = comeco + trecho.length
    return { texto: novo, inicio: cursor, fim: cursor }
  }
  return { texto: novo, inicio: comeco, fim: comeco + trecho.length }
}

/** Aplica a marca na seleção (`inicio`..`fim`) ou na linha do cursor. Repetir desfaz. */
export function aplicarMarca(texto: string, inicio: number, fim: number, marca: Marca): ComSelecao {
  if (marca === 'negrito') return negrito(texto, inicio, fim)
  return deLinha(texto, inicio, fim, PREFIXOS[marca])
}
