// Classificados · a lista (spec, seção 3.1): "Meus anúncios" no topo (quando a unidade tem algum),
// a busca, o filtro de tipo, a faixa de categorias (a mesma das indicações, que rola dentro dela),
// os cartões (o mais recente primeiro, a ordem vem da API) e o botão "Anunciar". O filtro mora no
// endereço (`?tipo=&categoria=&busca=&com_aviso=1`): voltar do anúncio devolve a mesma lista.
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useCarga } from '../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../avisos/componentes'
import { useSessao } from '../casca/contextoSessao'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { useAtrasado } from '../indicacoes/useAtrasado'
import { listarCategorias, listarClassificados } from './api'
import { CAMINHO_MEUS_ANUNCIOS, CAMINHO_NOVO_ANUNCIO } from './caminhos'
import { Cartao } from './Cartao'
import { comAvisoEmTexto, encontrados } from './formatos'
import type { TipoAnuncio } from './tipos'
import '../indicacoes/indicacoes.css'
import './classificados.css'

const ESPERA_DA_BUSCA_MS = 300
const CONVITE = 'Ainda não tem anúncio aqui. Que tal anunciar o que sobrou da obra?'
const TIPOS: { valor: TipoAnuncio | null; texto: string }[] = [
  { valor: null, texto: 'Tudo' },
  { valor: 'venda', texto: 'Vende' },
  { valor: 'troca', texto: 'Troca' },
  { valor: 'doacao', texto: 'Doa' },
]

function numero(texto: string | null): number | undefined {
  return texto && /^\d{1,15}$/.test(texto) ? Number(texto) : undefined
}

function tipoDaConsulta(texto: string | null): TipoAnuncio | undefined {
  return texto === 'venda' || texto === 'troca' || texto === 'doacao' ? texto : undefined
}

export function ListaClassificados() {
  const { eu } = useSessao()
  const [consulta, setConsulta] = useSearchParams()
  const tipo = tipoDaConsulta(consulta.get('tipo'))
  const categoria = numero(consulta.get('categoria'))
  const comAviso = !!eu?.gestao && consulta.get('com_aviso') === '1'
  const [digitado, setDigitado] = useState(consulta.get('busca') ?? '')
  const busca = useAtrasado(digitado.trim(), ESPERA_DA_BUSCA_MS)

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
      listarClassificados({
        tipo,
        categoria,
        busca: busca || undefined,
        com_aviso: comAviso || undefined,
      }),
    [tipo, categoria, busca, comAviso],
  )
  const lista = carga.dados
  const filtrando = tipo !== undefined || categoria !== undefined || !!busca || comAviso
  const campoDaBusca = useRef<HTMLInputElement>(null)

  function trocar(mudancas: Partial<Record<'tipo' | 'categoria' | 'com_aviso', string | null>>) {
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

  function verTodos() {
    setDigitado('')
    trocar({ tipo: null, categoria: null, com_aviso: null })
    campoDaBusca.current?.focus()
  }

  const anunciar = (
    <Link className="flutuante cla-anunciar" to={CAMINHO_NOVO_ANUNCIO}>
      <Icone nome="mais" /> Anunciar
    </Link>
  )

  return (
    <Tela titulo="Classificados" extra={anunciar}>
      {!!lista?.meus && (
        <Link className="cla-meus" to={CAMINHO_MEUS_ANUNCIOS}>
          <Icone nome="classificados" /> Meus anúncios ({lista.meus})
          <span className="seta">
            <Icone nome="seta" />
          </span>
        </Link>
      )}
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
        <label htmlFor="cla-busca" className="com-icone">
          <Icone nome="busca" tamanho={20} /> Procurar: o que você quer?
        </label>
        <input
          id="cla-busca"
          ref={campoDaBusca}
          type="search"
          value={digitado}
          onChange={(e) => setDigitado(e.target.value)}
          maxLength={80}
          autoComplete="off"
        />
        <p className="oculto" aria-live="polite">
          {filtrando && lista && carga.situacao === 'pronta' ? encontrados(lista.itens.length) : ''}
        </p>
      </div>
      {/* A mesma faixa das categorias: rola dentro dela, também com a letra grande. */}
      <div className="faixa-categorias cla-tipos" role="group" aria-label="O que você procura">
        {TIPOS.map((t) => (
          <button
            key={t.texto}
            type="button"
            className="chip"
            aria-pressed={(tipo ?? null) === t.valor}
            onClick={() => trocar({ tipo: t.valor })}
          >
            {t.texto}
          </button>
        ))}
      </div>
      {categorias.dados && (
        <nav className="faixa-categorias" aria-label="Categorias">
          <button
            type="button"
            className="chip"
            aria-pressed={categoria === undefined}
            onClick={() => trocar({ categoria: null })}
          >
            Todas
          </button>
          {categorias.dados.itens.map((c) => (
            <button
              key={c.id}
              type="button"
              className="chip"
              aria-pressed={categoria === c.id}
              onClick={() => trocar({ categoria: String(c.id) })}
            >
              {c.nome}
            </button>
          ))}
        </nav>
      )}
      {carga.situacao === 'erro' && !lista ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !lista ? (
        <Carregando />
      ) : lista.itens.length === 0 ? (
        filtrando ? (
          <div className="ind-vazio">
            <p className="vazio">{encontrados(0)}</p>
            <div className="ind-acoes">
              {busca ? (
                <button type="button" className="botao leve" onClick={limparBusca}>
                  Limpar a busca
                </button>
              ) : (
                <button type="button" className="botao leve" onClick={verTodos}>
                  Ver todos
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="ind-vazio">
            <p className="vazio">{CONVITE}</p>
            <Link className="botao" to={CAMINHO_NOVO_ANUNCIO}>
              <Icone nome="mais" /> Anunciar
            </Link>
          </div>
        )
      ) : (
        <div className="folha cla-lista">
          {lista.itens.map((a) => (
            <Cartao key={a.id} anuncio={a} />
          ))}
        </div>
      )}
    </Tela>
  )
}
