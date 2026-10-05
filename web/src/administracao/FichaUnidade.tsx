// H-08 · Resetar e H-09 · Papel de Comissão: a ficha de uma unidade (como `telaUnidade` do
// protótipo). Pertence ao épico B.
//
// O que é perigoso (resetar, mexer no papel de administrador) pede confirmação no lugar, em cima
// das opções, dizendo o que vai acontecer. Dar ou tirar o papel de Comissão é direto, como no
// protótipo, e o recado confirma.
import { useEffect, useRef, useState, type RefObject } from 'react'
import { useParams } from 'react-router'
import { ErroDaApi } from '../api/cliente'
import { Icone } from '../casca/Icone'
import { Placa } from '../casca/Placa'
import { Tela } from '../casca/Tela'
import { useRecado } from '../casca/contextoRecado'
import { useSessao } from '../casca/contextoSessao'
import {
  formatarCelular,
  formatarDataEHora,
  nomeDaUnidade,
  nomeDoPapel,
} from '../casca/formatar'
import './administracao.css'
import { buscarUnidade, darPapel, resetarUnidade, retirarPapel } from './api'
import type { PapelGerenciavel, UnidadeAdmin } from './tipos'

type Pendente =
  | { tipo: 'resetar' }
  | { tipo: 'dar' | 'tirar'; papel: PapelGerenciavel }

type Estado =
  | { situacao: 'carregando' }
  | { situacao: 'erro'; mensagem: string; naoExiste: boolean }
  | { situacao: 'pronto'; unidade: UnidadeAdmin }

function mensagemDe(erro: unknown): string {
  return erro instanceof ErroDaApi ? erro.mensagem : 'Algo deu errado. Tente de novo.'
}

export function FichaUnidade() {
  const { login = '' } = useParams()
  const [estado, setEstado] = useState<Estado>({ situacao: 'carregando' })

  useEffect(() => {
    let vale = true
    buscarUnidade(login).then(
      (unidade) => vale && setEstado({ situacao: 'pronto', unidade }),
      (erro: unknown) =>
        vale &&
        setEstado({
          situacao: 'erro',
          mensagem: mensagemDe(erro),
          naoExiste: erro instanceof ErroDaApi && erro.status === 404,
        }),
    )
    return () => {
      vale = false
    }
  }, [login])

  return (
    <Tela titulo="Unidade" voltar="/unidades">
      {estado.situacao === 'carregando' && (
        <p className="vazio" role="status">
          Abrindo a unidade…
        </p>
      )}
      {estado.situacao === 'erro' && (
        <div className={`aviso-caixa ${estado.naoExiste ? 'atencao' : 'erro'}`} role="alert">
          <p>{estado.mensagem}</p>
        </div>
      )}
      {estado.situacao === 'pronto' && (
        <Ficha
          key={estado.unidade.unidade.login}
          unidade={estado.unidade}
          aoMudar={(unidade) => setEstado({ situacao: 'pronto', unidade })}
        />
      )}
    </Tela>
  )
}

interface PropsFicha {
  unidade: UnidadeAdmin
  aoMudar: (unidade: UnidadeAdmin) => void
}

