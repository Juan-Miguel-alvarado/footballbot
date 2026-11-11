"""Herramientas de dibujo para las tarjetas: fuentes, colores, logo, texto.

Funciones puras con Pillow: no descargan nada. Todo el "estilo" (colores, fuentes, logo) está
aquí arriba, en un solo lugar: si quieres cambiar el look de todas las tarjetas, empieza aquí.

Estilo "Cancha índigo" (el del logo y el cartel del bot): fondo índigo profundo como una cancha
de noche, líneas de tiza blanca, un solo acento lavanda (el color del logo), esquinas
redondeadas y la figura del logo (assets/figure.png) como marca. La decoración son trazos de
tiza: líneas de cancha muy tenues y flechas curvas como las del cartel.

Fuentes (carpeta fonts/, licencia OFL = libres de usar y redistribuir):
- Inter: todo (títulos en Bold/ExtraBold, texto y números). Moderna y muy legible.
- Oswald: queda solo para los números grandes del marcador (alta y condensada).
Las dos son "variables": un solo archivo trae todos los pesos (Regular, SemiBold, Bold...).
"""

import io
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
FONT_FILES = {"text": "Inter.ttf", "title": "Inter.ttf", "score": "Oswald.ttf"}
LOGO_FILE = Path(__file__).resolve().parent / "assets" / "figure.png"

RGB = tuple[int, int, int]

# --- paleta (sacada del logo y del cartel del bot) ---------------------------------------------
# Los nombres vienen del estilo anterior: BLACK es el fondo de las tarjetas y BLUE el acento.
BLACK: RGB = (25, 29, 50)  # índigo noche: el fondo de todas las tarjetas
PANEL: RGB = (35, 41, 68)  # filas y paneles, un poco más claros
LINE: RGB = (58, 66, 102)  # líneas finas y bordes
BLUE: RGB = (124, 138, 206)  # lavanda: el color de la figura del logo (el acento)
BLUE_DEEP: RGB = (86, 99, 162)  # lavanda oscuro (bloques, el 2º del podio)
LAVENDER: RGB = (229, 232, 245)  # el fondo del icono del bot (fichas claras)
TEXT: RGB = (238, 240, 249)  # tiza
MUTED: RGB = (156, 164, 198)  # texto secundario
WIN: RGB = BLUE
DRAW: RGB = (92, 100, 134)
LOSS: RGB = (226, 106, 118)  # coral: solo para perder y descender
RADIUS = 14  # esquinas redondeadas de paneles y fichas


