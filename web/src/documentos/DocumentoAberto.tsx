// H-18 (abrir no celular, com opção de baixar) e H-19 (versões anteriores, com data). Para a
// gestão: quem vê, "Enviar nova versão" e "Arquivar". Sem entrar, o documento público (U2).
import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useLocation, useSearchParams } from 'react-router'
import { useRecado } from '../casca/contextoRecado'
import { useSessao } from '../casca/contextoSessao'
import { Icone } from '../casca/Icone'
import { centralizar } from '../casca/rolar'
import { Tela } from '../casca/Tela'
import { arquivarDocumento, abrirDocumento, enderecoParaAbrir } from './api'
import { comoErroDaApi, useCarga, useIdDoDocumento } from './carregar'
import { diaPorExtenso, nivelDe, tamanhoEmTexto, tipoEmTexto } from './formatos'
import { CaixaDeErro, Carregando, FalhaAoCarregar, FolhaDoDocumento, IconeDoc } from './pecas'
import { DocumentoPublicoAberto } from './Publicos'
import type { Documento, VersaoDocumento } from './tipos'
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

/** Fica fora da guarda `ExigeUnidade` (rotas.tsx): sem sessão, o link de um documento público
 *  abre a página dele (U2); os outros pedem para entrar. */
export function PaginaDocumento() {
  const id = useIdDoDocumento()
  const { estado, recarregar } = useSessao()
  if (id === null) return <DocumentoNaoEncontrado />
  if (estado.situacao === 'carregando') {
    return (
      <Tela titulo="Documento" voltar="/documentos">
        <Carregando />
      </Tela>
    )
  }
  if (estado.situacao === 'sem_conexao') {
    return (
      <Tela titulo="Documento" voltar="/documentos">
        <FalhaAoCarregar mensagem={estado.mensagem} tentar={() => void recarregar()} />
      </Tela>
    )
  }
  if (!estado.eu) return <DocumentoPublicoAberto key={id} id={id} />
  if (estado.eu.precisa_trocar_senha) return <Navigate to="/primeiro-acesso" replace />
  return <DocumentoAberto key={id} id={id} />
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

/** U9 e U1: a confirmação que fica na tela do documento (o recado da casca some sozinho). */
export type Confirmacao = 'publicado' | 'versao' | 'ja_publicado' | 'ja_enviada'

const CONFIRMACOES: Record<Confirmacao, string> = {
  publicado: 'Pronto: o documento foi publicado. Ele já aparece em Documentos.',
  versao: 'Pronto: a versão nova foi enviada. A de antes ficou em “Versões anteriores”.',
  ja_publicado:
    'Já estava publicado: o primeiro envio tinha dado certo, e nada foi publicado em dobro.',
  ja_enviada:
    'Já estava enviada: o primeiro envio tinha dado certo, e nada foi enviado em dobro.',
}

function ConfirmacaoFixa() {
  const estado = useLocation().state as { confirmacao?: Confirmacao; avisou?: boolean } | null
  const confirmacao = estado?.confirmacao
  if (!confirmacao || !(confirmacao in CONFIRMACOES)) return null
  return (
    <div className="aviso-caixa info doc-confirmacao">
      <Icone nome="certo" />
      <p>
        {CONFIRMACOES[confirmacao]}
        {estado?.avisou && ' O aviso saiu no mural.'}
      </p>
    </div>
  )
}

function Conteudo({ documento, trocar }: { documento: Documento; trocar: (d: Documento) => void }) {
  const { eu } = useSessao()
  const [consulta] = useSearchParams()
  // U7: a rota `.../abrir` volta para cá com o motivo quando o arquivo não pôde abrir.
  const naoAbriu = consulta.get('erro')

  return (
    <article className="doc-aberto">
      <ConfirmacaoFixa />
      {naoAbriu && (
        <CaixaDeErro>O arquivo não abriu agora. Tente de novo em alguns minutos.</CaixaDeErro>
      )}
      {documento.arquivado_em && (
        <div className="aviso-caixa atencao">
          <Icone nome="arquivar" />
          <p>
            Arquivado em {diaPorExtenso(documento.arquivado_em)}. Não aparece mais na lista; só a
            gestão vê.
          </p>
        </div>
      )}
      <FolhaDoDocumento documento={documento} />
      {documento.versoes_anteriores.length > 0 && (
        <VersoesAnteriores documento={documento} aberta={!!eu?.gestao} />
      )}
      {eu?.gestao && <ParaAGestao documento={documento} trocar={trocar} />}
    </article>
  )
}

/** Quando cada versão antiga deixou de valer: a data da versão seguinte (U4). */
function substituidaEm(documento: Documento, versao: number): string {
  if (versao + 1 === documento.versao) return documento.atualizado_em
  const seguinte = documento.versoes_anteriores.find((v) => v.versao === versao + 1)
  return seguinte?.enviada_em ?? documento.atualizado_em
}

function ItemDaVersao({ documento, v }: { documento: Documento; v: VersaoDocumento }) {
  return (
    <li className="doc-versao-item">
      <span>
        <b>Versão {v.versao}</b>
        <span className="suave">enviada em {diaPorExtenso(v.enviada_em)}</span>
        <span className="suave">
          Substituída pela versão {v.versao + 1} em {diaPorExtenso(substituidaEm(documento, v.versao))}
        </span>
        <span className="suave">
          {tipoEmTexto(v.arquivo.tipo)}, {tamanhoEmTexto(v.arquivo.tamanho_bytes)}
        </span>
      </span>
      <a
        className="texto-link com-icone"
        href={enderecoParaAbrir(documento.id, v.versao)}
        target="_blank"
        rel="noopener noreferrer"
      >
        <IconeDoc nome="fora" tamanho={20} />
        Abrir{' '}
        <span className="oculto">a versão {v.versao} (abre em outra aba)</span>
      </a>
    </li>
  )
}

/** U4: para o morador, recolhidas (o que vale é a versão de agora); para a gestão, abertas. */
function VersoesAnteriores({ documento, aberta }: { documento: Documento; aberta: boolean }) {
  const lista = (
    <ul className="folha" role="list">
      {documento.versoes_anteriores.map((v) => (
        <ItemDaVersao key={v.versao} documento={documento} v={v} />
      ))}
    </ul>
  )
  if (aberta) {
    return (
      <section className="doc-versoes" aria-labelledby="versoes-anteriores">
        <h2 className="secao" id="versoes-anteriores">
          Versões anteriores
        </h2>
        <p className="ajuda">Ficam guardadas como foram enviadas.</p>
        {lista}
      </section>
    )
  }
  return (
    <section className="doc-versoes" aria-labelledby="versoes-anteriores">
      <details>
        <summary id="versoes-anteriores">
          Ver versões anteriores ({documento.versoes_anteriores.length})
        </summary>
        <p className="ajuda">Valem as da folha de cima; estas ficam guardadas como foram.</p>
        {lista}
      </details>
    </section>
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
      {/* U12: quem vê é informação da gestão; o morador já está vendo. */}
      <p className="doc-quem">
        <Icone nome={documento.acesso === 'gestao' ? 'cadeado' : 'olho'} tamanho={20} />
        <span>Quem vê: {nivelDe(documento.acesso).quemVe}.</span>
      </p>
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
