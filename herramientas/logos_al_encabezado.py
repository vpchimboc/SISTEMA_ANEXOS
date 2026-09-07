#!/usr/bin/env python
"""
Mueve al encabezado los logos que quedaron dentro del texto.

El problema: en algunas plantillas los logos no están en el encabezado de
página sino como una imagen más del cuerpo (el primer párrafo del documento).
Eso tiene dos consecuencias que se ven al imprimir:

  - salen una sola vez, en la primera hoja, en vez de repetirse en todas;
  - ocupan sitio en el flujo del texto, así que empujan el contenido y se
    mueven si algo crece por encima.

Un logo institucional pertenece al encabezado: Word lo repite solo en cada
página y lo saca del flujo, que es justo lo que pide el formato oficial.

Qué hace: busca en el cuerpo las imágenes cuyo tamaño en bytes coincide con un
logo conocido (`HUELLA_LOGOS`), las vuelve a insertar en el encabezado de la
sección conservando su tamaño y su alineación, y las quita del cuerpo. Las
imágenes que NO son logos —fotos de evidencia, cronogramas pegados— no se
tocan: por eso la comparación es por huella y no por posición.

Uso:
    python herramientas/logos_al_encabezado.py            # solo diagnostica
    python herramientas/logos_al_encabezado.py --aplicar
"""

from __future__ import annotations

import argparse
import sys
from io import BytesIO
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from docx import Document  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Emu  # noqa: E402

from core import logos as mod_logos  # noqa: E402
from herramientas.construir_plantillas import HUELLA_LOGOS  # noqa: E402

DIR_PLANTILLAS = RAIZ / "plantillas"


def _drawings(elemento):
    return elemento.findall(".//" + qn("w:drawing"))


def _tamano(drawing) -> tuple[int, int]:
    """Ancho y alto en EMU declarados en el propio dibujo."""
    extent = drawing.find(".//" + qn("wp:extent"))
    if extent is None:
        return (0, 0)
    return (int(extent.get("cx")), int(extent.get("cy")))


def _rid(drawing) -> str | None:
    blip = drawing.find(".//" + qn("a:blip"))
    if blip is None:
        return None
    return blip.get(qn("r:embed"))


def analizar(ruta: Path) -> dict:
    """Logos del cuerpo (por huella) y logos ya en el encabezado."""
    encabezado = [i for i in mod_logos.inspeccionar(ruta)
                  if i["bytes_tam"] in HUELLA_LOGOS]
    todos = [i for i in mod_logos.inspeccionar(ruta, incluir_cuerpo=True)
             if i["bytes_tam"] in HUELLA_LOGOS]
    cuerpo = [i for i in todos if i["parte"] == "word/document.xml"]
    return {"encabezado": encabezado, "cuerpo": cuerpo}


def mover(ruta: Path, salida: Path | None = None) -> list[str]:
    """
    Pasa los logos del cuerpo al encabezado de la sección.

    Se reinsertan con python-docx en vez de mover el XML a mano: así la
    relación con el archivo de imagen se crea en `header1.xml.rels`, que es
    donde Word la busca. Moviendo el XML tal cual, el `r:embed` apuntaría a una
    relación del documento y la imagen saldría rota.
    """
    doc = Document(str(ruta))
    cambios: list[str] = []

    # Se recogen antes de tocar nada: al borrar cambian los índices.
    pendientes = []
    for parrafo in list(doc.paragraphs):
        for drawing in _drawings(parrafo._element):
            rid = _rid(drawing)
            if not rid:
                continue
            parte = doc.part.related_parts.get(rid)
            if parte is None:
                continue
            blob = parte.blob
            if len(blob) not in HUELLA_LOGOS:
                continue  # no es un logo: evidencia, cronograma, firma escaneada
            cx, cy = _tamano(drawing)
            pendientes.append({"parrafo": parrafo, "drawing": drawing,
                               "blob": blob, "cx": cx, "cy": cy,
                               "nombre": Path(parte.partname).name})

    if not pendientes:
        return cambios

    seccion = doc.sections[0]
    encabezado = seccion.header
    encabezado.is_linked_to_previous = False

    # Se reutiliza el primer párrafo del encabezado si está vacío; si ya tiene
    # un logo puesto, se añade al lado en vez de pisarlo.
    destino = encabezado.paragraphs[0]
    if destino.text.strip() or _drawings(destino._element):
        destino = encabezado.add_paragraph()
    destino.alignment = pendientes[0]["parrafo"].alignment

    for p in pendientes:
        corrida = destino.add_run()
        corrida.add_picture(BytesIO(p["blob"]),
                            width=Emu(p["cx"]) if p["cx"] else None,
                            height=Emu(p["cy"]) if p["cy"] else None)
        # El dibujo va dentro de una corrida; se quita esa corrida del cuerpo.
        corrida_origen = p["drawing"].getparent()
        while corrida_origen is not None and corrida_origen.tag != qn("w:r"):
            corrida_origen = corrida_origen.getparent()
        if corrida_origen is not None:
            corrida_origen.getparent().remove(corrida_origen)
        cambios.append(f"{p['nombre']} ({p['cx'] / 360000:.2f} x "
                       f"{p['cy'] / 360000:.2f} cm) -> encabezado")

    # Un párrafo que se queda sin nada estorba: dejaría una línea en blanco
    # justo donde antes estaban los logos.
    for p in {id(x["parrafo"]): x["parrafo"] for x in pendientes}.values():
        if not p.text.strip() and not _drawings(p._element):
            p._element.getparent().remove(p._element)

    doc.save(str(salida or ruta))
    return cambios


