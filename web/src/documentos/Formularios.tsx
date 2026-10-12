// H-17 · Novo documento e H-19 · Enviar nova versão. O arquivo vai primeiro (`enviarArquivo`:
// conferir, comprimir foto, pedir, mandar direto ao bucket, confirmar); depois o documento.
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import type { ErroDaApi } from '../api/cliente'
import { enviarArquivo } from '../arquivos/enviar'
import type { ArquivoEnviado } from '../arquivos/tipos'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { abrirDocumento, enviarNovaVersao, publicarDocumento } from './api'
import { comoErroDaApi, useCarga, useIdDoDocumento } from './carregar'
import { DocumentoNaoEncontrado } from './DocumentoAberto'
import { EscolherArquivo } from './EscolherArquivo'
import { ASSUNTOS, hojeEmRecife, NIVEIS } from './formatos'
import { Carregando, FalhaAoCarregar } from './pecas'
import type { CategoriaDocumento, NivelAcesso } from './tipos'
import './documentos.css'

const LIMITE_TITULO = 120
const DATA_MINIMA = '1990-01-01'
const DATA_MAXIMA = '2100-12-31'

// Erros do envio do arquivo (contrato, seção 5.1): a mensagem vai junto do botão do arquivo.
const ERROS_DO_ARQUIVO = new Set([
  'arquivo_recusado',
  'arquivo_nao_chegou',
  'muitos_arquivos',
  'arquivos_desligados',
  'armazenamento_indisponivel',
  'arquivo_nao_encontrado',
  // Os do documento: o arquivo enviado não serve mais (spec do épico, seção 2.2).
  'arquivo_invalido',
  'arquivo_em_uso',
])
// Com estes, o arquivo já enviado é esquecido: a próxima tentativa envia de novo.
const ESQUECER_O_ENVIADO = new Set(['arquivo_invalido', 'arquivo_em_uso', 'arquivo_nao_encontrado'])

type Campo = 'titulo' | 'data' | 'arquivo'
type Erros = Partial<Record<Campo, string>>

/** Mexeu no campo: o erro dele some. */
function sem(erros: Erros, campo: Campo): Erros {
  const resto = { ...erros }
  delete resto[campo]
  return resto
}

/** Os campos que a API marcou (422), com os nomes da tela. */
function errosDaApi(erro: ErroDaApi): Erros {
  const erros: Erros = {}
  for (const c of erro.campos) {
    if (c.campo === 'titulo') erros.titulo ??= c.mensagem
    else if (c.campo === 'data_documento') erros.data ??= c.mensagem
    else if (c.campo === 'arquivo' || c.campo === 'arquivo_id') erros.arquivo ??= c.mensagem
  }
  if (ERROS_DO_ARQUIVO.has(erro.codigo)) erros.arquivo ??= erro.mensagem
  return erros
}

function ErroGeral({ mensagem }: { mensagem: string }) {
  const caixa = useRef<HTMLDivElement>(null)
  useEffect(() => caixa.current?.focus(), [mensagem])
  return (
    <div className="aviso-caixa erro" role="alert" tabIndex={-1} ref={caixa}>
      <Icone nome="alerta" />
      <p>{mensagem}</p>
    </div>
  )
}

function ErroDoCampo({ id, mensagem }: { id: string; mensagem?: string }) {
  if (!mensagem) return null
  return (
    <p className="doc-erro-campo" id={id}>
      {mensagem}
    </p>
  )
}

/**
 * O arquivo escolhido e, se já foi enviado, o resultado: a publicação que falha depois do envio
 * (um título recusado, a internet) não manda o mesmo arquivo de novo.
 */
function useArquivoDoFormulario() {
  const [arquivo, setArquivo] = useState<File | null>(null)
  const enviado = useRef<{ de: File; resultado: ArquivoEnviado } | null>(null)

  async function enviar(onde: (etapa: 'enviando') => void): Promise<ArquivoEnviado> {
    if (!arquivo) throw new Error('sem arquivo')
    if (enviado.current?.de === arquivo) return enviado.current.resultado
    onde('enviando')
    const resultado = await enviarArquivo(arquivo, 'documento')
    enviado.current = { de: arquivo, resultado }
    return resultado
  }

  function esquecer() {
    enviado.current = null
  }

  return { arquivo, escolher: setArquivo, enviar, esquecer }
}

type Etapa = 'parado' | 'enviando' | 'publicando'

// --- H-17 · Novo documento --------------------------------------------------------------------

