// Primeira passada mecânica da regra da letra (spec docs/superpowers/specs/m5-letra.md, seção 3):
// troca px por rem (1rem = 16px) em toda declaração, e por em nas media queries, deixando em px
// só as exceções sem justificativa (borda, contorno de foco, sombra, canto, sublinhado e os tokens
// --r-* e --sombra). NÃO decide os casos de "/* px: motivo */" nem o teto (min com vw): depois de
// rodar, leia o diff, devolva à mão o que a spec manda ficar em px e rode a conferência visual.
//
// Uso, da raiz do repositório: node scripts/dev/px-para-rem.mjs web/src/avisos/avisos.css [...]
// (reescreve os arquivos; o git mostra o que mudou).
import { readFileSync, writeFileSync } from 'node:fs'

const EXCECOES = [
  /^border(-(top|right|bottom|left|block|inline)(-(start|end))?)?(-width)?$/,
  /^border(-(top|right|bottom|left|start|end)(-(left|right|start|end))?)?-radius$/,
  /^outline(-width|-offset)?$/,
  /^(box|text)-shadow$/,
  /^text-underline-offset$/,
  /^text-decoration-thickness$/,
  /^--(r-pequeno|r-medio|sombra)$/,
]

/** 18 → "1.125"; até 4 casas, sem zero sobrando. */
const emRem = (px) => {
  const valor = Number((px / 16).toFixed(4))
  return String(valor)
}
const trocar = (texto, unidade) =>
  texto.replace(/(?<![\w.-])(-?\d*\.?\d+)px\b/g, (_, n) => (Number(n) === 0 ? '0' : `${emRem(Number(n))}${unidade}`))

for (const arquivo of process.argv.slice(2)) {
  const css = readFileSync(arquivo, 'utf8')
  let trocas = 0
  // Media queries: o px vira em (o em da media query é o tamanho inicial do navegador).
  let saida = css.replace(/@(media|container)[^{]*\{/g, (prelude) => {
    const novo = trocar(prelude, 'em')
    if (novo !== prelude) trocas++
    return novo
  })
  // Declarações: `propriedade: valor` até o `;` ou o `}`, fora de comentário.
  saida = saida.replace(/\/\*[\s\S]*?\*\/|([\w-]+)(\s*:\s*)([^;{}]*)/g, (todo, prop, dois, valor) => {
    if (!prop || !/px\b/.test(valor) || EXCECOES.some((re) => re.test(prop.toLowerCase()))) return todo
    trocas++
    return `${prop}${dois}${trocar(valor, 'rem')}`
  })
  writeFileSync(arquivo, saida)
  console.log(`${arquivo}: ${trocas} trocas`)
}
