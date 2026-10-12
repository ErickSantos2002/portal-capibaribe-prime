// M3 · Épico B: os anexos no aviso aberto, na versão antiga e na prévia (spec `m3-anexos.md`,
// seção 3.3). Foto na própria tela (toque abre grande, com anterior e próxima); PDF como link que
// abre numa aba nova (a CSP não deixa embutir PDF). Os dois passam pela rota `…/abrir` do Portal,
// que confere a sessão e redireciona para um link novo (revisão U12).
import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ArquivoEnviado } from '../arquivos/tipos'
import { Icone } from '../casca/Icone'
import { descricaoDoAnexo, ehFoto } from './anexos'
import { enderecoDoAnexo } from './api'
import { IconeAnexo } from './IconesAnexo'
import './anexos.css'

/** Um anexo para mostrar. `previa`: a miniatura local (`blob:`) da foto ainda não publicada. */
export interface AnexoParaMostrar {
  arquivo: ArquivoEnviado
  previa?: string | null
}

/** Quantas vezes a miniatura tenta carregar antes de desistir sozinha. */
const TENTATIVAS_POR_VEZ = 2

/** O endereço da foto: a miniatura local, ou a rota de abrir do Portal (com `?tentativa=` para
 *  o navegador não reaproveitar a resposta que falhou). */
function enderecoDaFoto(avisoId: number | undefined, anexo: AnexoParaMostrar, tentativa = 1) {
  if (anexo.previa) return anexo.previa
  if (avisoId === undefined) return null
  const base = enderecoDoAnexo(avisoId, anexo.arquivo.id)
  return tentativa > 1 ? `${base}?tentativa=${tentativa}` : base
}

function useFotoQueTenta(avisoId: number | undefined, anexo: AnexoParaMostrar) {
  const [tentativa, setTentativa] = useState(1)
  const [falhasSeguidas, setFalhasSeguidas] = useState(0)
  const falhou = falhasSeguidas >= TENTATIVAS_POR_VEZ
  return {
    url: enderecoDaFoto(avisoId, anexo, tentativa),
    falhou,
    aoFalhar() {
      setFalhasSeguidas((f) => f + 1)
      if (falhasSeguidas + 1 < TENTATIVAS_POR_VEZ) setTentativa((t) => t + 1)
    },
    tentar() {
      setFalhasSeguidas(0)
      setTentativa((t) => t + 1)
    },
  }
}

/** A miniatura de uma foto que já está no Portal (usada também no formulário de correção). */
export function MiniaturaRemota({
  avisoId,
  arquivo,
}: {
  avisoId: number
  arquivo: ArquivoEnviado
}) {
  const foto = useFotoQueTenta(avisoId, { arquivo })
  if (foto.falhou || !foto.url) return <IconeAnexo nome="foto" tamanho={28} />
  return <img src={foto.url} alt="" onError={foto.aoFalhar} />
}

interface PropsVisualizador {
  avisoId?: number
  fotos: readonly AnexoParaMostrar[]
  inicio: number
  /** Fecha e diz qual foto estava aberta (o foco volta para a miniatura dela). */
  fechar: (indice: number) => void
}

/** As fotos grandes, por cima da tela (C4, U7, U8). Enquanto aberto: o resto da página fica
 *  inerte, o foco não sai, Esc fecha e as setas do teclado trocam de foto. O zoom de dois dedos
 *  do navegador continua valendo (nada de `touch-action: none`). */
function Visualizador({ avisoId, fotos, inicio, fechar }: PropsVisualizador) {
  const [indice, setIndice] = useState(inicio)
  const janela = useRef<HTMLDivElement>(null)
  const botaoFechar = useRef<HTMLButtonElement>(null)
  const atual = useRef(indice)
  useEffect(() => {
    atual.current = indice
  }, [indice])
  const varias = fotos.length > 1
  const rotulo = `Foto ${indice + 1} de ${fotos.length}`

  useEffect(() => {
    const dialogo = janela.current
    botaoFechar.current?.focus()
    // O resto da página fica inerte (nem foco nem leitor de tela chegam lá).
    const fundo = [...document.body.children].filter((e) => dialogo && !e.contains(dialogo))
    for (const e of fundo) e.setAttribute('inert', '')
    const rolagem = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function teclar(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        fechar(atual.current)
      } else if (e.key === 'ArrowRight') {
        setIndice((i) => (i + 1) % fotos.length)
      } else if (e.key === 'ArrowLeft') {
        setIndice((i) => (i - 1 + fotos.length) % fotos.length)
      } else if (e.key === 'Tab' && dialogo) {
        // O foco gira entre os botões da janela.
        const botoes = [...dialogo.querySelectorAll('button')]
        const posicao = botoes.indexOf(document.activeElement as HTMLButtonElement)
        const proximo = e.shiftKey ? posicao - 1 : posicao + 1
        e.preventDefault()
        botoes[(proximo + botoes.length) % botoes.length]?.focus()
      }
    }
    // O foco que escapar (um toque na foto, por exemplo) volta para a janela.
    function prender(e: FocusEvent) {
      if (dialogo && !dialogo.contains(e.target as Node)) botaoFechar.current?.focus()
    }
    document.addEventListener('keydown', teclar)
    document.addEventListener('focusin', prender)
    return () => {
      document.removeEventListener('keydown', teclar)
      document.removeEventListener('focusin', prender)
      for (const e of fundo) e.removeAttribute('inert')
      document.body.style.overflow = rolagem
    }
  }, [fechar, fotos.length])

  const url = enderecoDaFoto(avisoId, fotos[indice])
  return createPortal(
    <div
      ref={janela}
      className="anexo-visualizador"
      role="dialog"
      aria-modal="true"
      aria-label={rotulo}
      // Um toque na foto ou no fundo mantém o foco na janela.
      tabIndex={-1}
    >
      <div className="anexo-visualizador-topo">
        <p aria-live="polite">{rotulo}</p>
        <button
          ref={botaoFechar}
          type="button"
          className="botao leve"
          onClick={() => fechar(indice)}
        >
          <IconeAnexo nome="fechar" /> Fechar
        </button>
      </div>
      {url && <img src={url} alt={rotulo} />}
      {varias && (
        <div className="anexo-visualizador-passar">
          <button
            type="button"
            className="botao leve"
            aria-label="Foto anterior"
            onClick={() => setIndice((i) => (i - 1 + fotos.length) % fotos.length)}
          >
            <Icone nome="voltar" /> Anterior
          </button>
          <button
            type="button"
            className="botao leve"
            aria-label="Próxima foto"
            onClick={() => setIndice((i) => (i + 1) % fotos.length)}
          >
            Próxima <Icone nome="seta" />
          </button>
        </div>
      )}
    </div>,
    document.body,
  )
}