export function NovoDocumento() {
  const navegar = useNavigate()
  const [titulo, setTitulo] = useState('')
  const [categoria, setCategoria] = useState<CategoriaDocumento>('obra')
  const [data, setData] = useState(hojeEmRecife)
  const [acesso, setAcesso] = useState<NivelAcesso>('compradores')
  // Como no protótipo (dúvidas do épico A, item 1).
  const [avisar, setAvisar] = useState(true)
  const arquivo = useArquivoDoFormulario()
  const [erros, setErros] = useState<Erros>({})
  const [geral, setGeral] = useState('')
  const [etapa, setEtapa] = useState<Etapa>('parado')
  const podeAvisar = acesso !== 'gestao'

  function conferir(): Erros {
    const encontrados: Erros = {}
    if (!titulo.trim()) encontrados.titulo = 'Escreva o título do documento.'
    if (!data || data < DATA_MINIMA || data > DATA_MAXIMA) {
      encontrados.data = 'Escolha uma data entre 1990 e 2100.'
    }
    if (!arquivo.arquivo) encontrados.arquivo = 'Escolha o arquivo do documento.'
    return encontrados
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (etapa !== 'parado') return
    const encontrados = conferir()
    setErros(encontrados)
    const quantos = Object.keys(encontrados).length
    if (quantos > 0) {
      setGeral(quantos === 1 ? Object.values(encontrados)[0] : 'Confira os campos marcados.')
      return
    }
    setGeral('')
    try {
      const enviado = await arquivo.enviar(setEtapa)
      setEtapa('publicando')
      const documento = await publicarDocumento({
        titulo: titulo.trim(),
        categoria,
        data_documento: data,
        acesso,
        arquivo_id: enviado.id,
        avisar_unidades: podeAvisar && avisar,
      })
      navegar(`/documentos/${documento.id}`, {
        replace: true,
        state: { recado: 'Documento publicado.' },
      })
    } catch (e) {
      const erro = comoErroDaApi(e)
      if (ESQUECER_O_ENVIADO.has(erro.codigo)) arquivo.esquecer()
      setErros(errosDaApi(erro))
      setGeral(erro.mensagem)
      setEtapa('parado')
    }
  }

  return (
    <Tela titulo="Novo documento" voltar="/documentos">
      <form onSubmit={enviar} noValidate className="doc-form">
        {geral && <ErroGeral mensagem={geral} />}

        <label htmlFor="doc-titulo">Título</label>
        <input
          id="doc-titulo"
          type="text"
          value={titulo}
          maxLength={LIMITE_TITULO}
          onChange={(e) => {
            setTitulo(e.target.value)
            setErros((atuais) => sem(atuais, 'titulo'))
          }}
          aria-invalid={!!erros.titulo}
          aria-describedby={erros.titulo ? 'doc-titulo-erro' : 'doc-titulo-ajuda'}
          className={erros.titulo ? 'campo-erro' : undefined}
        />
        <ErroDoCampo id="doc-titulo-erro" mensagem={erros.titulo} />
        <p className="ajuda" id="doc-titulo-ajuda">
          Como as pessoas vão procurar, ex.: Regimento interno.
        </p>

        <div className="doc-lado">
          <div>
            <label htmlFor="doc-assunto">Assunto</label>
            <select
              id="doc-assunto"
              value={categoria}
              onChange={(e) => setCategoria(e.target.value as CategoriaDocumento)}
            >
              {ASSUNTOS.map((a) => (
                <option key={a.valor} value={a.valor}>
                  {a.nome}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="doc-data">Data do documento</label>
            <input
              id="doc-data"
              type="date"
              min={DATA_MINIMA}
              max={DATA_MAXIMA}
              value={data}
              onChange={(e) => {
                setData(e.target.value)
                setErros((atuais) => sem(atuais, 'data'))
              }}
              aria-invalid={!!erros.data}
              aria-describedby={erros.data ? 'doc-data-erro' : 'doc-data-ajuda'}
              className={erros.data ? 'campo-erro' : undefined}
            />
            <ErroDoCampo id="doc-data-erro" mensagem={erros.data} />
            <p className="ajuda" id="doc-data-ajuda">
              A data que está no documento.
            </p>
          </div>
        </div>

        <EscolherArquivo
          id="doc-arquivo"
          arquivo={arquivo.arquivo}
          erro={erros.arquivo}
          escolher={(escolhido) => {
            arquivo.escolher(escolhido)
            setErros((atuais) => sem(atuais, 'arquivo'))
          }}
        />

        <fieldset className="doc-niveis">
          <legend>Quem pode ver</legend>
          {NIVEIS.map((n) => (
            <label key={n.valor} className="opcao doc-nivel">
              <input
                type="radio"
                name="doc-acesso"
                value={n.valor}
                checked={acesso === n.valor}
                onChange={() => setAcesso(n.valor)}
              />
              <span>
                <b>{n.opcao}</b>
                <span className="suave">{n.explicacao}</span>
              </span>
            </label>
          ))}
        </fieldset>

        {podeAvisar ? (
          <div className="doc-avisar">
            <label className="opcao">
              <input
                type="checkbox"
                checked={avisar}
                onChange={(e) => setAvisar(e.target.checked)}
                aria-describedby="doc-avisar-ajuda"
              />
              Avisar os apartamentos
            </label>
            <p className="ajuda" id="doc-avisar-ajuda">
              {avisar
                ? 'Sai um aviso no mural, com o botão para abrir o documento, e a notificação para quem ligou.'
                : 'O documento fica só em Documentos, sem aviso no mural.'}
            </p>
          </div>
        ) : (
          <p className="ajuda doc-avisar">
            Documento só da gestão não gera aviso: os apartamentos não conseguiriam abrir.
          </p>
        )}

        <button className="botao doc-enviar" type="submit" disabled={etapa !== 'parado'}>
          {etapa === 'enviando'
            ? 'Enviando o arquivo…'
            : etapa === 'publicando'
              ? 'Publicando…'
              : 'Publicar documento'}
        </button>
      </form>
    </Tela>
  )
}

// --- H-19 · Enviar nova versão ----------------------------------------------------------------

export function PaginaNovaVersao() {
  const id = useIdDoDocumento()
  return id === null ? <DocumentoNaoEncontrado /> : <NovaVersao key={id} id={id} />
}

function NovaVersao({ id }: { id: number }) {
  const navegar = useNavigate()
  const [carga, recarregar] = useCarga(() => abrirDocumento(id), [id])
  const arquivo = useArquivoDoFormulario()
  const [erro, setErro] = useState('')
  const [geral, setGeral] = useState('')
  const [etapa, setEtapa] = useState<Etapa>('parado')

  if (carga.situacao === 'erro' && carga.erro.status === 404) {
    return <DocumentoNaoEncontrado mensagem={carga.erro.mensagem} />
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (etapa !== 'parado') return
    if (!arquivo.arquivo) {
      setErro('Escolha o arquivo da versão nova.')
      setGeral('Escolha o arquivo da versão nova.')
      return
    }
    setGeral('')
    try {
      const enviado = await arquivo.enviar(setEtapa)
      setEtapa('publicando')
      await enviarNovaVersao(id, { arquivo_id: enviado.id })
      navegar(`/documentos/${id}`, { replace: true, state: { recado: 'Nova versão enviada.' } })
    } catch (e) {
      const falha = comoErroDaApi(e)
      if (ESQUECER_O_ENVIADO.has(falha.codigo)) arquivo.esquecer()
      setErro(errosDaApi(falha).arquivo ?? '')
      setGeral(falha.mensagem)
      setEtapa('parado')
    }
  }

  const documento = carga.situacao === 'pronta' ? carga.dados : null
  return (
    <Tela titulo="Enviar nova versão" voltar={`/documentos/${id}`}>
      {carga.situacao === 'erro' ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !documento ? (
        <Carregando />
      ) : documento.arquivado_em ? (
        <div className="aviso-caixa atencao" role="alert">
          <Icone nome="arquivar" />
          <p>Documento arquivado não recebe versão nova.</p>
        </div>
      ) : (
        <form onSubmit={enviar} noValidate className="doc-form">
          <p className="doc-de">
            <span className="suave">Documento</span>
            <b>{documento.titulo}</b>
          </p>
          <div className="aviso-caixa info">
            <Icone nome="info" />
            <p>
              A versão de agora (versão {documento.versao}) vai para “Versões anteriores”, com a
              data. Nada se perde.
            </p>
          </div>
          {geral && <ErroGeral mensagem={geral} />}
          <EscolherArquivo
            id="doc-arquivo"
            arquivo={arquivo.arquivo}
            erro={erro || undefined}
            escolher={(escolhido) => {
              arquivo.escolher(escolhido)
              setErro('')
            }}
          />
          <button className="botao doc-enviar" type="submit" disabled={etapa !== 'parado'}>
            {etapa === 'enviando'
              ? 'Enviando o arquivo…'
              : etapa === 'publicando'
                ? 'Salvando…'
                : 'Enviar nova versão'}
          </button>
        </form>
      )}
    </Tela>
  )
}
