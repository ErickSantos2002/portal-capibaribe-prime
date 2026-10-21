// M3 · Épico B: os anexos no aviso aberto, na versão antiga e na prévia (spec `m3-anexos.md`,
// seção 3.3). Foto na própria tela (toque abre grande, com anterior e próxima); PDF como link que
// abre numa aba nova (a CSP não deixa embutir PDF). Os dois passam pela rota `…/abrir` do Portal,
// que confere a sessão e redireciona para um link novo (revisão U12).
import { useCallback, useEffect, useRef, useState } from 'react'

import type { ArquivoEnviado } from '../arquivos/tipos'
import { Icone } from '../casca/Icone'
import { descricaoDoAnexo, ehFoto } from './anexos'
import { enderecoDoAnexo } from './api'
import { IconeAnexo } from './IconesAnexo'
import { VisorDeFotos } from './VisorDeFotos'
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
  // Um link de verdade (U12): o Safari do iPhone não bloqueia a aba, e cada toque (mesmo com a
  // página aberta há horas) pede um link novo.
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
        <VisorDeFotos
          fotos={fotos.map((a) => enderecoDaFoto(avisoId, a))}
          inicio={aberta}
          fechar={fechar}
        />
      )}
    </section>
  )
}
