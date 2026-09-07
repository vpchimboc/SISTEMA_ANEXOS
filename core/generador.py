"""
Generación de anexos: renderiza la plantilla, aplica los logos y exporta.

docxtpl (Jinja2 sobre .docx) es lo que permite conservar el formato: no
reconstruye el documento, solo sustituye el texto de las etiquetas dentro del
XML original. Estilos, márgenes, tablas, encabezado y numeración quedan tal
cual estaban en el documento oficial.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from docxtpl import DocxTemplate

from . import contexto as mod_ctx
from . import db
from . import logos as mod_logos

RAIZ = Path(__file__).resolve().parent.parent
DIR_PLANTILLAS = RAIZ / "plantillas"
DIR_SALIDA = RAIZ / "salida"
DIR_LOGOS = RAIZ / "recursos" / "logos"


# --------------------------------------------------------------------------
# Catálogo de anexos
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Anexo:
    clave: str
    titulo: str
    plantilla: str
    # Sobre qué se repite el documento: None (uno solo), 'estudiantes',
    # 'docentes', 'meses', 'jornadas'
    itera: str | None = None
    patron: str = "{clave}"
    descripcion: str = ""
    variantes: tuple[str, ...] = field(default_factory=tuple)


CATALOGO: dict[str, Anexo] = {
    "1": Anexo("1", "Delegación de docentes", "anexo_1.docx",
               itera="docentes", patron="ANEXO 1 - {docente}",
               descripcion="Oficio que delega a cada docente al proyecto."),
    "2": Anexo("2", "Convocatoria", "anexo_2.docx",
               patron="ANEXO 2 - Convocatoria",
               descripcion="Convocatoria abierta a los estudiantes de la carrera."),
    "3": Anexo("3", "Solicitud de participación", "anexo_3.docx",
               itera="estudiantes", patron="ANEXO 3 - {estudiante}",
               descripcion="Solicitud que presenta cada estudiante."),
    "4": Anexo("4", "Respuesta al estudiante", "anexo_4.docx",
               itera="estudiantes", patron="ANEXO 4 - {estudiante}",
               descripcion="Notificación de aprobación de la solicitud."),
    "5": Anexo("5", "Delegación de estudiantes a docente de apoyo", "anexo_5.docx",
               itera="docentes", patron="ANEXO 5 - {docente}",
               descripcion="Asigna a cada docente de apoyo sus estudiantes."),
    "6": Anexo("6", "Plan de aprendizaje", "anexo_6.docx",
               itera="estudiantes", patron="ANEXO 6 - {estudiante}",
               descripcion="Plan de aprendizaje del estudiante en el proyecto."),
    "6.1": Anexo("6.1", "Seguimiento del plan (parcial)", "anexo_6.1.docx",
                 itera="estudiantes", patron="ANEXO 6.1 - {estudiante}",
                 descripcion="Evaluación parcial del plan de aprendizaje."),
    "6.2": Anexo("6.2", "Seguimiento del plan (final)", "anexo_6.2.docx",
                 itera="estudiantes", patron="ANEXO 6.2 - {estudiante}",
                 descripcion="Evaluación final del plan de aprendizaje."),
    "7": Anexo("7", "Planificación mensual", "anexo_7.docx",
               itera="meses", patron="ANEXO 7 - Planificacion {mes}",
               descripcion="Planificación de horas de docentes y estudiantes por mes."),
    "8": Anexo("8", "Registro diario de actividades", "anexo_8.docx",
               itera="estudiantes", patron="ANEXO 8 - {estudiante}",
               descripcion="Bitácora de actividades y horas de cada estudiante."),
    "9": Anexo("9", "Seguimiento mensual", "anexo_9.docx",
               itera="meses_docentes", patron="ANEXO 9 - {mes} - {docente}",
               descripcion="Seguimiento por mes y docente de apoyo."),
    "10": Anexo("10", "Informe de culminación (estudiante)", "anexo_10.docx",
                itera="estudiantes", patron="ANEXO 10 - {estudiante}",
                descripcion="Informe final del estudiante; las evidencias se completan en Word."),
    "11": Anexo("11", "Evaluación al estudiante", "anexo_11.docx",
                itera="estudiantes", patron="ANEXO 11 - {estudiante}",
                descripcion="Rúbrica de evaluación del docente de apoyo y del director."),
    "12": Anexo("12", "Registro de beneficiarios", "anexo_12.docx",
                itera="jornadas", patron="ANEXO 12 - {jornada}",
                descripcion="Hoja de firmas de beneficiarios por jornada de capacitación."),
    "13": Anexo("13", "Registro de visitas", "anexo_13.docx",
                itera="docentes", patron="ANEXO 13 - {docente}",
                descripcion="Registro de visitas del docente de apoyo a la institución."),

    # --- Documentos sin número de anexo (los "S/N" de la Constancia) --------
    "S1": Anexo("S1", "Informe del proceso de selección", "seleccion.docx",
                patron="SN 1 - Proceso de Seleccion",
                descripcion="Informe del proceso de selección de estudiantes."),
    "S2": Anexo("S2", "Informe de seguimiento al proyecto (ISTA)", "seguimiento.docx",
                patron="SN 2 - Informe de Seguimiento",
                descripcion="Formato ISTA de seguimiento a mitad de ejecución."),
    "S3": Anexo("S3", "Informe final del proyecto (ISTA)", "final.docx",
                patron="SN 3 - Informe Final",
                descripcion="Formato ISTA de cierre, con impacto e indicadores."),
    "S4": Anexo("S4", "Informe de socialización de resultados", "socializacion.docx",
                patron="SN 4 - Informe de Socializacion",
                descripcion="Divulgación de resultados a la comunidad."),
    "S5": Anexo("S5", "Constancia de recepción de anexos", "constancia.docx",
                patron="SN 5 - Constancia de Anexos",
                descripcion="Checklist de entrega; se marca con lo que generes."),
}


def anexos_disponibles() -> list[Anexo]:
    """Anexos del catálogo cuya plantilla existe en disco."""
    return [a for a in CATALOGO.values() if (DIR_PLANTILLAS / a.plantilla).exists()]


# --------------------------------------------------------------------------
# Manifiesto de plantillas (slots de logo por anexo)
# --------------------------------------------------------------------------

def cargar_manifiesto() -> dict:
    ruta = DIR_PLANTILLAS / "manifiesto.json"
    if not ruta.exists():
        return {}
    return json.loads(ruta.read_text(encoding="utf-8"))


def _slots_de(anexo: Anexo, manifiesto: dict) -> list[dict]:
    for datos in manifiesto.values():
        if datos.get("archivo") == anexo.plantilla:
            return datos.get("logos", [])
    return []


# --------------------------------------------------------------------------
# Nombres de archivo
# --------------------------------------------------------------------------

def nombre_seguro(texto: str) -> str:
    """Quita acentos y caracteres que Windows no admite en nombres de archivo."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r'[<>:"/\\|?*]', "", texto)
    return re.sub(r"\s+", " ", texto).strip()


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------

