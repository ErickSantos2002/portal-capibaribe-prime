// H-18 · Documentos públicos: a lista para quem ainda não entrou (o link da tela de entrada) e
// a página de um documento público aberto por link, sem entrar (revisão UX, U2).
import { Link, Navigate, useLocation } from 'react-router'
import { useSessao } from '../casca/contextoSessao'
import { Tela } from '../casca/Tela'
import { listarDocumentosPublicos } from './api'
import { useCarga } from './carregar'
import {
  BotoesDoArquivo,
  Carregando,
  FalhaAoCarregar,
  FolhaDoDocumento,
  LinhaDoDocumento,
  ListaAgrupada,
} from './pecas'
import type { DocumentoResumo } from './tipos'
import './documentos.css'

function ItemPublico(documento: DocumentoResumo) {
  return (
    <div className="item doc-publico" key={documento.id}>
      <h3>{documento.titulo}</h3>
      <LinhaDoDocumento documento={documento} />
      <span className="doc-publico-acoes">
        <BotoesDoArquivo
          id={documento.id}
          versao={documento.versao}
          abrirTexto="Abrir"
          nome={documento.titulo}
        />
      </span>
    </div>
  )
}

export function DocumentosPublicos() {
  const { eu } = useSessao()
  const [carga, recarregar] = useCarga(listarDocumentosPublicos, [])
  const itens = carga.dados?.itens
  const dentro = !!eu && !eu.precisa_trocar_senha

  return (
    <Tela titulo="Documentos públicos" voltar={dentro ? '/documentos' : '/entrar'}>
      <p className="suave doc-intro">
        Documentos do condomínio que qualquer pessoa pode ler, mesmo sem entrar no Portal.
      </p>
      {carga.situacao === 'erro' && !itens ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !itens ? (
        <Carregando />
      ) : (
        <ListaAgrupada
          itens={itens}
          busca=""
          vazio="Nenhum documento público ainda."
          item={ItemPublico}
        />
      )}
      {/* U11: o convite para entrar é só para quem ainda não entrou. */}
      {dentro ? (
        <p className="doc-rodape">
          <Link className="texto-link" to="/documentos">
            Ver todos os documentos
          </Link>
        </p>
      ) : (
        <div className="doc-rodape">
          <p className="ajuda">
            Os outros documentos aparecem depois que você entra com a conta do seu apartamento.
          </p>
          <Link className="botao leve" to="/entrar">
            Entrar
          </Link>
        </div>
      )}
    </Tela>
  )
}

/** U2: o link de um documento público aberto sem entrar. Os públicos vêm da lista (a API não
 *  tem o documento aberto sem sessão); não é público, ou não existe: pede para entrar, e depois
 *  de entrar a pessoa volta para o documento. */
export function DocumentoPublicoAberto({ id }: { id: number }) {
  const local = useLocation()
  const [carga, recarregar] = useCarga(listarDocumentosPublicos, [])
  if (carga.situacao === 'erro') {
    return (
      <Tela titulo="Documento" voltar="/documentos/publicos">
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      </Tela>
    )
  }
  if (carga.situacao === 'carregando') {
    return (
      <Tela titulo="Documento" voltar="/documentos/publicos">
        <Carregando />
      </Tela>
    )
  }
  const documento = carga.dados.itens.find((d) => d.id === id)
  if (!documento) return <Navigate to="/entrar" replace state={{ de: local.pathname }} />
  return (
    <Tela titulo="Documento" tituloDaAba={documento.titulo} voltar="/documentos/publicos">
      <article className="doc-aberto">
        <FolhaDoDocumento documento={documento} />
        <div className="doc-rodape">
          <p className="ajuda">
            Este documento é aberto a qualquer pessoa. Os outros aparecem depois que você entra
            com a conta do seu apartamento.
          </p>
          <Link className="botao leve" to="/entrar">
            Entrar
          </Link>
          <p>
            <Link className="texto-link" to="/documentos/publicos">
              Ver todos os documentos públicos
            </Link>
          </p>
        </div>
      </article>
    </Tela>
  )
}
