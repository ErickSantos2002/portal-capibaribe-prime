// H-18 (abrir no celular, com opção de baixar) e H-19 (versões anteriores, com data). Para a
// gestão: "Enviar nova versão" e "Arquivar".
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useRecado } from '../casca/contextoRecado'
import { useSessao } from '../casca/contextoSessao'
import { Icone } from '../casca/Icone'
import { centralizar } from '../casca/rolar'
import { Tela } from '../casca/Tela'
import { arquivarDocumento, abrirDocumento, linkDaVersao } from './api'
import { useArquivo } from './abrir'
import { comoErroDaApi, useCarga, useIdDoDocumento } from './carregar'
import {
  assuntoDe,
  dataDoDocumento,
  diaPorExtenso,
  nivelDe,
  tamanhoEmTexto,
  tipoEmTexto,
} from './formatos'
import { CaixaDeErro, Carregando, FalhaAoCarregar, IconeDoc } from './pecas'
import type { Documento } from './tipos'
import './documentos.css'

/** Link quebrado, documento que não existe ou que a unidade não vê: a mesma tela. */
export function DocumentoNaoEncontrado({ mensagem }: { mensagem?: string }) {
  return (
    <Tela titulo="Documento não encontrado" voltar="/documentos">
      <div className="aviso-caixa atencao" role="alert">
        <Icone nome="alerta" />
        <p>
          {mensagem ??
            'Não achamos este documento. O link pode estar incompleto, ou ele não está mais disponível.'}
        </p>
      </div>
      <Link className="botao" to="/documentos">
        Ir para os documentos
      </Link>
    </Tela>
  )
}

export function PaginaDocumento() {
  const id = useIdDoDocumento()
  return id === null ? <DocumentoNaoEncontrado /> : <DocumentoAberto key={id} id={id} />
}

function DocumentoAberto({ id }: { id: number }) {
  const [carga, recarregar, trocar] = useCarga(() => abrirDocumento(id), [id])
  if (carga.situacao === 'erro' && carga.erro.status === 404) {
    return <DocumentoNaoEncontrado mensagem={carga.erro.mensagem} />
  }
  return (
    <Tela titulo={carga.situacao === 'pronta' ? carga.dados.titulo : 'Documento'} voltar="/documentos">
      {carga.situacao === 'erro' ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : carga.situacao === 'carregando' ? (
        <Carregando />
      ) : (
        <Conteudo documento={carga.dados} trocar={trocar} />
      )}
    </Tela>
  )
}

