// Campos comuns de "Novo aviso" e "Corrigir aviso" (spec dos avisos com formatação, seção 3.4):
// título, categoria, texto com a barra de marcas e "Ver como fica", e "É um evento?".
import { useLayoutEffect, useRef, useState } from 'react'
import { Icone, type NomeDoIcone } from '../casca/Icone'
import { CATEGORIAS } from './categorias'
import { TextoDoAviso } from './componentes'
import { aplicarMarca, type Marca } from './marcas'
import { LIMITE_ONDE, LIMITE_TEXTO, LIMITE_TITULO, type Erros, type Rascunho } from './rascunho'

const BARRA: { marca: Marca; nome: string; icone: NomeDoIcone }[] = [
  { marca: 'titulo', nome: 'Título', icone: 'titulo' },
  { marca: 'negrito', nome: 'Negrito', icone: 'negrito' },
  { marca: 'lista', nome: 'Lista', icone: 'lista' },
  { marca: 'destaque', nome: 'Destaque', icone: 'info' },
]

function ErroDoCampo({ id, mensagem }: { id: string; mensagem?: string }) {
  if (!mensagem) return null
  return (
    <p className="avisos-erro-campo" id={id}>
      {mensagem}
    </p>
  )
}

interface Props {
  rascunho: Rascunho
  erros: Erros
  mudar: (mudanca: Partial<Rascunho>) => void
}