function Ficha({ unidade: u, aoMudar }: PropsFicha) {
  const { eu, recarregar } = useSessao()
  const recado = useRecado()
  const [pendente, setPendente] = useState<Pendente | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')
  const confirmacao = useRef<HTMLHeadingElement>(null)
  const propria = eu?.unidade.login === u.unidade.login
  const nome = nomeDaUnidade(u.unidade)
  const temComissao = u.papeis.includes('comissao')
  const temAdmin = u.papeis.includes('admin')
  const bloqueada = !!u.bloqueada_ate && new Date(u.bloqueada_ate) > new Date()

  useEffect(() => {
    if (pendente) confirmacao.current?.focus()
  }, [pendente])

  async function executar(acao: Pendente) {
    setOcupado(true)
    setErro('')
    try {
      let nova: UnidadeAdmin
      let texto: string
      if (acao.tipo === 'resetar') {
        nova = await resetarUnidade(u.unidade.login)
        texto = `${nome} resetado. A senha voltou a ser a inicial.`
      } else if (acao.tipo === 'dar') {
        nova = await darPapel(u.unidade.login, acao.papel)
        texto =
          acao.papel === 'comissao'
            ? `Agora o ${nome} é da Comissão.`
            : `Agora o ${nome} também administra o Portal.`
      } else {
        nova = await retirarPapel(u.unidade.login, acao.papel)
        texto =
          acao.papel === 'comissao'
            ? 'Papel de Comissão retirado. As opções somem na hora.'
            : 'Papel de administrador retirado.'
      }
      setPendente(null)
      aoMudar(nova)
      recado(texto)
      // Mexeu na própria unidade (reset ou o próprio papel): a sessão muda junto, e as guardas
      // levam para onde couber (entrar, ou "sem permissão").
      if (propria) await recarregar()
    } catch (falha) {
      setErro(mensagemDe(falha))
    } finally {
      setOcupado(false)
    }
  }

  function pedir(acao: Pendente) {
    setErro('')
    // Comissão é direto; reset e administrador pedem confirmação.
    if (acao.tipo !== 'resetar' && acao.papel === 'comissao') void executar(acao)
    else setPendente(acao)
  }

  return (
    <>
      <div className="centro">
        <Placa unidade={u.unidade} grande gestao={u.papeis.length > 0} />
      </div>
      <dl className="ficha">
        <div>
          <dt>Situação</dt>
          <dd>{u.ativada ? 'Já entrou' : 'Ainda não entrou'}</dd>
        </div>
        {u.ativada_em && (
          <div>
            <dt>Primeiro acesso</dt>
            <dd>{formatarDataEHora(u.ativada_em)}</dd>
          </div>
        )}
        {u.ativada && (
          <>
            <div>
              <dt>Responsável</dt>
              <dd>{u.responsavel_nome}</dd>
            </div>
            <div>
              <dt>Celular</dt>
              <dd>
                {u.celular && <a href={`tel:+55${u.celular}`}>{formatarCelular(u.celular)}</a>}
              </dd>
            </div>
            <div>
              <dt>E-mail</dt>
              <dd>{u.email ?? 'não informado'}</dd>
            </div>
          </>
        )}
        <div>
          <dt>Papel</dt>
          <dd>{u.papeis.length ? u.papeis.map(nomeDoPapel).join(' e ') : 'Apartamento comum'}</dd>
        </div>
        <div>
          <dt>Aparelhos conectados</dt>
          <dd>{u.aparelhos_conectados}</dd>
        </div>
        {bloqueada && u.bloqueada_ate && (
          <div>
            <dt>Entrada bloqueada até</dt>
            <dd>{formatarDataEHora(u.bloqueada_ate)}</dd>
          </div>
        )}
      </dl>

      {erro && (
        <div className="aviso-caixa erro" role="alert">
          <Icone nome="alerta" />
          <p>{erro}</p>
        </div>
      )}

      {pendente && (
        <Confirmacao
          acao={pendente}
          nome={nome}
          propria={propria}
          ocupado={ocupado}
          titulo={confirmacao}
          aoConfirmar={() => void executar(pendente)}
          aoCancelar={() => setPendente(null)}
        />
      )}

      {!pendente && (
        <div className="acoes-admin">
          <p className="secao">Resetar</p>
          <p className="ajuda">
            Resetar volta a senha para a inicial, apaga os contatos, desconecta os aparelhos e
            tira o papel de gestão. As leituras e os votos continuam.
            {!u.ativada && ' Também tira o bloqueio de senhas erradas.'}
          </p>
          <button
            type="button"
            className="botao perigo"
            disabled={ocupado}
            onClick={() => pedir({ tipo: 'resetar' })}
          >
            Resetar este apartamento
          </button>

          <p className="secao">Papel de gestão</p>
          {!u.ativada && !u.papeis.length ? (
            <div className="aviso-caixa info">
              <Icone nome="info" />
              <p>Só dá para dar papel a um apartamento que já entrou no Portal.</p>
            </div>
          ) : (
            <>
              <button
                type="button"
                className="botao leve"
                disabled={ocupado}
                onClick={() =>
                  pedir({ tipo: temComissao ? 'tirar' : 'dar', papel: 'comissao' })
                }
              >
                {temComissao ? 'Tirar papel de Comissão' : 'Dar papel de Comissão'}
              </button>
              <button
                type="button"
                className="botao leve"
                disabled={ocupado}
                onClick={() => pedir({ tipo: temAdmin ? 'tirar' : 'dar', papel: 'admin' })}
              >
                {temAdmin ? 'Tirar papel de administrador' : 'Dar papel de administrador'}
              </button>
            </>
          )}
        </div>
      )}
    </>
  )
}

interface PropsConfirmacao {
  acao: Pendente
  nome: string
  propria: boolean
  ocupado: boolean
  titulo: RefObject<HTMLHeadingElement | null>
  aoConfirmar: () => void
  aoCancelar: () => void
}

function Confirmacao({
  acao,
  nome,
  propria,
  ocupado,
  titulo,
  aoConfirmar,
  aoCancelar,
}: PropsConfirmacao) {
  let pergunta: string
  let efeitos: string[]
  let botao: string
  if (acao.tipo === 'resetar') {
    pergunta = `Resetar o ${nome}?`
    efeitos = [
      'A senha volta a ser a inicial (mudar123).',
      'Nome, celular e e-mail são apagados.',
      'Todos os aparelhos são desconectados.',
      'O papel de gestão, se houver, é retirado.',
      'O apartamento volta a "ainda não entrou".',
      'Leituras e votos continuam valendo. O reset fica no histórico.',
    ]
    if (propria) efeitos.push('É o seu apartamento: você sai do Portal neste aparelho.')
    botao = 'Sim, resetar'
  } else if (acao.tipo === 'dar') {
    pergunta = `Dar papel de administrador ao ${nome}?`
    efeitos = [
      'Ele vê o painel de unidades, os contatos e o histórico.',
      'Ele pode resetar apartamentos e dar ou tirar papéis, inclusive o seu.',
      'Fica registrado no histórico.',
    ]
    botao = 'Sim, dar o papel'
  } else {
    pergunta = `Tirar o papel de administrador do ${nome}?`
    efeitos = [
      'Ele deixa de ver o painel de unidades e o histórico na hora.',
      'Fica registrado no histórico.',
    ]
    if (propria) efeitos.push('É o seu apartamento: você perde o acesso a esta tela.')
    botao = 'Sim, tirar o papel'
  }
  return (
    <section className="confirmacao" aria-labelledby="confirmacao-titulo">
      <h2 id="confirmacao-titulo" ref={titulo} tabIndex={-1}>
        {pergunta}
      </h2>
      <ul>
        {efeitos.map((efeito) => (
          <li key={efeito}>{efeito}</li>
        ))}
      </ul>
      <div className="acoes-admin">
        <button type="button" className="botao perigo" disabled={ocupado} onClick={aoConfirmar}>
          {ocupado ? 'Aguarde…' : botao}
        </button>
        <button type="button" className="botao leve" disabled={ocupado} onClick={aoCancelar}>
          Cancelar
        </button>
      </div>
    </section>
  )
}
