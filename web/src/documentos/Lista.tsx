// H-18 · Documentos: a lista por assunto, com busca pelo título. Também "Documentos
// arquivados" (só a gestão), a mesma lista com os que saíram.
import { useState } from 'react'
import { Link } from 'react-router'
import { useSessao } from '../casca/contextoSessao'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { listarDocumentos } from './api'
import { useCarga } from './carregar'
import { encontrados, filtrar } from './formatos'
import { Carregando, FalhaAoCarregar, ItemDocumento, ListaAgrupada } from './pecas'
import './documentos.css'

export function ListaDocumentos({ arquivados = false }: { arquivados?: boolean }) {
  const { eu } = useSessao()
  const [busca, setBusca] = useState('')
  const [carga, recarregar] = useCarga(
    () => listarDocumentos({ arquivados: arquivados || undefined }),
    [arquivados],
  )
  const itens = carga.dados?.itens

  const novo = eu?.gestao && !arquivados && (
    <Link className="flutuante" to="/documentos/novo">
      <Icone nome="mais" /> Novo documento
    </Link>
  )

  return (
    <Tela
      titulo={arquivados ? 'Documentos arquivados' : 'Documentos'}
      voltar={arquivados ? '/documentos' : undefined}
      extra={novo}
    >
      {arquivados && (
        <div className="aviso-caixa info">
          <Icone nome="arquivar" />
          <p>Documentos que saíram da lista. Só a gestão vê esta página.</p>
        </div>
      )}
      <div className="doc-busca">
        <label htmlFor="doc-busca" className="com-icone">
          <Icone nome="busca" tamanho={20} /> Procurar documento
        </label>
        <input
          id="doc-busca"
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          maxLength={100}
          autoComplete="off"
        />
        <p className="oculto" aria-live="polite">
          {busca.trim() && itens ? encontrados(filtrar(itens, busca).length) : ''}
        </p>
      </div>
      {carga.situacao === 'erro' && !itens ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !itens ? (
        <Carregando />
      ) : (
        <ListaAgrupada
          itens={itens}
          busca={busca}
          vazio={arquivados ? 'Nenhum documento arquivado.' : 'Nenhum documento publicado ainda.'}
          item={(d) => <ItemDocumento key={d.id} documento={d} paraGestao={eu?.gestao} />}
        />
      )}
      {eu?.gestao && !arquivados && itens && (
        <p className="doc-rodape">
          <Link className="texto-link" to="/documentos/arquivados">
            <Icone nome="arquivar" /> Ver os documentos arquivados
          </Link>
        </p>
      )}
    </Tela>
  )
}
