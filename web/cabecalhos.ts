// Os cabeçalhos de segurança moram num lugar só: o vercel.json da raiz. O `vite preview` (e o
// teste) leem daqui, então o que se confere localmente é o que vai para produção.
import { readFileSync } from 'node:fs'

interface RegraDeCabecalho {
  source: string
  headers: { key: string; value: string }[]
}

export function cabecalhosDoVercel(): Record<string, string> {
  const arquivo = new URL('../vercel.json', import.meta.url)
  const config = JSON.parse(readFileSync(arquivo, 'utf8')) as { headers?: RegraDeCabecalho[] }
  const regra = config.headers?.find((r) => r.source === '/(.*)')
  return Object.fromEntries((regra?.headers ?? []).map((h) => [h.key, h.value]))
}
