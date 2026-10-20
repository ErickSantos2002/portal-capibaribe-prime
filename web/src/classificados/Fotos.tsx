// Classificados · as fotos do anúncio aberto (spec, seção 3.2): a primeira grande e as outras em
// miniatura; o toque abre a foto inteira por cima da tela, com "Anterior", "Próxima" e "Fechar"
// (também pelas setas e pelo Esc). Ao fechar, o foco volta à foto que abriu.
import { useEffect, useRef, useState } from 'react'
import { Icone } from '../casca/Icone'
import type { FotoDoAnuncio } from './tipos'

interface Props {
  fotos: FotoDoAnuncio[]
  titulo: string
}

export function FotosDoAnuncio({ fotos, titulo }: Props) {
  const [aberta, setAberta] = useState<number | null>(null)
  const botoes = useRef<(HTMLButtonElement | null)[]>([])
  const ultima = useRef<number | null>(null)

  useEffect(() => {
    if (aberta === null && ultima.current !== null) {
      botoes.current[ultima.current]?.focus()
      ultima.current = null
    }
  }, [aberta])

  if (fotos.length === 0) return null

  function abrir(indice: number) {
    ultima.current = indice
    setAberta(indice)
  }

  const nome = (i: number) => `Foto ${i + 1} de ${fotos.length}: ${titulo}`
  return (
    <section className="cla-fotos" aria-label="Fotos">
      <button
        type="button"
        className="cla-foto-grande"
        ref={(b) => {
          botoes.current[0] = b
        }}
        onClick={() => abrir(0)}
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
                onClick={() => abrir(i + 1)}
              >
                <img src={f.url} alt={nome(i + 1)} loading="lazy" decoding="async" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {aberta !== null && (
        <Visor fotos={fotos} indice={aberta} trocar={setAberta} nome={nome} fechar={() => setAberta(null)} />
      )}
    </section>
  )
}

interface PropsVisor {
  fotos: FotoDoAnuncio[]
  indice: number
  trocar: (i: number) => void
  nome: (i: number) => string
  fechar: () => void
}

function Visor({ fotos, indice, trocar, nome, fechar }: PropsVisor) {
  const fecharBotao = useRef<HTMLButtonElement>(null)
  const total = fotos.length
  useEffect(() => fecharBotao.current?.focus(), [])

  const anterior = () => trocar((indice - 1 + total) % total)
  const proxima = () => trocar((indice + 1) % total)

  return (
    <div
      className="cla-visor"
      role="dialog"
      aria-modal="true"
      aria-label={`Foto ${indice + 1} de ${total}`}
      onKeyDown={(e) => {
        if (e.key === 'Escape') fechar()
        else if (e.key === 'ArrowLeft' && total > 1) anterior()
        else if (e.key === 'ArrowRight' && total > 1) proxima()
      }}
    >
      <div className="cla-visor-topo">
        <span>
          Foto {indice + 1} de {total}
        </span>
        <button type="button" className="botao leve" ref={fecharBotao} onClick={fechar}>
          <Icone nome="fechar" /> Fechar
        </button>
      </div>
      <img className="cla-visor-foto" src={fotos[indice].url} alt={nome(indice)} />
      {total > 1 && (
        <div className="cla-visor-botoes">
          <button type="button" className="botao leve" onClick={anterior}>
            <Icone nome="voltar" /> Anterior
          </button>
          <button type="button" className="botao leve" onClick={proxima}>
            Próxima <Icone nome="seta" />
          </button>
        </div>
      )}
    </div>
  )
}
