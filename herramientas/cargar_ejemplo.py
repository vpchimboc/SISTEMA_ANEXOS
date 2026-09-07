#!/usr/bin/env python3
"""
Carga en la base los datos del proyecto anterior (U.E. Luis Monsalve Pozo).

Sirve para dos cosas: tener datos con los que probar que lo generado sale
idéntico a los anexos oficiales, y dejar el sistema con un ejemplo completo
que se puede editar desde la app para el proyecto siguiente.

    python herramientas/cargar_ejemplo.py [--reiniciar]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import db  # noqa: E402

PROYECTO = {
    "nombre": ("Mantenimiento de la infraestructura tecnológica y red de datos de "
               "laboratorios de computación de las unidades educativas de la "
               "Coordinación de Educación Zonal 6 - Fase V Unidad Educativa "
               "Luis Monsalve Pozo"),
    "nombre_corto": "Mantenimiento Laboratorios U.E. Luis Monsalve Pozo",
    "fase": "Fase V",
    "ciudad": "Cuenca",
    "codigo_convocatoria": "CONVOCATORIA – TAIPT – 2025 – 02",
    "carrera": "Tecnología Superior en Administración de Infraestructura y Plataformas Tecnológicas",
    "carrera_corta": "TAIPT",
    "periodo_academico": "30-2025-2P",
    "paralelo": "A",
    "jornada": "Matutina",
    "ciclo": "Cuarto",
    "ciclo_minimo": "cuarto",
    "entidad": "Unidad Educativa Luis Monsalve Pozo",
    "entidad_corta": "U.E. Luis Monsalve Pozo",
    "entidad_direccion": "Calle Virgen del Rosario y Santa Catalina",
    "entidad_telefono": "0985991161",
    "entidad_email": "ue.luismonsalve@gmail.com",
    "total_horas": 100,
    "fecha_inicio": "2025-09-29",
    "fecha_fin": "2025-12-12",
    "fecha_evaluacion": "2025-12-15",
    "fecha_elaboracion": "2025-09-26",
    "lugar": "U.E. Luis Monsalve Pozo",
}

PERSONAS = [
    {"rol": "director_proyecto", "titulo": "Ing.", "tratamiento": "Ingeniero",
     "nombre": "Williams Hidalgo Trelles Ávila", "cedula": "0104399860",
     "cargo": "DIRECTOR", "email": "williams.trelles@ucuenca.edu.ec", "orden": 0},
    {"rol": "docente_apoyo", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": "Williams Hidalgo Trelles Ávila", "cedula": "0104399860",
     "cargo": "DOCENTE DE APOYO", "email": "williams.trelles@ucuenca.edu.ec", "orden": 0},
    {"rol": "docente_apoyo", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": "Mónica Galarza Rodas", "cedula": "0104225644",
     "cargo": "DOCENTE DE APOYO", "email": "monica.galarza@ucuenca.edu.ec", "orden": 1},
    {"rol": "responsable_vinculacion", "titulo": "Ing.", "tratamiento": "Ingeniero",
     "nombre": "Jonnathan Fernando Nivicela Arbito", "cedula": "",
     "cargo": "Responsable de Prácticas pre profesionales de servicio comunitario",
     "email": "jonnathan.nivicela@ucuenca.edu.ec", "orden": 0},
    {"rol": "coordinador_carrera", "titulo": "Ing.", "tratamiento": "Ingeniera",
     "nombre": "Mónica Fernanda Galarza Rodas Mgtr.", "cedula": "0104225644",
     "cargo": "COORDINADORA DE LA CARRERA TAIPT", "email": "", "orden": 0},
    {"rol": "coordinador_vinculacion", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": "Marilyn Salazar", "cargo": "Coordinador de Vinculación", "orden": 0},
    {"rol": "representante_legal", "titulo": "Mgtr.", "tratamiento": "Magíster",
     "nombre": "Carlos Gonzalo Morales Figueroa", "cedula": "0103687323",
     "cargo": "Representante Legal", "telefono": "0985991161",
     "email": "ue.luismonsalve@gmail.com", "orden": 0},
]

ESTUDIANTES = [
    ("0106103781", "Kevin Israel", "Brito Dumaguala", "kevin.brito.est@tecazuay.edu.ec", "3", "M", 0),
    ("0107006686", "Jose Alfredo", "Murillo Quizhpi", "josea.murillo.est@tecazuay.edu.ec", "3", "M", 1),
    ("0107961757", "Paul Angel", "Mejia Morocho", "paul.mejia.est@tecazuay.edu.ec", "4", "M", 0),
    ("0107193930", "Alexander Miguel", "Coloma Ortiz", "alexander.coloma.est@tecazuay.edu.ec", "4", "M", 1),
    ("0151181898", "Jostin Alexander", "Molina Ortiz", "jostin.molina.est@tecazuay.edu.ec", "4", "M", 0),
]

ACTIVIDADES = [
    (1, "Recorrido por los Laboratorios de la U.E. con los estudiantes para la distribución de actividades.",
     "Lenguaje y Comunicación",
     "Articula los elementos didácticos y contenidos de la asignatura con los ejes transversales.",
     "Informe de visita técnica a los laboratorios de la U.E.", 2),
    (2, "Reunión entre docentes, estudiantes y representantes de la U.E. para establecer los requerimientos de software.",
     "Soporte de Hardware y Aplicaciones Informáticas",
     "Comprender la organización de los distintos componentes de un procesador y sus interrelaciones.",
     "Acta de reunión entre docentes, estudiantes y representantes de la U.E.", 2),
    (3, "Levantamiento de información sobre el estado actual de los laboratorios de computación y planificación de mantenimiento preventivo.",
     "Arquitectura de Computadores",
     "Comprender la organización de los distintos componentes de un procesador y sus interrelaciones.",
     "Fichas de Registro de Operaciones de Mantenimiento.", 16),
    (4, "Ejecución de mantenimiento preventivo en laboratorios de computación.",
     "Laboratorio de Infraestructura II",
     "Conocer las características y requerimientos para la instalación de un servidor Windows e instalarlo.",
     "Fichas de Registro de Operaciones de Mantenimiento.", 50),
    (5, "Levantamiento de información sobre el estado actual de la red de datos y planificación de mantenimiento preventivo en puntos de conexión de red.",
     "Redes de Datos I",
     "Conocer los principios fundamentales de la estructura de red y sus componentes.",
     "Informes de Revisión Técnica", 5),
    (6, "Ejecución de mantenimiento preventivo en puntos de conexión de red.",
     "Redes de Datos II",
     "Diseñar una red de área amplia utilizando diferentes tipos de dispositivos.",
     "Fichas de Registro de Operaciones de Mantenimiento.", 10),
    (7, "Planificación de temas de capacitación en base a requerimientos institucionales.",
     "Lenguaje y Comunicación",
     "Maneja criterios de diseño centrados en el usuario-cliente.",
     "Informes de capacitación", 10),
    (8, "Ejecución de capacitación dirigida a la comunidad educativa.",
     "Lenguaje y Comunicación",
     "Proporcionar a los alumnos un conocimiento más detallado acerca del hardware del computador.",
     "Informes de capacitación", 5),
]

REQUISITOS = ["Electrónica I", "Cloud Computing", "Data Center",
              "Gestión de Bases de Datos", "Seguridad Informática"]

CRONOGRAMA = [
    ("Emisión de la convocatoria", "23/09/2025"),
    ("Recepción de solicitudes", "24/09/2025"),
    ("Proceso de selección", "25/09/2025"),
    ("Notificación de resultados", "25/09/2025"),
]

MESES = [
    (1, "Septiembre 2025", "2025-09-26", "2025-10-01", "2025-09-26"),
    (2, "Octubre 2025", "2025-10-01", "2025-11-03", "2025-10-01"),
    (3, "Noviembre 2025", "2025-11-03", "2025-12-01", "2025-11-03"),
    (4, "Diciembre 2025", "2025-12-01", "2025-12-15", "2025-12-01"),
]

REGISTRO = [
    ("2025-09-29", "Recorrido por los Laboratorios de la U.E. con los estudiantes para la distribución de actividades.", 2),
    ("2025-09-29", "Reunión entre docentes, estudiantes y representantes de la unidad educativa para establecer los requerimientos de software.", 2),
    ("2025-09-30", "Inspección de hardware y periféricos: examen visual de las computadoras en busca de desgaste o daños físicos.", 4),
    ("2025-10-01", "Pruebas de operación: encendido de equipos y evaluación de su comportamiento.", 4),
    ("2025-10-02", "Inventario inicial: registro de características e identificativos y evaluación del disco duro.", 4),
    ("2025-10-03", "Inventario inicial: registro de características e identificativos y evaluación del disco duro.", 4),
    ("2025-10-08", "Creación de copias de seguridad del disco de datos de los estudiantes.", 5),
    ("2025-10-09", "Creación de copias de seguridad del disco de datos de los estudiantes.", 5),
    ("2025-10-13", "Desarmado y limpieza interna y externa de equipos con sopladoras de aire.", 5),
    ("2025-12-12", "Impartición de jornada de capacitación.", 2),
]

JORNADAS = [
    (1, "Primera Jornada de Capacitación", "2025-12-05", "3", "U.E. Luis Monsalve Pozo"),
    (2, "Segunda Jornada de Capacitación", "2025-12-12", "2", "U.E. Luis Monsalve Pozo"),
]

VISITAS = [
    ("2025-09-29", "14h00", "15h00",
     "Visita de seguimiento y observación de las actividades del proyecto de vinculación.",
     "Diálogo con el representante legal del establecimiento sobre el rendimiento del estudiante. "
     "Diálogo y observación con los estudiantes sobre las actividades ejecutadas.", ""),
    ("2025-10-17", "14h00", "15h00",
     "Visita de seguimiento y observación de las actividades del proyecto de vinculación.",
     "Diálogo con el representante legal del establecimiento sobre el rendimiento del estudiante. "
     "Diálogo y observación con los estudiantes sobre las actividades ejecutadas.", ""),
]

FECHAS = {
    "anexo1": "2025-09-22",
    "anexo2": "2025-09-23",
    "anexo2_limite": "2025-08-14",
    "anexo3": "2025-09-24",
    "anexo4": "2025-09-25",
    "anexo5": "2025-09-25",
    "anexo6": "2025-09-26",
    "anexo7": "2025-09-26",
    "anexo11": "2025-12-15",
    "anexo13": "2025-09-29",
}


def cargar(reiniciar: bool = False) -> None:
    if reiniciar and db.RUTA_DB.exists():
        db.RUTA_DB.unlink()
    db.inicializar()

    with db.conexion() as con:
        db.guardar_proyecto(con, PROYECTO)

        con.execute("DELETE FROM personas")
        ids_docentes = {}
        for persona in PERSONAS:
            nuevo = db.insertar(con, "personas", persona)
            if persona["rol"] == "docente_apoyo":
                ids_docentes[persona["nombre"]] = nuevo

        # Reparto de estudiantes por docente de apoyo, tal como en el proyecto real.
        asignacion = {
            "0106103781": "Williams Hidalgo Trelles Ávila",
            "0107961757": "Williams Hidalgo Trelles Ávila",
            "0151181898": "Williams Hidalgo Trelles Ávila",
            "0107193930": "Mónica Galarza Rodas",
            "0107006686": "Mónica Galarza Rodas",
        }
        con.execute("DELETE FROM estudiantes")
        for i, (cedula, nombres, apellidos, email, ciclo, sexo, _) in enumerate(ESTUDIANTES):
            db.insertar(con, "estudiantes", {
                "cedula": cedula, "nombres": nombres, "apellidos": apellidos,
                "nombre_completo": f"{nombres} {apellidos}", "email": email,
                "ciclo": ciclo, "paralelo": PROYECTO["paralelo"],
                "jornada": PROYECTO["jornada"], "sexo": sexo,
                "docente_apoyo_id": ids_docentes.get(asignacion.get(cedula)),
                "orden": i,
            })

        con.execute("DELETE FROM actividades")
        for nro, desc, asig, res, prod, horas in ACTIVIDADES:
            db.insertar(con, "actividades", {
                "nro": nro, "descripcion": desc, "descripcion_docente": desc,
                "asignatura": asig, "resultados_aprendizaje": res,
                "producto": prod, "horas": horas, "horas_docente": 6,
            })

        db.reemplazar_tabla(con, "requisitos",
                            [{"nombre": r} for r in REQUISITOS])
        db.reemplazar_tabla(con, "cronograma",
                            [{"actividad": a, "fecha": f} for a, f in CRONOGRAMA])

        con.execute("DELETE FROM fechas")
        for clave, valor in FECHAS.items():
            con.execute("INSERT INTO fechas (clave, valor) VALUES (?, ?)", (clave, valor))

        con.execute("DELETE FROM cortes")
        for corte, fecha in (("parcial", "2025-10-20"), ("final", "2025-12-15")):
            con.execute("INSERT INTO cortes (corte, fecha) VALUES (?, ?)", (corte, fecha))
        # También como fechas nombradas, que es como las piden los anexos 6.1 y 6.2.
        for clave, valor in (("anexo6_1", "2025-10-20"), ("anexo6_2", "2025-12-15")):
            con.execute("INSERT OR REPLACE INTO fechas (clave, valor) VALUES (?, ?)",
                        (clave, valor))

        # --- Meses del proyecto -------------------------------------------
        con.execute("DELETE FROM meses")
        ids_meses = []
        for nro, etiqueta, f_plan, f_seg, f_soc in MESES:
            ids_meses.append(db.insertar(con, "meses", {
                "nro": nro, "etiqueta": etiqueta,
                "fecha_planificacion": f_plan, "fecha_seguimiento": f_seg,
                "fecha_socializacion": f_soc,
            }))

        # --- Registro diario (común a todo el grupo) -----------------------
        db.reemplazar_tabla(con, "registro_diario", [
            {"fecha": f, "descripcion": d, "lugar": PROYECTO["entidad_corta"], "horas": h}
            for f, d, h in REGISTRO
        ])

        # --- Jornadas de capacitación --------------------------------------
        con.execute("DELETE FROM jornadas")
        for nro, asunto, fecha, horas, lugar in JORNADAS:
            db.insertar(con, "jornadas", {"nro": nro, "asunto": asunto,
                                          "fecha": fecha, "horas": horas, "lugar": lugar})

        # --- Visitas ---------------------------------------------------------
        db.reemplazar_tabla(con, "visitas", [
            {"fecha": f, "hora_inicio": hi, "hora_fin": hf, "asunto": a,
             "actividades": act, "observaciones": obs}
            for f, hi, hf, a, act, obs in VISITAS
        ])

        # --- Planificación y seguimiento del primer mes ----------------------
        estudiantes = db.listar(con, "estudiantes", donde="activo = 1")
        docentes = db.listar(con, "personas", donde="rol = 'docente_apoyo'")
        actividades = db.listar(con, "actividades", orden="nro")
        primeras = actividades[:3]
        mes1 = ids_meses[0]

        con.execute("DELETE FROM planificacion")
        orden = 0
        for docente in docentes:
            for act in primeras:
                db.insertar(con, "planificacion", {
                    "mes_id": mes1, "tipo": "docente", "persona_id": docente["id"],
                    "actividad_id": act["id"], "horas": 6,
                    "fecha_inicio": "2025-09-29", "fecha_fin": "2025-09-30",
                    "orden": orden})
                orden += 1
        for est in estudiantes:
            for act in primeras:
                db.insertar(con, "planificacion", {
                    "mes_id": mes1, "tipo": "estudiante", "persona_id": est["id"],
                    "actividad_id": act["id"], "horas": 8,
                    "fecha_inicio": "2025-09-29", "fecha_fin": "2025-09-30",
                    "orden": orden})
                orden += 1

        con.execute("DELETE FROM seguimiento")
        descripcion = "\n".join(a["descripcion"] for a in primeras)
        for i, est in enumerate(estudiantes):
            db.insertar(con, "seguimiento", {
                "mes_id": mes1, "estudiante_id": est["id"],
                "actividad_id": primeras[0]["id"], "descripcion": descripcion,
                "fecha_planificada": "2025-09-29", "finalizada": "SI",
                "fecha_fin_prevista": "2025-09-30", "avance": "100%", "orden": i})

        # --- Evaluaciones -----------------------------------------------------
        con.execute("DELETE FROM evaluacion_plan")
        for est in estudiantes:
            for i, act in enumerate(actividades):
                for corte, umbral in (("parcial", 3), ("final", len(actividades))):
                    completada = i < umbral
                    db.insertar(con, "evaluacion_plan", {
                        "estudiante_id": est["id"], "actividad_id": act["id"],
                        "corte": corte,
                        "avance": "100%" if completada else "0%",
                        "valoracion": "muy" if completada else "",
                        "logro": "si" if completada else ""})

        con.execute("DELETE FROM evaluacion_estudiante")
        for est in estudiantes:
            for item in ("1.1", "1.2", "1.3", "1.4"):
                db.insertar(con, "evaluacion_estudiante", {
                    "estudiante_id": est["id"], "evaluador": "docente_apoyo",
                    "item": item, "puntaje": 5})
            for item in ("2.1", "2.2", "2.3", "2.4"):
                db.insertar(con, "evaluacion_estudiante", {
                    "estudiante_id": est["id"], "evaluador": "director",
                    "item": item, "puntaje": 5})

    print(f"Datos de ejemplo cargados en {db.RUTA_DB}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reiniciar", action="store_true",
                    help="borra la base antes de cargar")
    cargar(**vars(ap.parse_args()))
