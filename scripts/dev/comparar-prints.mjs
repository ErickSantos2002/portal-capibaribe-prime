// Compara duas rodadas do conferir-letra.mjs, print a print (ImageMagick `compare`, tolerância de
// 2 %): a conversão para rem não pode mudar nada com a letra de fábrica (spec m5-letra, seção 6).
// Uso: node scripts/dev/comparar-prints.mjs /tmp/portal-letra-g1-antes /tmp/portal-letra-g1-depois [-16.png]
// O terceiro argumento é o fim do nome dos prints comparados (padrão: os de 16 px). Lista só os
// que mudaram, com a caixa onde mudaram; sai com código 1 se algum mudou.
import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const [antes, depois, sufixo = '-16.png'] = process.argv.slice(2)
if (!antes || !depois) {
  console.error('uso: node scripts/dev/comparar-prints.mjs <pasta-antes> <pasta-depois> [-16.png]')
  process.exit(2)
}
const tmp = mkdtempSync(join(tmpdir(), 'comparar-prints-'))
const tamanho = (p) => execFileSync('magick', ['identify', '-format', '%wx%h', p]).toString()
let mudaram = 0
let iguais = 0
for (const nome of readdirSync(depois).filter((n) => n.endsWith(sufixo)).sort()) {
  const a = join(antes, nome)
  const d = join(depois, nome)
  if (!existsSync(a)) {
    console.log(`${nome}: não existe em ${antes}`)
    continue
  }
  if (tamanho(a) !== tamanho(d)) {
    console.log(`${nome}: altura mudou, ${tamanho(a)} → ${tamanho(d)}`)
    mudaram++
    continue
  }
  const dif = join(tmp, nome)
  const r = spawnSync('compare', ['-metric', 'AE', '-fuzz', '2%', a, d, '-compose', 'src', dif])
  const pixels = Number.parseFloat(r.stderr.toString())
  if (pixels === 0) {
    iguais++
    continue
  }
  const caixa = execFileSync('magick', [dif, '-trim', '-format', '%wx%h%X%Y', 'info:']).toString()
  console.log(`${nome}: ${Math.round(pixels)} px diferentes, na caixa ${caixa}`)
  mudaram++
}
rmSync(tmp, { recursive: true, force: true })
console.log(`\n${iguais} iguais, ${mudaram} diferentes`)
process.exit(mudaram ? 1 : 0)
