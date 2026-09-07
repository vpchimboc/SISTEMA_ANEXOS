"""
Gestor de logos del encabezado.

Los anexos llevan dos imágenes en el encabezado (word/header*.xml): la de la
izquierda es el logo institucional y la de la derecha la de la entidad
beneficiaria / auspiciante. Este módulo las reemplaza sin abrir Word y sin
tocar absolutamente nada más del documento.

Cómo funciona
-------------
Un .docx es un ZIP. Dentro:
  word/header1.xml            -> el XML del encabezado, con las etiquetas <w:drawing>
  word/_rels/header1.xml.rels -> mapea cada rId a un archivo de word/media/
  word/media/imageN.png       -> los bytes de la imagen
  [Content_Types].xml         -> declara el tipo MIME de cada extensión

Entonces: se leen los drawings del encabezado EN ORDEN DE APARICIÓN (el primero
es el de la izquierda), se resuelve su rId al archivo de media, se sustituyen
los bytes por los del logo nuevo y se ajustan los atributos de tamaño
(<wp:extent> y <a:ext>), que van en EMU (1 cm = 360000 EMU).

Se reemplaza únicamente el media referenciado desde un encabezado; las imágenes
del cuerpo del documento (por ejemplo las evidencias del Anexo 10) no se tocan.
"""

from __future__ import annotations

import io
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

EMU_POR_CM = 360000

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
}

MIME_POR_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".emf": "image/x-emf",
    ".wmf": "image/x-wmf",
}


class ErrorLogo(Exception):
    """Problema al leer o reemplazar un logo."""


# --------------------------------------------------------------------------
# Inspección
# --------------------------------------------------------------------------

def _partes_encabezado(zf: zipfile.ZipFile) -> list[str]:
    return sorted(n for n in zf.namelist()
                  if re.fullmatch(r"word/header\d*\.xml", n))


def _rels_de(parte: str) -> str:
    p = Path(parte)
    return f"{p.parent.as_posix()}/_rels/{p.name}.rels"


def _mapa_rels(zf: zipfile.ZipFile, parte_rels: str) -> dict[str, str]:
    """rId -> ruta del media dentro del paquete (word/media/imageN.png)."""
    if parte_rels not in zf.namelist():
        return {}
    raiz = ET.fromstring(zf.read(parte_rels))
    mapa = {}
    for rel in raiz:
        rid = rel.get("Id")
        destino = rel.get("Target", "")
        if not rid or "media/" not in destino:
            continue
        mapa[rid] = "word/" + destino.lstrip("./").replace("../", "")
    return mapa


def inspeccionar(docx: Path | str, incluir_cuerpo: bool = False) -> list[dict]:
    """
    Devuelve la lista de imágenes del encabezado en orden de aparición:
    [{parte, rid, media, ancho_cm, alto_cm, bytes_tam}, ...]

    Con `incluir_cuerpo`, añade también las imágenes de word/document.xml. Hace
    falta porque no todos los formatos ponen los logos en el encabezado: el
    Anexo 5 no tiene encabezado y lleva los dos logos incrustados en el cuerpo.
    Quien llame con esta opción debe filtrar cuáles de esas imágenes son
    realmente logos (por ejemplo por su huella), o acabará tratando como logo
    una fotografía de evidencia.
    """
    docx = Path(docx)
    encontrados: list[dict] = []
    with zipfile.ZipFile(docx) as zf:
        partes = _partes_encabezado(zf)
        if incluir_cuerpo and "word/document.xml" in zf.namelist():
            partes = partes + ["word/document.xml"]
        for parte in partes:
            xml = zf.read(parte).decode("utf-8")
            rels = _mapa_rels(zf, _rels_de(parte))
            # Se recorren los <wp:extent> y los r:embed en el orden del XML.
            embeds = re.findall(r'r:embed="([^"]+)"', xml)
            extents = re.findall(r'<wp:extent\s+cx="(\d+)"\s+cy="(\d+)"', xml)
            for i, rid in enumerate(embeds):
                media = rels.get(rid, "")
                cx, cy = (extents[i] if i < len(extents) else ("0", "0"))
                encontrados.append({
                    "parte": parte,
                    "rid": rid,
                    "media": media,
                    "ancho_cm": round(int(cx) / EMU_POR_CM, 2),
                    "alto_cm": round(int(cy) / EMU_POR_CM, 2),
                    "bytes_tam": zf.getinfo(media).file_size if media in zf.namelist() else 0,
                })
    return encontrados


def extraer_logo(docx: Path | str, indice: int = 0) -> tuple[bytes, str]:
    """Devuelve (bytes, extensión) del logo `indice` del encabezado."""
    imgs = inspeccionar(docx)
    if indice >= len(imgs):
        raise ErrorLogo(f"El documento no tiene un logo en la posición {indice}")
    media = imgs[indice]["media"]
    with zipfile.ZipFile(docx) as zf:
        return zf.read(media), Path(media).suffix.lower()


