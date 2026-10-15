// H-21 · votar e trocar o voto (vale o último); H-22 · resultado e participação. Para a gestão:
// "Quais apartamentos votaram" e, enquanto ninguém votou, "Editar a enquete" (épico A).
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import type { Eu } from '../../api/tipos'
import { comoErroDaApi, useCarga } from '../../avisos/carregar'
import { Carregando, FalhaAoCarregar } from '../../avisos/componentes'
import { blocosEmTexto } from '../../avisos/formatos'
import { useSessao } from '../../casca/contextoSessao'
import { Icone } from '../../casca/Icone'
import { Tela } from '../../casca/Tela'
import { abrirEnquete, votar } from '../api'
import { CAMINHO_ENQUETES, caminhoEditarEnquete, caminhoVotantes } from '../caminhos'
import type { Enquete } from '../tipos'
import { participacaoEmTexto, porcentagem, quandoTermina, votosEmTexto } from './formatos'
import { useIdDaEnquete } from './useIdDaEnquete'
import './enquetes.css'

/** Link quebrado, enquete que não existe ou que é de outro bloco: a mesma tela. */
export function EnqueteNaoEncontrada({ mensagem }: { mensagem?: string }) {
  return (
    <Tela titulo="Enquete não encontrada" voltar={CAMINHO_ENQUETES}>
      <div className="aviso-caixa atencao" role="alert">
        <Icone nome="alerta" />
        <p>
          {mensagem ??
            'Não achamos esta enquete. O link pode estar incompleto, ou ela é de outro bloco.'}
        </p>
      </div>
      <Link className="botao" to={CAMINHO_ENQUETES}>
        Ir para as enquetes
      </Link>
    </Tela>
  )
}

export function PaginaEnquete() {
  const id = useIdDaEnquete()
  return id === null ? <EnqueteNaoEncontrada /> : <EnqueteAberta key={id} id={id} />
}

function EnqueteAberta({ id }: { id: number }) {
  const { eu } = useSessao()
  const [carga, recarregar, trocar] = useCarga(() => abrirEnquete(id), [id])

  // Revisão, ponto 5: a tela parada (celular no bolso) não sabe do voto trocado no outro
  // aparelho. Ao voltar para ela, busca a enquete de novo.
  useEffect(() => {
    function aoVoltar() {
      if (document.visibilityState === 'visible') recarregar()
    }
    document.addEventListener('visibilitychange', aoVoltar)
    return () => document.removeEventListener('visibilitychange', aoVoltar)
  }, [recarregar])

  // 422 é id fora do que o banco guarda: para quem abriu o link, é a mesma enquete que não existe.
  if (carga.situacao === 'erro' && [404, 422].includes(carga.erro.status)) {
    return <EnqueteNaoEncontrada mensagem={carga.erro.mensagem} />
  }
  // Enquanto recarrega (depois de "a enquete mudou"), a tela de antes continua, com o erro.
  const enquete = carga.dados
  return (
    <Tela titulo="Enquete" voltar={CAMINHO_ENQUETES}>
      {carga.situacao === 'erro' && !enquete ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : !enquete || !eu ? (
        <Carregando />
      ) : (
        <Conteudo enquete={enquete} eu={eu} trocar={trocar} recarregar={recarregar} />
      )}
    </Tela>
  )
}

function juntar(itens: string[]): string {
  if (itens.length < 2) return itens.join('')
  return `${itens.slice(0, -1).join(', ')} e ${itens[itens.length - 1]}`
}

/** Os textos das opções marcadas, na ordem da enquete. */
function textosDoVoto(enquete: Enquete): string {
  return juntar(enquete.opcoes.filter((o) => enquete.meu_voto.includes(o.id)).map((o) => o.texto))
}

interface PropsConteudo {
  enquete: Enquete
  eu: Eu
  trocar: (e: Enquete) => void
  recarregar: () => void
}

function Conteudo({ enquete, eu, trocar, recarregar }: PropsConteudo) {
  const final = quandoTermina(enquete.encerra_em)
  return (
    <article className="enq-aberta">
      <h2 className="enq-pergunta">{enquete.pergunta}</h2>
      {enquete.encerrada ? (
        <>
          <div className="aviso-caixa info">
            <Icone nome="relogio" />
            <p>Terminou em {final}. O resultado não muda mais.</p>
          </div>
          {enquete.meu_voto.length > 0 && (
            <p className="suave">Seu apartamento votou em {textosDoVoto(enquete)}.</p>
          )}
        </>
      ) : enquete.pode_votar ? (
        <>
          <p className="suave">
            O voto vale pelo apartamento {eu.unidade.apartamento} do Bloco {eu.unidade.bloco}. Dá
            para trocar até {final}.
          </p>
          <FormularioDoVoto enquete={enquete} trocar={trocar} recarregar={recarregar} />
        </>
      ) : (
        <div className="aviso-caixa info">
          <Icone nome="info" />
          <p>
            Esta enquete é para o {blocosEmTexto(enquete.blocos)}. Seu apartamento não vota nela.
          </p>
        </div>
      )}
      <Resultado enquete={enquete} />
      <p className="ajuda enq-consulta">
        Enquete é consulta. Não tem valor legal de votação em assembleia.
      </p>
      {eu.gestao && <ParaAGestao enquete={enquete} />}
    </article>
  )
}

