// Indicações · a lista (spec, seção 3.1): busca, faixa de categorias, os mais recomendados
// primeiro (a ordem vem da API) e o botão "Indicar alguém". O filtro mora no endereço
// (`?categoria=&busca=&com_aviso=1`): voltar do prestador aberto devolve a mesma lista.
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useCarga } from '../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../avisos/componentes'
import { useSessao } from '../casca/contextoSessao'
import { Icone } from '../casca/Icone'
import { Placa } from '../casca/Placa'
import { Tela } from '../casca/Tela'
import { listarCategorias, listarIndicacoes } from './api'
import { CAMINHO_NOVA_INDICACAO, caminhoIndicacao } from './caminhos'
import { comAvisoEmTexto, encontradas, naoRecomendamEmTexto, recomendamEmTexto } from './formatos'
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

  function trocar(chave: 'categoria' | 'com_aviso', valor: string | null) {
    setConsulta(
      (antes) => {
        const depois = new URLSearchParams(antes)
        if (valor === null) depois.delete(chave)
        else depois.set(chave, valor)
        return depois
      },
      { replace: true },
    )
  }

  const indicarAlguem = (
    <Link className="flutuante ind-indicar" to={CAMINHO_NOVA_INDICACAO}>
      <Icone nome="mais" /> Indicar alguém
    </Link>
  )

  return (
    <Tela titulo="Indicações" extra={indicarAlguem}>
      {!!lista?.com_aviso && (
        <button
          type="button"
          className="ind-com-aviso"
          aria-pressed={comAviso}
          onClick={() => trocar('com_aviso', comAviso ? null : '1')}
        >
          <Icone nome="alerta" /> {comAvisoEmTexto(lista.com_aviso)}
        </button>
      )}
      <div className="ind-busca">
        <label htmlFor="ind-busca" className="com-icone">
          <Icone nome="busca" tamanho={20} /> Procurar: nome ou serviço
        </label>
        <input
          id="ind-busca"
          type="search"
          value={digitado}
          onChange={(e) => setDigitado(e.target.value)}
          maxLength={80}
          autoComplete="off"
        />
        <p className="oculto" aria-live="polite">
          {busca && lista ? encontradas(lista.itens.length) : ''}
        </p>
      </div>
      {categorias.dados && (
        <nav className="faixa-categorias" aria-label="Categorias">
          <button
            type="button"
            className="chip"
            aria-pressed={categoria === undefined}
            onClick={() => trocar('categoria', null)}
          >
            Todos
          </button>
          {categorias.dados.itens.map((c) => (
            <button
              key={c.id}
              type="button"
              className="chip"
              aria-pressed={categoria === c.id}
              onClick={() => trocar('categoria', String(c.id))}
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
          <p className="vazio">{encontradas(0)}</p>
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
      <h3>{prestador.nome}</h3>
      <span className="seta">
        <Icone nome="seta" />
      </span>
      <span className="linha-meta">
        <span className="ind-recomendam">
          <span aria-hidden="true">👍 </span>
          {recomendamEmTexto(prestador.recomendam)}
        </span>
        {prestador.nao_recomendam > 0 && (
          <span className="ind-nao-recomendam">{naoRecomendamEmTexto(prestador.nao_recomendam)}</span>
        )}
        {avisos > 0 && (
          <span className="selo ind-selo-aviso">
            {avisos === 1 ? '1 aviso da vizinhança' : `${avisos} avisos da vizinhança`}
          </span>
        )}
      </span>
      {prestador.trecho && (
        <span className="ind-trecho">
          <Placa unidade={prestador.trecho.unidade} />
          <span className="ind-trecho-texto">“{prestador.trecho.comentario}”</span>
        </span>
      )}
    </Link>
  )
}
