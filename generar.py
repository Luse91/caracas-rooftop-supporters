# Genera las imágenes de la placa de Panas del lobby de Caracas Rooftop:
#   panas.png        -> TIRA de nombres que descarga el mundo (la placa la hace bajar sola si no caben)
#   supporters.png   -> placa completa (fondo + PANAS + primeros nombres): vista previa de editar.html
#                       y la imagen que usan las versiones viejas del mundo
#   placa_fondo.png  -> fondo con "PANAS" sin nombres (va metido dentro del mundo, en Unity)
# Entradas: fondo.png (placa vacía 1152x2048), panas.txt (un nombre por línea, # = comentario),
#           Marcellus-Regular.ttf (SIL OFL) y, si está, NotoSansJP.ttf para letras que Marcellus no tiene.
# Uso: python generar.py
#
# La tira: columnas de 1024 px de ancho, una fila de 104 px por nombre, hasta 19 filas por columna y
# 2 columnas (38 nombres). El mundo deduce todo del tamaño de la imagen: columnas = ancho / 1024,
# contenido = columnas x alto. (CR_PlacaSupporters + shader CaracasRooftop/PlacaNombres.)
import math
import os
import sys

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
MARCELLUS = os.path.join(AQUI, "Marcellus-Regular.ttf")
NOTO = os.environ.get("NOTO_JP", os.path.join(AQUI, "NotoSansJP.ttf"))

W, H = 1152, 2048
CX = W // 2
ANCHO_COL = 1024      # ancho de cada columna de la tira (= ancho de la ventana en la placa)
FILA = 104            # alto de cada nombre
FILAS_MAX = 19        # 19 x 104 = 1976 <= 2048
COLS_MAX = 2
VENTANA_X = (W - ANCHO_COL) // 2   # 64
VENTANA_Y = 560       # en la placa, donde empieza la lista
VENTANA_FILAS = 13    # los que caben quietos
TAM = 64
BASE = 74             # línea base del texto dentro de su fila
MARGEN = 60           # aire a los lados del nombre dentro de la columna

ORO_ARRIBA = (252, 228, 192)
ORO_ABAJO = (204, 152, 104)
BRILLO = (235, 165, 95)


def leer_panas():
    with open(os.path.join(AQUI, "panas.txt"), encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]


class Letras:
    """Marcellus para lo latino; Noto Sans JP para lo que Marcellus no tiene (japonés, etc.)."""

    def __init__(self):
        self.mapa_m = TTFont(MARCELLUS).getBestCmap()
        self.mapa_n = TTFont(NOTO).getBestCmap() if os.path.exists(NOTO) else {}
        if not self.mapa_n:
            print("OJO: sin NotoSansJP.ttf; letras que no sean latinas saldrán como cuadritos")
        self.cache = {}

    def fuente(self, c, tam):
        cual = "m" if ord(c) in self.mapa_m or not self.mapa_n or ord(c) not in self.mapa_n else "n"
        clave = (cual, tam)
        if clave not in self.cache:
            if cual == "m":
                self.cache[clave] = ImageFont.truetype(MARCELLUS, tam)
            else:
                f = ImageFont.truetype(NOTO, int(round(tam * 0.82)))
                try:
                    f.set_variation_by_axes([400])
                except Exception:
                    pass
                self.cache[clave] = f
        return self.cache[clave]


def mascara(letras, texto, tam, espaciado, alto, base):
    """Máscara L del texto en una línea, con la línea base en 'base'. Devuelve (máscara, ancho)."""
    def medir(t):
        anchos = [letras.fuente(c, t).getlength(c) for c in texto]
        return anchos, sum(anchos) + t * espaciado * (len(texto) - 1)

    anchos, total = medir(tam)
    m = Image.new("L", (int(total) + 8, alto), 0)
    d = ImageDraw.Draw(m)
    x = 4
    for c, a in zip(texto, anchos):
        d.text((x, base), c, font=letras.fuente(c, tam), fill=255, anchor="ls")
        x += a + tam * espaciado
    return m, total


def dorar(mascara_l, y0, y1, brillo=0.45):
    """RGB sobre negro: halo cálido + relleno dorado degradado entre y0 y y1."""
    w, h = mascara_l.size
    out = Image.new("RGB", (w, h), (0, 0, 0))
    halo = mascara_l.filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * brillo))
    out.paste(Image.new("RGB", (w, h), BRILLO), (0, 0), halo)
    grad = Image.new("RGB", (w, h))
    gd = ImageDraw.Draw(grad)
    for j in range(h):
        t = min(1.0, max(0.0, (j - y0) / max(1, y1 - y0)))
        gd.line([(0, j), (w, j)], fill=tuple(int(a + (b - a) * t) for a, b in zip(ORO_ARRIBA, ORO_ABAJO)))
    out.paste(grad, (0, 0), mascara_l)
    return out