function FormularioDoVoto({ enquete, trocar, recarregar }: Omit<PropsConteudo, 'eu'>) {
  const [escolha, setEscolha] = useState<number[]>(enquete.meu_voto)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const [acabouDeVotar, setAcabouDeVotar] = useState(false)
  const [mudouEmOutroAparelho, setMudouEmOutroAparelho] = useState(false)
  // Para onde o foco vai depois de votar: a confirmação ou o erro. `vez` faz o mesmo alvo
  // receber o foco de novo (dois erros iguais seguidos).
  const [foco, setFoco] = useState<{ alvo: 'confirmacao' | 'erro'; vez: number } | null>(null)
  const confirmacao = useRef<HTMLElement>(null)
  const alerta = useRef<HTMLDivElement>(null)
  const jaVotou = enquete.meu_voto.length > 0
  const mesma =
    escolha.length === enquete.meu_voto.length && escolha.every((o) => enquete.meu_voto.includes(o))
  const tipo = enquete.multipla_escolha ? 'checkbox' : 'radio'

  // O voto gravado mudou sem ter sido por este formulário (outro celular da mesma unidade):
  // a escolha acompanha, para o botão não "trocar" para o que já está gravado, e a tela avisa.
  const chave = enquete.meu_voto.join(',')
  const [vistoPorUltimo, setVistoPorUltimo] = useState(chave)
  if (chave !== vistoPorUltimo) {
    setVistoPorUltimo(chave)
    setEscolha(enquete.meu_voto)
    setAcabouDeVotar(false)
    setMudouEmOutroAparelho(true)
  }

  useEffect(() => {
    if (foco?.alvo === 'confirmacao') confirmacao.current?.focus()
    if (foco?.alvo === 'erro') alerta.current?.focus()
  }, [foco])

  function marcar(opcao: number, marcada: boolean) {
    setErro('')
    setMudouEmOutroAparelho(false)
    if (!enquete.multipla_escolha) setEscolha([opcao])
    else setEscolha((antes) => (marcada ? [...antes, opcao] : antes.filter((o) => o !== opcao)))
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault()
    if (escolha.length === 0 || mesma || enviando) return
    setEnviando(true)
    setErro('')
    // Revisão, ponto 4: o "Voto registrado." de antes não fica ao lado do erro desta troca.
    setAcabouDeVotar(false)
    setMudouEmOutroAparelho(false)
    const ordem = enquete.opcoes.map((o) => o.id).filter((o) => escolha.includes(o))
    try {
      const nova = await votar(enquete.id, { opcoes: ordem })
      setEscolha(nova.meu_voto)
      setVistoPorUltimo(nova.meu_voto.join(','))
      setAcabouDeVotar(true)
      setFoco((f) => ({ alvo: 'confirmacao', vez: (f?.vez ?? 0) + 1 }))
      trocar(nova)
    } catch (e) {
      const falha = comoErroDaApi(e)
      setErro(falha.mensagem)
      setFoco((f) => ({ alvo: 'erro', vez: (f?.vez ?? 0) + 1 }))
      // A enquete mudou (ou terminou) desde que a tela abriu: mostra a de agora.
      if (['enquete_mudou', 'enquete_encerrada', 'voto_mudou_agora'].includes(falha.codigo)) {
        if (falha.codigo === 'enquete_mudou') setEscolha([])
        recarregar()
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <>
      {mudouEmOutroAparelho && (
        <div className="aviso-caixa atencao enq-mudou">
          <Icone nome="info" />
          <p>O voto do seu apartamento foi trocado em outro aparelho.</p>
        </div>
      )}
      {jaVotou && (
        <section
          className="aviso-caixa info enq-confirmacao"
          aria-label="Seu voto"
          tabIndex={-1}
          ref={confirmacao}
        >
          <Icone nome="certo" />
          <p>
            {acabouDeVotar && 'Voto registrado. '}Seu apartamento já votou em{' '}
            <b>{textosDoVoto(enquete)}</b>. Se escolher outra, vale a nova.
          </p>
        </section>
      )}
      <form className="enq-voto" onSubmit={(e) => void enviar(e)}>
        <fieldset>
          <legend className="enq-legenda">
            {enquete.multipla_escolha ? 'Pode marcar mais de uma.' : 'Escolha uma opção.'}
          </legend>
          {enquete.opcoes.map((o) => (
            <label key={o.id} className="enq-opcao">
              <input
                type={tipo}
                name="opcao"
                value={o.id}
                checked={escolha.includes(o.id)}
                onChange={(e) => marcar(o.id, e.target.checked)}
              />
              <span>{o.texto}</span>
            </label>
          ))}
        </fieldset>
        {erro && (
          <div className="aviso-caixa erro" role="alert" tabIndex={-1} ref={alerta}>
            <Icone nome="alerta" />
            <p>{erro}</p>
          </div>
        )}
        <button
          className="botao enq-votar"
          type="submit"
          disabled={escolha.length === 0 || mesma || enviando}
        >
          {enviando ? 'Gravando o voto…' : jaVotou ? 'Trocar voto' : 'Votar'}
        </button>
        {/* O botão parado precisa dizer por quê: a pessoa não fica tocando sem resposta. */}
        {!enviando && (escolha.length === 0 || mesma) && (
          <p className="ajuda enq-dica">
            {jaVotou && escolha.length > 0
              ? 'Para trocar o voto, escolha outra opção.'
              : enquete.multipla_escolha
                ? 'Marque pelo menos uma opção para votar.'
                : 'Escolha uma opção para votar.'}
          </p>
        )}
      </form>
    </>
  )
}

function Resultado({ enquete }: { enquete: Enquete }) {
  const titulo = enquete.encerrada || !enquete.resultado_visivel ? 'Resultado' : 'Como está até agora'
  const votaram = enquete.participacao.votaram
  // A maior contagem ganha a barra em destaque quando a enquete termina (empate: todas).
  const maior = Math.max(0, ...enquete.opcoes.map((o) => o.votos ?? 0))
  return (
    <section className="enq-resultado" aria-labelledby="enq-resultado">
      <h2 className="secao" id="enq-resultado">
        {titulo}
      </h2>
      {enquete.resultado_visivel ? (
        <ul className="enq-barras" role="list">
          {enquete.opcoes.map((o) => {
            const votos = o.votos ?? 0
            // Porcentagem dos apartamentos que votaram (na múltipla escolha, a soma passa de 100).
            const pct = porcentagem(votos, votaram)
            const destaque = enquete.encerrada && votos > 0 && votos === maior
            return (
              <li key={o.id} className={destaque ? 'enq-barra mais-votada' : 'enq-barra'}>
                <div className="enq-barra-topo">
                  <span>
                    {o.texto}
                    {enquete.meu_voto.includes(o.id) && <span className="enq-seu"> seu voto</span>}
                  </span>
                  <b>
                    {votosEmTexto(votos)}, {pct}%
                  </b>
                </div>
                <div
                  className="enq-trilho"
                  role="meter"
                  aria-label={o.texto}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={pct}
                  aria-valuetext={`${pct}%`}
                >
                  <span style={{ width: `${pct}%` }} />
                </div>
              </li>
            )
          })}
        </ul>
      ) : (
        <p>
          O resultado aparece quando a enquete terminar, em {quandoTermina(enquete.encerra_em)}.
          Até lá, ninguém vê os votos, nem a Comissão.
        </p>
      )}
      <p className="ajuda">{participacaoEmTexto(enquete.participacao)}</p>
    </section>
  )
}

function ParaAGestao({ enquete }: { enquete: Enquete }) {
  return (
    <section className="enq-gestao" aria-labelledby="enq-gestao">
      <h2 className="secao" id="enq-gestao">
        Para a Comissão
      </h2>
      {/* Revisão, ponto 1: no "durante" aberto, a lista de quem votou, cruzada com a contagem
          ao vivo, diria em quê cada apartamento votou. A API também recusa. */}
      {enquete.mostrar_resultado === 'durante' && !enquete.encerrada ? (
        <div className="aviso-caixa info">
          <Icone nome="cadeado" />
          <p>
            Nesta enquete o resultado aparece durante a votação, então a lista de quem votou só
            aparece quando ela terminar. Para acompanhar quem falta durante a votação, crie a
            enquete com o resultado “só no fim”.
          </p>
        </div>
      ) : (
        <Link className="enq-cartao" to={caminhoVotantes(enquete.id)}>
          <Icone nome="enquetes" tamanho={28} />
          <span>
            <b>Quais apartamentos votaram</b>
            <span className="ajuda">Sem mostrar o voto de ninguém</span>
          </span>
          <Icone nome="seta" />
        </Link>
      )}
      {enquete.pode_editar && (
        <Link className="enq-cartao" to={caminhoEditarEnquete(enquete.id)}>
          <Icone nome="editar" tamanho={28} />
          <span>
            <b>Editar a enquete</b>
            <span className="ajuda">Só enquanto ninguém votou</span>
          </span>
          <Icone nome="seta" />
        </Link>
      )}
    </section>
  )
}
