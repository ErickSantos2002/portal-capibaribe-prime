// Épico C · Avisos: peças comuns às telas de avisos. Pertence ao épico C.
import { Fragment, type ReactNode } from 'react'
import { Link } from 'react-router'
import { formatarData } from '../casca/formatar'
import { Icone } from '../casca/Icone'
import { infoDaCategoria } from './categorias'
import { dataEmBloco, eventoCurto, eventoPorExtenso, jaAconteceu } from './datas'
import { analisar, trechos, type Bloco } from './formatacao'
import { assinatura, blocosEmTexto, destinoEmTexto } from './formatos'
import type { AvisoResumo, Categoria, Evento } from './tipos'

/** Uma linha do aviso: texto, negrito e links http(s), tudo como elementos do React. */
function Linha({ linha }: { linha: string }) {
  return (
    <>
      {trechos(linha).map((trecho, i) => {
        const conteudo = trecho.link ? (
          <a href={trecho.link} target="_blank" rel="noopener noreferrer">
            {trecho.texto}
          </a>
        ) : (
          trecho.texto
        )
        return trecho.negrito ? (
          <strong key={i}>{conteudo}</strong>
        ) : (
          <Fragment key={i}>{conteudo}</Fragment>
        )
      })}
    </>
  )
}

/** Linhas do mesmo parágrafo ou destaque: a quebra simples continua quebra. */
function Linhas({ linhas }: { linhas: string[] }) {
  return linhas.map((linha, i) => (
    <Fragment key={i}>
      {i > 0 && <br />}
      <Linha linha={linha} />
    </Fragment>
  ))
}

function DesenharBloco({ bloco, nivel }: { bloco: Bloco; nivel: 2 | 3 }) {
  switch (bloco.tipo) {
    case 'titulo': {
      const Titulo = nivel === 2 ? 'h2' : 'h3'
      return (
        <Titulo className="aviso-secao">
          <Linha linha={bloco.texto} />
        </Titulo>
      )
    }
    case 'lista':
      return (
        <ul className="aviso-lista">
          {bloco.itens.map((item, i) => (
            <li key={i}>
              <Linha linha={item} />
            </li>
          ))}
        </ul>
      )
    case 'numerada':
      return (
        <ol className="aviso-lista" start={bloco.inicio === 1 ? undefined : bloco.inicio}>
          {bloco.itens.map((item, i) => (
            <li key={i}>
              <Linha linha={item} />
            </li>
          ))}
        </ol>
      )
    case 'destaque':
      return (
        <div className="aviso-destaque">
          <Icone nome="info" />
          <p>
            <Linhas linhas={bloco.linhas} />
          </p>
        </div>
      )
    default:
      return (
        <p>
          <Linhas linhas={bloco.linhas} />
        </p>
      )
  }
}

/**
 * O texto do aviso com o Markdown restrito (spec dos avisos com formatação, seção 3.1): os
 * blocos de `analisar` viram elementos do React, e todo texto entra como texto (nada é
 * interpretado como HTML, nada de `dangerouslySetInnerHTML`). `nivel`: o nível do título de
 * seção (`## `): 2 no aviso aberto (o h1 é o título do aviso), 3 onde o título do aviso é h2
 * (versão antiga, prévia).
 */
export function TextoDoAviso({ texto, nivel = 2 }: { texto: string; nivel?: 2 | 3 }) {
  return (
    <div className="texto-aviso">
      {analisar(texto).map((bloco, i) => (
        <DesenharBloco key={i} bloco={bloco} nivel={nivel} />
      ))}
    </div>
  )
}

/** "ÍCONE OBRA": a categoria sempre com ícone e nome, nunca só pela cor. */
export function RotuloCategoria({ categoria }: { categoria: Categoria }) {
  const info = infoDaCategoria(categoria)
  return (
    <span className="rotulo-cat">
      <Icone nome={info.icone} tamanho={18} />
      {info.nome}
    </span>
  )
}

/** Data da publicação em bloco (dia grande, mês embaixo). O leitor de tela lê por extenso. */
export function DataEmBloco({ iso, lida = true }: { iso: string; lida?: boolean }) {
  const { dia, mes } = dataEmBloco(iso)
  return (
    <>
      <span className="data-bloco" aria-hidden="true">
        <span className="dia">{dia}</span>
        <span className="mes">{mes}</span>
      </span>
      {/* `lida = false`: a data já está escrita ao lado (aviso aberto). */}
      {lida && <span className="oculto">{formatarData(iso)}</span>}
    </>
  )
}

/** O quadro "Quando / Onde" do aviso que é um evento. */
export function QuadroEvento({ evento }: { evento: Evento }) {
  return (
    <dl className="aviso-evento">
      <div>
        <Icone nome="calendario" />
        <dt>Quando</dt>
        <dd>
          {eventoPorExtenso(evento.quando)}
          {jaAconteceu(evento.quando) && <span className="ja-aconteceu"> · Já aconteceu</span>}
        </dd>
      </div>
      {evento.onde && (
        <div>
          <Icone nome="local" />
          <dt>Onde</dt>
          <dd>{evento.onde}</dd>
        </div>
      )}
    </dl>
  )
}

/** Ainda não lido ("Novo") ou corrigido depois da leitura ("Corrigido", revisão do M1, U1). */
function chamaAtencao(aviso: AvisoResumo, arquivados?: boolean): 'novo' | 'corrigido' | null {
  if (arquivados) return null
  if (!aviso.lido) return 'novo'
  return aviso.corrigido_desde_a_leitura ? 'corrigido' : null
}