def fila_nombre(letras, nombre):
    """Una fila de la tira (ANCHO_COL x FILA) con el nombre centrado, en dorado sobre negro."""
    tam = TAM
    while True:
        m, ancho = mascara(letras, nombre, tam, 0.04, FILA, BASE)
        if ancho <= ANCHO_COL - 2 * MARGEN or tam <= 36:
            break
        tam -= 2
    fila = Image.new("L", (ANCHO_COL, FILA), 0)
    fila.paste(m, (int((ANCHO_COL - m.width) / 2), 0))
    return dorar(fila, BASE - 0.72 * tam, BASE + 0.2 * tam)


def tira(letras, panas):
    n = len(panas)
    if n > FILAS_MAX * COLS_MAX:
        print(f"OJO: {n} nombres; la placa admite {FILAS_MAX * COLS_MAX}, van los primeros")
        panas = panas[: FILAS_MAX * COLS_MAX]
        n = len(panas)
    cols = max(1, math.ceil(n / FILAS_MAX))
    filas = max(1, math.ceil(n / cols))
    img = Image.new("RGB", (ANCHO_COL * cols, FILA * filas), (0, 0, 0))
    for i, nombre in enumerate(panas):
        img.paste(fila_nombre(letras, nombre), ((i // filas) * ANCHO_COL, (i % filas) * FILA))
    return img, cols, filas


def encabezado(lienzo, letras, texto, y):
    m, _ = mascara(letras, texto, 34, 0.42, 60, 40)
    m = m.crop(m.getbbox())
    w, h = m.size
    x = CX - w // 2
    # sombra suave + texto dorado con halo, como el título de la placa
    sombra = Image.new("L", lienzo.size, 0)
    sombra.paste(m, (x, y + 3))
    sombra = sombra.filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.6))
    lienzo.paste(Image.new("RGB", lienzo.size, (0, 0, 0)), (0, 0), sombra)
    marco = Image.new("L", (w + 80, h + 80), 0)
    marco.paste(m, (40, 40))
    lienzo.paste(ImageChops.add(lienzo.crop((x - 40, y - 40, x + w + 40, y + h + 40)), dorar(marco, 40, 40 + h, 0.3)), (x - 40, y - 40))
    d = ImageDraw.Draw(lienzo)
    yc = y + h // 2
    for lado in (-1, 1):
        borde = x - 58 if lado < 0 else x + w + 58
        d.line([(borde, yc), (borde + lado * 140, yc)], fill=(170, 126, 86), width=2)
        r, rx = 6, borde - lado * 22
        d.polygon([(rx, yc - r), (rx + r, yc), (rx, yc + r), (rx - r, yc)], fill=(214, 170, 120))


def main():
    letras = Letras()
    panas = leer_panas()

    fondo = Image.open(os.path.join(AQUI, "fondo.png")).convert("RGB")
    encabezado(fondo, letras, "PANAS", 486)
    fondo.save(os.path.join(AQUI, "placa_fondo.png"), optimize=True)

    img, cols, filas = tira(letras, panas)
    img.save(os.path.join(AQUI, "panas.png"), optimize=True)

    # vista previa / placa para versiones viejas: los que caben quietos + "+ N MORE"
    placa = fondo.copy()
    for i, nombre in enumerate(panas[:VENTANA_FILAS]):
        caja = (VENTANA_X, VENTANA_Y + i * FILA, VENTANA_X + ANCHO_COL, VENTANA_Y + (i + 1) * FILA)
        placa.paste(ImageChops.add(placa.crop(caja), fila_nombre(letras, nombre)), caja[:2])
    if len(panas) > VENTANA_FILAS:
        resto = f"+ {len(panas) - VENTANA_FILAS} MORE"
        m, _ = mascara(letras, resto, 30, 0.3, 50, 36)
        m = m.crop(m.getbbox())
        y = VENTANA_Y + VENTANA_FILAS * FILA + 14
        caja = (CX - m.width // 2 - 30, y - 30, CX - m.width // 2 + m.width + 30, y + m.height + 30)
        marco = Image.new("L", (caja[2] - caja[0], caja[3] - caja[1]), 0)
        marco.paste(m, (30, 30))
        placa.paste(ImageChops.add(placa.crop(caja), dorar(marco, 30, 30 + m.height, 0.25)), caja[:2])
    placa.save(os.path.join(AQUI, "supporters.png"), optimize=True)

    print(f"{len(panas)} nombre(s): panas.png {img.width}x{img.height} ({cols} col x {filas} filas)")


if __name__ == "__main__":
    sys.exit(main())
