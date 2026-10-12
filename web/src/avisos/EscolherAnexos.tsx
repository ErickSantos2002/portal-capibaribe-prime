// M3 · Épico B: o campo "Fotos ou PDF, se tiver" do formulário do aviso (spec `m3-anexos.md`,
// seção 3.2). O arquivo é enviado assim que é escolhido; "Tirar" só tira da lista.
import { useState } from 'react'
import { ACEITAR } from '../arquivos/limites'
import { Icone } from '../casca/Icone'
import { descricaoDoAnexo, ehFoto, MAXIMO_DE_ANEXOS, type ItemAnexo } from './anexos'
import { MiniaturaRemota } from './AnexosDoAviso'
import { IconeAnexo } from './IconesAnexo'
import type { ListaDeAnexos } from './useAnexos'
import './anexos.css'

interface Props {
  anexos: ListaDeAnexos
  /** Na correção: as fotos que já estão no aviso aparecem pela miniatura do link. */
  avisoId?: number
  /** A mensagem embaixo do campo (anexo enviando ou com erro ao publicar, ou a da API). */
  erro?: string
  /** Mexeu na lista (a prévia volta a "Ver prévia"; o erro do campo some). */
  aoMudar?: () => void
}

function Miniatura({ item, avisoId }: { item: ItemAnexo; avisoId?: number }) {
  if (item.previa) return <img src={item.previa} alt="" />
  if (ehFoto(item.tipo) && avisoId !== undefined && item.arquivo && item.jaPublicado) {
    return <MiniaturaRemota avisoId={avisoId} arquivo={item.arquivo} />
  }
  return ehFoto(item.tipo) ? (
    <IconeAnexo nome="foto" tamanho={28} />
  ) : (
    <Icone nome="documentos" tamanho={28} />
  )
}

/** "Enviando 2 de 3…", quando há mais de um na vez; com um só, o próprio item diz. */
function andamento(itens: readonly ItemAnexo[]): string {
  const desta = itens.filter((i) => !i.jaPublicado)
  const enviando = desta.filter((i) => i.situacao === 'enviando').length
  if (enviando === 0 || desta.length < 2) return ''
  return `Enviando ${desta.length - enviando + 1} de ${desta.length}…`
}

export function EscolherAnexos({ anexos, avisoId, erro, aoMudar }: Props) {
  const [deFora, setDeFora] = useState<string[]>([])
  const { itens } = anexos
  const cheio = itens.length >= MAXIMO_DE_ANEXOS
  const descrito = ['anexos-ajuda', erro ? 'anexos-erro' : ''].filter(Boolean).join(' ')

  return (
    <div
      className="anexos-campo"
      role="group"
      aria-labelledby="anexos-rotulo"
      aria-describedby={descrito}
    >
      <p className="avisos-rotulo" id="anexos-rotulo">
        Fotos ou PDF, se tiver
      </p>
      <p className="ajuda" id="anexos-ajuda">
        Até 5 arquivos, de até 10 MB cada. Fotos grandes são reduzidas antes de enviar.
      </p>
      {itens.length > 0 && (
        <ul className="anexos-lista" role="list">
          {itens.map((item) => (
            <li key={item.chave} className={`anexo-item ${item.situacao}`}>
              <span className="anexo-miniatura">
                <Miniatura item={item} avisoId={avisoId} />
              </span>
              <span className="anexo-info">
                <span className="anexo-nome">{item.nome}</span>
                {item.situacao === 'enviando' && (
                  <>
                    <span className="anexo-detalhe">Enviando…</span>
                    <span className="anexo-barra" aria-hidden="true" />
                  </>
                )}
                {item.situacao === 'pronto' && item.arquivo && (
                  <span className="anexo-detalhe">
                    <Icone nome="certo" tamanho={18} /> {descricaoDoAnexo(item.arquivo)}
                  </span>
                )}
                {item.situacao === 'erro' && <span className="anexo-erro">{item.erro}</span>}
              </span>
              <span className="anexo-acoes">
                {item.situacao === 'erro' && (
                  <button
                    type="button"
                    className="botao leve"
                    aria-label={`Enviar de novo ${item.nome}`}
                    onClick={() => {
                      anexos.tentarDeNovo(item.chave)
                      aoMudar?.()
                    }}
                  >
                    Enviar de novo
                  </button>
                )}
                <button
                  type="button"
                  className="botao leve"
                  aria-label={`Tirar ${item.nome}`}
                  onClick={() => {
                    anexos.tirar(item.chave)
                    setDeFora([])
                    aoMudar?.()
                  }}
                >
                  <IconeAnexo nome="fechar" tamanho={20} /> Tirar
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="anexos-andamento" aria-live="polite">
        {andamento(itens)}
      </p>
      {deFora.length > 0 && (
        <div className="aviso-caixa atencao" role="status">
          <Icone nome="alerta" />
          <p>Até 5 anexos por aviso. Ficaram de fora: {deFora.join(', ')}.</p>
        </div>
      )}
      {cheio ? (
        <p className="ajuda">Já são 5 anexos, o máximo.</p>
      ) : (
        <div className="anexos-escolher">
          <input
            id="anexos-arquivo"
            className="anexos-input"
            type="file"
            multiple
            accept={ACEITAR}
            onChange={(e) => {
              const escolhidos = Array.from(e.target.files ?? [])
              // Limpa: escolher o mesmo arquivo de novo também conta como mudança.
              e.target.value = ''
              if (escolhidos.length === 0) return
              setDeFora(anexos.adicionar(escolhidos))
              aoMudar?.()
            }}
          />
          <label htmlFor="anexos-arquivo" className="botao leve">
            <IconeAnexo nome="clipe" /> Anexar foto ou PDF
          </label>
        </div>
      )}
      {erro && (
        <p className="avisos-erro-campo" id="anexos-erro">
          {erro}
        </p>
      )}
    </div>
  )
}
