#!/usr/bin/env python
"""
Coherencia de fechas de todo el proyecto.

Qué comprueba:

  1. Que toda fecha de ejecución caiga entre fecha_inicio y fecha_fin.
  2. Que ninguna caiga en sábado, domingo o feriado.
  3. Que las fechas del registro diario (Anexo 8) sean laborables reales.
  4. Que las horas del registro diario sumen el total del proyecto.
  5. Que los meses declarados existan dentro del plazo.
  6. Que las fechas administrativas guarden el orden lógico
     (elaboración <= inicio <= fin <= evaluación).

Los feriados van en FERIADOS, no calculados: en Ecuador varios se trasladan
por la Ley de Feriados y el traslado se publica cada año, así que adivinarlo
con una regla daría un resultado falso. Se revisa contra el calendario del
Ministerio de Trabajo y se corrige aquí cuando cambie el año.

Uso:
    python herramientas/verificar_fechas.py
    python herramientas/verificar_fechas.py --arreglar-registro
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import db  # noqa: E402

# Feriados nacionales de Ecuador con el traslado ya aplicado.
# 2026 verificado contra el calendario oficial del Ministerio de Trabajo.
FERIADOS: dict[date, str] = {
    date(2026, 1, 1):   "Año Nuevo",
    date(2026, 2, 16):  "Carnaval",
    date(2026, 2, 17):  "Carnaval",
    date(2026, 4, 3):   "Viernes Santo",
    date(2026, 5, 1):   "Día del Trabajo",
    date(2026, 5, 25):  "Batalla del Pichincha (traslado del 24)",
    date(2026, 8, 10):  "Primer Grito de Independencia",
    date(2026, 10, 9):  "Independencia de Guayaquil",
    date(2026, 11, 2):  "Día de los Difuntos",
    date(2026, 11, 3):  "Independencia de Cuenca",
    date(2026, 12, 25): "Navidad",
}

# Feriados locales de Cuenca, que es donde se ejecuta el proyecto.
FERIADOS_LOCALES: dict[date, str] = {
    date(2026, 4, 12): "Fundación de Cuenca",
}

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def feriado(f: date) -> str | None:
    return FERIADOS.get(f) or FERIADOS_LOCALES.get(f)


def laborable(f: date) -> tuple[bool, str]:
    """(es_laborable, motivo_si_no)."""
    if f.weekday() >= 5:
        return False, DIAS[f.weekday()]
    nombre = feriado(f)
    if nombre:
        return False, f"feriado · {nombre}"
    return True, ""


def dias_laborables(desde: date, hasta: date) -> list[date]:
    dias, actual = [], desde
    while actual <= hasta:
        if laborable(actual)[0]:
            dias.append(actual)
        actual += timedelta(days=1)
    return dias


def _fecha(valor) -> date | None:
    """
    Acepta 2026-08-10 y 10/08/2026.

    Hacen falta las dos: la base guarda ISO, pero el cronograma de la
    convocatoria se cargó en formato ecuatoriano y con solo ISO el
    verificador lo saltaba en silencio, que es peor que no verificarlo.
    """
    if not valor:
        return None
    texto = str(valor).strip()
    try:
        return date.fromisoformat(texto[:10])
    except ValueError:
        pass
    partes = texto.split("/")
    if len(partes) == 3:
        try:
            d, m, a = (int(x) for x in partes)
            return date(a, m, d)
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------
# Comprobaciones
# --------------------------------------------------------------------------

def revisar(con) -> tuple[list[str], list[str]]:
    """Devuelve (errores, avisos)."""
    errores: list[str] = []
    avisos: list[str] = []

    p = dict(con.execute("SELECT * FROM proyecto WHERE id = 1").fetchone())
    inicio, fin = _fecha(p["fecha_inicio"]), _fecha(p["fecha_fin"])
    if not inicio or not fin:
        return ["El proyecto no tiene fecha de inicio o de fin."], []
    if inicio > fin:
        errores.append(f"La fecha de inicio ({inicio}) es posterior a la de fin ({fin}).")

    habiles = dias_laborables(inicio, fin)
    print(f"Plazo: {inicio} a {fin}  ·  {(fin - inicio).days + 1} días "
          f"corridos  ·  {len(habiles)} laborables")
    fer = [(f, feriado(f)) for f in
           (inicio + timedelta(d) for d in range((fin - inicio).days + 1))
           if feriado(f)]
    if fer:
        print("Feriados dentro del plazo: "
              + ", ".join(f"{f} ({n})" for f, n in fer))
    print()

    # --- 1. Orden de las fechas administrativas ----------------------------
    orden = [("fecha_elaboracion", "elaboración"), ("fecha_inicio", "inicio"),
             ("fecha_fin", "fin"), ("fecha_evaluacion", "evaluación")]
    previa, previa_nombre = None, ""
    for clave, nombre in orden:
        f = _fecha(p[clave])
        if f is None:
            continue
        if previa and f < previa:
            errores.append(f"La fecha de {nombre} ({f}) es anterior a la de "
                           f"{previa_nombre} ({previa}).")
        previa, previa_nombre = f, nombre

    # --- 2. Tablas con fechas de ejecución ---------------------------------
    # Solo estas: son las que representan trabajo hecho en la institución y
    # por tanto deben caer en día laborable dentro del plazo. Las fechas
    # administrativas (elaboración, convocatoria) pueden ir fuera.
    EJECUCION = [
        ("registro_diario", "fecha", "Anexo 8 · registro diario"),
        ("visitas", "fecha", "Anexo 13 · visitas"),
        ("jornadas", "fecha", "Anexo 12 · jornadas"),
        # El cronograma NO va aquí: convocatoria y selección son anteriores al
        # inicio por definición. Se revisa más abajo, solo por día laborable.
        ("actividades_informe", "fecha", "actividades de los informes"),
        ("cortes", "fecha", "cortes de evaluación"),
        ("planificacion", "fecha_inicio", "Anexo 7 · planificación (inicio)"),
        ("planificacion", "fecha_fin", "Anexo 7 · planificación (fin)"),
        ("seguimiento", "fecha_planificada", "Anexo 9 · seguimiento (planificada)"),
        ("seguimiento", "fecha_fin_prevista", "Anexo 9 · seguimiento (fin prevista)"),
    ]
    for tabla, columna, etiqueta in EJECUCION:
        fuera, no_habiles = [], []
        for fila in con.execute(f"SELECT rowid, {columna} AS f FROM {tabla}"):
            f = _fecha(fila["f"])
            if f is None:
                continue
            if not (inicio <= f <= fin):
                fuera.append(f)
            else:
                ok, motivo = laborable(f)
                if not ok:
                    no_habiles.append((f, motivo))
        if fuera:
            errores.append(f"{etiqueta}: {len(fuera)} fecha(s) fuera del plazo "
                           f"-> {', '.join(sorted({str(x) for x in fuera}))}")
        if no_habiles:
            unicas = sorted(set(no_habiles))
            errores.append(f"{etiqueta}: {len(no_habiles)} fecha(s) en día no "
                           "laborable -> "
                           + ", ".join(f"{f} ({m})" for f, m in unicas))

    # --- 2b. Fechas administrativas ----------------------------------------
    # Pueden caer fuera del plazo (la convocatoria es anterior al inicio),
    # pero siguen siendo actos institucionales: no se emiten en fin de semana
    # ni en feriado.
    ADMINISTRATIVAS = [
        ("cronograma", "fecha", "actividad", "Anexo 2 · cronograma"),
        ("meses", "fecha_planificacion", "etiqueta", "Anexo 7 · fecha de planificación"),
        ("meses", "fecha_seguimiento", "etiqueta", "Anexo 9 · fecha de seguimiento"),
        ("meses", "fecha_socializacion", "etiqueta", "fecha de socialización"),
    ]
    for tabla, columna, rotulo, etiqueta in ADMINISTRATIVAS:
        malas = []
        for fila in con.execute(f"SELECT {columna} AS f, {rotulo} AS r FROM {tabla}"):
            f = _fecha(fila["f"])
            if f is None:
                continue
            ok, motivo = laborable(f)
            if not ok:
                malas.append(f"{f} ({motivo}) · {fila['r']}")
        if malas:
            errores.append(f"{etiqueta}: {len(malas)} en día no laborable -> "
                           + "; ".join(malas))

    # --- 3. Horas del registro diario --------------------------------------
    total = con.execute("SELECT COALESCE(SUM(horas), 0) AS t FROM registro_diario").fetchone()["t"]
    previsto = p["total_horas"] or 0
    if previsto and abs(total - previsto) > 0.01:
        errores.append(f"Anexo 8: las horas del registro suman {total:g} y el "
                       f"proyecto declara {previsto}.")
    else:
        print(f"Horas del registro diario: {total:g} de {previsto} · correcto")

    # --- 4. Meses declarados ------------------------------------------------
    meses_plazo = set()
    for d in range((fin - inicio).days + 1):
        f = inicio + timedelta(d)
        meses_plazo.add((f.year, f.month))
    for fila in con.execute("SELECT nro, etiqueta, fecha_planificacion, "
                            "fecha_seguimiento FROM meses ORDER BY nro"):
        for clave in ("fecha_planificacion", "fecha_seguimiento"):
            f = _fecha(fila[clave])
            if f and not (inicio <= f <= fin):
                avisos.append(f"Mes «{fila['etiqueta']}»: {clave} = {f}, "
                              "fuera del plazo de ejecución.")

    # --- 5. Días laborables sin registrar ----------------------------------
    con_registro = {_fecha(r["fecha"]) for r in
                    con.execute("SELECT fecha FROM registro_diario")}
    sin_usar = [d for d in habiles if d not in con_registro]
    if sin_usar:
        avisos.append(f"{len(sin_usar)} día(s) laborable(s) del plazo sin "
                      "actividad en el Anexo 8: "
                      + ", ".join(str(d) for d in sin_usar))

    return errores, avisos


def arreglar_registro(con) -> list[str]:
    """
    Mueve las entradas del registro diario que caen en día no laborable al
    siguiente día laborable libre, conservando el orden.

    No inventa horas ni descripciones: solo cambia la fecha, que es lo que la
    institución revisa contra el calendario.
    """
    p = dict(con.execute("SELECT * FROM proyecto WHERE id = 1").fetchone())
    inicio, fin = _fecha(p["fecha_inicio"]), _fecha(p["fecha_fin"])
    habiles = dias_laborables(inicio, fin)

    filas = [dict(r) for r in con.execute(
        "SELECT id, fecha, horas, descripcion FROM registro_diario "
        "ORDER BY fecha, orden, id")]
    ocupados = {_fecha(f["fecha"]) for f in filas}
    cambios = []
    for fila in filas:
        f = _fecha(fila["fecha"])
        if f is None:
            continue
        ok, motivo = laborable(f)
        if ok and inicio <= f <= fin:
            continue
        # Primer laborable posterior que no esté ya ocupado.
        destino = next((d for d in habiles if d > f and d not in ocupados), None)
        if destino is None:
            destino = next((d for d in habiles if d not in ocupados), None)
        if destino is None:
            cambios.append(f"{f}: sin día laborable libre donde moverla")
            continue
        con.execute("UPDATE registro_diario SET fecha = ? WHERE id = ?",
                    (destino.isoformat(), fila["id"]))
        ocupados.discard(f)
        ocupados.add(destino)
        cambios.append(f"{f} ({motivo}) -> {destino} "
                       f"[{fila['horas']:g}h] {(fila['descripcion'] or '')[:45]}")
    return cambios


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arreglar-registro", action="store_true",
                    help="mover las entradas del Anexo 8 que caen en día no "
                         "laborable al siguiente día hábil libre")
    args = ap.parse_args()

    with db.conexion() as con:
        if args.arreglar_registro:
            cambios = arreglar_registro(con)
            print("Cambios en el registro diario:")
            for c in cambios or ["   (ninguno: ya estaba correcto)"]:
                print("   ", c)
            print()

        errores, avisos = revisar(con)

    if errores:
        print(f"\nERRORES ({len(errores)}):")
        for e in errores:
            print("   ✗", e)
    if avisos:
        print(f"\nAVISOS ({len(avisos)}):")
        for a in avisos:
            print("   ·", a)
    if not errores and not avisos:
        print("\nTodo coherente.")
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
