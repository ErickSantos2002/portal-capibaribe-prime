// H-18 · Documentos públicos: para quem ainda não entrou (o link da tela de entrada). Sem
// sessão não existe o documento aberto (é da unidade logada): cada item abre e baixa aqui mesmo.
import { listarDocumentosPublicos, linkDaVersao } from './api'
import { useArquivo } from './abrir'
import { useCarga } from './carregar'
import { Tela } from '../casca/Tela'
import { CaixaDeErro, Carregando, FalhaAoCarregar, IconeDoc, LinhaDoDocumento, ListaAgrupada } from './pecas'
import type { DocumentoResumo } from './tipos'
import './documentos.css'

export function DocumentosPublicos() {
  const [carga, recarregar] = useCarga(listarDocumentosPublicos, [])
  const arquivo = useArquivo()
  const itens = carga.dados?.itens

  function Item(documento: DocumentoResumo) {
    const chave = String(documento.id)
    const pedir = (baixar: boolean) => () => linkDaVersao(documento.id, documento.versao, baixar)
    return (
      <div className="item doc-publico" key={documento.id}>
        <h3>{documento.titulo}</h3>
        <LinhaDoDocumento documento={documento} />
        <span className="doc-publico-acoes">
          <button
            type="button"
            className="botao"
            disabled={arquivo.ocupado !== null}
            onClick={() => arquivo.abrir(`abrir-${chave}`, pedir(false))}
          >
            <IconeDoc nome="fora" />
            {arquivo.ocupado === `abrir-${chave}` ? 'Abrindo…' : 'Abrir'}
            {' '}<span className="oculto">{documento.titulo}</span>
          </button>
          <button
            type="button"
            className="botao leve"
            disabled={arquivo.ocupado !== null}
            onClick={() => arquivo.baixar(`baixar-${chave}`, pedir(true))}
          >
            <IconeDoc nome="baixar" />
            {arquivo.ocupado === `baixar-${chave}` ? 'Baixando…' : 'Baixar'}
            {' '}<span className="oculto">{documento.titulo}</span>
          </button>
        </span>
      </div>
    )
  }

  return (
    <Tela titulo="Documentos públicos" voltar="/entrar">
      <p className="suave doc-intro">
        Documentos do condomínio que qualquer pessoa pode ler, mesmo sem entrar no Portal.
      </p>
      {arquivo.erro && <CaixaDeErro>{arquivo.erro}</CaixaDeErro>}
      {carga.situacao === 'erro' && !itens ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !itens ? (
        <Carregando />
      ) : (
        <ListaAgrupada itens={itens} busca="" vazio="Nenhum documento público ainda." item={Item} />
      )}
      <p className="ajuda doc-rodape">
        Os outros documentos aparecem depois que você entra com a conta do seu apartamento.
      </p>
    </Tela>
  )
}
