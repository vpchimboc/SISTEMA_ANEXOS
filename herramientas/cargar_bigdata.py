#!/usr/bin/env python3
"""
Carga el proyecto de Big Data / Fundación Mensajeros de la Paz (Fase 2).

Es el proyecto con el que vienen llenados los cinco documentos adicionales
(proceso de selección, seguimiento ISTA, informe final ISTA, socialización y
constancia). Deja el sistema listo para generarlos y comparar contra los
originales.

    python herramientas/cargar_bigdata.py --reiniciar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import db  # noqa: E402

NOMBRE = ("Plataforma web de análisis de los datos, aplicando técnicas de minería "
          "de datos y aprendizaje automático para la toma de decisiones de la "
          "fundación Mensajeros de la Paz")

PROYECTO = {
    "nombre": NOMBRE,
    "nombre_corto": "Plataforma Big Data - Mensajeros de la Paz",
    "fase": "Fase 2",
    "ciudad": "Cuenca",
    "carrera": "Tecnología Superior en Big Data",
    "carrera_corta": "Big Data",
    "director_carrera": "Ing. Priscila Bernal. Mgtr.",
    "entidad": "Fundación Mensajeros de La Paz",
    "entidad_corta": "Fundación Mensajeros de la Paz",
    "total_horas": 96,
    "fecha_inicio": "2026-06-01",
    "fecha_fin": "2026-09-04",
    "fecha_seguimiento": "2026-07-15",
    "fecha_entrega": "2026-09-10",
    "plazo_ejecucion": "3 Meses",
    "programa_vinculacion": ("Aplicación de tecnologías para responder a las "
                             "necesidades reales de los sectores más vulnerables."),
    "enlace_anexos": "",
}

PERSONAS = [
    {"rol": "director_proyecto", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": "Verónica Paulina Chimbo Coronel", "cedula": "1105050775",
     "cargo": "Directora del proyecto",
     "horas": "2h/semana por 3 meses = 24h de vinculación", "orden": 0},
    # En este proyecto la directora es además la docente de apoyo.
    {"rol": "docente_apoyo", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": "Verónica Paulina Chimbo Coronel", "cedula": "1105050775",
     "cargo": "DOCENTE DE APOYO",
     "horas": "2h/semana por 3 meses = 24h de vinculación", "orden": 1},
    {"rol": "responsable_vinculacion", "titulo": "Ing.", "tratamiento": "Ingeniera",
     "nombre": "Jessica Elizabeth Pinos Pinos. Mgtr.",
     "cargo": "Responsable de Prácticas pre profesionales de servicio comunitario",
     "orden": 0},
    {"rol": "coordinador_vinculacion", "titulo": "Ing.", "tratamiento": "Ingeniero",
     "nombre": "Freddy Vinicio Quito Baculima. Mgtr.",
     "cargo": "Coordinador de Vinculación con la Sociedad", "orden": 0},
    {"rol": "coordinador_carrera", "titulo": "Ing.", "tratamiento": "Ingeniera",
     "nombre": "Priscila Bernal. Mgtr.", "cargo": "DIRECTORA DE LA CARRERA BIG DATA",
     "orden": 0},
]

ESTUDIANTES = [
    ("0106758287", "Diego Sebastian", "Villa Garcia", "0106758287", "96"),
    ("0302893672", "Byron Fabian", "Mendieta Gordillo", "0302893672", "96"),
    ("0106191422", "Alexis Omar", "Matute Tenecela", "0106191422", "96"),
]

OPCIONES = {
    "linea_accion": "comunitario",
    "alcance": "provincial",
    "impacto": "social",
}

OBJETIVOS = [
    "Desarrollar la base de datos.",
    "Implementar herramientas de análisis de datos.",
    "Capacitar a la comunidad de la Fundación Mensajeros de la Paz.",
    "Elaborar el manual de usuario.",
]

NARRATIVA = {
    "objetivo_general": ("Fortalecer los procesos administrativos y de salud en la "
                         "Fundación Mensajeros de la Paz mediante el desarrollo de una "
                         "aplicación de big data en la web que facilite el proceso de "
                         "toma de decisiones."),
    "sel_antecedentes": (
        "En el marco del proyecto de fortalecimiento de los procesos administrativos y "
        "de salud en la Fundación Mensajeros de la Paz mediante el desarrollo de una "
        "aplicación de big data en la web, se busca involucrar a estudiantes en sus "
        "prácticas pre profesionales. La selección de estudiantes para participar en "
        "este proyecto se basa en los siguientes criterios:\n"
        "Créditos aprobados.\n"
        "Estudiantes con mejor promedio en las asignaturas relacionadas a las "
        "actividades a desarrollar en la Fundación.\n"
        "Número de estudiantes requeridos en esta etapa.\n"
        "Orden de llegada de las solicitudes de los estudiantes interesados."),
    "sel_objetivo": (
        "Brindar a los estudiantes la oportunidad de adquirir experiencia práctica en "
        "el desarrollo de aplicaciones de big data y su aplicación en el ámbito del "
        "servicio social, la administración y la salud."),
    "sel_desarrollo": (
        "Se realizó la publicación de la convocatoria a estudiantes de los últimos "
        "ciclos de la carrera de Big Data para participar en el desarrollo del proyecto "
        "de vinculación en cooperación con la Fundación Mensajeros de la Paz."),
    "sel_evidencias": "",
    "situacion_inicial": (
        "La Fundación Mensajeros de la Paz cuenta con Acuerdo de Creación No. 000103, "
        "de fecha 30 de enero de 1996 otorgado por el Ministerio de Bienestar Social.\n"
        "Es una organización de inspiración cristiana y sin fines de lucro, que propicia "
        "acciones integrales de prevención y restitución de los derechos de los niños, "
        "niñas, adolescentes, jóvenes, mujeres y sus familias.\n"
        "El problema detectado consiste en que la Fundación no cuenta con personal "
        "capacitado para desarrollar la aplicación tecnológica que permita mejorar sus "
        "procesos, especialmente los enfocados en la toma de decisiones informadas."),
    "situacion_beneficiarios": (
        "El Big Data permite el control y la gestión de la información, el soporte a la "
        "toma de decisiones y el desarrollo de las organizaciones.\n"
        "Los estudiantes de la carrera de Big Data están en capacidad de desarrollar el "
        "análisis y diseño de la herramienta que favorece al personal directivo y "
        "administrativo, y a las personas en situación de movilidad humana registradas "
        "en la Fundación."),
    "observaciones_informe": ("De manera general todas las actividades planificadas se "
                              "han realizado en su totalidad y sin novedad."),
    "impacto_descripcion": (
        "La implementación del proyecto de Big Data en la Fundación Mensajeros de la Paz "
        "tuvo un impacto social relevante.\n"
        "Mejora en la toma de decisiones informadas.\n"
        "Optimización de recursos y servicios."),
    "soc_antecedentes": "",
    "soc_objetivo": "",
    "soc_desarrollo": "",
    "soc_conclusiones": "",
}

ACTIVIDADES_SEGUIMIENTO = [
    ("Reunión con el personal administrativo para levantar los requerimientos.", "2026-06-01"),
    ("Identificar los procesos requeridos en cada servicio para crear la base de datos.", "2026-06-04"),
    ("Análisis y diseño de los componentes de la base de datos.", "2026-06-19"),
    ("Levantamiento de la información.", "2026-06-22"),
    ("Proceso de minería de datos.", "2026-07-06"),
    ("Proceso ETL de los datos.", "2026-07-07"),
    ("Realizar las consultas, informes y paneles.", "2026-07-16"),
]

ACTIVIDADES_FINAL = [
    ("Enlace de la base de datos con la página web de la fundación.", "2026-08-14"),
    ("Implementación de la herramienta en la página web de la Fundación.", "2026-08-17"),
    ("Planificación de la capacitación.", "2026-08-18"),
    ("Capacitación del uso de la herramienta para el personal médico y administrativo.", "2026-08-19"),
    ("Creación del manual de usuario de la herramienta.", "2026-08-20"),
    ("Socialización de los resultados a través de redes sociales y prensa.", "2026-08-21"),
]

INDICADORES = [
    (1, "Base de datos", "Cualitativo"),
    (2, "Herramientas de big data", "Cualitativo"),
    (3, "Capacitación al 100% de la comunidad", "Cuantitativo"),
    (4, "Manual de usuario para el manejo de la herramienta", "Cualitativo"),
]

MATRIZ = [
    ("Desarrollar la base de datos", "Base de datos", "Base de datos", "Base de datos", ""),
    ("Implementar la herramienta de análisis de datos", "Herramienta de Big Data",
     "Herramienta de Big Data", "Herramienta de Big Data", ""),
    ("Capacitar a la comunidad de la fundación", "El 100% de la comunidad capacitada",
     "Informe de las capacitaciones desarrolladas", "Informe terminado. Personal capacitado", ""),
    ("Elaborar el manual de usuario", "Manual de usuario para el manejo de la herramienta",
     "Manual de usuario para el manejo de la herramienta", "Manual terminado y entregado", ""),
]

CONCLUSIONES_SEGUIMIENTO = [
    "Durante el seguimiento del proyecto se lograron los objetivos principales establecidos inicialmente.",
    "Se implementó con éxito el análisis y diseño de los componentes de la base de datos.",
    "Se levantó correctamente la información, la cual pasó por el proceso ETL.",
    "Los estudiantes demostraron capacidad y conocimiento en el tratamiento de los datos.",
]

CONCLUSIONES_FINAL = [
    "En el proceso de desarrollo del proyecto se experimentaron situaciones que contribuyeron a la formación de los estudiantes.",
    "A través del análisis de los datos se trabajó con nuevas herramientas del área.",
    "Las actividades desarrolladas permitieron alcanzar los objetivos planteados.",
]

RECOMENDACIONES = [
    "Ampliar el tiempo asignado a las actividades de levantamiento de información.",
    "Ampliar la colaboración con el personal de la entidad beneficiaria desde el inicio del proyecto.",
]

# Checklist de la constancia. La cuarta columna dice a qué anexo del sistema
# corresponde cada fila, para poder marcarla automáticamente al generar.
CONSTANCIA = [
    ("1", "Delegación de docentes", "Por proyecto", "1"),
    ("2", "Convocatoria participación de proyecto de vinculación", "Por proyecto", "2"),
    ("3", "Solicitud de participación en proyecto de vinculación", "Por estudiante", "3"),
    ("S/N", "Proceso de selección", "Por proyecto", "S1"),
    ("4", "Respuesta al estudiante", "Por estudiante", "4"),
    ("5", "Delegación de estudiantes a docentes de apoyo",
     "Por docente de apoyo y/o director de proyecto", "5"),
    ("6", "Plan de Aprendizaje", "Por estudiante", "6"),
    ("7", "Planificación mensual de Actividades", "Por proyecto", "7"),
    ("8", "Registro diario de actividades de los estudiantes", "Por estudiante", "8"),
    ("9", "Seguimiento a cronograma", "Por proyecto", "9"),
    ("10", "Informe de culminación del proyecto de Vinculación (Estudiante)",
     "Por estudiante", "10"),
    ("11", "Evaluación al estudiante", "Por estudiante", "11"),
    ("12", "Registro de beneficiarios", "Por proyecto", "12"),
    ("13", "Registro de visitas a la institución", "Por proyecto", "13"),
    ("S/N", "Informe de Seguimiento al proyecto", "Por proyecto", "S2"),
    ("S/N", "Informe final del proyecto", "Por proyecto", "S3"),
    ("S/N", "Informe de socialización de resultados obtenidos a la comunidad",
     "Por proyecto", "S4"),
]

MESES = [
    (1, "Junio 2026", "2026-06-01", "2026-07-01"),
    (2, "Julio 2026", "2026-07-01", "2026-08-01"),
    (3, "Agosto 2026", "2026-08-01", "2026-09-01"),
]

JORNADAS = [
    (1, "Capacitación en el uso de la plataforma web", "2026-08-19", "3",
     "Fundación Mensajeros de la Paz"),
]

FECHAS = {
    "seleccion": "2026-05-21",
    "socializacion": "2026-09-07",
    "socializacion_aprobacion": "2026-09-10",
    "constancia": "2026-09-09",
}


def cargar(reiniciar: bool = False) -> None:
    if reiniciar and db.RUTA_DB.exists():
        db.RUTA_DB.unlink()
    db.inicializar()

    with db.conexion() as con:
        db.guardar_proyecto(con, PROYECTO)

        con.execute("DELETE FROM personas")
        for persona in PERSONAS:
            db.insertar(con, "personas", persona)

        con.execute("DELETE FROM estudiantes")
        for i, (cedula, nombres, apellidos, codigo, horas) in enumerate(ESTUDIANTES):
            db.insertar(con, "estudiantes", {
                "cedula": cedula, "nombres": nombres, "apellidos": apellidos,
                "nombre_completo": f"{nombres} {apellidos}",
                "codigo": codigo, "horas": horas, "orden": i,
            })

        con.execute("DELETE FROM opciones")
        for clave, valor in OPCIONES.items():
            con.execute("INSERT INTO opciones (clave, valor) VALUES (?, ?)", (clave, valor))

        con.execute("DELETE FROM narrativa")
        for clave, texto in NARRATIVA.items():
            con.execute("INSERT INTO narrativa (clave, texto) VALUES (?, ?)", (clave, texto))

        con.execute("DELETE FROM listas")
        listas = {
            "objetivos_especificos": OBJETIVOS,
            "conclusiones_seguimiento": CONCLUSIONES_SEGUIMIENTO,
            "conclusiones_final": CONCLUSIONES_FINAL,
            "recomendaciones": RECOMENDACIONES,
            "resultados_indicadores": [
                "Conjunto de directrices claras sobre los datos requeridos.",
                "Mapeo completo de los procesos y flujos de trabajo de cada servicio.",
                "Base de datos implementada y depurada.",
                "Consultas y panel de control con los datos relevantes.",
                "Manual de usuario entregado.",
            ],
            "productos": [
                "Informe de obtención de datos de la fundación y base de datos.",
                "Registro fotográfico del personal de la fundación.",
                "Informe de requerimientos de análisis de datos.",
                "Informes y scripts del análisis de datos en Power BI.",
                "Matriz de base de datos de las personas en movilidad humana.",
                "Informe de plan de capacitación e informe de capacitación.",
                "Manual de usuario de la herramienta.",
            ],
        }
        for clave, textos in listas.items():
            for i, texto in enumerate(textos):
                db.insertar(con, "listas", {"clave": clave, "texto": texto, "orden": i})

        nombres_est = "\n".join(f"{n} {a}" for _, n, a, _, _ in ESTUDIANTES)
        con.execute("DELETE FROM actividades_informe")
        for informe, filas, evidencia in (
                ("seguimiento", ACTIVIDADES_SEGUIMIENTO, "Anexo 6.1\nAnexo 7\nAnexo 8"),
                ("final", ACTIVIDADES_FINAL, "Anexo 8 y 10")):
            for i, (actividad, fecha) in enumerate(filas):
                db.insertar(con, "actividades_informe", {
                    "informe": informe, "actividad": actividad,
                    "cumplimiento": "50%" if informe == "seguimiento" else "100%",
                    "fecha": fecha, "responsables": nombres_est,
                    "evidencia": evidencia, "observaciones": "Ninguna", "orden": i})

        con.execute("DELETE FROM indicadores")
        for i, (nro, descripcion, tipo) in enumerate(INDICADORES):
            db.insertar(con, "indicadores", {"nro": nro, "descripcion": descripcion,
                                             "tipo": tipo, "orden": i})

        db.reemplazar_tabla(con, "matriz_objetivos", [
            {"objetivo": o, "indicador": i, "planificado": pl,
             "obtenido": ob, "observaciones": obs}
            for o, i, pl, ob, obs in MATRIZ])

        db.reemplazar_tabla(con, "constancia", [
            {"numero": n, "nombre": nom, "presentacion": pr, "anexo": a, "marcado": 0}
            for n, nom, pr, a in CONSTANCIA])

        # Los estudiantes quedan a cargo de la docente de apoyo.
        docente = con.execute(
            "SELECT id FROM personas WHERE rol = 'docente_apoyo' LIMIT 1").fetchone()
        if docente:
            con.execute("UPDATE estudiantes SET docente_apoyo_id = ?", (docente["id"],))

        con.execute("DELETE FROM meses")
        for nro, etiqueta, f_plan, f_seg in MESES:
            db.insertar(con, "meses", {
                "nro": nro, "etiqueta": etiqueta, "fecha_planificacion": f_plan,
                "fecha_seguimiento": f_seg, "fecha_socializacion": f_plan})

        con.execute("DELETE FROM jornadas")
        for nro, asunto, fecha, horas, lugar in JORNADAS:
            db.insertar(con, "jornadas", {"nro": nro, "asunto": asunto, "fecha": fecha,
                                          "horas": horas, "lugar": lugar})

        for clave, valor in FECHAS.items():
            con.execute("INSERT OR REPLACE INTO fechas (clave, valor) VALUES (?, ?)",
                        (clave, valor))

    print(f"Proyecto Big Data / Mensajeros de la Paz cargado en {db.RUTA_DB}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reiniciar", action="store_true", help="borra la base antes de cargar")
    cargar(**vars(ap.parse_args()))
