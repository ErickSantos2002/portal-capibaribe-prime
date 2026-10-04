import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { cabecalhosDoVercel } from './cabecalhos.ts'

export default defineConfig({
  plugins: [react()],
  server: {
    // Em desenvolvimento, /api vai para o uvicorn local (como a Vercel faz em produção).
    // Sem a CSP aqui: o modo dev do React injeta script embutido para o recarregamento.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  preview: {
    // O build servido localmente recebe os mesmos cabeçalhos de produção (vercel.json).
    headers: cabecalhosDoVercel(),
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
