/// <reference types="vitest/config" />
import { readFileSync } from 'node:fs'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { cabecalhosDoVercel } from './cabecalhos.ts'

// Para onde o /api vai em desenvolvimento e no preview. Várias cópias de trabalho ao mesmo tempo
// usam portas diferentes: `PORTAL_API_URL=http://127.0.0.1:8120 npm run preview`.
const API = process.env.PORTAL_API_URL ?? 'http://127.0.0.1:8000'

// Fonte única da versão do Portal: o package.json (README, seção Versões).
const { version: VERSAO } = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf8'),
) as { version: string }

export default defineConfig({
  plugins: [react()],
  define: {
    __VERSAO__: JSON.stringify(VERSAO),
  },
  server: {
    // Em desenvolvimento, /api vai para o uvicorn local (como a Vercel faz em produção).
    // Sem a CSP aqui: o modo dev do React injeta script embutido para o recarregamento.
    proxy: {
      '/api': API,
    },
  },
  // Testes de componente (Vitest + jsdom). Os testes de configuração em testes/ rodam com
  // node --test depois do build (ver package.json).
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,
  },
  preview: {
    // O build servido localmente recebe os mesmos cabeçalhos de produção (vercel.json).
    headers: cabecalhosDoVercel(),
    proxy: {
      '/api': API,
    },
  },
})
