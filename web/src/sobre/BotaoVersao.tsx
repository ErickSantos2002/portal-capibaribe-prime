// "Versão 1.1.0": um botão discreto que abre a janela com o que mudou no Portal. Fica no rodapé
// da entrada, no pé do menu lateral (computador) e no fim de Minha unidade (celular).
import { useEffect, useId, useRef, useState } from 'react'
import { Logo } from '../marca/Logo'
import { NOVIDADES, VERSAO, formatarDataDaVersao } from './novidades'
import './sobre.css'

export function BotaoVersao({ className }: { className?: string }) {
  const [aberta, setAberta] = useState(false)
  const botao = useRef<HTMLButtonElement>(null)

  return (
    <>
      <button
        ref={botao}
        type="button"
        className={className ? `versao-btn ${className}` : 'versao-btn'}
        aria-haspopup="dialog"
        onClick={() => setAberta(true)}
      >
        Versão {VERSAO}
      </button>
      {aberta && (
        <JanelaDeVersao
          aoFechar={() => {
            setAberta(false)
            // O botão de origem recebe o foco de volta (o navegador também faz, mas a janela
            // sai do DOM ao fechar: garantimos aqui).
            botao.current?.focus()
          }}
        />
      )}
    </>
  )
}

/**
 * `<dialog>` nativo aberto com showModal(): o resto da tela fica inerte (o Tab não sai da
 * janela), Esc fecha, e o fundo escurecido também. Toda forma de fechar passa pelo evento
 * `close`, que chama `aoFechar` uma vez.
 */
function JanelaDeVersao({ aoFechar }: { aoFechar: () => void }) {
  const janela = useRef<HTMLDialogElement>(null)
  const idTitulo = useId()
  const idMudou = useId()

  useEffect(() => {
    const dialogo = janela.current
    // O StrictMode monta duas vezes: abrir só se ainda não estiver aberta.
    if (dialogo && !dialogo.open) dialogo.showModal()
  }, [])

  return (
    <dialog
      ref={janela}
      className="janela"
      aria-modal="true"
      aria-labelledby={idTitulo}
      onClose={aoFechar}
      onClick={(evento) => {
        // O clique cai no próprio <dialog> só fora da caixa (no fundo escurecido).
        if (evento.target === evento.currentTarget) evento.currentTarget.close()
      }}
    >
      <div className="janela-caixa">
        <header className="janela-topo">
          <Logo pequeno />
          <h2 id={idTitulo}>Versão {VERSAO}</h2>
          <p className="suave">do Portal Capibaribe Prime</p>
        </header>
        {/* Rola sozinha no celular; com tabIndex, o teclado também rola. */}
        <section className="janela-rolagem" tabIndex={0} aria-labelledby={idMudou}>
          <h3 id={idMudou}>O que mudou</h3>
          <ol className="novidades">
            {NOVIDADES.map((novidade) => (
              <li key={novidade.versao}>
                <h4>
                  {novidade.versao}
                  {novidade.nome && <span className="novidades-nome"> {novidade.nome}</span>}
                </h4>
                <time dateTime={novidade.data}>{formatarDataDaVersao(novidade.data)}</time>
                <ul>
                  {novidade.itens.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </section>
        <div className="janela-pe">
          <button type="button" className="botao" onClick={() => janela.current?.close()}>
            Fechar
          </button>
        </div>
      </div>
    </dialog>
  )
}
