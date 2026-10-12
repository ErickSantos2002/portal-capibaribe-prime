// M3 · Épico B: os anexos no aviso aberto, na versão antiga e na prévia (spec `m3-anexos.md`,
// seção 3.3). Foto na própria tela (toque abre grande); PDF como botão que abre numa aba nova
// (a CSP não deixa embutir PDF). O link vale 5 minutos e é pedido na hora, nunca guardado.
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ArquivoEnviado } from '../arquivos/tipos'
import { Icone } from '../casca/Icone'
import { descricaoDoAnexo, ehFoto } from './anexos'
import { linkDoAnexo } from './api'
import { comoErroDaApi } from './carregar'
import { IconeAnexo } from './IconesAnexo'
import './anexos.css'

/** Um anexo para mostrar. `previa`: a miniatura local (`blob:`) da foto ainda não publicada. */
export interface AnexoParaMostrar {
  arquivo: ArquivoEnviado
  previa?: string | null
}

/** Quantas vezes a foto pede o link antes de desistir sozinha (o link pode ter vencido). */
const PEDIDOS_POR_VEZ = 2

/** O endereço da foto: a miniatura local, ou o link pedido à API (e pedido de novo se a
 *  imagem falhar uma vez). `falhou`: desistiu; `tentar` recomeça. */
function useEnderecoDaFoto(
  avisoId: number | undefined,
  arquivo: ArquivoEnviado,
  previa?: string | null,
) {
  const [vez, setVez] = useState(0)
  const [pedidos, setPedidos] = useState(1)
  const [link, setLink] = useState<{ vez: number; url: string } | null>(null)
  const [falhou, setFalhou] = useState(false)
  const remoto = !previa && avisoId !== undefined

  useEffect(() => {
    if (!remoto) return
    let valendo = true
    linkDoAnexo(avisoId, arquivo.id)
      .then((l) => valendo && setLink({ vez, url: l.url }))
      .catch(() => valendo && setFalhou(true))
    return () => {
      valendo = false
    }
  }, [remoto, avisoId, arquivo.id, vez])

  const url = previa ?? (link?.vez === vez ? link.url : null)
  return {
    url,
    falhou,
    /** A imagem não carregou: pede o link de novo, ou desiste. */
    aoFalhar() {
      if (!remoto || pedidos >= PEDIDOS_POR_VEZ) {
        setFalhou(true)
        return
      }
      setPedidos((p) => p + 1)
      setVez((v) => v + 1)
    },
    tentar() {
      setFalhou(false)
      setPedidos(1)
      setVez((v) => v + 1)
    },
  }
}

/** A foto grande, por cima da tela. Esc ou "Fechar" fecham; o foco fica no "Fechar". */
function Visualizador({ url, nome, fechar }: { url: string; nome: string; fechar: () => void }) {
  const botao = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    botao.current?.focus()
    const antes = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = antes
    }
  }, [])
  return createPortal(
    <div
      className="anexo-visualizador"
      role="dialog"
      aria-modal="true"
      aria-label={`Foto: ${nome}`}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          e.stopPropagation()
          fechar()
        } else if (e.key === 'Tab') {
          // O único controle da janela é o "Fechar": o foco não sai dela.
          e.preventDefault()
          botao.current?.focus()
        }
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) fechar()
      }}
    >
      <div className="anexo-visualizador-topo">
        <p>{nome}</p>
        <button ref={botao} type="button" className="botao leve" onClick={fechar}>
          <IconeAnexo nome="fechar" /> Fechar
        </button>
      </div>
      <img src={url} alt={`Foto: ${nome}`} />
    </div>,
    document.body,
  )
}

/** A miniatura de uma foto que já está no Portal (usada também no formulário de correção). */
export function MiniaturaRemota({
  avisoId,
  arquivo,
}: {
  avisoId: number
  arquivo: ArquivoEnviado
}) {
  const foto = useEnderecoDaFoto(avisoId, arquivo)
  if (foto.falhou || !foto.url) return <IconeAnexo nome="foto" tamanho={28} />
  return <img src={foto.url} alt="" onError={foto.aoFalhar} />
}

interface PropsFoto {
  avisoId?: number
  anexo: AnexoParaMostrar
  unica: boolean
}

function Foto({ avisoId, anexo, unica }: PropsFoto) {
  const { arquivo } = anexo
  const foto = useEnderecoDaFoto(avisoId, arquivo, anexo.previa)
  const [aberta, setAberta] = useState(false)
  const botao = useRef<HTMLButtonElement>(null)

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
    <>
      <button
        ref={botao}
        type="button"
        className={`anexo-foto${unica ? ' unica' : ''}`}
        aria-label={`Ver a foto ${arquivo.nome} em tamanho grande`}
        disabled={!foto.url}
        onClick={() => setAberta(true)}
      >
        {foto.url ? (
          <img src={foto.url} alt={`Foto: ${arquivo.nome}`} onError={foto.aoFalhar} />
        ) : (
          <IconeAnexo nome="foto" tamanho={32} />
        )}
      </button>
      {aberta && foto.url && (
        <Visualizador
          url={foto.url}
          nome={arquivo.nome}
          fechar={() => {
            setAberta(false)
            botao.current?.focus()
          }}
        />
      )}
    </>
  )
}

function Pdf({ avisoId, arquivo }: { avisoId?: number; arquivo: ArquivoEnviado }) {
  const [abrindo, setAbrindo] = useState(false)
  const [erro, setErro] = useState('')
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

  async function abrir(id: number) {
    // A aba nasce no toque (o Safari do iPhone bloqueia a que nasce depois de esperar a API).
    const aba = window.open('', '_blank')
    setAbrindo(true)
    setErro('')
    try {
      const { url } = await linkDoAnexo(id, arquivo.id)
      if (aba) {
        aba.opener = null
        aba.location.href = url
      } else {
        window.location.assign(url)
      }
    } catch (e) {
      aba?.close()
      setErro(comoErroDaApi(e).mensagem)
    } finally {
      setAbrindo(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className="anexo-pdf"
        aria-busy={abrindo}
        onClick={() => abrir(avisoId)}
      >
        {conteudo}
      </button>
      {erro && (
        <div className="aviso-caixa erro" role="alert">
          <Icone nome="alerta" />
          <p>{erro}</p>
        </div>
      )}
    </>
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
  if (anexos.length === 0) return null
  const fotos = anexos.filter((a) => ehFoto(a.arquivo.tipo))
  const pdfs = anexos.filter((a) => !ehFoto(a.arquivo.tipo))
  return (
    <section className="anexos" aria-label="Anexos">
      {fotos.length > 0 && (
        <div className={`anexos-fotos${fotos.length === 1 ? ' uma' : ''}`}>
          {fotos.map((a) => (
            <Foto key={a.arquivo.id} avisoId={avisoId} anexo={a} unica={fotos.length === 1} />
          ))}
        </div>
      )}
      {pdfs.map((a) => (
        <Pdf key={a.arquivo.id} avisoId={avisoId} arquivo={a.arquivo} />
      ))}
    </section>
  )
}
