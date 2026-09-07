#!/usr/bin/env python3
"""
Vacía los datos operativos para empezar un proyecto nuevo.

Conserva la estructura, la configuración de logos y — si se pide — las personas
y el plan de aprendizaje, que normalmente se repiten entre fases del mismo
proyecto. Antes de borrar nada hace una copia de seguridad de la base.

    python herramientas/nuevo_proyecto.py                 # borra todo lo operativo
    python herramientas/nuevo_proyecto.py --conservar-plan --conservar-personas
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import db  # noqa: E402

SIEMPRE = [
    "estudiantes", "registro_diario", "meses", "planificacion", "seguimiento",
    "evaluacion_plan", "evaluacion_estudiante", "jornadas", "beneficiarios",
    "visitas", "evidencias", "cronograma", "fechas", "cortes",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conservar-plan", action="store_true",
                    help="no borra actividades ni asignaturas requisito")
    ap.add_argument("--conservar-personas", action="store_true",
                    help="no borra docentes, director ni coordinadores")
    args = ap.parse_args()

    if not db.RUTA_DB.exists():
        print("No hay base de datos todavía; no hay nada que limpiar.")
        return 0

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    respaldo = db.RUTA_DB.with_name(f"anexos_respaldo_{marca}.db")
    shutil.copy2(db.RUTA_DB, respaldo)
    print(f"Copia de seguridad: {respaldo.name}")

    tablas = list(SIEMPRE)
    if not args.conservar_plan:
        tablas += ["actividades", "requisitos"]
    if not args.conservar_personas:
        tablas.append("personas")

    with db.conexion() as con:
        for tabla in tablas:
            con.execute(f"DELETE FROM {tabla}")
        con.execute("""
            UPDATE proyecto SET nombre = '', nombre_corto = '', fase = '',
              codigo_convocatoria = '', entidad = '', entidad_corta = '',
              entidad_direccion = '', entidad_descripcion = '',
              entidad_telefono = '', entidad_email = '',
              fecha_inicio = '', fecha_fin = '', fecha_evaluacion = '',
              fecha_convocatoria = '', fecha_max_solicitudes = '',
              fecha_elaboracion = '', lugar = ''
            WHERE id = 1
        """)

    print("Listo. Se conservó:",
          ", ".join(x for x, cond in (("plan de aprendizaje", args.conservar_plan),
                                      ("personas", args.conservar_personas)) if cond)
          or "solo la configuración de logos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
