// H-07 · Painel de ativação (como `telaAdmin` do protótipo). Pertence ao épico B.
// Grade: os 64 apartamentos de cada bloco, do 7º andar ao térreo (já entrou = verde, papel de
// gestão = faixa amarela). Lista: responsável, celular e data do primeiro acesso, com filtro.
import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ErroDaApi } from '../api/cliente'
import { Icone } from '../casca/Icone'
import { Placa } from '../casca/Placa'
import { Tela } from '../casca/Tela'
import { useSessao } from '../casca/contextoSessao'
import { formatarCelular, formatarData, nomeDoPapel } from '../casca/formatar'
import './administracao.css'
import { buscarPainel } from './api'
import type { PainelAtivacao, ResumoBloco, Situacao, UnidadePainel } from './tipos'

type Modo = 'grade' | 'lista'

const FILTROS: [Situacao, string][] = [
  ['todas', 'Todas'],
  ['ativadas', 'Já entraram'],
  ['nao_ativadas', 'Ainda não'],
  ['gestao', 'Com papel'],
]

type Estado =
  | { situacao: 'carregando' }
  | { situacao: 'erro'; mensagem: string }
  | { situacao: 'pronto'; painel: PainelAtivacao; de: Situacao }

export function Painel() {
  const [modo, setModo] = useState<Modo>('grade')
  const [filtro, setFiltro] = useState<Situacao>('todas')
  const [estado, setEstado] = useState<Estado>({ situacao: 'carregando' })
  const [tentativa, setTentativa] = useState(0)
  // A Comissão lê o painel; o histórico é só do administrador.
  const admin = useSessao().eu?.admin ?? false
  // A grade mostra sempre o prédio inteiro; o filtro vale para a lista.
  const situacao: Situacao = modo === 'grade' ? 'todas' : filtro

  useEffect(() => {
    let vale = true
    buscarPainel(situacao).then(
      (painel) => vale && setEstado({ situacao: 'pronto', painel, de: situacao }),
      (erro: unknown) =>
        vale &&
        setEstado({
          situacao: 'erro',
          mensagem: erro instanceof ErroDaApi ? erro.mensagem : 'Não deu para abrir o painel.',
        }),
    )
    return () => {
      vale = false
    }
  }, [situacao, tentativa])

  return (
    <Tela titulo="Unidades">
      {estado.situacao === 'carregando' && (
        <p className="vazio" role="status">
          Abrindo o painel…
        </p>
      )}
      {estado.situacao === 'erro' && (
        <>
          <div className="aviso-caixa erro" role="alert">
            <p>{estado.mensagem}</p>
          </div>
          <button type="button" className="botao" onClick={() => setTentativa((n) => n + 1)}>
            Tentar de novo
          </button>
        </>
      )}
      {estado.situacao === 'pronto' && (
        <Conteudo
          painel={estado.painel}
          modo={modo}
          filtro={filtro}
          listado={estado.de}
          aoMudarModo={setModo}
          aoMudarFiltro={setFiltro}
        />
      )}
      {admin && (
        <div className="carregar-mais">
          <Link className="botao leve" to="/historico">
            <Icone nome="relogio" /> Histórico de ações
          </Link>
        </div>
      )}
    </Tela>
  )
}

interface PropsConteudo {
  painel: PainelAtivacao
  modo: Modo
  filtro: Situacao
  /** O filtro com que a lista na tela foi buscada (o novo pode estar a caminho). */
  listado: Situacao
  aoMudarModo: (modo: Modo) => void
  aoMudarFiltro: (filtro: Situacao) => void
}

