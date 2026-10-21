// Classificados · o cartão da lista e de "Meus anúncios" (spec, seção 3.1): a capa (ou um marcador
// sem foto), o selo do tipo, o título, a categoria, a placa, há quanto tempo e a situação.
import { Link } from 'react-router'
import { formatarData } from '../casca/formatar'
import { Icone } from '../casca/Icone'
import { Placa } from '../casca/Placa'
import { caminhoAnuncio } from './caminhos'
import { haQuanto, seloDaSituacao, seloDoTipo } from './formatos'
import type { AnuncioResumo } from './tipos'

export function Cartao({ anuncio, mostrarPlaca = true }: { anuncio: AnuncioResumo; mostrarPlaca?: boolean }) {
  const situacao = seloDaSituacao(anuncio.situacao, anuncio.vencido, anuncio.escondido)
  const avisos = anuncio.avisos_abertos ?? 0
  return (
    <Link className="item cla-cartao" to={caminhoAnuncio(anuncio.id)}>
      <span className="cla-capa" aria-hidden="true">
        {anuncio.capa ? (
          <img src={anuncio.capa} alt="" loading="lazy" decoding="async" />
        ) : (
          <Icone nome="classificados" tamanho={32} />
        )}
      </span>
      <span className="cla-cartao-texto">
        <span className={`cla-tipo cla-tipo-${anuncio.tipo}`}>
          {seloDoTipo(anuncio.tipo, anuncio.preco_centavos)}
        </span>
        <h2>{anuncio.titulo}</h2>
        <span className="cla-categoria">{anuncio.categoria.nome}</span>
        <span className="linha-meta cla-meta">
          {mostrarPlaca && <Placa unidade={anuncio.unidade} />}
          {/* Em "Meus anúncios", o aberto diz até quando fica na lista (revisão UX 12). */}
          <span className="cla-quando">
            {!mostrarPlaca && !situacao
              ? `Fica na lista até ${formatarData(anuncio.vence_em)}`
              : haQuanto(anuncio.em)}
          </span>
          {situacao && <span className={`selo cla-situacao cla-${anuncio.situacao}`}>{situacao}</span>}
          {avisos > 0 && (
            <span className="selo ind-selo-aviso">
              {avisos === 1 ? '1 aviso da vizinhança' : `${avisos} avisos da vizinhança`}
            </span>
          )}
        </span>
      </span>
      <span className="seta">
        <Icone nome="seta" />
      </span>
    </Link>
  )
}