def _catalogo_logos(con) -> dict:
    return {l["clave"]: l for l in db.listar(con, "logos", orden="clave")}


def _renderizar(anexo: Anexo, ctx: dict, destino: Path,
                slots: list[dict], catalogo_logos: dict,
                avisos: list[str] | None = None) -> Path:
    plantilla = DIR_PLANTILLAS / anexo.plantilla
    if not plantilla.exists():
        raise FileNotFoundError(f"Falta la plantilla {plantilla}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    doc = DocxTemplate(str(plantilla))
    doc.render(ctx)
    doc.save(str(destino))

    asignaciones = mod_logos.asignaciones_desde_manifiesto(slots, catalogo_logos, DIR_LOGOS)
    if asignaciones:
        # Algunos formatos (Anexo 5) llevan los logos en el cuerpo porque no
        # tienen encabezado; el manifiesto lo indica por slot.
        en_cuerpo = any(s.get("en_cuerpo") for s in slots)
        mod_logos.aplicar_logos(destino, asignaciones, avisos=avisos,
                                incluir_cuerpo=en_cuerpo)
    return destino


def generar(claves: list[str], carpeta_salida: Path | str | None = None,
            ruta_db: Path | str | None = None,
            a_pdf: bool = False) -> dict:
    """
    Genera los anexos indicados. Devuelve
    {"archivos": [Path, ...], "errores": [str, ...]}.
    """
    carpeta = Path(carpeta_salida) if carpeta_salida else DIR_SALIDA
    manifiesto = cargar_manifiesto()
    generados: list[Path] = []
    errores: list[str] = []
    avisos: list[str] = []

    with db.conexion(ruta_db) as con:
        base = mod_ctx.construir(con)
        catalogo_logos = _catalogo_logos(con)

    # La constancia refleja lo que realmente se está entregando: se marca cada
    # fila cuyo anexo entra en esta generación, sin perder las que ya venían
    # marcadas a mano desde la app.
    seleccion = set(claves)
    base["constancia"] = [
        dict(fila, marca=(mod_ctx.MARCA_CHECK
                          if (fila.get("anexo") in seleccion or fila.get("marcado"))
                          else ""))
        for fila in base.get("constancia", [])
    ]

    for clave in claves:
        anexo = CATALOGO.get(clave)
        if anexo is None:
            errores.append(f"Anexo {clave}: no está en el catálogo")
            continue
        slots = _slots_de(anexo, manifiesto)

        try:
            for ctx, etiqueta in _iteraciones(anexo, base):
                nombre = anexo.patron.format(**etiqueta)
                destino = carpeta / f"{nombre_seguro(nombre)}.docx"
                generados.append(_renderizar(anexo, ctx, destino, slots,
                                             catalogo_logos, avisos))
        except Exception as e:  # se reporta y se sigue con los demás anexos
            errores.append(f"Anexo {clave}: {e}")

    if a_pdf and generados:
        convertidos, fallos = a_pdf_lote(generados)
        generados.extend(convertidos)
        errores.extend(fallos)

    # Los avisos de logos no son fallos: el documento sale bien, solo conserva
    # el logo original. Se reportan sin repetir el mismo mensaje.
    for aviso in dict.fromkeys(avisos):
        errores.append(aviso)

    return {"archivos": generados, "errores": errores}


SINGULAR = {"estudiantes": "estudiante", "docentes": "docente",
            "meses": "mes", "jornadas": "jornada"}


def _nombre_de(elemento: dict) -> str:
    return (elemento.get("nombre_completo") or elemento.get("nombre")
            or elemento.get("etiqueta") or elemento.get("asunto")
            or str(elemento.get("nro", "")))


def _enriquecer(anexo: Anexo, ctx: dict, base: dict) -> None:
    """Añade al contexto los datos derivados que necesita cada anexo."""
    estudiante = ctx.get("estudiante") or {}
    mes = ctx.get("mes") or {}
    docente = ctx.get("docente") or {}

    if anexo.clave in {"8"}:
        ctx["registro"], ctx["total_registro"] = mod_ctx.registro_de(base, estudiante)

    if anexo.clave == "6.1":
        ctx["plan"] = mod_ctx.plan_de(base, estudiante, "parcial")
    if anexo.clave == "6.2":
        ctx["plan"] = mod_ctx.plan_de(base, estudiante, "final")

    if anexo.clave == "11":
        ctx["ev"], ctx["marca"] = mod_ctx.evaluacion_de(base, estudiante)

    if anexo.clave == "7":
        ctx["plan_docentes"] = mod_ctx.planificacion_de(base, mes, "docente")
        ctx["plan_estudiantes"] = mod_ctx.planificacion_de(base, mes, "estudiante")

    if anexo.clave == "9":
        ctx["seguimiento"] = mod_ctx.seguimiento_de(base, mes, docente)

    # --- Informes narrativos ------------------------------------------------
    if anexo.clave in {"S2", "S3"}:
        informe = "seguimiento" if anexo.clave == "S2" else "final"
        ctx["actividades_informe"] = mod_ctx.actividades_informe_de(base, informe)
        ctx["objetivos_especificos"] = mod_ctx.lista_de(base, "objetivos_especificos")
        ctx["conclusiones"] = mod_ctx.lista_de(base, f"conclusiones_{informe}")

    if anexo.clave == "S3":
        ctx["resultados_indicadores"] = mod_ctx.lista_de(base, "resultados_indicadores")
        ctx["productos"] = mod_ctx.lista_de(base, "productos")
        ctx["recomendaciones"] = mod_ctx.lista_de(base, "recomendaciones")


def _iteraciones(anexo: Anexo, base: dict):
    """Genera (contexto, etiquetas_para_el_nombre) por cada documento a producir."""
    if anexo.itera is None:
        ctx = dict(base)
        _enriquecer(anexo, ctx, base)
        yield ctx, {"clave": anexo.clave}
        return

    # Caso especial: el Anexo 9 se emite por mes Y por docente de apoyo,
    # porque el documento oficial lleva la firma de un solo docente.
    if anexo.itera == "meses_docentes":
        meses = base.get("meses") or []
        docentes = base.get("docentes") or []
        if not meses:
            raise ValueError("no hay meses registrados")
        if not docentes:
            raise ValueError("no hay docentes de apoyo registrados")
        for mes in meses:
            for docente in docentes:
                ctx = dict(base)
                ctx["mes"] = mod_ctx.preparar_mes(mes)
                ctx["docente"] = docente
                _enriquecer(anexo, ctx, base)
                if not ctx.get("seguimiento"):
                    continue  # ese docente no tiene estudiantes con seguimiento ese mes
                yield ctx, {"clave": anexo.clave,
                            "mes": mes.get("etiqueta", ""),
                            "docente": docente.get("nombre", "")}
        return

    elementos = base.get(anexo.itera) or []
    if not elementos:
        raise ValueError(f"no hay {anexo.itera} registrados")

    singular = SINGULAR[anexo.itera]

    for elemento in elementos:
        ctx = dict(base)
        if singular == "mes":
            elemento = mod_ctx.preparar_mes(elemento)
        elif singular == "jornada":
            elemento = mod_ctx.preparar_jornada(elemento)
        ctx[singular] = elemento

        if anexo.itera == "docentes":
            # Cada docente de apoyo lleva solo los estudiantes que tiene a cargo.
            propios = [e for e in base["estudiantes"]
                       if (e.get("docente_apoyo") or {}).get("id") == elemento.get("id")]
            ctx["estudiantes"] = propios or base["estudiantes"]

        _enriquecer(anexo, ctx, base)
        yield ctx, {"clave": anexo.clave, singular: _nombre_de(elemento)}


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

def _buscar_libreoffice() -> str | None:
    for nombre in ("soffice", "libreoffice",
                   r"C:\Program Files\LibreOffice\program\soffice.exe"):
        ruta = shutil.which(nombre) or (nombre if Path(nombre).exists() else None)
        if ruta:
            return ruta
    return None


def a_pdf_lote(archivos: list[Path]) -> tuple[list[Path], list[str]]:
    """
    Convierte .docx a .pdf. Prioriza Word (docx2pdf) porque respeta al 100%
    la paginación del formato oficial; si no está, usa LibreOffice.
    """
    convertidos: list[Path] = []
    errores: list[str] = []

    if sys.platform.startswith("win"):
        try:
            from docx2pdf import convert  # type: ignore
            for archivo in archivos:
                try:
                    convert(str(archivo), str(archivo.with_suffix(".pdf")))
                    convertidos.append(archivo.with_suffix(".pdf"))
                except Exception as e:
                    errores.append(f"PDF {archivo.name}: {e}")
            return convertidos, errores
        except ImportError:
            errores.append(
                "No está instalado docx2pdf; se intentará con LibreOffice. "
                "Para usar Word: pip install docx2pdf"
            )

    soffice = _buscar_libreoffice()
    if not soffice:
        errores.append(
            "No se encontró Word (docx2pdf) ni LibreOffice: no se generaron PDF."
        )
        return convertidos, errores

    for archivo in archivos:
        try:
            subprocess.run(
                [soffice, "--headless", "--convert-to", "pdf",
                 "--outdir", str(archivo.parent), str(archivo)],
                check=True, capture_output=True, timeout=180,
            )
            pdf = archivo.with_suffix(".pdf")
            if pdf.exists():
                convertidos.append(pdf)
            else:
                errores.append(f"PDF {archivo.name}: LibreOffice no produjo salida")
        except Exception as e:
            errores.append(f"PDF {archivo.name}: {e}")

    return convertidos, errores