# --------------------------------------------------------------------------
# Conversión de formato
# --------------------------------------------------------------------------

def _convertir(datos: bytes, extension_destino: str) -> bytes:
    """
    Ajusta el logo nuevo al mismo formato que el que reemplaza, para no tener
    que tocar [Content_Types].xml ni las relaciones. Si ya coincide, no hace nada.
    """
    try:
        from PIL import Image
    except ImportError as e:  # pragma: no cover
        raise ErrorLogo(
            "Falta la librería Pillow para convertir el logo. Instálala con: pip install Pillow"
        ) from e

    ext = extension_destino.lower()
    with Image.open(io.BytesIO(datos)) as img:
        formato_actual = (img.format or "").lower()
        objetivo = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG",
                    "gif": "GIF", "bmp": "BMP"}.get(ext.lstrip("."))
        if objetivo is None:
            raise ErrorLogo(f"No se puede escribir un logo con extensión {ext}")
        if formato_actual == objetivo.lower():
            return datos
        salida = io.BytesIO()
        if objetivo == "JPEG":
            # JPEG no admite transparencia: se aplana sobre blanco.
            fondo = Image.new("RGB", img.size, (255, 255, 255))
            conv = img.convert("RGBA")
            fondo.paste(conv, mask=conv.split()[-1])
            fondo.save(salida, "JPEG", quality=95)
        else:
            img.convert("RGBA" if objetivo == "PNG" else "RGB").save(salida, objetivo)
        return salida.getvalue()


def proporcion(datos: bytes) -> float:
    """Relación ancho/alto del logo, para sugerir tamaños sin deformarlo."""
    from PIL import Image
    with Image.open(io.BytesIO(datos)) as img:
        return img.width / img.height if img.height else 1.0


# --------------------------------------------------------------------------
# Reemplazo
# --------------------------------------------------------------------------

def _ajustar_tamano(xml: str, indice: int, ancho_cm: float, alto_cm: float) -> str:
    """
    Cambia el tamaño del drawing número `indice`. En el XML de Word cada imagen
    lleva el tamaño duplicado: en <wp:extent> (el hueco en el texto) y en
    <a:ext> (el tamaño del gráfico). Hay que actualizar los dos.
    """
    cx = int(round(ancho_cm * EMU_POR_CM))
    cy = int(round(alto_cm * EMU_POR_CM))

    def sustituir(patron: str, texto: str, nth: int, nuevo: str) -> str:
        contador = {"i": 0}

        def _rep(m):
            actual = contador["i"]
            contador["i"] += 1
            return nuevo if actual == nth else m.group(0)

        return re.sub(patron, _rep, texto)

    xml = sustituir(r'<wp:extent\s+cx="\d+"\s+cy="\d+"\s*/>', xml, indice,
                    f'<wp:extent cx="{cx}" cy="{cy}"/>')
    xml = sustituir(r'<a:ext\s+cx="\d+"\s+cy="\d+"\s*/>', xml, indice,
                    f'<a:ext cx="{cx}" cy="{cy}"/>')
    return xml