@lru_cache(maxsize=64)
def font(kind: str, size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont:
    """Fuente `kind` ("text" o "title") en ese tamaño y peso. Se guarda en caché."""
    loaded = ImageFont.truetype(str(FONTS_DIR / FONT_FILES[kind]), size)
    loaded.set_variation_by_name(weight)
    return loaded


def hex_rgb(value: int) -> RGB:
    """0x3D195B -> (61, 25, 91)."""
    return ((value >> 16) & 255, (value >> 8) & 255, value & 255)


def fit_font(
    text: str, kind: str, weight: str, max_size: int, max_width: int, min_size: int = 12
) -> ImageFont.FreeTypeFont:
    """La fuente más grande (hasta `max_size`) con la que `text` cabe en `max_width` píxeles."""
    size = max_size
    while size > min_size and font(kind, size, weight).getlength(text) > max_width:
        size -= 2
    return font(kind, size, weight)


def truncate(text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Corta el texto con "…" si no cabe en `max_width`."""
    if fnt.getlength(text) <= max_width:
        return text
    while text and fnt.getlength(text + "…") > max_width:
        text = text[:-1]
    return text.rstrip() + "…"


def load_icon(data: bytes | None, size: int) -> Image.Image | None:
    """Escudo/logo cuadrado de `size` px con su transparencia, o None si no hay imagen."""
    if not data:
        return None
    try:
        image = Image.open(io.BytesIO(data)).convert("RGBA")
    except OSError:  # no es una imagen válida
        return None
    scale = size / max(image.size)
    image = image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(image, ((size - image.width) // 2, (size - image.height) // 2), image)
    return canvas


def paste_icon(
    canvas: Image.Image, icon: Image.Image | None, center: tuple[int, int], shadow: bool = False
) -> None:
    """Pega un icono centrado en `center`. Con `shadow`, le pone una sombra suave debajo."""
    if icon is None:
        return
    x = center[0] - icon.width // 2
    y = center[1] - icon.height // 2
    if shadow:
        alpha = icon.getchannel("A").filter(ImageFilter.GaussianBlur(icon.width // 14 or 1))
        dark = Image.new("RGBA", icon.size, (0, 0, 0, 0))
        dark.putalpha(alpha.point(lambda a: a * 0.6))
        canvas.paste(dark, (x + icon.width // 30, y + icon.width // 20), dark)
    canvas.paste(icon, (x, y), icon)


def to_png(image: Image.Image, keep_alpha: bool = False) -> bytes:
    """La imagen como PNG. Las tarjetas van sin transparencia; `keep_alpha` la conserva."""
    output = io.BytesIO()
    image.convert("RGBA" if keep_alpha else "RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


# Colores para los avatares sin foto: tonos del logo, distintos para cada jugador
AVATAR_FILLS: tuple[RGB, ...] = (
    (124, 138, 206),
    (86, 99, 162),
    (104, 128, 190),
    (140, 128, 200),
    (96, 140, 186),
    (110, 112, 176),
)


def avatar_fill(name: str) -> RGB:
    """Siempre el mismo color para el mismo nombre (así cada jugador se reconoce)."""
    return AVATAR_FILLS[sum(name.encode()) % len(AVATAR_FILLS)]


def avatar(
    data: bytes | None, size: int, name: str = "?", fill: RGB = (88, 101, 242)
) -> Image.Image:
    """Avatar redondo de `size` px. Sin imagen, un círculo de color con la inicial del nombre."""
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)  # borde suave

    picture: Image.Image | None = None
    if data:
        try:
            picture = (
                Image.open(io.BytesIO(data))
                .convert("RGBA")
                .resize((size, size), Image.Resampling.LANCZOS)
            )
        except OSError:
            picture = None
    if picture is None:
        picture = Image.new("RGBA", (size, size), (*fill, 255))
        initial = (name.strip()[:1] or "?").upper()
        ImageDraw.Draw(picture).text(
            (size // 2, size // 2), initial, font=font("title", size // 2, "Bold"),
            fill=TEXT, anchor="mm",
        )  # fmt: skip
    picture.putalpha(mask)
    return picture


# --- el logo del bot ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _logo_rgba() -> Image.Image:
    """La figura del logo (el jugador pateando) en blanco, con fondo transparente."""
    return Image.open(LOGO_FILE).convert("RGBA")


def logo(size: int, opacity: float = 1.0, color: RGB = TEXT) -> Image.Image:
    """La figura del logo de `size` px de alto, del color `color`, con fondo transparente."""
    image = _logo_rgba()
    width = round(image.width * size / image.height)
    alpha = image.getchannel("A").resize((width, size), Image.Resampling.LANCZOS)
    if opacity < 1:
        alpha = alpha.point(lambda a: round(a * opacity))
    out = Image.new("RGBA", (width, size), (*color, 255))
    out.putalpha(alpha)
    return out


def shards(width: int, opacity: float = 1.0, color: RGB = TEXT) -> Image.Image:
    """Una flecha curva de tiza, como la del cartel del bot: sube desde abajo a la derecha y
    apunta hacia la izquierda.

    Se llama "shards" por el estilo anterior (los fragmentos del balón): las tarjetas la usan
    igual, para señalar al escudo o al ganador. Se dibuja a 3x y se reduce: queda suave.
    """
    k = 3
    w, h = width * k, round(width * 0.95) * k
    stroke = max(5, width // 8) * k
    layer = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(layer)
    start, control, end = (w * 0.78, h * 0.92), (w * 0.78, h * 0.22), (w * 0.2, h * 0.24)

    def point(t: float) -> tuple[float, float]:
        # Curva de Bézier cuadrática: de `start` a `end`, tirada hacia `control`
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1]
        return x, y

    def dot(x: float, y: float) -> None:
        r = stroke / 2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=255)

    points = [point(i / 40) for i in range(41)]
    draw.line(points, fill=255, width=stroke, joint="curve")
    dot(*start)
    # La punta: dos trazos hacia atrás, a 40 grados de la dirección final de la curva
    direction = math.atan2(end[1] - control[1], end[0] - control[0])
    for turn in (math.radians(140), math.radians(-140)):
        angle = direction + turn
        tip = (end[0] + w * 0.22 * math.cos(angle), end[1] + w * 0.22 * math.sin(angle))
        draw.line((end, tip), fill=255, width=stroke)
        dot(*tip)
    dot(*end)
    alpha = layer.resize((width, h // k), Image.Resampling.LANCZOS)
    if opacity < 1:
        alpha = alpha.point(lambda a: round(a * opacity))
    out = Image.new("RGBA", alpha.size, (*color, 255))
    out.putalpha(alpha)
    return out.crop(out.getbbox())


def paste(canvas: Image.Image, image: Image.Image, xy: tuple[int, int]) -> None:
    """Pega una imagen con transparencia (se puede salir del borde: se recorta sola)."""
    canvas.alpha_composite(image, dest=(max(0, xy[0]), max(0, xy[1])),
                           source=(max(0, -xy[0]), max(0, -xy[1])))  # fmt: skip


def hex_texture(canvas: Image.Image, box: tuple[int, int, int, int], size: int = 34) -> None:
    """Textura de fondo dentro de `box`: líneas de cancha de tiza muy tenues y un poco de grano.

    Se llama "hex" por el estilo anterior (los hexágonos del balón). `size` ya no se usa.
    """
    left, top, right, bottom = box
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    chalk = (*TEXT, 22)
    # Media cancha vista desde arriba: la línea del medio y el círculo central a la derecha
    mid = right - (bottom - top) * 0.9
    draw.line((mid, top, mid, bottom), fill=chalk, width=3)
    r = (bottom - top) * 0.62
    cy = (top + bottom) / 2
    draw.ellipse((mid - r, cy - r, mid + r, cy + r), outline=chalk, width=3)
    draw.rectangle((left + 1, top + 1, right - 2, bottom - 2), outline=(*TEXT, 12), width=2)
    canvas.alpha_composite(layer)
    _grain(canvas, box)


def _grain(canvas: Image.Image, box: tuple[int, int, int, int], amount: int = 10) -> None:
    """Un poco de grano de papel dentro de `box` (como la textura del cartel)."""
    width, height = box[2] - box[0], box[3] - box[1]
    if width <= 0 or height <= 0:
        return
    noise = Image.effect_noise((width, height), 64).point(lambda v: abs(v - 128) // 4)
    alpha = noise.point(lambda v: min(amount, v))
    layer = Image.new("RGBA", (width, height), (*TEXT, 255))
    layer.putalpha(alpha)
    canvas.alpha_composite(layer, (box[0], box[1]))


def icon(side: int) -> Image.Image:
    """El icono del bot: la figura lavanda sobre una ficha clara con esquinas redondeadas
    (el mismo que el avatar del bot en Discord)."""
    k = 3
    tile_img = Image.new("RGBA", (side * k, side * k), (0, 0, 0, 0))
    ImageDraw.Draw(tile_img).rounded_rectangle(
        (0, 0, side * k - 1, side * k - 1), radius=side * k // 4, fill=(*LAVENDER, 255)
    )
    tile_img = tile_img.resize((side, side), Image.Resampling.LANCZOS)
    figure = logo(round(side * 0.68), color=BLUE_DEEP)
    tile_img.alpha_composite(figure, ((side - figure.width) // 2, (side - figure.height) // 2))
    return tile_img


def brand(canvas: Image.Image, right: int, top: int, size: int = 64) -> None:
    """El icono del bot con su borde derecho en `right`, como la marca de un canal de TV."""
    side = round(size * 0.82)
    paste(canvas, icon(side), (right - side, top + (size - side) // 2))


def rounded(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    fill: RGB | None = None,
    outline: RGB | None = None,
    width: int = 1,
    radius: int = RADIUS,
) -> None:
    """Un rectángulo con las esquinas redondeadas del estilo (paneles, fichas, barras)."""
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def outline_icon(icon: Image.Image, stroke: int) -> Image.Image:
    """Añade un borde claro y suave que sigue la forma de la imagen (efecto sticker).

    El borde sale de desenfocar la transparencia y volver a endurecerla: así queda redondeado
    y sin escalones, en vez del borde dentado que daba engordar píxel a píxel.
    `icon` debe tener margen transparente de al menos `stroke` px alrededor.
    """
    alpha = icon.getchannel("A")
    spread = alpha.filter(ImageFilter.GaussianBlur(stroke * 0.7))
    # Rampa corta: el borde queda nítido (1-2 px de suavizado), no como un halo difuso
    outline = spread.point(lambda a: max(0, min(255, (a - 10) * 18)))
    canvas = Image.new("RGBA", icon.size, (0, 0, 0, 0))
    canvas.paste((236, 239, 244, 255), (0, 0), outline)
    canvas.alpha_composite(icon)
    return canvas


def sticker(data: bytes | None, size: int, stroke: int = 0) -> Image.Image | None:
    """El escudo como "sticker": recortado a su forma, con un borde claro alrededor.

    El borde sigue el contorno del escudo (no es un cuadro ni un círculo), así se ven también
    los escudos negros sobre el fondo negro, y todos quedan con el mismo look de cromo.
    `size` es el lado total, borde incluido. `stroke` = grosor del borde (0 = automático).
    """
    stroke = stroke or max(2, size // 24)
    icon = load_icon(data, size - 2 * stroke)
    if icon is None:
        return None
    padded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    padded.paste(icon, (stroke, stroke), icon)
    return outline_icon(padded, stroke)


def tile(
    canvas: Image.Image,
    data: bytes | None,
    box: tuple[int, int, int, int],
    border: RGB | None = None,
) -> None:
    """Pega el escudo como sticker centrado en `box`. `border`: un aro de color detrás."""
    side = min(box[2] - box[0], box[3] - box[1])
    center = ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)
    if border:
        draw = ImageDraw.Draw(canvas)
        r = side // 2 + 8
        draw.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), outline=border,
                     width=3)  # fmt: skip
    icon = sticker(data, side)
    if icon is not None:
        canvas.alpha_composite(icon, (center[0] - side // 2, center[1] - side // 2))


def wordmark(draw: ImageDraw.ImageDraw, xy: tuple[int, int], anchor: str = "ls") -> None:
    """ "FOOTBALLTRIVIA" en pequeño, con FOOTBALL en blanco y TRIVIA en azul."""
    fnt = font("title", 18, "ExtraBold")
    x, y = xy
    first, second = "FOOTBALL", "TRIVIA"
    width = fnt.getlength(first + second)
    if anchor.startswith("r"):
        x -= width
    draw.text((x, y), first, font=fnt, fill=TEXT, anchor="l" + anchor[1])
    draw.text((x + fnt.getlength(first), y), second, font=fnt, fill=BLUE, anchor="l" + anchor[1])
