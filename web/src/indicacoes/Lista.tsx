// Indicações · a lista (spec, seção 3.1): busca, a lista de escolher "Categoria", os mais recomendados
// primeiro (a ordem vem da API) e o botão "Indicar alguém". O filtro mora no endereço
// (`?categoria=&busca=&com_aviso=1`): voltar do prestador aberto devolve a mesma lista.
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useCarga } from '../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../avisos/componentes'
import { useSessao } from '../casca/contextoSessao'
import { Icone } from '../casca/Icone'
import { Placa } from '../casca/Placa'
import { Tela } from '../casca/Tela'
import { listarCategorias, listarIndicacoes } from './api'
import { CAMINHO_NOVA_INDICACAO, caminhoIndicacao } from './caminhos'
import { Contagens } from './Contagens'
import { comAvisoEmTexto, encontradas } from './formatos'
import type { PrestadorResumo } from './tipos'
import { useAtrasado } from './useAtrasado'
import './indicacoes.css'

const ESPERA_DA_BUSCA_MS = 300
const CONVITE = 'Ainda não tem indicação aqui. Seja o primeiro a indicar alguém.'

function numero(texto: string | null): number | undefined {
  return texto && /^\d{1,15}$/.test(texto) ? Number(texto) : undefined
}

export function ListaIndicacoes() {
  const { eu } = useSessao()
  const [consulta, setConsulta] = useSearchParams()
  const categoria = numero(consulta.get('categoria'))
  const comAviso = !!eu?.gestao && consulta.get('com_aviso') === '1'
  const [digitado, setDigitado] = useState(consulta.get('busca') ?? '')
  const busca = useAtrasado(digitado.trim(), ESPERA_DA_BUSCA_MS)

  // A busca vai para o endereço quando a pessoa para de digitar (sem encher o histórico).
  useEffect(() => {
    setConsulta(
      (antes) => {
        const depois = new URLSearchParams(antes)
        if (busca) depois.set('busca', busca)
        else depois.delete('busca')
        return depois
      },
      { replace: true },
    )
  }, [busca, setConsulta])

  const [categorias] = useCarga(() => listarCategorias(), [])
  const [carga, recarregar] = useCarga(
    () =>
      listarIndicacoes({
        categoria,
        busca: busca || undefined,
        com_aviso: comAviso || undefined,
      }),
    [categoria, busca, comAviso],
  )
  const lista = carga.dados
  const filtrando = categoria !== undefined || !!busca || comAviso
  const campoDaBusca = useRef<HTMLInputElement>(null)

  /** Muda o filtro no endereço; `null` tira a chave. */
  function trocar(mudancas: Partial<Record<'categoria' | 'com_aviso', string | null>>) {
    setConsulta(
      (antes) => {
        const depois = new URLSearchParams(antes)
        for (const [chave, valor] of Object.entries(mudancas)) {
          if (valor === null || valor === undefined) depois.delete(chave)
          else depois.set(chave, valor)
        }
        return depois
      },
      { replace: true },
    )
  }

  function limparBusca() {
    setDigitado('')
    campoDaBusca.current?.focus()
  }

  /** Sem filtro nenhum: a lista inteira. */
  function verTodas() {
    setDigitado('')
    trocar({ categoria: null, com_aviso: null })
    campoDaBusca.current?.focus()
  }

  const indicarAlguem = (
    <Link className="flutuante ind-indicar" to={CAMINHO_NOVA_INDICACAO}>
      <Icone nome="mais" /> Indicar alguém
    </Link>
  )

  return (
    <Tela titulo="Indicações" extra={indicarAlguem}>
      {/* Com o filtro ligado, o botão fica mesmo com zero (a gestão resolveu tudo): é por ele
          que se desliga o filtro. */}
      {(comAviso || !!lista?.com_aviso) && (
        <button
          type="button"
          className="ind-com-aviso"
          aria-pressed={comAviso}
          onClick={() => trocar({ com_aviso: comAviso ? null : '1' })}
        >
          <Icone nome="alerta" /> {comAvisoEmTexto(lista?.com_aviso ?? 0)}
        </button>
      )}
      <div className="ind-busca">
        <label htmlFor="ind-busca" className="com-icone">
          <Icone nome="busca" tamanho={20} /> Procurar: nome ou serviço
        </label>
        <input
          id="ind-busca"
          ref={campoDaBusca}
          type="search"
          value={digitado}
          onChange={(e) => setDigitado(e.target.value)}
          maxLength={80}
          autoComplete="off"
        />
        {/* Anuncia a contagem a cada busca, categoria ou filtro da gestão. */}
        <p className="oculto" aria-live="polite">
          {filtrando && lista && carga.situacao === 'pronta' ? encontradas(lista.itens.length) : ''}
        </p>
      </div>
      {/* A categoria numa lista de escolher nativa (pedido do Erick depois do lançamento): a
          faixa rolava para o lado sem sinal nenhum. "Todos" tira só a categoria; o filtro "com
          aviso" da gestão liga e desliga pelo botão dele, e "Ver todas" tira os dois. */}
      <div className="ind-filtro">
        <label htmlFor="ind-filtro-categoria">Categoria</label>
        <select
          id="ind-filtro-categoria"
          value={categoria === undefined ? '' : String(categoria)}
          onChange={(e) => trocar({ categoria: e.target.value || null })}
        >
          <option value="">Todos</option>
          {categorias.dados?.itens.map((c) => (
            <option key={c.id} value={String(c.id)}>
              {c.nome}
            </option>
          ))}
        </select>
      </div>
      {carga.situacao === 'erro' && !lista ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !lista ? (
        <Carregando />
      ) : lista.itens.length === 0 ? (
        filtrando ? (
          <div className="ind-vazio">
            <p className="vazio">{encontradas(0)}</p>
            <div className="ind-acoes">
              {busca ? (
                <button type="button" className="botao leve" onClick={limparBusca}>
                  Limpar a busca
                </button>
              ) : (
                <button type="button" className="botao leve" onClick={verTodas}>
                  Ver todas
                </button>
              )}
              {categoria !== undefined && (
                <Link className="botao" to={CAMINHO_NOVA_INDICACAO}>
                  <Icone nome="mais" /> Indicar alguém
                </Link>
              )}
            </div>
          </div>
        ) : (
          <div className="ind-vazio">
            <p className="vazio">{CONVITE}</p>
            <Link className="botao" to={CAMINHO_NOVA_INDICACAO}>
              <Icone nome="mais" /> Indicar alguém
            </Link>
          </div>
        )
      ) : (
        <div className="folha">
          {/* h2: o h1 é o título da tela (como no mural). */}
          {lista.itens.map((p) => (
            <Cartao key={p.id} prestador={p} />
          ))}
        </div>
      )}
    </Tela>
  )
}

function Cartao({ prestador }: { prestador: PrestadorResumo }) {
  const avisos = prestador.avisos_abertos ?? 0
  return (
    <Link className="item ind-cartao" to={caminhoIndicacao(prestador.id)}>
      <span className="ind-categoria">{prestador.categoria.nome}</span>
      <h2>{prestador.nome}</h2>
      <span className="seta">
        <Icone nome="seta" />
      </span>
      <span className="linha-meta">
        <Contagens recomendam={prestador.recomendam} naoRecomendam={prestador.nao_recomendam} />
        {avisos > 0 && (
          <span className="selo ind-selo-aviso">
            {avisos === 1 ? '1 aviso da vizinhança' : `${avisos} avisos da vizinhança`}
          </span>
        )}
      </span>
      {prestador.trecho && (
        <span className="ind-trecho">
          <Placa unidade={prestador.trecho.unidade} />
          <span className="ind-trecho-texto">
            <span aria-hidden="true">{prestador.trecho.recomenda ? '👍 ' : '👎 '}</span>
            <span className="oculto">
              {prestador.trecho.recomenda ? 'Recomenda: ' : 'Não recomenda: '}
            </span>
            “{prestador.trecho.comentario}”
          </span>
        </span>
      )}
    </Link>
  )
}
