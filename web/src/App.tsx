import { useEffect, useState } from 'react'

// Página "no ar" do M0: prova que front, API e banco conversam. Nenhuma tela de morador ainda.

type Saude =
  | { estado: 'carregando' }
  | { estado: 'ok'; unidades: number }
  | { estado: 'indisponivel' }

const formatar = new Intl.NumberFormat('pt-BR')

function useSaude(): Saude {
  const [saude, setSaude] = useState<Saude>({ estado: 'carregando' })

  useEffect(() => {
    const controle = new AbortController()
    fetch('/api/saude', { signal: controle.signal, cache: 'no-store' })
      .then(async (resposta) => {
        if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`)
        const corpo: unknown = await resposta.json()
        const unidades = (corpo as { unidades?: unknown }).unidades
        if (typeof unidades !== 'number') throw new Error('resposta inesperada')
        setSaude({ estado: 'ok', unidades })
      })
      .catch((erro: unknown) => {
        if (erro instanceof DOMException && erro.name === 'AbortError') return
        setSaude({ estado: 'indisponivel' })
      })
    return () => controle.abort()
  }, [])

  return saude
}

export default function App() {
  const saude = useSaude()

  return (
    <main className="entrada">
      <span className="placa marca" aria-hidden="true">
        <small>Capibaribe</small>
        <strong>PRIME</strong>
      </span>
      <h1>Portal Capibaribe Prime</h1>
      <p className="suave">Os avisos oficiais do condomínio, num lugar só.</p>

      <section className="cartao" aria-live="polite">
        <p className="selo">Em construção</p>
        {saude.estado === 'carregando' && <p>Conferindo o sistema…</p>}
        {saude.estado === 'ok' && (
          <p>
            O Portal está no ar, com{' '}
            <strong>{formatar.format(saude.unidades)} unidades</strong> cadastradas.
          </p>
        )}
        {saude.estado === 'indisponivel' && (
          <p>O Portal está sendo montado. Volte em breve.</p>
        )}
      </section>
    </main>
  )
}