/** "Ver como fica" usa o mesmo renderizador do aviso aberto (`TextoDoAviso`). */
export function CamposDoAviso({ rascunho, erros, mudar }: Props) {
  const campoDoTexto = useRef<HTMLTextAreaElement>(null)
  // Seleção a devolver ao campo depois que a barra mudou o texto.
  const selecao = useRef<{ inicio: number; fim: number } | null>(null)
  const [vendo, setVendo] = useState(false)

  useLayoutEffect(() => {
    const campo = campoDoTexto.current
    if (!campo || !selecao.current) return
    campo.focus()
    campo.setSelectionRange(selecao.current.inicio, selecao.current.fim)
    selecao.current = null
  }, [rascunho.texto])

  // Erro no texto (ao enviar): volta a escrever para a pessoa ver o campo marcado.
  const mostrandoPrevia = vendo && !erros.texto

  function marcar(marca: Marca) {
    const campo = campoDoTexto.current
    if (!campo) return
    const r = aplicarMarca(campo.value, campo.selectionStart, campo.selectionEnd, marca)
    selecao.current = { inicio: r.inicio, fim: r.fim }
    mudar({ texto: r.texto })
  }

  return (
    <>
      <label htmlFor="aviso-titulo">Título</label>
      <input
        id="aviso-titulo"
        type="text"
        value={rascunho.titulo}
        onChange={(e) => mudar({ titulo: e.target.value })}
        maxLength={LIMITE_TITULO}
        aria-invalid={!!erros.titulo}
        aria-describedby={erros.titulo ? 'aviso-titulo-erro' : undefined}
        className={erros.titulo ? 'campo-erro' : undefined}
      />
      <ErroDoCampo id="aviso-titulo-erro" mensagem={erros.titulo} />

      <fieldset className="avisos-categorias">
        <legend>Categoria</legend>
        <div className="categorias-op">
          {CATEGORIAS.map((c) => (
            <label key={c.valor} className={`cat-${c.valor}`}>
              <input
                type="radio"
                name="aviso-categoria"
                value={c.valor}
                checked={rascunho.categoria === c.valor}
                onChange={() => mudar({ categoria: c.valor })}
              />
              <span>
                <Icone nome={c.icone} />
                {c.nome}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="avisos-texto-topo">
        {mostrandoPrevia ? (
          <p className="avisos-rotulo" id="aviso-texto-rotulo">
            Texto do aviso: assim vai ficar
          </p>
        ) : (
          <label htmlFor="aviso-texto" id="aviso-texto-rotulo">
            Texto do aviso
          </label>
        )}
        <button
          type="button"
          className="texto-link avisos-ver"
          aria-pressed={mostrandoPrevia}
          onClick={() => setVendo(!mostrandoPrevia)}
        >
          <Icone nome={mostrandoPrevia ? 'editar' : 'olho'} />
          {mostrandoPrevia ? 'Voltar a escrever' : 'Ver como fica'}
        </button>
      </div>
      {mostrandoPrevia ? (
        <div className="avisos-como-fica" aria-labelledby="aviso-texto-rotulo" role="region">
          {rascunho.texto.trim() ? (
            <TextoDoAviso texto={rascunho.texto} nivel={3} />
          ) : (
            <p className="suave">Ainda não tem texto.</p>
          )}
        </div>
      ) : (
        <>
          <div className="avisos-barra" role="group" aria-label="Formatar o texto">
            {BARRA.map((b) => (
              <button
                key={b.marca}
                type="button"
                className="avisos-marca"
                onClick={() => marcar(b.marca)}
              >
                <Icone nome={b.icone} tamanho={20} />
                {b.nome}
              </button>
            ))}
          </div>
          <textarea
            id="aviso-texto"
            ref={campoDoTexto}
            value={rascunho.texto}
            onChange={(e) => mudar({ texto: e.target.value })}
            maxLength={LIMITE_TEXTO}
            aria-invalid={!!erros.texto}
            aria-describedby={`aviso-texto-ajuda${erros.texto ? ' aviso-texto-erro' : ''}`}
            className={erros.texto ? 'campo-erro' : undefined}
          />
          <p className="ajuda" id="aviso-texto-ajuda">
            Deixe uma linha em branco entre os parágrafos. Se preferir digitar: <b>##</b> no começo
            da linha faz um título, <b>-</b> faz uma lista, <b>&gt;</b> faz um destaque e{' '}
            <b>**assim**</b> fica em negrito. Endereços com https:// viram link.
          </p>
          <ErroDoCampo id="aviso-texto-erro" mensagem={erros.texto} />
        </>
      )}

      <label className="opcao avisos-evento-chave">
        <input
          type="checkbox"
          checked={rascunho.eEvento}
          onChange={(e) => mudar({ eEvento: e.target.checked })}
        />
        É um evento? (reunião, vistoria, mutirão)
      </label>
      {rascunho.eEvento && (
        <fieldset
          className="avisos-evento-campos"
          aria-describedby={erros.evento ? 'aviso-evento-erro' : undefined}
        >
          <legend className="oculto">Quando e onde</legend>
          <div className="avisos-quando">
            <div>
              <label htmlFor="aviso-dia">Dia</label>
              <input
                id="aviso-dia"
                type="date"
                value={rascunho.dia}
                onChange={(e) => mudar({ dia: e.target.value })}
                aria-invalid={!!erros.evento && !rascunho.dia}
                className={erros.evento && !rascunho.dia ? 'campo-erro' : undefined}
              />
            </div>
            <div>
              <label htmlFor="aviso-hora">Hora</label>
              <input
                id="aviso-hora"
                type="time"
                value={rascunho.hora}
                onChange={(e) => mudar({ hora: e.target.value })}
                aria-invalid={!!erros.evento && !rascunho.hora}
                className={erros.evento && !rascunho.hora ? 'campo-erro' : undefined}
              />
            </div>
          </div>
          <ErroDoCampo id="aviso-evento-erro" mensagem={erros.evento} />
          <label htmlFor="aviso-onde">Onde (se quiser)</label>
          <input
            id="aviso-onde"
            type="text"
            value={rascunho.onde}
            onChange={(e) => mudar({ onde: e.target.value })}
            maxLength={LIMITE_ONDE}
            aria-describedby="aviso-onde-ajuda"
          />
          <p className="ajuda" id="aviso-onde-ajuda">
            Ex.: Stand de vendas, na entrada da obra.
          </p>
        </fieldset>
      )}
    </>
  )
}
