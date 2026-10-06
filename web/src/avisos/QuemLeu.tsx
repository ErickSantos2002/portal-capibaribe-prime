// H-16 · Saber quem leu: "X leram, Y ainda não" e os apartamentos que não leram, por bloco.
import { Link } from 'react-router'
import { useRecado } from '../casca/contextoRecado'
import { useSessao } from '../casca/contextoSessao'
import { NaoEncontrado } from '../casca/guardas'
import { Tela } from '../casca/Tela'
import type { UnidadeRef } from '../api/tipos'
import { abrirAviso, buscarLeitura } from './api'
import { useCarga, useIdDoAviso } from './carregar'
import { Carregando, FalhaAoCarregar } from './componentes'
import { listaParaCopiar, ordemDaGrade } from './formatos'
import type { Leitura } from './tipos'
import './avisos.css'

export function PaginaQuemLeu() {
  const id = useIdDoAviso()
  return id === null ? <NaoEncontrado /> : <QuemLeu key={id} id={id} />
}

function QuemLeu({ id }: { id: number }) {
  const [carga, recarregar] = useCarga(() => Promise.all([abrirAviso(id), buscarLeitura(id)]), [id])
  if (carga.situacao === 'erro' && carga.erro.status === 404) return <NaoEncontrado />
  return (
    <Tela titulo="Quem leu" voltar={`/avisos/${id}`}>
      {carga.situacao === 'erro' ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : carga.situacao === 'carregando' ? (
        <Carregando />
      ) : (
        <Conteudo titulo={carga.dados[0].titulo} leitura={carga.dados[1]} />
      )}
    </Tela>
  )
}

function porBloco(unidades: UnidadeRef[]): [number, UnidadeRef[]][] {
  const grupos = new Map<number, UnidadeRef[]>()
  for (const u of ordemDaGrade(unidades)) grupos.set(u.bloco, [...(grupos.get(u.bloco) ?? []), u])
  return [...grupos]
}

interface PropsConteudo {
  titulo: string
  leitura: Leitura
}

function Conteudo({ titulo, leitura }: PropsConteudo) {
  const recado = useRecado()
  const faltam = leitura.total - leitura.lidos

  async function copiar() {
    try {
      await navigator.clipboard.writeText(
        listaParaCopiar(titulo, leitura.nao_entraram, leitura.entraram_sem_ler),
      )
      recado('Lista copiada. Dá para colar no grupo.')
    } catch {
      recado('Não deu para copiar. Selecione os apartamentos e copie à mão.')
    }
  }

  return (
    <>
      <p className="suave avisos-quem-leu-aviso">
        Aviso: <b>{titulo}</b>
      </p>
      {/* U5: números em texto corrido, sem cara de botão. */}
      <p className="avisos-contagem">
        <b>
          {leitura.lidos} {leitura.lidos === 1 ? 'leu' : 'leram'}
        </b>{' '}
        · {faltam} ainda não
      </p>
      <p className="ajuda">
        Contam todos os apartamentos do destino, inclusive os que ainda não entraram no Portal.
      </p>
      {faltam === 0 ? (
        <div className="aviso-caixa info">
          <p>Todos os apartamentos do destino já leram.</p>
        </div>
      ) : (
        <>
          <button type="button" className="botao leve avisos-copiar" onClick={() => void copiar()}>
            Copiar a lista
          </button>
          <Grupo
            id="nao-entraram"
            titulo="Ainda não entrou no Portal"
            ajuda="Não fizeram o primeiro acesso: precisam da senha inicial e do endereço do Portal."
            unidades={leitura.nao_entraram}
          />
          <Grupo
            id="entraram-sem-ler"
            titulo="Entrou, mas não leu este aviso"
            ajuda="Já usam o Portal: basta lembrar de abrir o aviso."
            unidades={leitura.entraram_sem_ler}
          />
        </>
      )}
    </>
  )
}

function Grupo(props: { id: string; titulo: string; ajuda: string; unidades: UnidadeRef[] }) {
  const { eu } = useSessao()
  const { id, titulo, ajuda, unidades } = props
  return (
    <section aria-labelledby={id}>
      <h2 className="secao" id={id}>
        {titulo} ({unidades.length})
      </h2>
      {unidades.length === 0 ? (
        <p className="ajuda">Nenhum apartamento.</p>
      ) : (
        <>
          <p className="ajuda">{ajuda}</p>
          {porBloco(unidades).map(([bloco, doBloco]) => (
            <section key={bloco} aria-labelledby={`${id}-${bloco}`}>
              <h3 className="avisos-bloco" id={`${id}-${bloco}`}>
                Bloco {bloco}
              </h3>
              <ul className="grade avisos-grade">
                {doBloco.map((u) => (
                  <li key={u.login}>
                    {eu?.admin ? (
                      <Link
                        to={`/unidades/${u.login}`}
                        aria-label={`Bloco ${u.bloco}, apartamento ${u.apartamento}`}
                      >
                        {u.apartamento}
                      </Link>
                    ) : (
                      <span aria-label={`Bloco ${u.bloco}, apartamento ${u.apartamento}`}>
                        {u.apartamento}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </>
      )}
    </section>
  )
}
