#!/usr/bin/env python
"""
Da de baja a un estudiante que no participa en el proyecto.

Dos modos:

  --desactivar  (por defecto)  marca `activo = 0`. Deja de salir en todos los
                anexos, pero se conservan sus filas por si vuelve o por si hay
                que justificar algo. Es reversible desde la app.
  --eliminar    borra la fila. Las claves foráneas en cascada se llevan su
                seguimiento y sus dos tablas de evaluación. No se puede
                deshacer salvo restaurando una copia.

En los dos casos se limpian las filas de `planificacion` que le apuntan, que es
lo que ninguna cascada hace: `planificacion.persona_id` guarda el id del
estudiante pero NO está declarada como clave foránea, porque la misma columna
sirve para docentes. Sin limpiarlas, el Anexo 7 saca una línea con el nombre y
la cédula vacíos.

Uso:
    python herramientas/quitar_estudiante.py "Karol Fernanda Chavez Jara"
    python herramientas/quitar_estudiante.py 0150563534 --aplicar
    python herramientas/quitar_estudiante.py 0150563534 --aplicar --eliminar
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import db  # noqa: E402


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def buscar(con, referencia: str) -> dict | None:
    objetivo = normalizar(referencia)
    estudiantes = db.listar(con, "estudiantes", orden="orden, id")
    for e in estudiantes:
        if normalizar(e["cedula"]) == objetivo:
            return dict(e)
    coincidencias = [dict(e) for e in estudiantes
                     if objetivo in normalizar(e["nombre_completo"])]
    if len(coincidencias) == 1:
        return coincidencias[0]
    if len(coincidencias) > 1:
        print("Hay más de un estudiante que coincide; use la cédula:")
        for c in coincidencias:
            print(f"   {c['cedula']}  {c['nombre_completo']}")
    return None


def dependencias(con, id_est: int) -> dict[str, int]:
    cuentas = {}
    for tabla in ("seguimiento", "evaluacion_plan", "evaluacion_estudiante",
                  "registro_diario"):
        cuentas[tabla] = con.execute(
            f"SELECT COUNT(*) AS n FROM {tabla} WHERE estudiante_id = ?",
            (id_est,)).fetchone()["n"]
    cuentas["planificacion"] = con.execute(
        "SELECT COUNT(*) AS n FROM planificacion "
        "WHERE tipo = 'estudiante' AND persona_id = ?", (id_est,)).fetchone()["n"]
    return cuentas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("estudiante", help="cédula o parte del nombre")
    ap.add_argument("--aplicar", action="store_true",
                    help="hacer el cambio; por defecto solo informa")
    ap.add_argument("--eliminar", action="store_true",
                    help="borrar la fila en vez de desactivarla")
    args = ap.parse_args()

    with db.conexion() as con:
        estudiante = buscar(con, args.estudiante)
        if estudiante is None:
            print(f"No encuentro a «{args.estudiante}».")
            print("Registrados:")
            for e in db.listar(con, "estudiantes", orden="orden, id"):
                print(f"   {e['cedula']}  {e['nombre_completo']}"
                      + ("" if e["activo"] else "  (inactivo)"))
            return 1

        print(f"Estudiante: {estudiante['nombre_completo']} "
              f"({estudiante['cedula']}), activo={estudiante['activo']}")
        deps = dependencias(con, estudiante["id"])
        print("Filas asociadas:")
        for tabla, n in deps.items():
            print(f"   {tabla:24} {n}")

        activos = con.execute(
            "SELECT COUNT(*) AS n FROM estudiantes WHERE activo = 1").fetchone()["n"]
        print(f"\nEstudiantes activos ahora: {activos} -> "
              f"{activos - (1 if estudiante['activo'] else 0)}")

        if not args.aplicar:
            print("\n(Vista previa. Añada --aplicar para hacerlo.)")
            return 0

        # Las filas de planificación no las cubre ninguna cascada.
        con.execute("DELETE FROM planificacion WHERE tipo = 'estudiante' "
                    "AND persona_id = ?", (estudiante["id"],))
        if args.eliminar:
            con.execute("DELETE FROM estudiantes WHERE id = ?", (estudiante["id"],))
            print("\nEliminado. Su seguimiento y sus evaluaciones se fueron con él.")
        else:
            con.execute("UPDATE estudiantes SET activo = 0 WHERE id = ?",
                        (estudiante["id"],))
            print("\nDesactivado. Deja de salir en los anexos; sus filas se conservan.")

        for tabla in ("estudiantes", "seguimiento", "evaluacion_plan",
                      "evaluacion_estudiante", "planificacion"):
            n = con.execute(f"SELECT COUNT(*) AS n FROM {tabla}").fetchone()["n"]
            print(f"   {tabla:24} {n}")
    print("\nVuelva a generar los documentos desde la app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
