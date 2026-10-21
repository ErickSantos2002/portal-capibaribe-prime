// Classificados · a lista (spec, seção 3.1): "Meus anúncios" no topo (quando a unidade tem algum),
// a busca, as listas de escolher "Tipo" e "Categoria" (o mesmo filtro das indicações),
// os cartões (o mais recente primeiro, a ordem vem da API) e o botão "Anunciar". O filtro mora no
// endereço (`?tipo=&categoria=&busca=&com_aviso=1`): voltar do anúncio devolve a mesma lista.
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useCarga } from '../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../avisos/componentes'
import { useSessao } from '../casca/contextoSessao'
import { useLetraGrande } from '../casca/letra'
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
  { valor: 'procura', texto: 'Procura' },
]

function numero(texto: string | null): number | undefined {
  return texto && /^\d{1,15}$/.test(texto) ? Number(texto) : undefined
}

function tipoDaConsulta(texto: string | null): TipoAnuncio | undefined {
  return texto === 'venda' || texto === 'troca' || texto === 'doacao' || texto === 'procura'
    ? texto
    : undefined
}

export function ListaClassificados() {
  const { eu } = useSessao()
  const grande = useLetraGrande()
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

  // Com a letra grande, o botão flutuante cobria a busca: ele entra no começo da lista, no fluxo
  // da página (revisão UX 10). Com a letra de fábrica, o de sempre, fixo embaixo.
  const anunciar = grande ? null : (
    <Link className="flutuante cla-anunciar" to={CAMINHO_NOVO_ANUNCIO}>
      <Icone nome="mais" /> Anunciar
    </Link>
  )
  const abertos = lista?.meus_abertos ?? 0

  return (
    <Tela titulo="Classificados" extra={anunciar}>
      {grande && (
        <Link className="botao cla-anunciar cla-anunciar-no-fluxo" to={CAMINHO_NOVO_ANUNCIO}>
          <Icone nome="mais" /> Anunciar
        </Link>
      )}
      {!!lista?.meus && (
        <Link className="cla-meus" to={CAMINHO_MEUS_ANUNCIOS}>
          {/* O número é só dos abertos (revisão UX 12); o link aparece também com só vencidos ou
              encerrados, que dá para renovar ou rever. */}
          <Icone nome="classificados" /> Meus anúncios{abertos > 0 ? ` (${abertos})` : ''}
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
      {/* Tipo e categoria em listas de escolher nativas, uma embaixo da outra (pedido do Erick
          depois do lançamento): os chips de tipo quebravam deixando "Procura" sozinho, e a faixa
          de categorias rolava para o lado sem sinal nenhum. "Tudo" e "Todas" tiram a chave. */}
      <div className="ind-filtro">
        <label htmlFor="cla-filtro-tipo">Tipo</label>
        <select
          id="cla-filtro-tipo"
          value={tipo ?? ''}
          onChange={(e) => trocar({ tipo: e.target.value || null })}
        >
          {TIPOS.map((t) => (
            <option key={t.texto} value={t.valor ?? ''}>
              {t.texto}
            </option>
          ))}
        </select>
      </div>
      <div className="ind-filtro">
        <label htmlFor="cla-filtro-categoria">Categoria</label>
        <select
          id="cla-filtro-categoria"
          value={categoria === undefined ? '' : String(categoria)}
          onChange={(e) => trocar({ categoria: e.target.value || null })}
        >
          <option value="">Todas</option>
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
