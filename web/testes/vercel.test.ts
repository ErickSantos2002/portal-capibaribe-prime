// Conferências do vercel.json que não dependem de deploy.
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { test } from 'node:test'

const raiz = new URL('../../', import.meta.url)
const config = JSON.parse(readFileSync(new URL('vercel.json', raiz), 'utf8'))

test('a função da API não leva os testes nem as migrações', () => {
  const funcoes = config.services.api.functions as Record<string, { excludeFiles?: string }>
  const [[caminho, opcoes]] = Object.entries(funcoes)
  // O padrão precisa casar com o arquivo de entrada de verdade, senão a Vercel recusa o build.
  assert.ok(existsSync(new URL(`api/${caminho}`, raiz)), `api/${caminho} não existe`)
  assert.equal(config.services.api.entrypoint, caminho.replace(/\.py$/, '').replace('/', '.') + ':app')
  assert.match(opcoes.excludeFiles ?? '', /testes\/\*\*/)
  assert.match(opcoes.excludeFiles ?? '', /migracoes\/\*\*/)
})

test('/api vai para a FastAPI antes do resto ir para o front', () => {
  const destinos = config.rewrites.map((r: { source: string; destination: { service: string } }) => [
    r.source,
    r.destination.service,
  ])
  assert.deepEqual(destinos, [
    ['/api/(.*)', 'api'],
    ['/(.*)', 'web'],
  ])
  assert.deepEqual(config.regions, ['gru1'])
})
