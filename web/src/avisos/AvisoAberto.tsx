// H-14 (abrir), H-15 (corrigido, fixar, arquivar) e H-16 (conta como lido ao abrir).
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useRecado } from '../casca/contextoRecado'
import { useSessao } from '../casca/contextoSessao'
import { formatarData } from '../casca/formatar'
import { NaoEncontrado } from '../casca/guardas'
import { Icone } from '../casca/Icone'
import { centralizar } from '../casca/rolar'
import { Tela } from '../casca/Tela'
import { abrirAviso, arquivarAviso, marcarLido, mudarFixado } from './api'
import { comoErroDaApi, useCarga, useIdDoAviso } from './carregar'
import { Carregando, FalhaAoCarregar, TextoDoAviso } from './componentes'
import { assinatura, destinoEmTexto } from './formatos'
import type { AvisoCompleto } from './tipos'
import './avisos.css'

export function PaginaAviso() {
  const id = useIdDoAviso()
  return id === null ? <NaoEncontrado /> : <AvisoAberto key={id} id={id} />
}

function AvisoAberto({ id }: { id: number }) {
  const [carga, recarregar, trocar] = useCarga(() => abrirAviso(id), [id])
  const marcado = useRef(false)

  // H-16: abrir o aviso conta como lido. O GET só lê (contrato); a leitura é um POST à parte.
  useEffect(() => {
    if (carga.situacao !== 'pronta' || marcado.current) return
    marcado.current = true
    // Também quando foi corrigido depois da leitura: tira o selo "Corrigido" (revisão do M1, U1).
    if (!carga.dados.lido || carga.dados.corrigido_desde_a_leitura) marcarLido(id).catch(() => {})
  }, [carga, id])

  if (carga.situacao === 'erro' && carga.erro.status === 404) return <NaoEncontrado />
  return (
    // U9: o assunto do aviso é o h1 e o título da aba.
    <Tela titulo={carga.situacao === 'pronta' ? carga.dados.titulo : 'Aviso'} voltar="/avisos">
      {carga.situacao === 'erro' ? (
        <FalhaAoCarregar mensagem={carga.erro.mensagem} tentar={recarregar} />
      ) : carga.situacao === 'carregando' ? (
        <Carregando />
      ) : (
        <Conteudo aviso={carga.dados} trocar={trocar} />
      )}
    </Tela>
  )
}

function Conteudo({ aviso, trocar }: { aviso: AvisoCompleto; trocar: (a: AvisoCompleto) => void }) {
  const { eu } = useSessao()
  return (
    <article className="aviso-aberto">
      <p className="suave">
        {aviso.fixado && 'Fixado. '}Publicado {assinatura(aviso.publicado_por)} em{' '}
        {formatarData(aviso.publicado_em)}, para {destinoEmTexto(aviso)}.
      </p>
      {aviso.arquivado_em && (
        <div className="aviso-caixa atencao">
          <Icone nome="arquivar" />
          <p>
            Arquivado em {formatarData(aviso.arquivado_em)}. Não aparece mais no mural, mas continua
            guardado em Avisos arquivados.
          </p>
        </div>
      )}
      {aviso.editado_em && (
        <div className="aviso-caixa info">
          <Icone nome="editar" />
          <div className="avisos-versoes">
            <p>Corrigido em {formatarData(aviso.editado_em)}.</p>
            <details>
              <summary>
                {aviso.versoes_anteriores.length > 1
                  ? 'Ver as versões de antes'
                  : 'Ver como era antes'}
              </summary>
              {aviso.versoes_anteriores.map((v) => (
                <section key={v.versao} className="avisos-versao">
                  <p className="suave">
                    {v.versao === 1 ? 'Publicado' : 'Corrigido'} em {formatarData(v.criada_em)}:
                  </p>
                  <h2 className="avisos-versao-titulo">{v.titulo}</h2>
                  <TextoDoAviso texto={v.texto} />
                </section>
              ))}
            </details>
          </div>
        </div>
      )}
      <TextoDoAviso texto={aviso.texto} />
      {eu?.gestao && <ParaAGestao aviso={aviso} trocar={trocar} />}
    </article>
  )
}

function ParaAGestao({
  aviso,
  trocar,
}: {
  aviso: AvisoCompleto
  trocar: (a: AvisoCompleto) => void
}) {
  const recado = useRecado()
  const [confirmando, setConfirmando] = useState(false)
  const blocoDaConfirmacao = useRef<HTMLDivElement>(null)
  // U2 (revisão do M1): a confirmação inteira no meio da tela, longe do recado e das abas.
  useEffect(() => {
    if (confirmando) centralizar(blocoDaConfirmacao.current)
  }, [confirmando])
  const [ocupado, setOcupado] = useState(false)
  const [erro, setErro] = useState('')

  async function agir(acao: () => Promise<AvisoCompleto>, mensagem: string) {
    setOcupado(true)
    setErro('')
    try {
      trocar(await acao())
      setConfirmando(false)
      recado(mensagem)
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
      {aviso.leitura && (
        <Link className="avisos-cartao" to={`/avisos/${aviso.id}/leitura`}>
          <Icone nome="olho" tamanho={28} />
          <span>
            <b>
              {aviso.leitura.lidos} de {aviso.leitura.total} apartamentos leram
            </b>
            <span className="ajuda">Ver quem ainda não leu</span>
          </span>
        </Link>
      )}
      {erro && (
        <div className="aviso-caixa erro" role="alert">
          <Icone nome="alerta" />
          <p>{erro}</p>
        </div>
      )}
      {!aviso.arquivado_em && (
        <div className="avisos-acoes">
          <Link className="botao leve" to={`/avisos/${aviso.id}/corrigir`}>
            <Icone nome="editar" /> Corrigir aviso
          </Link>
          <button
            type="button"
            className="botao leve"
            disabled={ocupado}
            onClick={() =>
              agir(
                () => mudarFixado(aviso.id, !aviso.fixado),
                aviso.fixado ? 'Aviso tirado do topo do mural.' : 'Aviso fixado no topo do mural.',
              )
            }
          >
            <Icone nome="pino" />{' '}
            {aviso.fixado ? 'Tirar do topo do mural' : 'Fixar no topo do mural'}
          </button>
          {confirmando ? (
            <div
              className="aviso-caixa atencao"
              role="group"
              aria-labelledby="confirmar-arquivar"
              ref={blocoDaConfirmacao}
              tabIndex={-1}
            >
              <Icone nome="alerta" />
              <div>
                <p id="confirmar-arquivar">
                  O aviso sai do mural e fica em Avisos arquivados. Não dá para trazer de volta.
                </p>
                <button
                  type="button"
                  className="botao perigo"
                  disabled={ocupado}
                  onClick={() => agir(() => arquivarAviso(aviso.id), 'Aviso arquivado.')}
                >
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
            <button
              type="button"
              className="botao leve"
              disabled={ocupado}
              onClick={() => setConfirmando(true)}
            >
              <Icone nome="arquivar" /> Arquivar
            </button>
          )}
        </div>
      )}
    </section>
  )
}
