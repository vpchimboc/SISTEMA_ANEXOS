#!/usr/bin/env python3
"""
Carga la SÉPTIMA FASE del proyecto: U.E. Zoila Aurora Palacios (carrera TAIPT).

Los datos salen del "Informe Continuación de Proyecto Mantenimiento Laboratorios
UE Zoila Esperanza Palacios - TAIPT.docx".

Los 13 estudiantes se toman de RegistroAsistencia-TAIPT-AC1-202-A.xls, que
tiene exactamente los 13 participantes que el informe anuncia.

Lo que ninguna de las dos fuentes dice queda marcado como (COMPLETAR) para que
salte a la vista en la app y en cualquier documento generado antes de revisarlo:
  - el docente de apoyo
  - el responsable de prácticas pre profesionales de la carrera
  - el código de la convocatoria

Ojo con el nombre: el ARCHIVO dice "Zoila Esperanza Palacios" pero el TEXTO del
informe dice "Zoila Aurora Palacios" de principio a fin. Se usa el del texto.

    python herramientas/cargar_zoila.py --reiniciar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import db  # noqa: E402

FALTA = "(COMPLETAR)"

CARRERA = "Administración de Infraestructura y Plataformas Tecnológicas"
ENTIDAD = "Unidad Educativa Zoila Aurora Palacios"

PROYECTO = {
    "nombre": ("Mantenimiento de la infraestructura tecnológica y red de datos de "
               "laboratorios de computación de las Unidades Educativas Fiscales de "
               "la Coordinación de Educación Zonal 6 - Séptima Fase Unidad "
               "Educativa Zoila Aurora Palacios"),
    "nombre_corto": "Mantenimiento Laboratorios U.E. Zoila Aurora Palacios",
    "fase": "Séptima Fase",
    "ciudad": "Cuenca",
    "codigo_convocatoria": FALTA,
    "carrera": f"Tecnología Superior en {CARRERA}",
    "carrera_corta": "TAIPT",
    "periodo_academico": FALTA,
    "paralelo": "A",
    "jornada": "Matutina",
    "ciclo": "Cuarto",
    "ciclo_minimo": "cuarto",
    "entidad": ENTIDAD,
    "entidad_corta": "U.E. Zoila Aurora Palacios",
    "entidad_direccion": FALTA,
    "entidad_telefono": FALTA,
    "entidad_email": FALTA,
    "total_horas": 100,
    "fecha_inicio": "2026-07-20",
    "fecha_fin": "2026-09-11",
    "fecha_evaluacion": "2026-09-11",
    "fecha_elaboracion": "2026-07-11",
    "fecha_entrega": "2026-07-11",
    "lugar": "U.E. Zoila Aurora Palacios",
    "plazo_ejecucion": "2 meses",
    "programa_vinculacion": ("Aplicación de tecnologías para responder a las "
                             "necesidades reales de los sectores más vulnerables."),
    "director_carrera": "Mgtr. Mónica Galarza Rodas",
    "entidad_descripcion": (
        "Unidad Educativa Zoila Aurora Palacios, institución fiscal adscrita a la "
        "Coordinación de Educación Zonal 6."),
}

PERSONAS = [
    {"rol": "director_proyecto", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": "Diego Calé", "cedula": FALTA, "cargo": "DIRECTOR DE PROYECTO",
     "horas": FALTA, "orden": 0},
    # El informe no nombra al docente de apoyo: hay que completarlo antes de
    # generar los anexos 1, 5, 9 y 13.
    {"rol": "docente_apoyo", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": FALTA, "cedula": FALTA, "cargo": "DOCENTE DE APOYO",
     "horas": FALTA, "orden": 0},
    {"rol": "responsable_vinculacion", "titulo": "Ing.", "tratamiento": "Ingeniero",
     "nombre": FALTA, "cedula": "",
     "cargo": "Responsable de Prácticas pre profesionales de servicio comunitario",
     "orden": 0},
    {"rol": "coordinador_carrera", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": "Mónica Galarza Rodas", "cedula": "",
     "cargo": f"COORDINADORA DE LA CARRERA DE {CARRERA.upper()}", "orden": 0},
    {"rol": "coordinador_vinculacion", "titulo": "Ing.", "tratamiento": "Ingeniero",
     "nombre": "Vinicio Quito", "cedula": "",
     "cargo": "Coordinador de Vinculación con la Sociedad", "orden": 0},
    {"rol": "representante_legal", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": "Alexandra Ortega", "cedula": FALTA,
     "cargo": "RECTORA U.E. ZOILA AURORA PALACIOS", "telefono": FALTA,
     "email": FALTA, "orden": 0},
]

# Las ocho actividades salen del cronograma valorado del informe (ANEXO 1).
# El reparto de horas no consta ahí: se mantiene el de las fases anteriores,
# que suma las 100 horas por estudiante que el informe sí declara.
ACTIVIDADES = [
    (1, "Recorrido por el laboratorio de la U.E. con los estudiantes para la "
        "distribución de actividades.",
     "Lenguaje y Comunicación",
     "Articula los elementos didácticos y contenidos de la asignatura con los ejes transversales.",
     "Informe de visita técnica al laboratorio de la U.E.", 2, 30.0),
    (2, "Reunión entre docentes, estudiantes y representantes de la U.E. para "
        "establecer los requerimientos de software.",
     "Soporte de Hardware y Aplicaciones Informáticas",
     "Comprender la organización de los distintos componentes de un procesador y sus interrelaciones.",
     "Acta de reunión entre docentes, estudiantes y representantes de la U.E.", 2, 30.0),
    (3, "Levantamiento de información sobre el estado actual del laboratorio de "
        "computación y planificación de mantenimiento preventivo.",
     "Arquitectura de Computadores",
     "Comprender la organización de los distintos componentes de un procesador y sus interrelaciones.",
     "Fichas de Registro de Operaciones de Mantenimiento.", 16, 125.0),
    (4, "Ejecución de mantenimiento preventivo en el Laboratorio de Computación.",
     "Laboratorio de Infraestructura II",
     "Conocer las características y requerimientos para la instalación de un servidor Windows e instalarlo.",
     "Fichas de Registro de Operaciones de Mantenimiento.", 50, 625.0),
    (5, "Levantamiento de información sobre el estado actual de la red de datos y "
        "planificación de mantenimiento preventivo en puntos de conexión de red.",
     "Redes de Datos I",
     "Conocer los principios fundamentales de la estructura de red y sus componentes.",
     "Informes de Revisión Técnica", 5, 200.0),
    (6, "Ejecución de mantenimiento preventivo en puntos de conexión de red.",
     "Redes de Datos II",
     "Diseñar una red de área amplia utilizando diferentes tipos de dispositivos.",
     "Fichas de Registro de Operaciones de Mantenimiento.", 10, 125.0),
    (7, "Planificación de temas de capacitación en base a requerimientos institucionales.",
     "Lenguaje y Comunicación",
     "Maneja criterios de diseño centrados en el usuario-cliente.",
     "Informes de capacitación", 10, 128.0),
    (8, "Ejecución de capacitación.",
     "Lenguaje y Comunicación",
     "Proporcionar a los alumnos un conocimiento más detallado acerca del hardware del computador.",
     "Informes de capacitación", 5, 450.0),
]

# Los 13 estudiantes salen de RegistroAsistencia-TAIPT-AC1-202-A. El informe
# anuncia justo 13 participantes, así que la lista cuadra.
# El "sexo" se deduce del nombre y solo decide si el Anexo 4 dice "Señor" o
# "Señorita": conviene revisarlo. El correo no consta en ninguna fuente.
ESTUDIANTES = [
    ("0150796175", "NAYELY DE LOS ANGELES", "ANGUISACA CRESPO", "F"),
    ("0107385387", "DANIELA ESTEFANIA", "ARAUZ BELTRAN", "F"),
    ("1106235169", "RAFAEL BENJAMIN", "ARMIJOS MERINO", "M"),
    ("0930282256", "CRISTHIAN JAVIER", "CAMPUZANO CEVALLOS", "M"),
    ("0104611421", "PABLO XAVIER", "CARPIO RUIZ", "M"),
    ("0150563534", "KAROL FERNANDA", "CHAVEZ JARA", "F"),
    ("0107984999", "HENRY JOSUE", "CLAVIJO LLIVICHUZHCA", "M"),
    ("0958724593", "PABLO STIVEN", "DAVILA CEPEDA", "M"),
    ("0104048194", "JORGE ALBERTO", "ESPARZA CASTILLO", "M"),
    ("0150871374", "CHRISTOPHER JOSUE", "LLANOS AYALA", "M"),
    ("0150304699", "PAUL DAVID", "MOROCHO FAJARDO", "M"),
    ("0150557882", "ANAHI DEL ROSARIO", "OCHOA GONZALEZ", "F"),
    ("0107410607", "CHRISTIAN SANTIAGO", "SACAQUIRIN PEREIRA", "M"),
]

MESES = [
    (1, "Julio 2026", "2026-07-20", "2026-08-03", "2026-07-20"),
    (2, "Agosto 2026", "2026-08-03", "2026-09-01", "2026-08-03"),
    (3, "Septiembre 2026", "2026-09-01", "2026-09-11", "2026-09-01"),
]

OBJETIVO_GENERAL = (
    "Fortalecer los procesos educativos de unidades educativas fiscales, mediante "
    "el mantenimiento preventivo de la infraestructura tecnológica de sus "
    "laboratorios de computación, mejorando la disponibilidad de los recursos "
    "tecnológicos que facilitan las actividades académicas de la comunidad educativa.")

OBJETIVOS_ESPECIFICOS = [
    "Dar continuidad al proyecto de mantenimiento de la infraestructura tecnológica "
    "y de la red de datos de los laboratorios de computación de las unidades "
    "educativas fiscales de la Coordinación de Educación Zonal 6, mediante la "
    "ejecución de una séptima fase en la Unidad Educativa Zoila Aurora Palacios.",
    "Realizar una revisión técnica del cableado estructurado y de la red de datos "
    "del laboratorio de computación, con el fin de identificar necesidades de "
    "mejora y garantizar su correcto funcionamiento.",
    "Fortalecer las competencias de la comunidad educativa mediante procesos de "
    "capacitación orientados al uso adecuado y cuidado del laboratorio de "
    "computación, así como al manejo de herramientas y plataformas tecnológicas "
    "aplicadas a la enseñanza y el aprendizaje.",
]

CONCLUSIONES = [
    "La continuidad del proyecto en su séptima fase permitirá fortalecer los "
    "procesos educativos de la Unidad Educativa Zoila Aurora Palacios mediante "
    "actividades de mantenimiento preventivo de la infraestructura tecnológica, "
    "contribuyendo a mejorar la disponibilidad, confiabilidad y funcionamiento de "
    "los laboratorios de computación en beneficio de la comunidad educativa.",
    "La revisión técnica de los equipos informáticos, del cableado estructurado y "
    "de la red de datos permitirá identificar oportunamente las necesidades de "
    "mantenimiento y mejora, favoreciendo un entorno tecnológico más seguro, "
    "estable y eficiente para el desarrollo de las actividades académicas.",
    "Las actividades de capacitación dirigidas a docentes y estudiantes "
    "fortalecerán las competencias digitales de la comunidad educativa, "
    "promoviendo el uso adecuado de los recursos tecnológicos, el cuidado de los "
    "equipos y el aprovechamiento de herramientas y plataformas tecnológicas.",
    "En la ejecución de esta séptima fase participarán 13 estudiantes de la "
    "Carrera de Administración de Infraestructura y Plataformas Tecnológicas, y "
    "cada estudiante cumplirá un total de 100 horas de vinculación.",
]

RECOMENDACIONES = [
    "Dar continuidad a las siguientes fases del proyecto de vinculación en otras "
    "instituciones educativas fiscales de la Coordinación de Educación Zonal 6, "
    "con el propósito de ampliar el impacto social y contribuir al fortalecimiento "
    "de la infraestructura tecnológica de los laboratorios de computación.",
    "Continuar promoviendo la participación activa de estudiantes de la carrera en "
    "proyectos de vinculación con la sociedad, fortaleciendo su formación práctica "
    "y el desarrollo de competencias técnicas, trabajo colaborativo, liderazgo y "
    "compromiso con las necesidades de la comunidad.",
]

ANTECEDENTES = (
    "El Reglamento de Régimen Académico, en su artículo 42, establece como "
    "requisito previo a la obtención del título que las y los estudiantes acrediten "
    "servicios a la comunidad mediante prácticas preprofesionales debidamente "
    "monitoreadas, realizadas en coordinación con organizaciones comunitarias, "
    "empresas e instituciones públicas y privadas relacionadas con la especialidad.\n"
    "El proyecto se ejecuta bajo el convenio VC-ISTA-46-2023 entre la Coordinación "
    "de Educación Zonal 6 y el Instituto Superior Tecnológico del Azuay.\n"
    "Fases ya ejecutadas: Sayausí (jul–oct 2023), San Joaquín (feb–may 2024), "
    "Chiquintad (nov–dic 2024), Remigio Romero y Cordero (nov–dic 2024), "
    "Luis Monsalve Pozo (sep 2025–ene 2026) y Mary Corylé (sep 2025–ene 2026).\n"
    "Esta séptima fase extiende las acciones a la Unidad Educativa Zoila Aurora "
    "Palacios, con requerimientos tecnológicos y de conectividad equivalentes.")

REQUISITOS = ["Electrónica I", "Cloud Computing", "Data Center",
              "Gestión de Bases de Datos", "Seguridad Informática"]

FECHAS = {clave: "2026-07-20" for clave in
          ("anexo1", "anexo2", "anexo3", "anexo4", "anexo5", "anexo6")}
FECHAS.update({
    "anexo2_limite": "2026-07-17",
    "anexo6_1": "2026-08-14",
    "anexo6_2": "2026-09-11",
    "anexo11": "2026-09-11",
    "anexo13": "2026-07-20",
    "seleccion": "2026-07-11",
    "socializacion": "2026-09-11",
    "socializacion_aprobacion": "2026-09-11",
    "constancia": "2026-09-11",
})

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
        docente = None
        for i, (cedula, nombres, apellidos, sexo) in enumerate(ESTUDIANTES):
            db.insertar(con, "estudiantes", {
                "cedula": cedula,
                "nombres": nombres.title(), "apellidos": apellidos.title(),
                "nombre_completo": f"{nombres.title()} {apellidos.title()}",
                "email": "", "telefono": "",
                "ciclo": PROYECTO["ciclo"], "paralelo": PROYECTO["paralelo"],
                "jornada": PROYECTO["jornada"], "codigo": cedula,
                "horas": str(PROYECTO["total_horas"]), "sexo": sexo, "orden": i})
        fila = con.execute(
            "SELECT id FROM personas WHERE rol = 'docente_apoyo' LIMIT 1").fetchone()
        if fila:
            con.execute("UPDATE estudiantes SET docente_apoyo_id = ?", (fila["id"],))

        con.execute("DELETE FROM actividades")
        for nro, desc, asig, res, prod, horas, monto in ACTIVIDADES:
            db.insertar(con, "actividades", {
                "nro": nro, "descripcion": desc, "descripcion_docente": desc,
                "asignatura": asig, "resultados_aprendizaje": res,
                "producto": prod, "horas": horas, "horas_docente": 6,
                "detalle_especifico": f"Presupuesto referencial: USD {monto:.2f}"})

        db.reemplazar_tabla(con, "requisitos", [{"nombre": r} for r in REQUISITOS])
        db.reemplazar_tabla(con, "cronograma", [
            {"actividad": "Emisión de la convocatoria", "fecha": "15/07/2026"},
            {"actividad": "Recepción de solicitudes", "fecha": "17/07/2026"},
            {"actividad": "Proceso de selección", "fecha": "18/07/2026"},
            {"actividad": "Notificación de resultados", "fecha": "18/07/2026"},
        ])

        con.execute("DELETE FROM meses")
        for nro, etiqueta, f_plan, f_seg, f_soc in MESES:
            db.insertar(con, "meses", {
                "nro": nro, "etiqueta": etiqueta, "fecha_planificacion": f_plan,
                "fecha_seguimiento": f_seg, "fecha_socializacion": f_soc})

        con.execute("DELETE FROM narrativa")
        narrativa = {
            "objetivo_general": OBJETIVO_GENERAL,
            "situacion_inicial": ANTECEDENTES,
            "sel_antecedentes": ANTECEDENTES,
            "sel_objetivo": OBJETIVO_GENERAL,
            "sel_desarrollo": FALTA,
            "sel_evidencias": "",
            "situacion_beneficiarios": FALTA,
            "observaciones_informe": "",
            "impacto_descripcion": FALTA,
            "soc_antecedentes": "", "soc_objetivo": "",
            "soc_desarrollo": "", "soc_conclusiones": "",
        }
        for clave, texto in narrativa.items():
            con.execute("INSERT INTO narrativa (clave, texto) VALUES (?, ?)",
                        (clave, texto))

        con.execute("DELETE FROM opciones")
        for clave, valor in (("linea_accion", "asesoria"),
                             ("alcance", "cantonal"), ("impacto", "social")):
            con.execute("INSERT INTO opciones (clave, valor) VALUES (?, ?)",
                        (clave, valor))

        con.execute("DELETE FROM listas")
        for clave, textos in (("objetivos_especificos", OBJETIVOS_ESPECIFICOS),
                              ("conclusiones_seguimiento", CONCLUSIONES),
                              ("conclusiones_final", CONCLUSIONES),
                              ("recomendaciones", RECOMENDACIONES)):
            for i, texto in enumerate(textos):
                db.insertar(con, "listas", {"clave": clave, "texto": texto, "orden": i})

        # Actividades de los informes ISTA, tomadas del cronograma valorado.
        con.execute("DELETE FROM actividades_informe")
        for informe in ("seguimiento", "final"):
            for i, (_, desc, _, _, _, _, _) in enumerate(ACTIVIDADES):
                db.insertar(con, "actividades_informe", {
                    "informe": informe, "actividad": desc,
                    "cumplimiento": "0%", "fecha": "", "responsables": FALTA,
                    "evidencia": "Anexo 8", "observaciones": "Ninguna", "orden": i})

        db.reemplazar_tabla(con, "constancia", [
            {"numero": n, "nombre": nom, "presentacion": pr, "anexo": a, "marcado": 0}
            for n, nom, pr, a in CONSTANCIA])

        con.execute("DELETE FROM fechas")
        for clave, valor in FECHAS.items():
            con.execute("INSERT INTO fechas (clave, valor) VALUES (?, ?)", (clave, valor))

    print(f"Séptima fase (U.E. Zoila Aurora Palacios) cargada en {db.RUTA_DB}")
    print("\nFalta completar en la app:")
    print("  · Estudiantes  — 13 cargados del registro de asistencia; faltan")
    print("                   correos y conviene revisar el sexo (Señor/Señorita)")
    print("  · Personas     — docente de apoyo y responsable de vinculación")
    print("  · Proyecto     — periodo académico, código de convocatoria,")
    print("                   dirección/teléfono/correo de la U.E.")
    print("  · Informes     — desarrollo, situación de beneficiarios e impacto")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reiniciar", action="store_true", help="borra la base antes de cargar")
    cargar(**vars(ap.parse_args()))
