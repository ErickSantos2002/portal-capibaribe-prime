import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Fonte servida pelo próprio Portal, sem requisição a terceiros (LGPD).
import '@fontsource/atkinson-hyperlegible/400.css'
import '@fontsource/atkinson-hyperlegible/700.css'
import './estilo.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
