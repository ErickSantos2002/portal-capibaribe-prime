// H-14 · Mural, e H-15 · Avisos arquivados (a mesma lista, só com os arquivados).
import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useSessao } from '../casca/contextoSessao'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { FaixaNotificacoes } from '../notificacoes/FaixaNotificacoes'
import { listarAvisos } from './api'
import { useCarga } from './carregar'
import { AvisoFixado, Carregando, FalhaAoCarregar, ItemAviso } from './componentes'
import './avisos.css'

// Espera a pessoa parar de digitar antes de perguntar à API.
const ESPERA_DA_BUSCA_MS = 300

function useAtrasado(valor: string, ms: number): string {
  const [atrasado, setAtrasado] = useState(valor)
  useEffect(() => {
    const relogio = window.setTimeout(() => setAtrasado(valor), ms)
    return () => window.clearTimeout(relogio)
  }, [valor, ms])
  return atrasado
}

function encontrados(n: number): string {
  if (n === 0) return 'Nenhum aviso encontrado.'
  return n === 1 ? '1 aviso encontrado.' : `${n} avisos encontrados.`
}

export function Mural({ arquivados = false }: { arquivados?: boolean }) {
  const { eu } = useSessao()
  const [digitado, setDigitado] = useState('')
  const busca = useAtrasado(digitado.trim(), ESPERA_DA_BUSCA_MS)
  const [carga, recarregar] = useCarga(
    () => listarAvisos({ busca: busca || undefined, arquivados: arquivados || undefined }),
    [busca, arquivados],
  )
  const itens = carga.dados?.itens
  // Sem busca, os fixados ficam no topo, em amarelo; buscando, tudo vira uma lista só.
  const destacados = !busca && !arquivados ? (itens ?? []).filter((a) => a.fixado) : []
  const lista = (itens ?? []).filter((a) => !destacados.includes(a))

  const novoAviso = eu?.gestao && !arquivados && (
    <Link className="flutuante" to="/avisos/novo">
      <Icone nome="mais" /> Novo aviso
    </Link>
  )

  return (
    <Tela
      titulo={arquivados ? 'Avisos arquivados' : 'Avisos'}
      voltar={arquivados ? '/avisos' : undefined}
      extra={novoAviso}
    >
      {arquivados && (
        <div className="aviso-caixa info">
          <Icone nome="arquivar" />
          <p>Avisos que saíram do mural. Continuam guardados como foram publicados.</p>
        </div>
      )}
      {/* M2 (épico A): "Falta um passo: ative as notificações", só quando dá para ativar. */}
      {!arquivados && <FaixaNotificacoes />}
      {destacados.map((aviso) => (
        <AvisoFixado key={aviso.id} aviso={aviso} />
      ))}
      <div className="avisos-busca">
        <label htmlFor="busca" className="com-icone">
          <Icone nome="busca" tamanho={20} /> Procurar nos avisos
        </label>
        <input
          id="busca"
          type="search"
          value={digitado}
          onChange={(e) => setDigitado(e.target.value)}
          maxLength={100}
          autoComplete="off"
        />
        <p className="oculto" aria-live="polite">
          {busca && itens ? encontrados(lista.length + destacados.length) : ''}
        </p>
      </div>
      {carga.situacao === 'erro' && !itens ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !itens ? (
        <Carregando />
      ) : lista.length > 0 ? (
        <div className="avisos-lista">
          {lista.map((aviso) => (
            <ItemAviso key={aviso.id} aviso={aviso} arquivados={arquivados} />
          ))}
        </div>
      ) : destacados.length === 0 ? (
        <div className="folha">
          <p className="vazio">
            {busca
              ? 'Nenhum aviso com essas palavras. Tente outra palavra.'
              : arquivados
                ? 'Nenhum aviso arquivado.'
                : 'Nenhum aviso publicado ainda.'}
          </p>
        </div>
      ) : null}
      {carga.situacao === 'erro' && itens && (
        <div className="aviso-caixa erro" role="alert">
          <p>{carga.erro.mensagem}</p>
        </div>
      )}
      {!arquivados && itens && (
        <p className="avisos-arquivados">
          <Link className="texto-link" to="/avisos/arquivados">
            <Icone nome="arquivar" /> Ver os avisos arquivados
          </Link>
        </p>
      )}
    </Tela>
  )
}
