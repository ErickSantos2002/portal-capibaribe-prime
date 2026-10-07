// "Receber os avisos" (H-05; protótipo `#instalar`; spec m2-push.md, seção 3.2): a oferta única
// depois do primeiro acesso, e o passo a passo de instalar, que Minha unidade também abre.
// Recusar não atrapalha nada: "Ir para o mural" está sempre lá.
import { useEffect, useState, useSyncExternalStore } from 'react'
import { Link, useLocation } from 'react-router'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import {
  acompanharInstalacao,
  ehSafariDoIphone,
  instalado,
  pedirInstalacao,
  plataforma,
  podeInstalar,
} from './aparelho'
import { ControleNotificacoes } from './ControleNotificacoes'
import { marcarOfertaVista } from './ganchos'
import { useNotificacoes } from './useNotificacoes'
import './notificacoes.css'

export function ReceberAvisos() {
  const local = useLocation()
  const estado = local.state as { de?: unknown; ativado?: unknown } | null
  const deMinhaUnidade = estado?.de === 'minha-unidade'
  // Vindo do primeiro acesso: o "ativado" entra no texto (o recado flutuante cobria a pergunta).
  const ativado = estado?.ativado === true
  const n = useNotificacoes()
  // Uma vez por aparelho: daqui em diante, o primeiro acesso (se houver de novo) vai ao mural.
  useEffect(() => marcarOfertaVista(), [])
  const celular = plataforma() !== 'computador'

  return (
    <Tela titulo="Receber os avisos" voltar={deMinhaUnidade ? '/minha-unidade' : undefined}>
      {ativado && (
        <p className="notif-situacao ligada notif-ativado">
          <Icone nome="certo" />
          <span>Pronto, o apartamento está ativado.</span>
        </p>
      )}
      <h2>Quer ser avisado na hora?</h2>
      <p>
        Dois passos, uma vez só. Dá para fazer depois em <b>Minha unidade</b>.
      </p>

      <section className="folha notif-cartao" aria-labelledby="notif-instalar">
        <h3 id="notif-instalar" className="com-icone">
          <Icone nome={celular ? 'celular' : 'monitor'} />
          {celular ? 'Coloque o Portal na tela inicial' : 'Coloque o Portal no computador'}
        </h3>
        <p className="ajuda">Ele abre como um aplicativo, direto pelo ícone.</p>
        <Instalar />
      </section>

      {n.situacao !== 'desligado' && (
        <section className="folha notif-cartao" aria-labelledby="notif-ativar">
          <h3 id="notif-ativar" className="com-icone">
            <Icone nome="sino" />
            Ative as notificações
          </h3>
          <p className="ajuda">Só quando sair aviso oficial do condomínio.</p>
          <ControleNotificacoes n={n} />
        </section>
      )}

      <Link className="botao notif-mural" to="/avisos">
        Ir para o mural
      </Link>
    </Tela>
  )
}

function Instalar() {
  const pode = useSyncExternalStore(acompanharInstalacao, podeInstalar)
  const [resultado, setResultado] = useState<'aceitou' | 'recusou' | null>(null)

  if (instalado()) {
    return (
      <p className="notif-situacao ligada">
        <Icone nome="certo" />
        <span>Pronto: o Portal já está na tela inicial.</span>
      </p>
    )
  }
  if (resultado === 'aceitou') {
    return (
      <p className="notif-situacao ligada" role="status">
        <Icone nome="certo" />
        <span>Instalado. Procure o ícone Capibaribe na tela inicial.</span>
      </p>
    )
  }
  if (pode) {
    return (
      <button
        type="button"
        className="botao leve"
        onClick={() =>
          void pedirInstalacao().then((r) => setResultado(r === 'aceitou' ? 'aceitou' : 'recusou'))
        }
      >
        Instalar na tela inicial
      </button>
    )
  }
  if (plataforma() === 'iphone') {
    return (
      <>
        {/* `role="list"`: o Safari tira a semântica de lista com `list-style: none`. */}
        <ol className="notif-passos" role="list">
          <li>
            Toque em <b>Compartilhar</b> (o quadrado com a seta para cima). Se não aparecer, toque
            antes nos três pontinhos <b>•••</b>.
          </li>
          <li>
            Role a lista e toque em <b>Adicionar à Tela de Início</b>.
          </li>
          <li>
            Toque em <b>Adicionar</b>, no canto de cima.
          </li>
          <li>
            Abra o Portal pelo ícone novo, Capibaribe. Se pedir, entre de novo com bloco,
            apartamento e senha.
          </li>
          <li>
            Lá dentro, toque em <b>Ativar notificações</b>.
          </li>
        </ol>
        <p className="aviso-caixa atencao notif-iphone">
          No iPhone, as notificações só chegam se o Portal for aberto pelo ícone.
        </p>
        {!ehSafariDoIphone() && (
          <p className="ajuda">Se não achar a opção, abra este endereço no Safari.</p>
        )}
      </>
    )
  }
  if (plataforma() === 'android') {
    return (
      <p className="notif-dica">
        Toque nos três pontinhos ⋮ do navegador (no Samsung, nas três linhas ☰, embaixo) e
        escolha <b>Instalar aplicativo</b> ou <b>Adicionar à tela inicial</b>.
        {resultado === 'recusou' && ' Ou deixe para depois: tudo funciona pelo navegador.'}
      </p>
    )
  }
  return (
    <p className="notif-dica">
      No Chrome ou no Edge, o Portal vira uma janela própria: clique no ícone de tela com seta, no
      fim da barra de endereço. No Firefox não dá para instalar, mas tudo funciona pelo navegador.
    </p>
  )
}
