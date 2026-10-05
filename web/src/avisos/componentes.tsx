// Épico C · Avisos: peças comuns às telas de avisos. Pertence ao épico C.
import { Link } from 'react-router'
import { formatarData } from '../casca/formatar'
import { Icone } from '../casca/Icone'
import { assinatura, blocosEmTexto, destinoEmTexto, paragrafos, partesDaLinha } from './formatos'
import type { AvisoResumo } from './tipos'

/**
 * O texto do aviso é texto puro (contrato, seção 4.4): cada parágrafo vira um `<p>` com a
 * quebra simples preservada pelo CSS (`white-space: pre-line`) e só endereços http(s) viram
 * link. Tudo passa pelo React como texto: nada é interpretado como HTML.
 */
export function TextoDoAviso({ texto }: { texto: string }) {
  return (
    <div className="texto-aviso">
      {paragrafos(texto).map((paragrafo, i) => (
        <p key={i}>
          {partesDaLinha(paragrafo).map((parte, j) =>
            parte.link ? (
              <a key={j} href={parte.link} target="_blank" rel="noopener noreferrer">
                {parte.texto}
              </a>
            ) : (
              parte.texto
            ),
          )}
        </p>
      ))}
    </div>
  )
}

function Meta({ aviso, arquivados }: { aviso: AvisoResumo; arquivados?: boolean }) {
  const novo = !aviso.lido && !arquivados
  return (
    <span className="linha-meta">
      {novo && <span className="selo novo">Novo</span>}
      <span>{formatarData(aviso.publicado_em)}</span>
      {!aviso.para_todos && <span>{blocosEmTexto(aviso.blocos)}</span>}
      {aviso.editado_em && <span>corrigido</span>}
      {arquivados && aviso.arquivado_em && (
        <span>arquivado em {formatarData(aviso.arquivado_em)}</span>
      )}
    </span>
  )
}

interface PropsItem {
  aviso: AvisoResumo
  arquivados?: boolean
  /** Na prévia de H-12, o item não é link (o aviso ainda não existe). */
  previa?: boolean
}

/** Uma linha do mural: título (negrito se ainda não lido) e detalhes. */
export function ItemAviso({ aviso, arquivados, previa }: PropsItem) {
  const classe = `item${!aviso.lido && !arquivados ? ' novo' : ''}`
  const conteudo = (
    <>
      <h3>{aviso.titulo}</h3>
      {!previa && (
        <span className="seta">
          <Icone nome="seta" />
        </span>
      )}
      <Meta aviso={aviso} arquivados={arquivados} />
    </>
  )
  if (previa) return <div className={classe}>{conteudo}</div>
  return (
    <Link className={classe} to={`/avisos/${aviso.id}`}>
      {conteudo}
    </Link>
  )
}

/** Aviso fixado: o único bloco do mural com cor de fundo (protótipo). */
export function AvisoFixado({ aviso, previa }: { aviso: AvisoResumo; previa?: boolean }) {
  const conteudo = (
    <>
      <span className="rotulo">
        <Icone nome="pino" tamanho={20} /> Fixado {assinatura(aviso.publicado_por)}
        {!aviso.para_todos && `, para ${destinoEmTexto(aviso)}`}
        {!aviso.lido && <span className="selo novo">Novo</span>}
      </span>
      <h3>{aviso.titulo}</h3>
      <p>{aviso.resumo}</p>
    </>
  )
  if (previa) return <div className="fixado">{conteudo}</div>
  return (
    <Link className="fixado" to={`/avisos/${aviso.id}`}>
      {conteudo}
    </Link>
  )
}

/** Erro ao carregar, com "Tentar de novo". */
export function FalhaAoCarregar({ mensagem, tentar }: { mensagem: string; tentar: () => void }) {
  return (
    <>
      <div className="aviso-caixa erro" role="alert">
        <Icone nome="alerta" />
        <p>{mensagem}</p>
      </div>
      <button type="button" className="botao leve" onClick={tentar}>
        Tentar de novo
      </button>
    </>
  )
}

export function Carregando() {
  return (
    <p className="vazio" role="status">
      Carregando…
    </p>
  )
}