function Conteudo({ painel, modo, filtro, listado, aoMudarModo, aoMudarFiltro }: PropsConteudo) {
  const { resumo } = painel
  return (
    <>
      <div className="resumo">
        <div>
          <b>{resumo.ativadas}</b>já entraram
        </div>
        <div>
          <b>{resumo.total - resumo.ativadas}</b>ainda não
        </div>
        <div>
          <b>{resumo.percentual}%</b>adesão
        </div>
      </div>

      <div className="admin-controles">
        <div className="chips" role="group" aria-label="Mostrar como">
          {(
            [
              ['grade', 'Grade'],
              ['lista', 'Lista com contatos'],
            ] as const
          ).map(([valor, texto]) => (
            <button
              key={valor}
              type="button"
              className="chip"
              aria-pressed={modo === valor}
              onClick={() => aoMudarModo(valor)}
            >
              {texto}
            </button>
          ))}
        </div>
        {modo === 'lista' && (
          <div className="chips" role="group" aria-label="Quais apartamentos">
            {FILTROS.map(([valor, texto]) => (
              <button
                key={valor}
                type="button"
                className="chip"
                aria-pressed={filtro === valor}
                onClick={() => aoMudarFiltro(valor)}
              >
                {texto}
              </button>
            ))}
          </div>
        )}
      </div>

      {modo === 'grade' && (
        <div className="legenda">
          <span>
            <i className="at" />
            já entrou
          </span>
          <span>
            <i />
            ainda não
          </span>
          <span>
            <i className="ge" />
            Comissão ou administrador
          </span>
        </div>
      )}

      {modo === 'grade' ? (
        <Grade painel={painel} />
      ) : (
        <Lista painel={painel} filtro={listado} />
      )}
    </>
  )
}

function tituloDoBloco(bloco: ResumoBloco): string {
  return `${bloco.nome}: ${bloco.ativadas} de ${bloco.total} (${bloco.percentual}%)`
}

function doBloco(painel: PainelAtivacao, numero: number): UnidadePainel[] {
  return painel.unidades.filter((u) => u.unidade.bloco === numero)
}

function Grade({ painel }: { painel: PainelAtivacao }) {
  return (
    <>
      {painel.blocos.map((bloco) => {
        // Do 7º andar ao térreo, como o prédio visto de frente.
        const unidades = doBloco(painel, bloco.numero).sort(
          (a, b) => b.andar - a.andar || a.unidade.login.localeCompare(b.unidade.login),
        )
        return (
          <section key={bloco.numero} aria-label={bloco.nome}>
            <p className="secao">{tituloDoBloco(bloco)}</p>
            <div className="grade">
              {unidades.map((u) => {
                const classes = [u.ativada && 'at', u.papeis.length > 0 && 'ge']
                  .filter(Boolean)
                  .join(' ')
                const papel = u.papeis.length ? `, ${u.papeis.map(nomeDoPapel).join(' e ')}` : ''
                return (
                  <Link
                    key={u.unidade.login}
                    to={`/unidades/${u.unidade.login}`}
                    className={classes || undefined}
                    aria-label={`Apartamento ${u.unidade.apartamento}, ${u.ativada ? 'já entrou' : 'ainda não entrou'}${papel}`}
                  >
                    {u.unidade.apartamento}
                  </Link>
                )
              })}
            </div>
          </section>
        )
      })}
    </>
  )
}

const VAZIO: Record<Situacao, string> = {
  todas: 'Nenhum apartamento cadastrado.',
  ativadas: 'Nenhum apartamento entrou no Portal ainda.',
  nao_ativadas: 'Todos os apartamentos já entraram no Portal.',
  gestao: 'Nenhum apartamento tem papel de gestão.',
}

function Lista({ painel, filtro }: { painel: PainelAtivacao; filtro: Situacao }) {
  if (painel.unidades.length === 0) return <p className="vazio">{VAZIO[filtro]}</p>
  return (
    <>
      {painel.blocos.map((bloco) => {
        const unidades = doBloco(painel, bloco.numero)
        if (unidades.length === 0) return null
        return (
          <section key={bloco.numero} aria-label={bloco.nome}>
            <p className="secao">{tituloDoBloco(bloco)}</p>
            <div className="folha">
              {unidades.map((u) => (
                <LinhaUnidade key={u.unidade.login} unidade={u} />
              ))}
            </div>
          </section>
        )
      })}
    </>
  )
}

function LinhaUnidade({ unidade: u }: { unidade: UnidadePainel }) {
  return (
    <Link className="item unidade-linha" to={`/unidades/${u.unidade.login}`}>
      <Placa unidade={u.unidade} gestao={u.papeis.length > 0} />
      <h3>{u.ativada ? (u.responsavel_nome ?? 'Responsável não informado') : 'Ainda não entrou'}</h3>
      <span className="linha-meta">
        {u.celular && <span>{formatarCelular(u.celular)}</span>}
        {u.ativada_em && <span>entrou em {formatarData(u.ativada_em)}</span>}
        {u.papeis.map((p) => (
          <span key={p} className="selo">
            {nomeDoPapel(p)}
          </span>
        ))}
      </span>
      <span className="seta" aria-hidden="true">
        <Icone nome="seta" />
      </span>
    </Link>
  )
}