function Conteudo({ documento, trocar }: { documento: Documento; trocar: (d: Documento) => void }) {
  const { eu } = useSessao()
  const arquivo = useArquivo()
  const assunto = assuntoDe(documento.categoria)
  const atual = (baixar: boolean) => () => linkDaVersao(documento.id, documento.versao, baixar)

  return (
    <article className="doc-aberto">
      {documento.arquivado_em && (
        <div className="aviso-caixa atencao">
          <Icone nome="arquivar" />
          <p>
            Arquivado em {diaPorExtenso(documento.arquivado_em)}. Não aparece mais na lista; só a
            gestão vê.
          </p>
        </div>
      )}
      <div className="doc-folha">
        <p className="doc-assunto">
          <Icone nome="documentos" tamanho={20} />
          {assunto.nome}
        </p>
        <p className="doc-data">Documento de {dataDoDocumento(documento.data_documento)}</p>
        <p className="doc-arquivo">
          {tipoEmTexto(documento.arquivo.tipo)}, {tamanhoEmTexto(documento.arquivo.tamanho_bytes)}
        </p>
        <p className="doc-versao suave">
          Versão {documento.versao}, enviada em {diaPorExtenso(documento.atualizado_em)}
        </p>
        <div className="doc-botoes">
          <button
            type="button"
            className="botao"
            disabled={arquivo.ocupado !== null}
            onClick={() => arquivo.abrir('abrir', atual(false))}
          >
            <IconeDoc nome="fora" />
            {arquivo.ocupado === 'abrir' ? 'Abrindo…' : 'Abrir o documento'}
          </button>
          <button
            type="button"
            className="botao leve"
            disabled={arquivo.ocupado !== null}
            onClick={() => arquivo.baixar('baixar', atual(true))}
          >
            <IconeDoc nome="baixar" />
            {arquivo.ocupado === 'baixar' ? 'Baixando…' : 'Baixar'}
          </button>
        </div>
      </div>
      {arquivo.erro && <CaixaDeErro>{arquivo.erro}</CaixaDeErro>}
      <p className="doc-quem">
        <Icone nome={documento.acesso === 'gestao' ? 'cadeado' : 'olho'} tamanho={20} />
        <span>Quem vê: {nivelDe(documento.acesso).quemVe}.</span>
      </p>

      {documento.versoes_anteriores.length > 0 && (
        <section className="doc-versoes" aria-labelledby="versoes-anteriores">
          <h2 className="secao" id="versoes-anteriores">
            Versões anteriores
          </h2>
          <p className="ajuda">Ficam guardadas como foram enviadas.</p>
          <ul className="folha" role="list">
            {documento.versoes_anteriores.map((v) => (
              <li key={v.versao} className="doc-versao-item">
                <span>
                  <b>Versão {v.versao}</b>
                  <span className="suave">
                    enviada em {diaPorExtenso(v.enviada_em)} · {tipoEmTexto(v.arquivo.tipo)},{' '}
                    {tamanhoEmTexto(v.arquivo.tamanho_bytes)}
                  </span>
                </span>
                <button
                  type="button"
                  className="botao leve"
                  disabled={arquivo.ocupado !== null}
                  onClick={() =>
                    arquivo.abrir(`versao-${v.versao}`, () =>
                      linkDaVersao(documento.id, v.versao),
                    )
                  }
                >
                  <IconeDoc nome="fora" />
                  {arquivo.ocupado === `versao-${v.versao}` ? 'Abrindo…' : 'Abrir'}
                  {' '}<span className="oculto">a versão {v.versao}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {eu?.gestao && <ParaAGestao documento={documento} trocar={trocar} />}
    </article>
  )
}

function ParaAGestao({ documento, trocar }: { documento: Documento; trocar: (d: Documento) => void }) {
  const recado = useRecado()
  const [confirmando, setConfirmando] = useState(false)
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')
  const confirmacao = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (confirmando) centralizar(confirmacao.current)
  }, [confirmando])

  if (documento.arquivado_em) return null

  async function arquivar() {
    setOcupado(true)
    setErro('')
    try {
      trocar(await arquivarDocumento(documento.id))
      setConfirmando(false)
      recado('Documento arquivado.')
    } catch (e) {
      setErro(comoErroDaApi(e).mensagem)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <section aria-labelledby="para-a-gestao">
      <h2 id="para-a-gestao" className="secao">
        Para a gestão
      </h2>
      {erro && <CaixaDeErro>{erro}</CaixaDeErro>}
      <div className="doc-acoes">
        <Link className="botao leve" to={`/documentos/${documento.id}/nova-versao`}>
          <IconeDoc nome="clipe" /> Enviar nova versão
        </Link>
        {confirmando ? (
          <div
            className="aviso-caixa atencao"
            role="group"
            aria-labelledby="confirmar-arquivar"
            ref={confirmacao}
            tabIndex={-1}
          >
            <Icone nome="alerta" />
            <div>
              <p id="confirmar-arquivar">
                O documento sai da lista e fica em Documentos arquivados, que só a gestão vê. Não
                dá para trazer de volta.
              </p>
              <button type="button" className="botao perigo" disabled={ocupado} onClick={arquivar}>
                <Icone nome="arquivar" /> Arquivar de vez
              </button>
              <button
                type="button"
                className="botao leve"
                disabled={ocupado}
                onClick={() => setConfirmando(false)}
              >
                Cancelar
              </button>
            </div>
          </div>
        ) : (
          <button type="button" className="botao leve" onClick={() => setConfirmando(true)}>
            <Icone nome="arquivar" /> Arquivar
          </button>
        )}
      </div>
    </section>
  )
}
