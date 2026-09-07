#!/usr/bin/env python
"""
Reparte el registro diario (Anexo 8) día por día.

El Anexo 8 es un registro DIARIO: la institución espera una fila por cada día
laborable del plazo. Lo que había no cumplía eso — dos actividades compartían
el 20/07 y el 17/08, una caía en el feriado del 10/08 y siete días laborables
quedaban en blanco.

Cómo reparte:

  1. Agrupa las filas en bloques por descripción (las descripciones repetidas
     en días seguidos son un mismo bloque de trabajo). Cada bloque conserva
     SU TOTAL DE HORAS: no se inventa ni se pierde trabajo.
  2. Calcula los días laborables del plazo, sin fines de semana ni feriados.
  3. Reparte los días entre los bloques en proporción a sus horas, por el
     método del resto mayor y con un mínimo de un día por bloque, de modo que
     la suma de días asignados sea exactamente el número de días laborables.
  4. Dentro de cada bloque reparte sus horas entre sus días en tramos de media
     hora, dejando las fracciones mayores en los primeros días.

El total del proyecto no cambia: si entraron 100 horas, salen 100 horas.

Uso:
    python herramientas/distribuir_registro.py            # solo muestra
    python herramientas/distribuir_registro.py --aplicar  # escribe en la base
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import db  # noqa: E402
from herramientas.verificar_fechas import _fecha, dias_laborables  # noqa: E402

# Tramo mínimo de horas por día. Entero por defecto, que es como venían las
# horas en el documento oficial; con --medias-horas se admite 0,5.
PASO = 1.0


def bloques(filas: list[dict]) -> list[dict]:
    """Agrupa filas consecutivas con la misma descripción."""
    grupos: list[dict] = []
    for fila in filas:
        desc = (fila["descripcion"] or "").strip()
        if grupos and grupos[-1]["descripcion"] == desc:
            grupos[-1]["horas"] += fila["horas"] or 0
            grupos[-1]["ids"].append(fila["id"])
        else:
            grupos.append({"descripcion": desc, "horas": fila["horas"] or 0,
                           "lugar": fila["lugar"], "ids": [fila["id"]]})
    return grupos


def repartir_dias(grupos: list[dict], total_dias: int) -> list[int]:
    """
    Días por bloque, proporcionales a las horas, sumando exactamente
    `total_dias` y con al menos un día cada uno (método del resto mayor).
    """
    if total_dias < len(grupos):
        raise ValueError(f"Hay {len(grupos)} bloques de actividad y solo "
                         f"{total_dias} días laborables: no cabe uno por día.")
    # Techo por bloque: no puede ocupar más días que tramos de hora tiene, o
    # algún día saldría con cero horas, que en un registro diario es un error.
    techo = [max(1, round(g["horas"] / PASO)) for g in grupos]
    if sum(techo) < total_dias:
        raise ValueError(
            f"Con tramos de {PASO:g} h las {sum(g['horas'] for g in grupos):g} "
            f"horas no alcanzan para {total_dias} días sin dejar días en cero. "
            "Pruebe con --medias-horas.")

    horas_totales = sum(g["horas"] for g in grupos) or 1
    sobrantes = total_dias - len(grupos)
    exactos = [g["horas"] / horas_totales * sobrantes for g in grupos]
    dias = [1 + int(x) for x in exactos]
    restos = sorted(range(len(grupos)),
                    key=lambda i: exactos[i] - int(exactos[i]), reverse=True)
    for i in restos[:total_dias - sum(dias)]:
        dias[i] += 1

    # Se recorta lo que pase del techo y se reubica en los bloques que aún
    # tienen sitio, empezando por los de más horas.
    holgura = sorted(range(len(grupos)), key=lambda i: grupos[i]["horas"],
                     reverse=True)
    exceso = 0
    for i in range(len(dias)):
        if dias[i] > techo[i]:
            exceso += dias[i] - techo[i]
            dias[i] = techo[i]
    for i in holgura:
        if exceso <= 0:
            break
        cabe = min(exceso, techo[i] - dias[i])
        dias[i] += cabe
        exceso -= cabe
    if exceso:
        raise ValueError("No se pudo repartir todos los días sin dejar alguno en cero.")
    return dias


def repartir_horas(total: float, n: int) -> list[float]:
    """Reparte `total` horas entre `n` días en tramos de PASO, sin perder nada."""
    tramos = round(total / PASO)
    base, sobra = divmod(tramos, n)
    return [(base + (1 if i < sobra else 0)) * PASO for i in range(n)]


def planificar(con) -> list[dict]:
    p = dict(con.execute("SELECT * FROM proyecto WHERE id = 1").fetchone())
    inicio, fin = _fecha(p["fecha_inicio"]), _fecha(p["fecha_fin"])
    if not inicio or not fin:
        raise ValueError("El proyecto no tiene fechas de inicio y fin.")
    dias = dias_laborables(inicio, fin)

    filas = [dict(r) for r in con.execute(
        "SELECT id, fecha, descripcion, lugar, horas FROM registro_diario "
        "ORDER BY fecha, orden, id")]
    if not filas:
        raise ValueError("El registro diario está vacío.")

    grupos = bloques(filas)
    reparto = repartir_dias(grupos, len(dias))

    plan, cursor = [], 0
    for grupo, n in zip(grupos, reparto):
        horas = repartir_horas(grupo["horas"], n)
        for i in range(n):
            plan.append({"fecha": dias[cursor + i],
                         "descripcion": grupo["descripcion"],
                         "lugar": grupo["lugar"],
                         "horas": horas[i]})
        cursor += n
    return plan


def aplicar(con, plan: list[dict]) -> None:
    con.execute("DELETE FROM registro_diario")
    for orden, fila in enumerate(plan):
        con.execute(
            "INSERT INTO registro_diario (estudiante_id, fecha, descripcion, "
            "lugar, horas, orden) VALUES (NULL, ?, ?, ?, ?, ?)",
            (fila["fecha"].isoformat(), fila["descripcion"], fila["lugar"],
             fila["horas"], orden))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aplicar", action="store_true",
                    help="escribir el reparto en la base (por defecto solo lo muestra)")
    ap.add_argument("--medias-horas", action="store_true",
                    help="permitir medias horas; por defecto solo horas enteras")
    args = ap.parse_args()

    global PASO
    if args.medias_horas:
        PASO = 0.5

    with db.conexion() as con:
        plan = planificar(con)

        DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
        print(f"{'Fecha':12} {'Día':4} {'Horas':>6}  Actividad")
        print("-" * 96)
        for fila in plan:
            print(f"{fila['fecha']}  {DIAS[fila['fecha'].weekday()]:4} "
                  f"{fila['horas']:6g}  {fila['descripcion'][:66]}")
        print("-" * 96)
        total = sum(f["horas"] for f in plan)
        fechas = {f["fecha"] for f in plan}
        print(f"{len(plan)} filas · {len(fechas)} días distintos · {total:g} horas")

        if len(fechas) != len(plan):
            print("AVISO: hay días repetidos en el reparto.")

        if args.aplicar:
            aplicar(con, plan)
            print("\nAplicado. Vuelva a derivar los anexos dependientes con:")
            print("   python herramientas/cargar_actividades.py")
        else:
            print("\n(Solo vista previa. Use --aplicar para escribirlo.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