def aplicar_logos(docx: Path | str, asignaciones: dict, salida: Path | str | None = None,
                  avisos: list[str] | None = None,
                  incluir_cuerpo: bool = False) -> Path:
    """
    Reemplaza los logos del encabezado.

    `asignaciones` va indexado por SLOT (0 = primera imagen del encabezado en
    orden de aparición, 1 = segunda…):

        {
          0: {"archivo": "recursos/logos/tecazuay.png", "ancho_cm": 4.39, "alto_cm": 1.34},
          1: {"archivo": "recursos/logos/senescyt.jpg"},
        }

    Se indexa por slot y no por "izquierda/derecha" porque el orden de los
    logos no es el mismo en todos los anexos; quién es cada slot lo dice el
    manifiesto de plantillas.

    Un slot ausente, o con archivo vacío y sin medidas, se deja intacto. Si
    solo se dan las medidas, se redimensiona la imagen existente.

    `avisos` recoge, si se pasa, los logos que no se pudieron reemplazar.

    Devuelve la ruta del documento resultante.
    """
    docx = Path(docx)
    salida = Path(salida) if salida else docx
    if not docx.exists():
        raise ErrorLogo(f"No existe el documento: {docx}")

    imgs = inspeccionar(docx, incluir_cuerpo=incluir_cuerpo)
    if not imgs:
        raise ErrorLogo(f"{docx.name} no tiene imágenes en el encabezado")

    # Bytes nuevos por ruta de media, y XML modificados por parte.
    nuevos_media: dict[str, bytes] = {}
    xml_por_parte: dict[str, str] = {}

    # Índice del drawing dentro de SU parte (para ajustar el tamaño correcto).
    indice_local: dict[str, int] = {}
    for i, img in enumerate(imgs):
        parte = img["parte"]
        idx = indice_local.get(parte, 0)
        indice_local[parte] = idx + 1

        cfg = asignaciones.get(i) or {}
        archivo = (cfg.get("archivo") or "").strip()
        ancho = cfg.get("ancho_cm")
        alto = cfg.get("alto_cm")
        if not archivo and not ancho and not alto:
            continue

        if archivo:
            origen = Path(archivo)
            if not origen.exists():
                raise ErrorLogo(f"No existe el archivo de logo: {origen}")
            destino_ext = Path(img["media"]).suffix.lower()
            nuevos_media[img["media"]] = _convertir(origen.read_bytes(), destino_ext)

        if ancho and alto:
            with zipfile.ZipFile(docx) as zf:
                xml = xml_por_parte.get(parte) or zf.read(parte).decode("utf-8")
            xml_por_parte[parte] = _ajustar_tamano(xml, idx, float(ancho), float(alto))

    # Un media que está en el encabezado y ADEMÁS en el cuerpo no se puede
    # reemplazar sin alterar el contenido: pasa en el informe de selección,
    # donde la misma imagen del logo aparece dentro del documento. Se omite
    # (el documento conserva el original) y se reporta.
    # No aplica cuando el propio slot vive en el cuerpo, que es como el Anexo 5
    # lleva sus logos: ahí sustituirlo es justo lo que se quiere.
    medias_de_cuerpo = {img["media"] for img in imgs
                        if img["parte"] == "word/document.xml"}
    with zipfile.ZipFile(docx) as zf:
        if "word/document.xml" in zf.namelist() and nuevos_media:
            rels_doc = _mapa_rels(zf, "word/_rels/document.xml.rels")
            compartidos = sorted((set(rels_doc.values()) & set(nuevos_media))
                                 - medias_de_cuerpo)
            for media in compartidos:
                nuevos_media.pop(media, None)
            if compartidos and avisos is not None:
                avisos.append(
                    f"{docx.name}: el logo del encabezado es la misma imagen que una "
                    "del cuerpo del documento; se conserva el original para no "
                    "alterar el contenido.")

    if not nuevos_media and not xml_por_parte:
        return salida if salida == docx else Path(shutil.copy2(docx, salida))

    # Reescritura del ZIP conservando el resto de partes byte a byte.
    temporal = salida.with_suffix(salida.suffix + ".tmp")
    temporal.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(docx) as zf_in, \
         zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED) as zf_out:
        for info in zf_in.infolist():
            nombre = info.filename
            if nombre in nuevos_media:
                zf_out.writestr(nombre, nuevos_media[nombre])
            elif nombre in xml_por_parte:
                zf_out.writestr(nombre, xml_por_parte[nombre].encode("utf-8"))
            else:
                zf_out.writestr(info, zf_in.read(nombre))

    shutil.move(str(temporal), str(salida))
    return salida


def asignaciones_desde_manifiesto(slots: list[dict], catalogo: dict,
                                  carpeta_logos: Path | str) -> dict:
    """
    Traduce la configuración lógica de logos a asignaciones por slot.

    slots    : lista del manifiesto -> [{"indice": 0, "logico": "institucional",
                                         "ancho_cm": 4.39, "alto_cm": 1.34}, ...]
    catalogo : {"institucional": {"archivo": "tecazuay.png", "escala": 1.0,
                                  "activo": 1}, ...}
    """
    carpeta_logos = Path(carpeta_logos)
    asignaciones: dict[int, dict] = {}
    for slot in slots:
        cfg = catalogo.get(slot.get("logico", ""))
        if not cfg or not cfg.get("activo", 1):
            continue
        entrada: dict = {}
        archivo = (cfg.get("archivo") or "").strip()
        ruta = carpeta_logos / archivo if archivo else None
        if ruta and ruta.exists():
            entrada["archivo"] = str(ruta)

        escala = float(cfg.get("escala") or 1.0)
        ancho = slot["ancho_cm"] * escala
        alto = slot["alto_cm"] * escala

        # Si el logo nuevo tiene otra relación de aspecto que el hueco del
        # formato, se deformaría. Con `proporcion` se respeta el ancho del
        # formato y se recalcula el alto a partir de la imagen.
        if ruta and ruta.exists() and cfg.get("proporcion", 1):
            try:
                relacion = proporcion(ruta.read_bytes())
                if relacion > 0:
                    alto = ancho / relacion
            except Exception:
                pass

        if entrada.get("archivo") or abs(escala - 1.0) > 1e-6:
            entrada["ancho_cm"] = round(ancho, 3)
            entrada["alto_cm"] = round(alto, 3)
        if entrada:
            asignaciones[slot["indice"]] = entrada
    return asignaciones
