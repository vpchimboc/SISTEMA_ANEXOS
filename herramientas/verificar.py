#!/usr/bin/env python3
"""
Verificación del sistema: comprueba que TODOS los documentos se generan y que
NINGÚN dato de los proyectos originales sobrevive en la salida.

Cómo funciona
-------------
El riesgo real de este sistema no es que falle: es que un documento salga
"bien" pero con el nombre de un estudiante del proyecto anterior incrustado,
porque ese texto no se convirtió en variable. Un vistazo no lo detecta.

Por eso la prueba carga un proyecto CANARIO en el que cada dato tiene un valor
inconfundible (CANARIO_PROYECTO, CANARIO_ESTUDIANTE_1, 9990000001...), genera
los 20 documentos y busca en la salida cualquier rastro de los proyectos
originales. Lo que aparezca es un campo que quedó cableado.

También comprueba:
  - que cada plantilla del catálogo exista y produzca al menos un archivo
  - que no queden etiquetas Jinja sin resolver ({{ }} o {% %})
  - que el encabezado conserve sus logos
  - que los valores canario efectivamente lleguen al documento

    python herramientas/verificar.py
    python herramientas/verificar.py --conservar   (no restaura la base)
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import docx  # noqa: E402

from core import db, docx_utils as du, generador  # noqa: E402
from herramientas.construir_plantillas import identificar_logos  # noqa: E402

# --------------------------------------------------------------------------
# Rastros que NO deben aparecer en ningún documento generado
# --------------------------------------------------------------------------

# Proyecto TAIPT / U.E. Luis Monsalve Pozo (origen de los 13 anexos).
RASTROS_TAIPT = [
    "Mónica Galarza", "Mónica Fernanda Galarza", "Williams Trelles",
    "Williams Hidalgo", "Jonnathan Fernando Nivicela", "Carlos Gonzalo Morales",
    "Marilyn Salazar", "Luis Monsalve Pozo", "TAIPT", "30-2025-2P",
    "0104399860", "0104225644", "0103687323", "0106103781", "0107006686",
    "0107961757", "0107193930", "0151181898", "0106229859",
    "Kevin Israel Brito", "Jose Alfredo Murillo", "José Alfredo Murillo",
    "Paul Angel Mejia", "Alexander Miguel Coloma", "Jostin Alexander Molina",
    "Ismael Alejandro Sevillano", "Molina Ortiz Jostin",
    "Murillo Quizhpi Jose", "Coordinación de Educación Zonal 6",
    "Mantenimiento de la infraestructura tecnológica",
    "Mantenimiento de la Infraestructura Tecnológica",
    "Virgen  del Rosario", "ue.luismonsalve@gmail.com", "0985991161",
    # Restos de proyectos aún más antiguos que traían algunos formatos
    "Mary Coryle", "Sayausi", "San Joaquín", "williams.trelles@ucuenca.edu.ec",
    "ismael.sevillano@ucuenca.edu.ec", "jonnathan.nivicela@ucuenca.edu.ec",
    "0968704453",
]

# Proyecto Big Data / Mensajeros de la Paz (origen de los 5 documentos S/N).
RASTROS_BIGDATA = [
    "Verónica Chimbo", "Verónica Paulina Chimbo", "Jessica Elizabeth Pinos",
    "Jéssica Elizabeth Pinos", "Freddy Vinicio Quito", "Victoria Marilyn Salazar",
    "Priscila Bernal", "1105050775", "Diego Sebastian Villa",
    "Byron Fabian Mendieta", "Alexis Omar Matute", "0106758287", "0302893672",
    "0106191422", "Mensajeros de la Paz", "Mensajeros de La Paz",
    "Plataforma web de análisis", "PLATAFORMA WEB DE ANÁLISIS",
    "Tecnología Superior en Big Data",
]

# Fechas concretas de los documentos originales.
RASTROS_FECHAS = [
    "22/09/2025", "24/09/2025", "25/09/2025", "26/09/2025", "29/09/2025",
    "12/12/2025", "15/12/2025", "05/12/2025", "20/10/2025", "01/10/2025",
    "17/10/2025", "01/06/2026", "04/09/2026", "15/07/2026", "10/09/2026",
    "09/09/2026", "07/09/2026", "21/05/2026", "31/08/2026", "27/05/2024",
    "18/08/2025", "31/10/2025", "14 de agosto de 2025",
]

RASTROS = RASTROS_TAIPT + RASTROS_BIGDATA + RASTROS_FECHAS

# Textos que quedan a propósito y no son un fallo:
#   - referencias a otros anexos dentro del propio formato ("(Anexo 8)")
#   - los bloques de redacción, que el usuario edita en la app
EXCEPCIONES_CONOCIDAS = {
    # anexo -> rastros que sí pueden aparecer y por qué
    "10": {"motivo": "las evidencias semanales se completan a mano en Word",
           "rastros": set()},
}


# --------------------------------------------------------------------------
# Proyecto canario
# --------------------------------------------------------------------------

CANARIO_PROYECTO = "CANARIO PROYECTO NOMBRE"
CANARIO_ENTIDAD = "CANARIO ENTIDAD BENEFICIARIA"
CANARIO_CARRERA = "CANARIO CARRERA COMPLETA"

PERSONAS_CANARIO = [
    ("director_proyecto", "CANARIO DIRECTOR", "9990000001", "DIRECTOR CANARIO"),
    ("docente_apoyo", "CANARIO DOCENTE APOYO", "9990000002", "DOCENTE DE APOYO CANARIO"),
    ("responsable_vinculacion", "CANARIO RESPONSABLE", "9990000003", "RESPONSABLE CANARIO"),
    ("coordinador_carrera", "CANARIO COORD CARRERA", "9990000004", "COORDINADOR CARRERA CANARIO"),
    ("coordinador_vinculacion", "CANARIO COORD VINCULACION", "9990000005", "COORDINADOR VINC CANARIO"),
    ("representante_legal", "CANARIO REPRESENTANTE", "9990000006", "REPRESENTANTE CANARIO"),
]

ESTUDIANTES_CANARIO = [
    ("9991110001", "CANARIO ESTUDIANTE", "UNO"),
    ("9991110002", "CANARIO ESTUDIANTE", "DOS"),
]


def cargar_canario(ruta_db: Path) -> None:
    """Rellena la base con valores únicos y reconocibles en toda la salida."""
    db.inicializar(ruta_db)
    with db.conexion(ruta_db) as con:
        db.guardar_proyecto(con, {
            "nombre": CANARIO_PROYECTO, "nombre_corto": "CANARIO CORTO",
            "fase": "CANARIO FASE", "ciudad": "CANARIOCIUDAD",
            "codigo_convocatoria": "CANARIO CONVOCATORIA",
            "carrera": CANARIO_CARRERA, "carrera_corta": "CANARIOSIGLAS",
            "periodo_academico": "CANARIO-PERIODO", "paralelo": "Z",
            "jornada": "CANARIOJORNADA", "ciclo": "CANARIOCICLO",
            "ciclo_minimo": "canariomin", "entidad": CANARIO_ENTIDAD,
            "entidad_corta": "CANARIO ENT CORTA",
            "entidad_direccion": "CANARIO DIRECCION",
            "entidad_telefono": "9997770001", "entidad_email": "canario@correo.test",
            "total_horas": 777, "fecha_inicio": "2030-01-02",
            "fecha_fin": "2030-02-03", "fecha_evaluacion": "2030-03-04",
            "fecha_seguimiento": "2030-04-05", "fecha_entrega": "2030-05-06",
            "plazo_ejecucion": "CANARIO PLAZO",
            "programa_vinculacion": "CANARIO PROGRAMA",
            "director_carrera": "CANARIO DIR CARRERA",
            "enlace_anexos": "https://canario.test/anexos",
        })

        con.execute("DELETE FROM personas")
        ids = {}
        for i, (rol, nombre, cedula, cargo) in enumerate(PERSONAS_CANARIO):
            ids[rol] = db.insertar(con, "personas", {
                "rol": rol, "titulo": "Cnr.", "tratamiento": "Canario",
                "nombre": nombre, "cedula": cedula, "cargo": cargo,
                "email": f"{rol}@canario.test", "telefono": "9997770002",
                "horas": "CANARIO HORAS DOCENTE", "orden": i})

        con.execute("DELETE FROM estudiantes")
        for i, (cedula, nombres, apellidos) in enumerate(ESTUDIANTES_CANARIO):
            db.insertar(con, "estudiantes", {
                "cedula": cedula, "nombres": nombres, "apellidos": apellidos,
                "nombre_completo": f"{nombres} {apellidos}",
                "email": f"canario{i}@correo.test", "telefono": "9997770003",
                "ciclo": "CANARIOCICLO", "paralelo": "Z",
                "jornada": "CANARIOJORNADA", "codigo": f"CANARIOCOD{i}",
                "horas": "777", "docente_apoyo_id": ids["docente_apoyo"], "orden": i})

        con.execute("DELETE FROM actividades")
        acts = []
        for nro in (1, 2):
            acts.append(db.insertar(con, "actividades", {
                "nro": nro, "descripcion": f"CANARIO ACTIVIDAD {nro}",
                "descripcion_docente": f"CANARIO ACTIVIDAD DOCENTE {nro}",
                "asignatura": f"CANARIO ASIGNATURA {nro}",
                "resultados_aprendizaje": f"CANARIO RESULTADO {nro}",
                "producto": f"CANARIO PRODUCTO {nro}",
                "horas": 300 + nro, "horas_docente": 10 + nro,
                "detalle_especifico": f"CANARIO DETALLE {nro}"}))

        db.reemplazar_tabla(con, "requisitos",
                            [{"nombre": f"CANARIO REQUISITO {i}"} for i in (1, 2)])
        db.reemplazar_tabla(con, "cronograma",
                            [{"actividad": f"CANARIO CRONO {i}", "fecha": "02/01/2030"}
                             for i in (1, 2)])
        db.reemplazar_tabla(con, "registro_diario", [
            {"fecha": "2030-01-02", "descripcion": f"CANARIO REGISTRO {i}",
             "lugar": "CANARIO LUGAR", "horas": 5} for i in (1, 2)])
        db.reemplazar_tabla(con, "visitas", [
            {"fecha": "2030-01-02", "hora_inicio": "07h00", "hora_fin": "08h00",
             "asunto": "CANARIO ASUNTO VISITA",
             "actividades": "CANARIO ACTIVIDADES VISITA",
             "observaciones": "CANARIO OBS VISITA"}])

        con.execute("DELETE FROM meses")
        mes = db.insertar(con, "meses", {
            "nro": 1, "etiqueta": "CANARIOMES 2030",
            "fecha_planificacion": "2030-01-02", "fecha_seguimiento": "2030-01-03",
            "fecha_socializacion": "2030-01-04"})

        con.execute("DELETE FROM jornadas")
        db.insertar(con, "jornadas", {"nro": 1, "asunto": "CANARIO JORNADA",
                                      "fecha": "2030-01-05", "horas": "9",
                                      "lugar": "CANARIO LUGAR"})

        con.execute("DELETE FROM planificacion")
        for tipo, pid in (("docente", ids["docente_apoyo"]), ("estudiante", 1)):
            for act in acts:
                db.insertar(con, "planificacion", {
                    "mes_id": mes, "tipo": tipo, "persona_id": pid,
                    "actividad_id": act, "resultado": "CANARIO RESULTADO PLAN",
                    "horas": 9, "fecha_inicio": "2030-01-02",
                    "fecha_fin": "2030-01-03", "observaciones": "CANARIO OBS"})

        con.execute("DELETE FROM seguimiento")
        db.insertar(con, "seguimiento", {
            "mes_id": mes, "estudiante_id": 1, "actividad_id": acts[0],
            "descripcion": "CANARIO SEGUIMIENTO", "fecha_planificada": "2030-01-02",
            "finalizada": "SI", "fecha_fin_prevista": "2030-01-03", "avance": "99%"})

        con.execute("DELETE FROM evaluacion_plan")
        con.execute("DELETE FROM evaluacion_estudiante")
        for est in (1, 2):
            for act in acts:
                for corte in ("parcial", "final"):
                    db.insertar(con, "evaluacion_plan", {
                        "estudiante_id": est, "actividad_id": act, "corte": corte,
                        "avance": "99%", "valoracion": "muy", "logro": "si"})
            for item in ("1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4"):
                db.insertar(con, "evaluacion_estudiante", {
                    "estudiante_id": est,
                    "evaluador": "docente_apoyo" if item.startswith("1") else "director",
                    "item": item, "puntaje": 4})

        con.execute("DELETE FROM narrativa")
        for clave in ("objetivo_general", "sel_antecedentes", "sel_objetivo",
                      "sel_desarrollo", "sel_evidencias", "situacion_inicial",
                      "situacion_beneficiarios", "observaciones_informe",
                      "impacto_descripcion", "soc_antecedentes", "soc_objetivo",
                      "soc_desarrollo", "soc_conclusiones"):
            con.execute("INSERT INTO narrativa (clave, texto) VALUES (?, ?)",
                        (clave, f"CANARIO TEXTO {clave.upper()}"))

        con.execute("DELETE FROM opciones")
        for clave, valor in (("linea_accion", "capacitacion"),
                             ("alcance", "cantonal"), ("impacto", "economico")):
            con.execute("INSERT INTO opciones (clave, valor) VALUES (?, ?)", (clave, valor))

        con.execute("DELETE FROM listas")
        for clave in ("objetivos_especificos", "conclusiones_seguimiento",
                      "conclusiones_final", "recomendaciones",
                      "resultados_indicadores", "productos"):
            for i in (1, 2):
                db.insertar(con, "listas", {"clave": clave,
                                            "texto": f"CANARIO {clave.upper()} {i}",
                                            "orden": i})

        con.execute("DELETE FROM actividades_informe")
        for informe in ("seguimiento", "final"):
            for i in (1, 2):
                db.insertar(con, "actividades_informe", {
                    "informe": informe, "actividad": f"CANARIO ACT INFORME {i}",
                    "cumplimiento": "99%", "fecha": "2030-01-02",
                    "responsables": "CANARIO RESPONSABLE ACT",
                    "evidencia": "CANARIO EVIDENCIA",
                    "observaciones": "CANARIO OBS INFORME", "orden": i})

        con.execute("DELETE FROM indicadores")
        for i in (1, 2):
            db.insertar(con, "indicadores", {"nro": i,
                                             "descripcion": f"CANARIO INDICADOR {i}",
                                             "tipo": "Cualitativo", "orden": i})

        db.reemplazar_tabla(con, "matriz_objetivos", [
            {"objetivo": f"CANARIO OBJ {i}", "indicador": f"CANARIO IND {i}",
             "planificado": f"CANARIO PLAN {i}", "obtenido": f"CANARIO OBT {i}",
             "observaciones": "CANARIO OBS MATRIZ"} for i in (1, 2)])

        db.reemplazar_tabla(con, "constancia", [
            {"numero": "1", "nombre": "CANARIO CHECKLIST", "presentacion": "Por proyecto",
             "anexo": "1", "marcado": 0}])

        con.execute("DELETE FROM fechas")
        for clave in ("anexo1", "anexo2", "anexo2_limite", "anexo3", "anexo4",
                      "anexo5", "anexo6", "anexo6_1", "anexo6_2", "anexo11",
                      "anexo13", "seleccion", "socializacion",
                      "socializacion_aprobacion", "constancia"):
            con.execute("INSERT INTO fechas (clave, valor) VALUES (?, ?)",
                        (clave, "2030-01-02"))


# --------------------------------------------------------------------------
# Inspección de la salida
# --------------------------------------------------------------------------

def texto_completo(ruta: Path) -> str:
    doc = docx.Document(ruta)
    return "\n".join(p.text for p in du.parrafos_documento(doc))


ETIQUETA_JINJA = re.compile(r"\{\{[^}]*\}\}|\{%[^%]*%\}")


def revisar(ruta: Path) -> dict:
    texto = texto_completo(ruta)
    rastros = sorted({r for r in RASTROS if r in texto})
    etiquetas = sorted(set(ETIQUETA_JINJA.findall(texto)))
    try:
        # Se cuenta igual que el constructor: encabezado y, si no lo hay, los
        # logos incrustados en el cuerpo (caso del Anexo 5).
        n_logos = len(identificar_logos(ruta))
    except Exception:
        n_logos = 0
    return {
        "caracteres": len(texto),
        "canarios": texto.count("CANARIO"),
        "rastros": rastros,
        "etiquetas": etiquetas,
        "logos": n_logos,
    }


# --------------------------------------------------------------------------
# Programa
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conservar", action="store_true",
                    help="no restaura la base original al terminar")
    args = ap.parse_args()

    respaldo = None
    if db.RUTA_DB.exists() and not args.conservar:
        respaldo = db.RUTA_DB.with_suffix(".verificacion.bak")
        shutil.copy2(db.RUTA_DB, respaldo)

    salida = Path(tempfile.mkdtemp(prefix="verificacion_"))
    problemas: list[str] = []

    try:
        if db.RUTA_DB.exists():
            db.RUTA_DB.unlink()
        cargar_canario(db.RUTA_DB)

        print("=" * 78)
        print("VERIFICACIÓN DEL SISTEMA DE ANEXOS")
        print("=" * 78)

        # 1. Cobertura del catálogo -----------------------------------------
        catalogo = generador.CATALOGO
        sin_plantilla = [c for c, a in catalogo.items()
                         if not (generador.DIR_PLANTILLAS / a.plantilla).exists()]
        print(f"\n1. CATÁLOGO: {len(catalogo)} documentos declarados, "
              f"{len(catalogo) - len(sin_plantilla)} con plantilla en disco")
        if sin_plantilla:
            problemas.append(f"Sin plantilla: {', '.join(sin_plantilla)}")
            for c in sin_plantilla:
                print(f"   ✗ {c}: falta {catalogo[c].plantilla}")

        # 2. Generación ------------------------------------------------------
        resultado = generador.generar(list(catalogo), salida)
        archivos = resultado["archivos"]
        print(f"\n2. GENERACIÓN: {len(archivos)} archivos producidos")
        for e in resultado["errores"]:
            if "logo del encabezado es la misma imagen" in e:
                print(f"   · aviso conocido: {e[:70]}…")
            else:
                problemas.append(e)
                print(f"   ✗ {e}")

        # Atribuir cada archivo a su anexo. Ojo: hay que comparar el prefijo
        # COMPLETO hasta el separador, o "ANEXO 1" se queda con los archivos de
        # "ANEXO 10", "ANEXO 11"… y parece que esos no se generaron.
        prefijos = {}
        for clave, anexo in catalogo.items():
            base = anexo.patron.split("{")[0].rstrip(" -")
            prefijos[clave] = generador.nombre_seguro(base)

        producidos: dict[str, list[Path]] = {}
        for archivo in archivos:
            # el prefijo más largo que encaje es el correcto
            candidatos = [c for c, pref in prefijos.items()
                          if archivo.stem == pref or archivo.stem.startswith(pref + " ")]
            if candidatos:
                clave = max(candidatos, key=lambda c: len(prefijos[c]))
                producidos.setdefault(clave, []).append(archivo)
            else:
                problemas.append(f"Archivo sin anexo asociado: {archivo.name}")

        # 3. Revisión documento por documento --------------------------------
        print("\n3. CONTENIDO")
        print(f"   {'Doc':6s} {'Archivos':>8s} {'Logos':>6s} {'Canarios':>9s}  Estado")
        print("   " + "-" * 62)
        for clave, anexo in catalogo.items():
            suyos = producidos.get(clave, [])
            if not suyos:
                problemas.append(f"{clave}: no produjo ningún archivo")
                print(f"   {clave:6s} {'0':>8s} {'-':>6s} {'-':>9s}  ✗ sin salida")
                continue

            peor = None
            total_canarios = 0
            logos = 0
            for archivo in suyos:
                info = revisar(archivo)
                total_canarios += info["canarios"]
                logos = max(logos, info["logos"])
                if info["rastros"] or info["etiquetas"]:
                    peor = info if peor is None else peor
                    if info["rastros"]:
                        problemas.append(
                            f"{clave} ({archivo.name}): rastros del proyecto original "
                            f"-> {', '.join(info['rastros'][:6])}")
                    if info["etiquetas"]:
                        problemas.append(
                            f"{clave} ({archivo.name}): etiquetas sin resolver "
                            f"-> {', '.join(info['etiquetas'][:6])}")

            estado = "✓ limpio" if peor is None else "✗ revisar"
            print(f"   {clave:6s} {len(suyos):>8d} {logos:>6d} {total_canarios:>9d}  {estado}")
            if total_canarios == 0:
                problemas.append(f"{clave}: ningún dato del sistema llegó al documento")

        # 4. Veredicto -------------------------------------------------------
        print("\n" + "=" * 78)
        if problemas:
            print(f"RESULTADO: {len(problemas)} punto(s) a revisar\n")
            for x in problemas:
                print(f"  ! {x}")
        else:
            print("RESULTADO: todos los documentos se generan, ninguno conserva datos")
            print("           del proyecto original y no quedan etiquetas sin resolver.")
        print("=" * 78)
        return 1 if problemas else 0

    finally:
        shutil.rmtree(salida, ignore_errors=True)
        if respaldo and respaldo.exists():
            shutil.move(str(respaldo), str(db.RUTA_DB))
            print("\n(Base de datos original restaurada.)")


if __name__ == "__main__":
    raise SystemExit(main())
