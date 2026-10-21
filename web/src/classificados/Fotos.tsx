// Classificados · as fotos do anúncio aberto (spec, seção 3.2): a primeira grande e as outras em
// miniatura; o toque abre a foto inteira no visor comum dos anexos (`avisos/VisorDeFotos.tsx`:
// fundo inerte, foco preso, Esc, sem rolar por trás). Ao fechar, o foco volta à foto que estava
// aberta (revisão UX 1).
import { useCallback, useEffect, useRef, useState } from 'react'
import { VisorDeFotos } from '../avisos/VisorDeFotos'
import type { FotoDoAnuncio } from './tipos'

interface Props {
  fotos: FotoDoAnuncio[]
  titulo: string
}

export function FotosDoAnuncio({ fotos, titulo }: Props) {
  const [aberta, setAberta] = useState<number | null>(null)
  const botoes = useRef<(HTMLButtonElement | null)[]>([])
  const focarDepois = useRef<number | null>(null)
  const fechar = useCallback((indice: number) => {
    focarDepois.current = indice
    setAberta(null)
  }, [])

  // Depois que a página deixou de estar inerte (o visor já saiu).
  useEffect(() => {
    if (aberta !== null || focarDepois.current === null) return
    botoes.current[focarDepois.current]?.focus()
    focarDepois.current = null
  }, [aberta])

  if (fotos.length === 0) return null
  const nome = (i: number) => `Foto ${i + 1} de ${fotos.length}: ${titulo}`
  return (
    <section className="cla-fotos" aria-label="Fotos">
      <button
        type="button"
        className="cla-foto-grande"
        ref={(b) => {
          botoes.current[0] = b
        }}
        onClick={() => setAberta(0)}
      >
        <img src={fotos[0].url} alt={nome(0)} decoding="async" />
        {fotos.length > 1 && <span className="cla-foto-conta">1 de {fotos.length}</span>}
      </button>
      {fotos.length > 1 && (
        <ul className="cla-miniaturas">
          {fotos.slice(1).map((f, i) => (
            <li key={f.id}>
              <button
                type="button"
                ref={(b) => {
                  botoes.current[i + 1] = b
                }}
                onClick={() => setAberta(i + 1)}
              >
                <img src={f.url} alt={nome(i + 1)} loading="lazy" decoding="async" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {aberta !== null && (
        <VisorDeFotos
          fotos={fotos.map((f) => f.url)}
          inicio={aberta}
          fechar={fechar}
          descrever={nome}
        />
      )}
    </section>
  )
}