interface PropsMeta {
  aviso: AvisoResumo
  arquivados?: boolean
  /** No cartão a data está no bloco; no fixado, na linha. */
  comData?: boolean
}

function Meta({ aviso, arquivados, comData }: PropsMeta) {
  const selo = chamaAtencao(aviso, arquivados)
  return (
    <span className="linha-meta">
      {selo === 'novo' && <span className="selo novo">Novo</span>}
      {selo === 'corrigido' && <span className="selo novo">Corrigido</span>}
      {comData && <span>{formatarData(aviso.publicado_em)}</span>}
      {!aviso.para_todos && <span>{blocosEmTexto(aviso.blocos)}</span>}
      {aviso.editado_em && <span>corrigido em {formatarData(aviso.editado_em)}</span>}
      {arquivados && aviso.arquivado_em && (
        <span>arquivado em {formatarData(aviso.arquivado_em)}</span>
      )}
    </span>
  )
}

/** "Sáb, 11/10 · 9h" (ou "Já aconteceu") no cartão do mural. */
function LinhaEvento({ quando }: { quando: string }) {
  return (
    <span className="linha-evento">
      <Icone nome="calendario" tamanho={18} />
      {eventoCurto(quando)}
    </span>
  )
}

interface PropsItem {
  aviso: AvisoResumo
  arquivados?: boolean
  /** Na prévia de H-12, o item não é link (o aviso ainda não existe). */
  previa?: boolean
}

/** Um cartão do mural (modelo A): faixa e data na cor da categoria, rótulo, título e resumo. */
export function ItemAviso({ aviso, arquivados, previa }: PropsItem) {
  const classe = `cartao-aviso cat-${aviso.categoria}${chamaAtencao(aviso, arquivados) ? ' novo' : ''}`
  const conteudo = (
    <>
      <DataEmBloco iso={aviso.publicado_em} />
      <span className="cartao-corpo">
        <RotuloCategoria categoria={aviso.categoria} />
        {/* h2: no mural, o h1 é o título da tela (U9, heading-order). */}
        <h2>{aviso.titulo}</h2>
        {aviso.resumo && <span className="cartao-resumo">{aviso.resumo}</span>}
        {aviso.evento_quando && <LinhaEvento quando={aviso.evento_quando} />}
        <Meta aviso={aviso} arquivados={arquivados} />
      </span>
      {!previa && (
        <span className="seta">
          <Icone nome="seta" />
        </span>
      )}
    </>
  )
  if (previa) return <div className={classe}>{conteudo}</div>
  return (
    <Link className={classe} to={`/avisos/${aviso.id}`}>
      {conteudo}
    </Link>
  )
}

/** Aviso fixado: o único bloco do mural com fundo ipê (protótipo), agora com a categoria. */
export function AvisoFixado({ aviso, previa }: { aviso: AvisoResumo; previa?: boolean }) {
  const conteudo = (
    <>
      <span className="rotulo">
        <Icone nome="pino" tamanho={20} /> Fixado {assinatura(aviso.publicado_por)}
        {!aviso.para_todos && `, para ${destinoEmTexto(aviso)}`}
      </span>
      <RotuloCategoria categoria={aviso.categoria} />
      <h2>{aviso.titulo}</h2>
      <p>{aviso.resumo}</p>
      {aviso.evento_quando && <LinhaEvento quando={aviso.evento_quando} />}
      {/* U1: a mesma linha de detalhes dos outros itens (data, correção, selo). */}
      <Meta aviso={{ ...aviso, para_todos: true }} comData />
    </>
  )
  if (previa) return <div className={`fixado cat-${aviso.categoria}`}>{conteudo}</div>
  return (
    <Link className={`fixado cat-${aviso.categoria}`} to={`/avisos/${aviso.id}`}>
      {conteudo}
    </Link>
  )
}

interface PropsCorpo {
  aviso: Pick<
    AvisoResumo,
    'categoria' | 'publicado_em' | 'publicado_por' | 'para_todos' | 'blocos' | 'fixado'
  >
  evento: Evento | null
  texto: string
  /** O que vai entre o cabeçalho (com o quadro do evento) e o texto: arquivado, corrigido. */
  avisos?: ReactNode
  nivel?: 2 | 3
}

/**
 * O aviso aberto (e a prévia do formulário): cabeçalho com a data em bloco, a categoria e quem
 * publicou para quem; o quadro "Quando / Onde" se for evento; depois o texto formatado.
 */
export function CorpoDoAviso({ aviso, evento, texto, avisos, nivel = 2 }: PropsCorpo) {
  return (
    <>
      <header className="aviso-cabecalho">
        <DataEmBloco iso={aviso.publicado_em} lida={false} />
        <div>
          <RotuloCategoria categoria={aviso.categoria} />
          <p className="suave">
            {aviso.fixado && 'Fixado. '}Publicado {assinatura(aviso.publicado_por)} em{' '}
            {formatarData(aviso.publicado_em)}, para {destinoEmTexto(aviso)}.
          </p>
        </div>
      </header>
      {evento && <QuadroEvento evento={evento} />}
      {avisos}
      <TextoDoAviso texto={texto} nivel={nivel} />
    </>
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
    // `aria-live`, não `role="status"`: a região de status da tela é a do recado (casca).
    <p className="vazio" aria-live="polite">
      Carregando…
    </p>
  )
}
