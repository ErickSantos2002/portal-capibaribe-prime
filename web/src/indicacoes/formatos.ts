// Indicações · formatos da tela: telefone, links e as contagens em texto.

/** "(81) 9 9999-0001" (celular) e "(81) 3333-4444" (fixo). Outra coisa volta como veio. */
export function telefoneNaTela(d: string): string {
  if (/^\d{11}$/.test(d)) return `(${d.slice(0, 2)}) ${d[2]} ${d.slice(3, 7)}-${d.slice(7)}`
  if (/^\d{10}$/.test(d)) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`
  return d
}

/** O DDD entre parênteses e o resto, para a tela não quebrar o número no meio. */
export function partesDoTelefone(d: string): [string, string] {
  const tela = telefoneNaTela(d)
  const espaco = tela.indexOf(' ')
  return espaco > 0 ? [tela.slice(0, espaco), tela.slice(espaco + 1)] : [tela, '']
}

/** Celular tem 11 dígitos (o terceiro é 9); fixo, 10. */
export const ehCelular = (d: string) => d.length === 11

export const linkWhatsApp = (d: string) => `https://wa.me/55${d}`

export const linkTelefone = (d: string) => `tel:+55${d}`

export const linkInstagram = (usuario: string) => `https://www.instagram.com/${usuario}/`

export function recomendamEmTexto(n: number): string {
  if (n === 0) return 'Nenhum vizinho recomenda ainda'
  return n === 1 ? '1 vizinho recomenda' : `${n} vizinhos recomendam`
}

export function naoRecomendamEmTexto(n: number): string {
  return n === 1 ? '1 não recomenda' : `${n} não recomendam`
}

export function comAvisoEmTexto(n: number): string {
  return n === 1 ? '1 indicação com aviso da vizinhança' : `${n} indicações com aviso da vizinhança`
}

export function encontradas(n: number): string {
  if (n === 0) return 'Nenhuma indicação encontrada.'
  return n === 1 ? '1 indicação encontrada.' : `${n} indicações encontradas.`
}
