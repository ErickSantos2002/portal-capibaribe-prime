// Classificados · as fotos do formulário (spec, seção 3.3): até 4, enviadas assim que escolhidas
// (o envio do M3, com a compressão que tira o GPS), cada uma com "Tirar". A primeira é a capa;
// reordenar não precisa: tirar e pôr de novo resolve.
import { useEffect, useRef } from 'react'
import { comoErroDaApi } from '../avisos/carregar'
import { Icone } from '../casca/Icone'
import { ACEITAR_FOTOS, FOTOS_POR_ANUNCIO, enviarFoto } from './fotos'

export interface FotoNoFormulario {
  /** Só da tela (a mesma foto pode ser escolhida duas vezes). */
  chave: string
  /** A id da foto já enviada e conferida (ou a que já estava no anúncio). */
  id?: number
  /** Para a miniatura: o link da foto do anúncio, ou a da própria escolha (blob). */
  url: string
  situacao: 'enviando' | 'pronta' | 'erro'
  erro?: string
  /** A miniatura foi criada aqui (blob:) e tem de ser liberada. */
  local?: boolean
}

interface Props {
  fotos: FotoNoFormulario[]
  mudar: (atualizar: (antes: FotoNoFormulario[]) => FotoNoFormulario[]) => void
  erro?: string
}

let contador = 0

export function EscolherFotos({ fotos, mudar, erro }: Props) {
  const campo = useRef<HTMLInputElement>(null)
  const sobram = FOTOS_POR_ANUNCIO - fotos.length
  // As miniaturas locais são liberadas quando saem da tela.
  const locais = useRef(new Set<string>())
  useEffect(() => {
    const atuais = new Set(fotos.filter((f) => f.local).map((f) => f.url))
    for (const url of locais.current) {
      if (!atuais.has(url)) URL.revokeObjectURL(url)
    }
    locais.current = atuais
  }, [fotos])
  useEffect(
    () => () => {
      for (const url of locais.current) URL.revokeObjectURL(url)
    },
    [],
  )

  async function mandar(chave: string, arquivo: File) {
    try {
      const id = await enviarFoto(arquivo)
      mudar((antes) => antes.map((f) => (f.chave === chave ? { ...f, id, situacao: 'pronta' } : f)))
    } catch (e) {
      const mensagem = comoErroDaApi(e).mensagem
      mudar((antes) =>
        antes.map((f) => (f.chave === chave ? { ...f, situacao: 'erro', erro: mensagem } : f)),
      )
    }
  }

  function escolher(lista: FileList | null) {
    if (!lista) return
    const novas = Array.from(lista).slice(0, Math.max(0, sobram))
    const itens: FotoNoFormulario[] = novas.map((arquivo) => ({
      chave: `foto-${++contador}`,
      url: URL.createObjectURL(arquivo),
      situacao: 'enviando',
      local: true,
    }))
    mudar((antes) => [...antes, ...itens].slice(0, FOTOS_POR_ANUNCIO))
    itens.forEach((item, i) => void mandar(item.chave, novas[i]))
    if (campo.current) campo.current.value = ''
  }

  return (
    <fieldset className="cla-escolher-fotos" aria-describedby="cla-fotos-ajuda">
      <legend>Fotos (até 4, opcional)</legend>
      <p className="ajuda" id="cla-fotos-ajuda">
        A primeira é a capa. Evite fotos com pessoas ou documentos.
      </p>
      {fotos.length > 0 && (
        <ul className="cla-fotos-escolhidas">
          {fotos.map((f, i) => (
            <li key={f.chave} className={f.situacao === 'erro' ? 'com-erro' : undefined}>
              <img src={f.url} alt={`Foto ${i + 1}${i === 0 ? ' (capa)' : ''}`} />
              <p className="cla-foto-estado" aria-live="polite">
                {f.situacao === 'enviando'
                  ? 'Enviando…'
                  : f.situacao === 'erro'
                    ? f.erro
                    : i === 0
                      ? 'Capa'
                      : `Foto ${i + 1}`}
              </p>
              <button
                type="button"
                className="botao leve"
                onClick={() => mudar((antes) => antes.filter((x) => x.chave !== f.chave))}
              >
                Tirar<span className="oculto"> a foto {i + 1}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {erro && (
        <p className="ind-erro-campo" role="alert">
          {erro}
        </p>
      )}
      {sobram > 0 && (
        <div className="cla-escolher">
          {/* O campo fica invisível, mas focável: quem vê é o rótulo-botão (como nos anexos). */}
          <input
            id="cla-fotos"
            ref={campo}
            className="cla-input-foto"
            type="file"
            accept={ACEITAR_FOTOS}
            multiple
            onChange={(e) => escolher(e.target.files)}
          />
          <label htmlFor="cla-fotos" className="botao leve">
            <Icone nome="mais" /> {fotos.length === 0 ? 'Escolher fotos' : 'Pôr mais uma foto'}
          </label>
        </div>
      )}
    </fieldset>
  )
}
