// Épico A do M3 · o campo "Arquivo" de "Novo documento" e "Enviar nova versão": um botão grande
// que abre os arquivos do aparelho e, depois de escolher, o nome e o tamanho do que vai.
import { ACEITAR } from '../arquivos/limites'
import { tamanhoEmTexto } from './formatos'
import { IconeDoc } from './pecas'

interface Props {
  id: string
  arquivo: File | null
  erro?: string
  escolher: (arquivo: File | null) => void
}

export function EscolherArquivo({ id, arquivo, erro, escolher }: Props) {
  const ajuda = `${id}-ajuda`
  const idDoErro = `${id}-erro`
  return (
    <div className="doc-arquivo-campo">
      <p className="doc-rotulo" id={`${id}-rotulo`}>
        Arquivo
      </p>
      {arquivo && (
        <p className="doc-escolhido" aria-live="polite">
          <IconeDoc nome="clipe" />
          <span>
            <b>{arquivo.name}</b>
            <span className="suave">{tamanhoEmTexto(arquivo.size)}</span>
          </span>
        </p>
      )}
      {/* O input fica escondido só para os olhos: o teclado e o leitor de tela chegam nele, e o
          rótulo grande é o alvo do toque. */}
      <label className={`botao leve doc-escolher${erro ? ' campo-erro' : ''}`}>
        <input
          id={id}
          type="file"
          accept={ACEITAR}
          className="oculto"
          aria-describedby={erro ? `${idDoErro} ${ajuda}` : ajuda}
          aria-invalid={!!erro}
          onChange={(e) => {
            escolher(e.target.files?.[0] ?? null)
            // Escolher o mesmo arquivo de novo (depois de um erro) também conta.
            e.target.value = ''
          }}
        />
        <IconeDoc nome="clipe" />
        {arquivo ? 'Escolher outro arquivo (PDF ou foto)' : 'Escolher PDF ou foto'}
      </label>
      {erro && (
        <p className="doc-erro-campo" id={idDoErro}>
          {erro}
        </p>
      )}
      <p className="ajuda" id={ajuda}>
        PDF ou foto, até 20 MB. Foto grande é reduzida antes de enviar.
      </p>
    </div>
  )
}