interface PropsFoto {
  avisoId?: number
  anexo: AnexoParaMostrar
  posicao: number
  total: number
  abrir: () => void
  botao: (elemento: HTMLButtonElement | null) => void
}

function Foto({ avisoId, anexo, posicao, total, abrir, botao }: PropsFoto) {
  const foto = useFotoQueTenta(avisoId, anexo)
  const unica = total === 1
  const rotulo = `Foto ${posicao} de ${total}`

  if (foto.falhou) {
    return (
      <div className={`anexo-foto falhou${unica ? ' unica' : ''}`}>
        <IconeAnexo nome="foto" tamanho={32} />
        <p>Não deu para mostrar a foto.</p>
        <button type="button" className="texto-link" onClick={foto.tentar}>
          Tentar de novo
        </button>
      </div>
    )
  }
  return (
    <button
      ref={botao}
      type="button"
      className={`anexo-foto${unica ? ' unica' : ''}`}
      // U7: o morador não vê o nome técnico do arquivo (IMG_2031.webp).
      aria-label={`Ver a foto ${posicao} de ${total} em tamanho grande`}
      onClick={abrir}
    >
      {foto.url ? (
        <img src={foto.url} alt={rotulo} onError={foto.aoFalhar} />
      ) : (
        <IconeAnexo nome="foto" tamanho={32} />
      )}
      {/* U9: a miniatura diz que dá para ampliar. */}
      <span className="anexo-ampliar" aria-hidden="true">
        <Icone nome="busca" tamanho={18} /> Ampliar
      </span>
    </button>
  )
}

function Pdf({ avisoId, arquivo }: { avisoId?: number; arquivo: ArquivoEnviado }) {
  const conteudo = (
    <>
      <Icone nome="documentos" tamanho={32} />
      <span>
        <span className="anexo-nome">{arquivo.nome}</span>
        <span className="anexo-detalhe">
          {descricaoDoAnexo(arquivo)}
          {avisoId !== undefined && ' · abre em outra aba'}
        </span>
      </span>
    </>
  )
  // Na prévia o aviso ainda não existe: o PDF aparece, mas não abre.
  if (avisoId === undefined) return <div className="anexo-pdf">{conteudo}</div>
  // Um link de verdade (U12): o Safari do iPhone não bloqueia a aba e recarregar funciona.
  return (
    <a
      className="anexo-pdf"
      href={enderecoDoAnexo(avisoId, arquivo.id)}
      target="_blank"
      rel="noopener noreferrer"
    >
      {conteudo}
    </a>
  )
}

/** Os anexos de uma versão do aviso. Sem anexo, nada. `avisoId` ausente: é a prévia. */
export function AnexosDoAviso({
  avisoId,
  anexos,
}: {
  avisoId?: number
  anexos: readonly AnexoParaMostrar[]
}) {
  const [aberta, setAberta] = useState<number | null>(null)
  const miniaturas = useRef<(HTMLButtonElement | null)[]>([])
  const focarDepois = useRef<number | null>(null)
  const fechar = useCallback((indice: number) => {
    focarDepois.current = indice
    setAberta(null)
  }, [])
  // O foco volta para a miniatura da foto que estava aberta, depois que a página deixou de
  // estar inerte (a janela já saiu).
  useEffect(() => {
    if (aberta !== null || focarDepois.current === null) return
    miniaturas.current[focarDepois.current]?.focus()
    focarDepois.current = null
  }, [aberta])
  if (anexos.length === 0) return null
  const fotos = anexos.filter((a) => ehFoto(a.arquivo.tipo))
  const pdfs = anexos.filter((a) => !ehFoto(a.arquivo.tipo))
  return (
    <section className="anexos" aria-label="Anexos">
      {fotos.length > 0 && (
        <div className={`anexos-fotos${fotos.length === 1 ? ' uma' : ''}`}>
          {fotos.map((a, i) => (
            <Foto
              key={a.arquivo.id}
              avisoId={avisoId}
              anexo={a}
              posicao={i + 1}
              total={fotos.length}
              abrir={() => setAberta(i)}
              botao={(elemento) => {
                miniaturas.current[i] = elemento
              }}
            />
          ))}
        </div>
      )}
      {pdfs.map((a) => (
        <Pdf key={a.arquivo.id} avisoId={avisoId} arquivo={a.arquivo} />
      ))}
      {aberta !== null && (
        <Visualizador
          avisoId={avisoId}
          fotos={fotos}
          inicio={aberta}
          fechar={fechar}
        />
      )}
    </section>
  )
}
