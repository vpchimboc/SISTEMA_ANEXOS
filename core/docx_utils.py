"""
Utilidades de bajo nivel sobre .docx (python-docx).

El problema central: Word parte el texto de un párrafo en "runs" arbitrarios
(cada corrección ortográfica, cada cambio de idioma o de revisión abre un run
nuevo). Por eso un simple `run.text.replace(...)` casi nunca encuentra la
cadena buscada: "Mónica Galarza" puede estar partido en "Mónica ", "Gal",
"arza". Estas funciones trabajan sobre el texto concatenado del párrafo y
vuelven a repartirlo respetando el formato del primer run afectado.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Callable, Iterable

from docx.document import Document as _Doc
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph


# --------------------------------------------------------------------------
# Recorrido
# --------------------------------------------------------------------------

def parrafos(contenedor) -> Iterable[Paragraph]:
    """Todos los párrafos de un documento/celda, incluidos los de tablas anidadas."""
    for p in contenedor.paragraphs:
        yield p
    for t in getattr(contenedor, "tables", []):
        for fila in t.rows:
            for celda in fila.cells:
                yield from parrafos(celda)


def parrafos_documento(doc: _Doc) -> Iterable[Paragraph]:
    """Párrafos del cuerpo, de las tablas y también de encabezados y pies."""
    yield from parrafos(doc)
    for seccion in doc.sections:
        for parte in (seccion.header, seccion.footer,
                      seccion.first_page_header, seccion.first_page_footer,
                      seccion.even_page_header, seccion.even_page_footer):
            if parte is not None:
                yield from parrafos(parte)


def texto_documento(doc: _Doc) -> str:
    return "\n".join(p.text for p in parrafos_documento(doc))


# --------------------------------------------------------------------------
# Reemplazo respetando formato
# --------------------------------------------------------------------------

def _runs_visibles(p: Paragraph):
    """
    Runs del párrafo en orden de aparición, incluidos los que están dentro de
    un hipervínculo (<w:hyperlink>). `Paragraph.runs` los omite, y por eso una
    búsqueda sobre `p.text` encontraba texto que luego no se podía reemplazar.
    """
    from docx.text.run import Run
    return [Run(r, p) for r in p._element.iter(qn("w:r"))]


def reemplazar_en_parrafo(p: Paragraph, buscar: str, reemplazo: str,
                          regex: bool = False, contador: dict | None = None) -> int:
    """
    Reemplaza `buscar` por `reemplazo` dentro del párrafo, aunque la cadena
    esté partida entre varios runs. El texto nuevo hereda el formato del run
    donde empieza la coincidencia. Devuelve cuántas veces reemplazó.
    """
    runs = _runs_visibles(p)
    if not runs:
        return 0
    completo = "".join(r.text for r in runs)
    patron = buscar if regex else re.escape(buscar)
    if not re.search(patron, completo):
        return 0

    nuevo, n = re.subn(patron, reemplazo, completo)
    if n == 0:
        return 0

    # Todo el texto se coloca en el primer run y los demás se vacían.
    # Es la estrategia que menos rompe: el párrafo conserva su estilo, su
    # numeración, sus tabuladores y su formato de párrafo; solo se unifica
    # el formato de carácter, que en estos anexos es homogéneo por párrafo.
    runs[0].text = nuevo
    for r in runs[1:]:
        r.text = ""
    if contador is not None:
        contador["n"] = contador.get("n", 0) + n
    return n


PREFIJO_REGEX = "re:"


def reemplazar(doc: _Doc, cambios: list[tuple[str, str]], regex: bool = False) -> dict[str, int]:
    """
    Aplica una lista de (buscar, reemplazar) a todo el documento.

    Si `buscar` empieza por "re:", el resto se interpreta como expresión
    regular. Devuelve cuántas veces se aplicó cada cambio, para poder auditar
    que ninguna regla quedó sin efecto (señal de que la plantilla cambió).
    """
    conteo: dict[str, int] = {b: 0 for b, _ in cambios}
    for p in parrafos_documento(doc):
        for buscar, reemplazo in cambios:
            if buscar.startswith(PREFIJO_REGEX):
                patron, es_regex = buscar[len(PREFIJO_REGEX):], True
            else:
                patron, es_regex = buscar, regex
            conteo[buscar] += reemplazar_en_parrafo(p, patron, reemplazo, regex=es_regex)
    return conteo


def reemplazar_texto_celda(celda: _Cell, texto: str) -> None:
    """
    Deja la celda con un único párrafo con `texto`, conservando su formato.

    Usa la lista de runs que incluye los hipervínculos: si no, un correo
    escrito como enlace (mailto:) sobrevive y el texto nuevo se le suma en
    lugar de sustituirlo. Pasaba con el correo de la entidad en el Anexo 10.
    """
    primero = celda.paragraphs[0]
    for extra in celda.paragraphs[1:]:
        extra._element.getparent().remove(extra._element)
    runs = _runs_visibles(primero)
    if runs:
        runs[0].text = texto
        for r in runs[1:]:
            r.text = ""
    else:
        primero.add_run(texto)


# --------------------------------------------------------------------------
# Filas de tabla: convertir una fila de ejemplo en bucle de docxtpl
# --------------------------------------------------------------------------

def _fila_de_control(modelo, etiqueta: str, despues: bool):
    """
    Crea una fila que contiene únicamente una etiqueta {%tr ... %}.

    docxtpl ELIMINA la fila completa donde encuentra un {%tr %}. Por eso las
    etiquetas de apertura y cierre no pueden ir en la misma fila que se quiere
    repetir: van en dos filas propias, una arriba y otra abajo, que desaparecen
    al renderizar. Es un detalle que no está en la documentación obvia y que
    hace fallar el render con "unknown tag 'endfor'".
    """
    from docx.table import _Row
    nueva_el = deepcopy(modelo._element)
    if despues:
        modelo._element.addnext(nueva_el)
    else:
        modelo._element.addprevious(nueva_el)
    nueva = _Row(nueva_el, modelo._parent)
    for i, celda in enumerate(nueva.cells):
        reemplazar_texto_celda(celda, etiqueta if i == 0 else "")
    return nueva


def tabla_a_bucle(tabla: Table, fila_modelo: int, expresion: str,
                  celdas: dict[int, str], filas_a_borrar: list[int] | None = None) -> None:
    """
    Convierte una tabla con filas de ejemplo en una tabla con un bucle.

    tabla        : la tabla de python-docx
    fila_modelo  : índice de la fila que se conserva como plantilla del bucle
    expresion    : p. ej. "for a in actividades"
    celdas       : {índice_de_celda: "{{ a.descripcion }}"} con el contenido nuevo
    filas_a_borrar: índices de las demás filas de ejemplo (se eliminan)

    Resultado en el .docx:

        [ {%tr for a in actividades %} ]   <- fila de control, desaparece
        [ {{ a.nro }} | {{ a.descripcion }} ]   <- se repite
        [ {%tr endfor %} ]                 <- fila de control, desaparece
    """
    # Se toman las referencias a los elementos ANTES de insertar nada, porque
    # insertar filas desplaza los índices.
    a_borrar = [tabla.rows[i]._element for i in (filas_a_borrar or [])]
    modelo = tabla.rows[fila_modelo]

    for idx, contenido in celdas.items():
        if idx < len(modelo.cells):
            reemplazar_texto_celda(modelo.cells[idx], contenido)

    _fila_de_control(modelo, "{%%tr %s %%}" % expresion, despues=False)
    _fila_de_control(modelo, "{%tr endfor %}", despues=True)

    for el in a_borrar:
        el.getparent().remove(el)


def tabla_a_bucle_grupo(tabla: Table, desde: int, hasta: int, expresion: str,
                        celdas_por_fila: dict[int, dict[int, str]],
                        filas_a_borrar: list[int] | None = None) -> None:
    """
    Igual que `tabla_a_bucle` pero repitiendo un GRUPO de filas.

    Lo necesita el Anexo 13, donde cada visita ocupa tres filas (fecha,
    cabecera y contenido): el bucle tiene que envolver las tres, no una.

    desde/hasta      : rango de filas del grupo (ambos incluidos)
    celdas_por_fila  : {índice_fila_absoluto: {índice_celda: "texto"}}
    """
    a_borrar = [tabla.rows[i]._element for i in (filas_a_borrar or [])]

    for i_fila, celdas in celdas_por_fila.items():
        fila = tabla.rows[i_fila]
        for i_celda, contenido in celdas.items():
            if i_celda < len(fila.cells):
                reemplazar_texto_celda(fila.cells[i_celda], contenido)

    _fila_de_control(tabla.rows[desde], "{%%tr %s %%}" % expresion, despues=False)
    _fila_de_control(tabla.rows[hasta + 1], "{%tr endfor %}", despues=True)

    for el in a_borrar:
        el.getparent().remove(el)


def recortar_desde(doc: _Doc, indice_bloque: int) -> int:
    """
    Elimina todo el cuerpo del documento a partir de un bloque (párrafo o
    tabla). Se usa para quedarse con UNA copia cuando el documento oficial
    trae la misma ficha repetida varias veces (Anexos 9, 12 y 13).

    No toca la última sección (<w:sectPr>), que es donde viven los márgenes y
    la referencia al encabezado: borrarla desmontaría el formato de página.
    """
    body = doc.element.body
    hijos = [h for h in body.iterchildren()
             if h.tag in (qn("w:p"), qn("w:tbl"))]
    borrados = 0
    for hijo in hijos[indice_bloque:]:
        hijo.getparent().remove(hijo)
        borrados += 1
    return borrados


def clonar_fila(tabla: Table, indice: int) -> None:
    """Duplica una fila justo debajo de sí misma."""
    fila = tabla.rows[indice]._element
    fila.addnext(deepcopy(fila))


def borrar_filas(tabla: Table, indices: Iterable[int]) -> None:
    for idx in sorted(indices, reverse=True):
        fila = tabla.rows[idx]._element
        fila.getparent().remove(fila)


# --------------------------------------------------------------------------
# Bloques del cuerpo
# --------------------------------------------------------------------------

def bloques(doc: _Doc):
    """Cuerpo del documento en orden real: ('p', Paragraph) o ('t', Table)."""
    from docx.table import Table as _T
    body = doc.element.body
    idx_t = 0
    idx_p = 0
    tablas = doc.tables
    parras = doc.paragraphs
    for hijo in body.iterchildren():
        if hijo.tag == qn("w:p"):
            if idx_p < len(parras):
                yield "p", parras[idx_p]
            idx_p += 1
        elif hijo.tag == qn("w:tbl"):
            if idx_t < len(tablas):
                yield "t", tablas[idx_t]
            idx_t += 1


def buscar_parrafo(doc: _Doc, texto: str, exacto: bool = False) -> Paragraph | None:
    for p in parrafos_documento(doc):
        if (p.text.strip() == texto) if exacto else (texto in p.text):
            return p
    return None


def eliminar_parrafo(p: Paragraph) -> None:
    p._element.getparent().remove(p._element)


def escribir_parrafo(p: Paragraph, texto: str) -> None:
    """Sustituye todo el contenido del párrafo conservando su estilo."""
    if p.runs:
        p.runs[0].text = texto
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(texto)


def aplicar_a_parrafos(doc: _Doc, fn: Callable[[Paragraph], None]) -> None:
    for p in parrafos_documento(doc):
        fn(p)


def tiene_imagen(p: Paragraph) -> bool:
    """True si el párrafo contiene un dibujo (imagen incrustada)."""
    return p._element.find(".//" + qn("w:drawing")) is not None or \
        p._element.find(".//" + qn("w:pict")) is not None


def parrafos_entre(contenedor, desde: str, hasta: str | None = None,
                   incluir_desde: bool = False) -> list[Paragraph]:
    """
    Párrafos con texto situados entre dos anclas. Se usa para localizar los
    bloques de redacción de los informes largos sin depender de índices, que
    cambian en cuanto alguien añade un párrafo en Word.
    """
    seleccion, dentro = [], False
    for p in contenedor.paragraphs:
        texto = p.text.strip()
        if not dentro:
            if desde in texto:
                dentro = True
                if incluir_desde:
                    seleccion.append(p)
            continue
        if hasta and hasta in texto:
            break
        if texto or tiene_imagen(p):
            seleccion.append(p)
    return seleccion


def bloque_a_variable(parrafos_bloque: list[Paragraph], etiqueta: str) -> int:
    """
    Sustituye un bloque de redacción por una sola etiqueta Jinja.

    El primer párrafo de solo texto pasa a ser `{{ etiqueta }}` y los demás
    párrafos de solo texto se eliminan. Los párrafos que contienen imágenes se
    respetan: en estos informes son las evidencias fotográficas y los
    cronogramas pegados como imagen, y borrarlos rompería el documento.

    docxtpl convierte los saltos de línea del valor en <w:br/>, así que un
    texto de varios párrafos sigue viéndose separado.

    Devuelve cuántos párrafos se eliminaron.
    """
    texto_puros = [p for p in parrafos_bloque if not tiene_imagen(p)]
    if not texto_puros:
        return 0
    escribir_parrafo(texto_puros[0], etiqueta)
    for p in texto_puros[1:]:
        eliminar_parrafo(p)
    return len(texto_puros) - 1


def insertar_parrafo_junto(referencia: Paragraph, texto: str,
                           despues: bool = False) -> Paragraph:
    """
    Inserta un párrafo antes o después de `referencia`, copiando su formato.
    Se usa para las etiquetas de control {%p ... %} de docxtpl, que deben
    ocupar un párrafo entero.
    """
    nuevo_el = deepcopy(referencia._element)
    if despues:
        referencia._element.addnext(nuevo_el)
    else:
        referencia._element.addprevious(nuevo_el)
    nuevo = Paragraph(nuevo_el, referencia._parent)
    for r in list(nuevo.runs):
        r._element.getparent().remove(r._element)
    nuevo.add_run(texto)
    return nuevo


def lista_a_bucle(parrafos_lista: list[Paragraph], expresion: str,
                  contenido: str) -> None:
    """
    Convierte una lista de párrafos de ejemplo (viñetas, numeración) en un
    bucle de docxtpl:

        {%p for r in requisitos %}
        {{ r.nombre }}          <- conserva el estilo de lista del original
        {%p endfor %}

    El primer párrafo se reutiliza como modelo y los demás se eliminan.
    """
    if not parrafos_lista:
        raise ValueError("No se recibió ningún párrafo para convertir en bucle")
    modelo = parrafos_lista[0]
    insertar_parrafo_junto(modelo, "{%%p %s %%}" % expresion, despues=False)
    escribir_parrafo(modelo, contenido)
    insertar_parrafo_junto(modelo, "{%p endfor %}", despues=True)
    for extra in parrafos_lista[1:]:
        eliminar_parrafo(extra)
