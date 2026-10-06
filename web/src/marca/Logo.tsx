// O logo do Capibaribe Prime Residence (gerado por scripts/dev/gerar-icones.py). Servido pelo
// próprio Portal (a CSP só aceita imagem da mesma origem) e com tamanho reservado, para a tela
// não pular quando a imagem chega. Só sobre fundo claro: no tema escuro vai num cartão claro.
import logo1x from './logo.webp'
import logo2x from './logo@2x.webp'
import './marca.css'

export function Logo({ pequeno }: { pequeno?: boolean }) {
  return (
    <span className={pequeno ? 'logo pequeno' : 'logo'}>
      <img
        src={logo1x}
        srcSet={`${logo1x} 1x, ${logo2x} 2x`}
        width={260}
        height={185}
        alt="Capibaribe Prime Residence"
      />
    </span>
  )
}
