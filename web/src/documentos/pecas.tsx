// Épico A do M3 · peças comuns às telas de documentos. Pertence ao épico A.
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Icone } from '../casca/Icone'
import { enderecoParaAbrir } from './api'
import {
  agrupar,
  assuntoDe,
  dataDoDocumento,
  diaPorExtenso,
  filtrar,
  tamanhoEmTexto,
  tipoEmTexto,
} from './formatos'
import type { DocumentoResumo } from './tipos'

// Ícones que a casca não tem, no mesmo traço do `Icone` (2 px, 24×24). Desenho constante do
// código, nunca dado de fora (dúvidas do épico A, item 7).
const DESENHOS = {
  baixar: '<path d="M12 4v11"/><path d="M7 10.5l5 5 5-5"/><path d="M5 20h14"/>',
  fora: '<path d="M14 4.5h5.5V10"/><path d="M19.5 4.5 11 13"/><path d="M18 14v5.5H4.5V6H10"/>',
  clipe:
    '<path d="M20 11.5 12.2 19.3a5 5 0 0 1-7.1-7.1l8.1-8.1a3.3 3.3 0 0 1 4.7 4.7l-8 8a1.7 1.7 0 0 1-2.4-2.4l7.3-7.3"/>',
} as const

export function IconeDoc({ nome, tamanho = 24 }: { nome: keyof typeof DESENHOS; tamanho?: number }) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      dangerouslySetInnerHTML={{ __html: DESENHOS[nome] }}
    />
  )
}

export function Carregando() {
  return (
    <p className="vazio" aria-live="polite">
      Carregando…
    </p>
  )
}

export function CaixaDeErro({ children }: { children: ReactNode }) {
  return (
    <div className="aviso-caixa erro" role="alert">
      <Icone nome="alerta" />
      <p>{children}</p>
    </div>
  )
}

export function FalhaAoCarregar({ mensagem, tentar }: { mensagem: string; tentar: () => void }) {
  return (
    <>
      <CaixaDeErro>{mensagem}</CaixaDeErro>
      <button type="button" className="botao leve" onClick={tentar}>
        Tentar de novo
      </button>
    </>
  )
}

/** Data, versão, quando foi arquivado e, para a gestão, os selos de quem vê (U15, U16). */
export function LinhaDoDocumento({
  documento,
  paraGestao = false,
}: {
  documento: DocumentoResumo
  paraGestao?: boolean
}) {
  return (
    <span className="linha-meta">
      <span>{dataDoDocumento(documento.data_documento)}</span>
      {documento.versao > 1 && <span>versão {documento.versao}</span>}
      {documento.arquivado_em && <span>arquivado em {diaPorExtenso(documento.arquivado_em)}</span>}
      {paraGestao && documento.acesso === 'gestao' && (
        <span className="doc-marca">
          <Icone nome="cadeado" tamanho={16} /> só a gestão vê
        </span>
      )}
      {paraGestao && documento.acesso === 'publico' && (
        <span className="doc-marca doc-marca-publico">
          <Icone nome="olho" tamanho={16} /> qualquer pessoa vê
        </span>
      )}
    </span>
  )
}

/** Um documento da lista: leva ao documento aberto (H-18). */
export function ItemDocumento({
  documento,
  paraGestao,
}: {
  documento: DocumentoResumo
  paraGestao?: boolean
}) {
  return (
    <Link className="item" to={`/documentos/${documento.id}`}>
      <h3>{documento.titulo}</h3>
      <span className="seta">
        <Icone nome="seta" />
      </span>
      <LinhaDoDocumento documento={documento} paraGestao={paraGestao} />
    </Link>
  )
}

/** A "folha" do documento aberto: assunto, título inteiro (o do topo pode ser cortado, U17),
 *  data, arquivo, versão e os botões. Também a do documento público aberto sem entrar (U2). */
export function FolhaDoDocumento({ documento }: { documento: DocumentoResumo }) {
  return (
    <div className="doc-folha">
      <p className="doc-assunto">
        <Icone nome="documentos" tamanho={20} />
        {assuntoDe(documento.categoria).nome}
      </p>
      <p className="doc-titulo">{documento.titulo}</p>
      <p className="doc-data">Documento de {dataDoDocumento(documento.data_documento)}</p>
      <p className="doc-arquivo">
        {tipoEmTexto(documento.arquivo.tipo)}, {tamanhoEmTexto(documento.arquivo.tamanho_bytes)}
      </p>
      <p className="doc-versao suave">
        Versão {documento.versao}, enviada em {diaPorExtenso(documento.atualizado_em)}
      </p>
      <div className="doc-botoes">
        <BotoesDoArquivo id={documento.id} versao={documento.versao} />
      </div>
    </div>
  )
}

/** U7: "Abrir" (outra aba) e "Baixar" (fica na tela) pelo endereço do Portal, que confere o
 *  acesso e redireciona para um link novo a cada toque. `nome`: o que o leitor de tela ouve
 *  depois do verbo (ex.: o título, na lista dos públicos). */
export function BotoesDoArquivo({
  id,
  versao,
  abrirTexto = 'Abrir o documento',
  nome,
}: {
  id: number
  versao: number
  abrirTexto?: string
  nome?: string
}) {
  const complemento = nome ? (
    <>
      {' '}
      <span className="oculto">{nome}</span>
    </>
  ) : null
  return (
    <>
      <a
        className="botao"
        href={enderecoParaAbrir(id, versao)}
        target="_blank"
        rel="noopener noreferrer"
      >
        <IconeDoc nome="fora" />
        {abrirTexto}
        {complemento}{' '}
        <span className="oculto">(abre em outra aba)</span>
      </a>
      <a className="botao leve" href={enderecoParaAbrir(id, versao, true)}>
        <IconeDoc nome="baixar" />
        Baixar
        {complemento}
      </a>
    </>
  )
}

/** Busca + lista agrupada por assunto. `item` desenha cada documento. */
export function ListaAgrupada({
  itens,
  busca,
  vazio,
  item,
}: {
  itens: readonly DocumentoResumo[]
  busca: string
  vazio: string
  item: (documento: DocumentoResumo) => ReactNode
}) {
  const achados = filtrar(itens, busca)
  if (achados.length === 0) {
    return (
      <div className="folha">
        <p className="vazio">
          {busca.trim() ? 'Nenhum documento com essas palavras. Tente outra palavra.' : vazio}
        </p>
      </div>
    )
  }
  return (
    <>
      {agrupar(achados).map((grupo) => (
        <section key={grupo.assunto.valor} aria-labelledby={`grupo-${grupo.assunto.valor}`}>
          <h2 className="secao" id={`grupo-${grupo.assunto.valor}`}>
            {grupo.assunto.grupo}
          </h2>
          <div className="folha">{grupo.itens.map(item)}</div>
        </section>
      ))}
    </>
  )
}
