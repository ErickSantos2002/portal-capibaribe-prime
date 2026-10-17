import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
// Fonte servida pelo próprio Portal, sem requisição a terceiros (LGPD).
import '@fontsource/atkinson-hyperlegible/400.css'
import '@fontsource/atkinson-hyperlegible/700.css'
import './estilo.css'
import { vigiarLetra } from './casca/letra'
import { registrarServiceWorker } from './notificacoes/ganchos'
import { rotas } from './rotas'

const roteador = createBrowserRouter(rotas)

// Marca o html com a letra grande e a tela baixa antes do primeiro desenho (M5, revisões, R1).
vigiarLetra()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={roteador} />
  </StrictMode>,
)

// M2 (H-05): service worker do PWA e das notificações. O épico A implementa.
registrarServiceWorker()
