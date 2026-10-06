"""Gera o logo e os ícones do Portal a partir do logo original do Capibaribe Prime Residence.

Os originais (1408x1408, ~1 MB) ficam FORA do repositório. Para refazer:

    uv run --with pillow --with numpy python scripts/dev/gerar-icones.py <logo-com-fundo-branco.jpg>

Por que o JPG com fundo branco, e não o PNG "sem fundo": o recorte do PNG deixou o contorno com
alfa parcial e cor escurecida (as letras ficam sujas sobre fundo escuro). Aqui o alfa sai do
próprio branco ("cor para alfa", como no GIMP): cada pixel vira a cor mais saturada que, sobre
branco, dá exatamente o pixel original. Funciona sobre qualquer fundo.

Saídas (caminhos relativos à raiz do repositório):
  web/src/marca/logo.webp, logo@2x.webp   logo inteiro, recortado justo (1x e 2x)
  web/public/favicon.ico                  só a espiral, fundo transparente (16, 32, 48)
  web/public/apple-touch-icon.png         espiral sobre o papel, 180
  web/public/icon-192.png, icon-512.png   espiral sobre o papel (prontos para o PWA do M2)
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
MARCA = RAIZ / "web/src/marca"
PUBLICO = RAIZ / "web/public"

# --papel do estilo.css: o fundo dos ícones de tela inicial.
PAPEL = (0xF4, 0xF6, 0xF2, 255)
# Abaixo disso é ruído do JPG no branco (99,9% do fundo fica abaixo de 32 na distância ao branco).
LIMIAR_RUIDO = 24
# Largura do logo na tela (px CSS); o 2x serve as telas de alta densidade.
LARGURA_LOGO = 260
# A espiral ocupa as linhas acima de "CAPIBARIBE" no original.
FIM_DA_ESPIRAL = 600


def cor_para_alfa(rgb: np.ndarray) -> Image.Image:
    """Tira o branco: alfa = quanto o pixel se afasta do branco; cor = a que, sobre branco, dá o pixel."""
    c = rgb.astype(np.float64)
    distancia = (255.0 - c).max(axis=2)
    alfa = np.clip((distancia - LIMIAR_RUIDO) / (255.0 - LIMIAR_RUIDO), 0.0, 1.0)
    a_bruto = np.maximum(distancia / 255.0, 1e-6)[..., None]
    cor = 255.0 - (255.0 - c) / a_bruto
    cor = np.clip(cor, 0, 255)
    rgba = np.dstack([cor, alfa * 255.0]).round().astype(np.uint8)
    rgba[alfa == 0] = 0
    return Image.fromarray(rgba, "RGBA")


def justo(imagem: Image.Image) -> Image.Image:
    caixa = imagem.getchannel("A").getbbox()
    assert caixa, "imagem vazia"
    return imagem.crop(caixa)


def reduzir(imagem: Image.Image, largura: int) -> Image.Image:
    """Reduz com alfa pré-multiplicado (sem halo claro na borda)."""
    altura = round(imagem.height * largura / imagem.width)
    return imagem.convert("RGBa").resize((largura, altura), Image.Resampling.LANCZOS).convert("RGBA")


def quadrado(espiral: Image.Image, lado: int, ocupacao: float, fundo=(0, 0, 0, 0)) -> Image.Image:
    """A espiral centrada num quadrado, ocupando `ocupacao` da largura (o resto é respiro)."""
    pequena = reduzir(espiral, round(lado * ocupacao))
    tela = Image.new("RGBA", (lado, lado), fundo)
    tela.alpha_composite(pequena, ((lado - pequena.width) // 2, (lado - pequena.height) // 2))
    return tela


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    original = np.asarray(Image.open(sys.argv[1]).convert("RGB"))
    logo = justo(cor_para_alfa(original))
    espiral = justo(cor_para_alfa(original[:FIM_DA_ESPIRAL]))

    MARCA.mkdir(parents=True, exist_ok=True)
    for sufixo, fator in (("", 1), ("@2x", 2)):
        reduzir(logo, LARGURA_LOGO * fator).save(
            MARCA / f"logo{sufixo}.webp", "WEBP", quality=88, alpha_quality=90, method=6
        )

    # Favicon: pouco respiro, para a espiral não sumir em 16 px.
    # Cada tamanho reduzido aqui (alfa pré-multiplicado), não pelo gravador de ICO.
    tamanhos = [quadrado(espiral, lado, 0.96) for lado in (48, 32, 16)]
    tamanhos[0].save(
        PUBLICO / "favicon.ico",
        sizes=[(t.width, t.height) for t in tamanhos],
        append_images=tamanhos[1:],
    )

    # Tela inicial: o iOS arredonda os cantos; o Android (maskable) corta num círculo de 80%.
    quadrado(espiral, 180, 0.76, PAPEL).convert("RGB").save(
        PUBLICO / "apple-touch-icon.png", optimize=True
    )
    for lado in (192, 512):
        quadrado(espiral, lado, 0.72, PAPEL).convert("RGB").save(
            PUBLICO / f"icon-{lado}.png", optimize=True
        )

    for arquivo in sorted({*MARCA.glob("logo*.webp"), *PUBLICO.glob("*icon*")}):
        print(f"{arquivo.relative_to(RAIZ)}: {arquivo.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
