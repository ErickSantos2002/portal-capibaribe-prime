// H-22 · "Quais apartamentos votaram", só para a gestão: quem votou e quem falta, por bloco, para
// cobrar participação. Nunca em quê (a API nem manda).
import { Link } from 'react-router'
import type { UnidadeRef } from '../../api/tipos'
import { useCarga } from '../../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../../avisos/componentes'
import { ordemDaGrade } from '../../avisos/formatos'
import { useRecado } from '../../casca/contextoRecado'
import { useSessao } from '../../casca/contextoSessao'
import { Tela } from '../../casca/Tela'
import { abrirEnquete, votantes as buscarVotantes } from '../api'
import { caminhoEnquete } from '../caminhos'
import type { Enquete, Votantes } from '../tipos'
import { EnqueteNaoEncontrada } from './EnqueteAberta'
import { useIdDaEnquete } from './useIdDaEnquete'
import { faltamParaCopiar, participacaoEmTexto } from './formatos'
import './enquetes.css'

export function PaginaVotantes() {
  const id = useIdDaEnquete()
  return id === null ? <EnqueteNaoEncontrada /> : <QuaisVotaram key={id} id={id} />
}

function QuaisVotaram({ id }: { id: number }) {
  const [carga, recarregar] = useCarga(
    () => Promise.all([abrirEnquete(id), buscarVotantes(id)]),
    [id],
  )
  if (carga.situacao === 'erro' && carga.erro.status === 404) {
    return <EnqueteNaoEncontrada mensagem={carga.erro.mensagem} />
  }
  return (
    <Tela titulo="Quais apartamentos votaram" voltar={caminhoEnquete(id)}>
      {carga.situacao === 'erro' ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : carga.situacao === 'carregando' ? (
        <Carregando />
      ) : (
        <Conteudo enquete={carga.dados[0]} lista={carga.dados[1]} />
      )}
    </Tela>
  )
}

function Conteudo({ enquete, lista }: { enquete: Enquete; lista: Votantes }) {
  const recado = useRecado()
  const faltam = lista.entraram_sem_votar.length + lista.nao_entraram.length

  async function copiar() {
    try {
      await navigator.clipboard.writeText(faltamParaCopiar(enquete.pergunta, lista))
      recado('Lista copiada. Dá para colar no grupo.')
    } catch {
      recado('Não deu para copiar. Selecione os apartamentos e copie à mão.')
    }
  }

  return (
    <>
      <p className="suave">
        Enquete:{' '}
        <Link className="texto-link" to={caminhoEnquete(enquete.id)}>
          {enquete.pergunta}
        </Link>
      </p>
      <p className="enq-contagem">
        <b>{participacaoEmTexto(enquete.participacao)}</b>
      </p>
      <p className="ajuda">
        Mostra só quem votou, nunca em quê. Contam todos os apartamentos do destino, inclusive os
        que ainda não entraram no Portal.
      </p>
      {faltam > 0 && (
        <button type="button" className="botao leve enq-copiar" onClick={() => void copiar()}>
          Copiar a lista de quem falta
        </button>
      )}
      <Grupo id="enq-votaram" titulo="Votaram" unidades={lista.votaram} votou />
      <Grupo
        id="enq-entraram"
        titulo="Entrou, mas não votou"
        ajuda="Já usam o Portal: basta lembrar da enquete."
        unidades={lista.entraram_sem_votar}
      />
      <Grupo
        id="enq-nao-entraram"
        titulo="Ainda não entrou no Portal"
        ajuda="Não fizeram o primeiro acesso: precisam da senha inicial e do endereço do Portal."
        unidades={lista.nao_entraram}
      />
    </>
  )
}

interface PropsGrupo {
  id: string
  titulo: string
  ajuda?: string
  unidades: UnidadeRef[]
  votou?: boolean
}

function Grupo({ id, titulo, ajuda, unidades, votou }: PropsGrupo) {
  const { eu } = useSessao()
  const blocos = new Map<number, UnidadeRef[]>()
  for (const u of ordemDaGrade(unidades)) blocos.set(u.bloco, [...(blocos.get(u.bloco) ?? []), u])
  return (
    <section aria-labelledby={id}>
      <h2 className="secao" id={id}>
        {titulo} ({unidades.length})
      </h2>
      {unidades.length === 0 ? (
        <p className="ajuda">Nenhum apartamento.</p>
      ) : (
        <>
          {ajuda && <p className="ajuda">{ajuda}</p>}
          {[...blocos].map(([bloco, doBloco]) => (
            <div key={bloco}>
              <h3 className="enq-bloco">Bloco {bloco}</h3>
              <ul className={votou ? 'enq-grade votou' : 'enq-grade'}>
                {doBloco.map((u) => {
                  const nome = `Bloco ${u.bloco}, apartamento ${u.apartamento}`
                  return (
                    <li key={u.login}>
                      {eu?.admin ? (
                        <Link to={`/unidades/${u.login}`} aria-label={nome}>
                          {u.apartamento}
                        </Link>
                      ) : (
                        <span aria-label={nome}>{u.apartamento}</span>
                      )}
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </>
      )}
    </section>
  )
}
