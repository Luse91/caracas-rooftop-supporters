# Genera supporters.png (placa del lobby de Caracas Rooftop) a partir de:
#   fondo.png     -> placa vacía 1152x2048 ("OUR SUPPORTERS", Ávila y sol)
#   panas.txt     -> un nombre por línea (las líneas con # se ignoran)
#   Marcellus-Regular.ttf (SIL OFL, ver OFL.txt)
# Uso: python generar.py
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(AQUI, "Marcellus-Regular.ttf")
W, H = 1152, 2048
CX = W // 2

ORO_ARRIBA = (252, 228, 192)
ORO_ABAJO = (204, 152, 104)
BRILLO = (235, 165, 95)


def leer_panas():
    with open(os.path.join(AQUI, "panas.txt"), encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]


def mascara_texto(texto, tam, espaciado=0.0):
    """Máscara L del texto (con espaciado entre letras en fracción del tamaño)."""
    f = ImageFont.truetype(FUENTE, tam)
    extra = int(round(tam * espaciado))
    anchos = [f.getlength(c) for c in texto]
    ancho = int(sum(anchos) + extra * (len(texto) - 1)) + 4
    asc, desc = f.getmetrics()
    m = Image.new("L", (ancho, asc + desc + 4), 0)
    d = ImageDraw.Draw(m)
    x = 2
    for c, a in zip(texto, anchos):
        d.text((x, 2), c, font=f, fill=255)
        x += a + extra
    return m.crop(m.getbbox())


def pegar_oro(lienzo, mascara, cx, y, brillo=0.45):
    """Pega la máscara centrada en cx con relleno degradado dorado, sombra y halo."""
    w, h = mascara.size
    x = int(cx - w / 2)
    pad = 40
    # halo cálido
    halo = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    halo.paste(mascara, (pad, pad))
    halo = halo.filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * brillo))
    lienzo.paste(Image.new("RGB", halo.size, BRILLO), (x - pad, y - pad), halo)
    # sombra
    sombra = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    sombra.paste(mascara, (pad, pad + 3))
    sombra = sombra.filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.6))
    lienzo.paste(Image.new("RGB", sombra.size, (0, 0, 0)), (x - pad, y - pad), sombra)
    # relleno dorado (degradado vertical)
    grad = Image.new("RGB", (w, h))
    gd = ImageDraw.Draw(grad)
    for j in range(h):
        t = j / max(1, h - 1)
        gd.line([(0, j), (w, j)], fill=tuple(int(a + (b - a) * t) for a, b in zip(ORO_ARRIBA, ORO_ABAJO)))
    lienzo.paste(grad, (x, y), mascara)
    return x, w, h


def encabezado(lienzo, texto, y):
    m = mascara_texto(texto, 34, espaciado=0.42)
    x, w, h = pegar_oro(lienzo, m, CX, y, brillo=0.3)
    # rayitas y rombos a los lados
    d = ImageDraw.Draw(lienzo)
    yc = y + h // 2
    for lado in (-1, 1):
        borde = x - 58 if lado < 0 else x + w + 58
        fin = borde + lado * 140
        d.line([(borde, yc), (fin, yc)], fill=(170, 126, 86), width=2)
        r = 6
        rx = borde - lado * 22
        d.polygon([(rx, yc - r), (rx + r, yc), (rx, yc + r), (rx - r, yc)], fill=(214, 170, 120))
    return y + h


def main():
    lienzo = Image.open(os.path.join(AQUI, "fondo.png")).convert("RGB")
    panas = leer_panas()
    y = encabezado(lienzo, "PANAS", 486)
    y += 78
    # una columna; si no caben, dos columnas con letra más chica
    tam, paso = 64, 104
    if len(panas) > 13:
        tam, paso = 50, 82
    filas = 13 if tam == 64 else 17
    columnas = [panas[:filas], panas[filas:filas * 2]] if len(panas) > filas else [panas]
    centros = [CX] if len(columnas) == 1 else [CX - 250, CX + 250]
    for col, cx in zip(columnas, centros):
        yy = y
        for nombre in col:
            pegar_oro(lienzo, mascara_texto(nombre, tam, espaciado=0.04), cx, yy)
            yy += paso
    if len(panas) > filas * 2:
        print(f"OJO: {len(panas)} nombres, solo caben {filas * 2}")
    lienzo.save(os.path.join(AQUI, "supporters.png"), optimize=True)
    print("supporters.png:", len(panas), "nombre(s)")


if __name__ == "__main__":
    main()