def actualizar_manifiesto(nombre_archivo: str) -> str:
    """
    Reescribe los slots de logo de esa plantilla en el manifiesto.

    Es obligatorio después de mover: el generador aplica los logos por índice
    de slot y con la marca `en_cuerpo`. Si el manifiesto sigue diciendo que el
    logo está en el cuerpo, el reemplazo iría al sitio equivocado o no haría
    nada.
    """
    import json
    ruta_man = DIR_PLANTILLAS / "manifiesto.json"
    if not ruta_man.exists():
        return "sin manifiesto"
    datos = json.loads(ruta_man.read_text(encoding="utf-8"))
    clave = next((k for k, v in datos.items()
                  if v.get("archivo") == nombre_archivo), None)
    if clave is None:
        return "no está en el manifiesto"

    slots = []
    for i, img in enumerate(mod_logos.inspeccionar(DIR_PLANTILLAS / nombre_archivo)):
        logico = HUELLA_LOGOS.get(img["bytes_tam"])
        if logico is None:
            continue
        slots.append({"indice": i, "logico": logico,
                      "ancho_cm": img["ancho_cm"], "alto_cm": img["alto_cm"],
                      "media": img["media"], "en_cuerpo": False})
    datos[clave]["logos"] = slots
    ruta_man.write_text(json.dumps(datos, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return f"{clave}: {len(slots)} slot(s) en el encabezado"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aplicar", action="store_true",
                    help="mover de verdad; por defecto solo diagnostica")
    ap.add_argument("--plantilla", nargs="*",
                    help="nombres concretos; por defecto, todas")
    args = ap.parse_args()

    nombres = args.plantilla or [p.name for p in sorted(DIR_PLANTILLAS.glob("*.docx"))]
    total = 0
    for nombre in nombres:
        ruta = DIR_PLANTILLAS / nombre
        if not ruta.exists():
            print(f"{nombre}: no existe")
            continue
        estado = analizar(ruta)
        n_cuerpo = len(estado["cuerpo"])
        if not n_cuerpo:
            print(f"  ok   {nombre:22} {len(estado['encabezado'])} logo(s) en el encabezado")
            continue
        total += n_cuerpo
        print(f"  ---> {nombre:22} {len(estado['encabezado'])} en encabezado, "
              f"{n_cuerpo} DENTRO DEL TEXTO")
        if args.aplicar:
            for linea in mover(ruta):
                print(f"        {linea}")
            despues = analizar(ruta)
            print(f"        ahora: {len(despues['encabezado'])} en encabezado, "
                  f"{len(despues['cuerpo'])} en el cuerpo")
            print(f"        manifiesto -> {actualizar_manifiesto(nombre)}")

    if total and not args.aplicar:
        print(f"\n{total} logo(s) dentro del texto. Use --aplicar para moverlos.")
    elif not total:
        print("\nTodos los logos están en el encabezado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
