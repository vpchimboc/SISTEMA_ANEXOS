#!/usr/bin/env python3
"""
Deriva del registro diario toda la información de actividades que piden los
demás anexos, adaptada al proyecto activo.

Por qué derivar en vez de copiar
--------------------------------
Los anexos de la fase anterior traen esta información, pero copiarla arrastra
dos problemas: las fechas y la unidad educativa son las de esa fase, y las
horas no siempre cuadran entre documentos (en el Anexo 7 original el mes de
octubre declara 73 h por estudiante mientras el Anexo 8 registra 67).

Aquí se toma como única fuente el registro diario (Anexo 8) y de ahí salen el
resto. Así el expediente es internamente consistente: las horas del Anexo 7
suman las del Anexo 8, y el Anexo 9 refleja lo que el Anexo 8 dice que se hizo.

Genera:
  Anexo 7   planificación mensual de docentes y estudiantes
  Anexo 9   seguimiento mensual por estudiante
  Anexo 12  jornadas de capacitación
  Anexo 13  visitas del docente de apoyo (cada dos semanas)
  Anexo 6.1 evaluación parcial del plan   6.2 evaluación final
  Anexo 11  rúbrica del estudiante
  S/N 2 y 3 tabla de actividades de los informes ISTA

    python herramientas/cargar_actividades.py
    python herramientas/cargar_actividades.py --sin-evaluaciones
"""

from __future__ import annotations

import argparse
import sys
from collections import OrderedDict, defaultdict
from datetime import timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import db  # noqa: E402
from core.contexto import MESES_ES, _a_fecha, fecha_corta  # noqa: E402

# Qué actividad del plan de aprendizaje corresponde a cada entrada del registro.
# Se busca por el inicio de la descripción; el orden va de lo más específico a
# lo más general para que no se solapen ("Mantenimiento a puntos de red" es la
# actividad 6, pero "Mantenimiento a tomacorrientes" es parte de la 4).
MAPA_ACTIVIDADES = [
    ("Recorrido por los Laboratorios", 1),
    ("Recorrido por el laboratorio", 1),
    ("Reunión entre docentes", 2),
    ("Inspección de hardware", 3),
    ("Pruebas de operación", 3),
    ("Inventario inicial", 3),
    ("Creación de copias de seguridad", 4),
    ("Desarmado y limpieza", 4),
    ("Selección y pruebas de sistema operativo", 4),
    ("Instalación y configuración inicial", 4),
    ("Instalación de programas", 4),
    ("Activación de licencias", 4),
    ("Restauración de copias", 4),
    ("Mantenimiento y reemplazo de periféricos", 4),
    ("Mantenimiento a tomacorrientes", 4),
    ("Revisión de equipos que presentan fallas", 4),
    ("Etiquetado de equipos", 4),
    ("Actualización de inventario", 4),
    ("Revisión de cables y conexiones", 5),
    ("Pruebas de conectividad", 5),
    ("Mantenimiento a puntos de red", 6),
    ("Revisión de los requerimientos y expectativas de capacitación", 7),
    ("Desarrollo de planes de estudio", 7),
    ("Impartición de jornada", 8),
]

HORAS_DOCENTE_MES = 6
ASUNTO_VISITA = ("Visita de seguimiento y observación de las actividades del "
                 "proyecto de vinculación.")
ACTIVIDADES_VISITA = ("Diálogo con el representante legal del establecimiento sobre "
                      "el rendimiento del estudiante.\nDiálogo y observación con los "
                      "estudiantes sobre las actividades ejecutadas.")


def actividad_de(descripcion: str) -> int | None:
    texto = (descripcion or "").strip()
    for prefijo, nro in MAPA_ACTIVIDADES:
        if texto.startswith(prefijo):
            return nro
    return None


def etiqueta_mes(fecha) -> str:
    return f"{MESES_ES[fecha.month - 1].capitalize()} {fecha.year}"


def cargar(sin_evaluaciones: bool = False) -> None:
    with db.conexion() as con:
        proyecto = db.obtener_proyecto(con)
        registro = db.listar(con, "registro_diario")
        actividades = db.listar(con, "actividades", orden="nro, id")
        estudiantes = db.listar(con, "estudiantes", donde="activo = 1")
        docentes = db.listar(con, "personas", donde="rol = 'docente_apoyo'")

        if not registro:
            print("No hay registro diario cargado. Ejecuta antes:")
            print("  python herramientas/cargar_registro.py --reubicar")
            return
        if not actividades or not estudiantes:
            print("Faltan actividades del plan o estudiantes.")
            return

        por_nro = {a["nro"]: a for a in actividades}

        # --- Clasificar el registro y agrupar por mes ----------------------
        sin_clasificar = []
        # mes -> {nro_actividad: {"horas": x, "desde": f, "hasta": f}}
        meses = OrderedDict()
        for fila in registro:
            fecha = _a_fecha(fila["fecha"])
            if not fecha:
                continue
            nro = actividad_de(fila["descripcion"])
            if nro is None or nro not in por_nro:
                sin_clasificar.append(fila["descripcion"][:70])
                continue
            clave = (fecha.year, fecha.month)
            grupo = meses.setdefault(clave, {})
            dato = grupo.setdefault(nro, {"horas": 0.0, "desde": fecha, "hasta": fecha})
            dato["horas"] += float(fila["horas"])
            dato["desde"] = min(dato["desde"], fecha)
            dato["hasta"] = max(dato["hasta"], fecha)

        if sin_clasificar:
            print("AVISO: estas entradas del registro no encajan en ninguna "
                  "actividad del plan y se omiten:")
            for x in dict.fromkeys(sin_clasificar):
                print("   ·", x)

        meses = OrderedDict(sorted(meses.items()))

        # --- Meses ---------------------------------------------------------
        con.execute("DELETE FROM meses")
        ids_mes = {}
        for i, (clave, grupo) in enumerate(meses.items(), start=1):
            desde = min(d["desde"] for d in grupo.values())
            hasta = max(d["hasta"] for d in grupo.values())
            ids_mes[clave] = db.insertar(con, "meses", {
                "nro": i, "etiqueta": etiqueta_mes(desde),
                "fecha_planificacion": (desde - timedelta(days=1)).isoformat(),
                "fecha_seguimiento": hasta.isoformat(),
                "fecha_socializacion": (desde - timedelta(days=1)).isoformat()})

        # --- Anexo 7: planificación mensual --------------------------------
        con.execute("DELETE FROM planificacion")
        orden = 0
        for clave, grupo in meses.items():
            mes_id = ids_mes[clave]
            for docente in docentes:
                for nro in sorted(grupo):
                    db.insertar(con, "planificacion", {
                        "mes_id": mes_id, "tipo": "docente",
                        "persona_id": docente["id"], "actividad_id": por_nro[nro]["id"],
                        "resultado": por_nro[nro]["producto"],
                        "horas": HORAS_DOCENTE_MES,
                        "fecha_inicio": grupo[nro]["desde"].isoformat(),
                        "fecha_fin": grupo[nro]["hasta"].isoformat(),
                        "orden": orden})
                    orden += 1
            for estudiante in estudiantes:
                for nro in sorted(grupo):
                    db.insertar(con, "planificacion", {
                        "mes_id": mes_id, "tipo": "estudiante",
                        "persona_id": estudiante["id"], "actividad_id": por_nro[nro]["id"],
                        "resultado": por_nro[nro]["producto"],
                        "horas": grupo[nro]["horas"],
                        "fecha_inicio": grupo[nro]["desde"].isoformat(),
                        "fecha_fin": grupo[nro]["hasta"].isoformat(),
                        "orden": orden})
                    orden += 1

        # --- Anexo 9: seguimiento mensual ----------------------------------
        con.execute("DELETE FROM seguimiento")
        orden = 0
        for clave, grupo in meses.items():
            mes_id = ids_mes[clave]
            descripcion = "\n".join(por_nro[n]["descripcion"] for n in sorted(grupo))
            desde = min(d["desde"] for d in grupo.values())
            hasta = max(d["hasta"] for d in grupo.values())
            for estudiante in estudiantes:
                db.insertar(con, "seguimiento", {
                    "mes_id": mes_id, "estudiante_id": estudiante["id"],
                    "actividad_id": por_nro[min(grupo)]["id"],
                    "descripcion": descripcion,
                    "fecha_planificada": desde.isoformat(), "finalizada": "SI",
                    "fecha_fin_prevista": hasta.isoformat(), "avance": "100%",
                    "orden": orden})
                orden += 1

        # --- Anexo 12: jornadas de capacitación ----------------------------
        capacitaciones = [f for f in registro if actividad_de(f["descripcion"]) == 8]
        con.execute("DELETE FROM jornadas")
        ordinales = ["Primera", "Segunda", "Tercera", "Cuarta", "Quinta"]
        for i, fila in enumerate(capacitaciones):
            nombre = ordinales[i] if i < len(ordinales) else f"{i + 1}ª"
            db.insertar(con, "jornadas", {
                "nro": i + 1, "asunto": f"{nombre} Jornada de Capacitación",
                "fecha": fila["fecha"], "horas": str(int(float(fila["horas"]))),
                "lugar": fila["lugar"] or proyecto.get("entidad_corta", "")})

        # --- Anexo 13: visitas cada dos semanas ----------------------------
        inicio = min(_a_fecha(f["fecha"]) for f in registro if _a_fecha(f["fecha"]))
        fin = max(_a_fecha(f["fecha"]) for f in registro if _a_fecha(f["fecha"]))
        visitas, dia = [], inicio
        while dia <= fin:
            visitas.append({
                "fecha": dia.isoformat(), "hora_inicio": "14h00", "hora_fin": "15h00",
                "asunto": ASUNTO_VISITA, "actividades": ACTIVIDADES_VISITA,
                "observaciones": ""})
            dia += timedelta(days=14)
        # Una visita final el último día, que es cuando se cierra el proyecto.
        if visitas and visitas[-1]["fecha"] != fin.isoformat():
            visitas.append(dict(visitas[-1], fecha=fin.isoformat()))
        db.reemplazar_tabla(con, "visitas", visitas)

        # --- Anexos 6.1 / 6.2 y 11 -----------------------------------------
        if not sin_evaluaciones:
            # El corte parcial se sitúa al final del penúltimo mes: las
            # actividades cerradas para entonces van al 100 % y el resto en 0 %.
            claves = list(meses)
            corte = max(meses[claves[max(len(claves) - 2, 0)]].values(),
                        key=lambda d: d["hasta"])["hasta"]

            fin_actividad = {}
            for grupo in meses.values():
                for nro, dato in grupo.items():
                    fin_actividad[nro] = max(fin_actividad.get(nro, dato["hasta"]),
                                             dato["hasta"])

            con.execute("DELETE FROM evaluacion_plan")
            con.execute("DELETE FROM evaluacion_estudiante")
            for estudiante in estudiantes:
                for actividad in actividades:
                    cerrada = fin_actividad.get(actividad["nro"])
                    completa = bool(cerrada and cerrada <= corte)
                    db.insertar(con, "evaluacion_plan", {
                        "estudiante_id": estudiante["id"],
                        "actividad_id": actividad["id"], "corte": "parcial",
                        "avance": "100%" if completa else "0%",
                        "valoracion": "muy" if completa else "",
                        "logro": "si" if completa else ""})
                    db.insertar(con, "evaluacion_plan", {
                        "estudiante_id": estudiante["id"],
                        "actividad_id": actividad["id"], "corte": "final",
                        "avance": "100%", "valoracion": "muy", "logro": "si"})
                for item in ("1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4"):
                    db.insertar(con, "evaluacion_estudiante", {
                        "estudiante_id": estudiante["id"],
                        "evaluador": "docente_apoyo" if item.startswith("1") else "director",
                        "item": item, "puntaje": 5})

            con.execute("DELETE FROM cortes")
            for corte_clave, fecha in (("parcial", corte), ("final", fin)):
                con.execute("INSERT INTO cortes (corte, fecha) VALUES (?, ?)",
                            (corte_clave, fecha.isoformat()))
                con.execute("INSERT OR REPLACE INTO fechas (clave, valor) VALUES (?, ?)",
                            (f"anexo6_{'1' if corte_clave == 'parcial' else '2'}",
                             fecha.isoformat()))

        # --- Informes ISTA: tabla de actividades ---------------------------
        responsables = "\n".join(e["nombre_completo"] for e in estudiantes)
        con.execute("DELETE FROM actividades_informe")
        for informe in ("seguimiento", "final"):
            limite = corte if not sin_evaluaciones else fin
            for i, actividad in enumerate(actividades):
                cerrada = fin_actividad.get(actividad["nro"]) if not sin_evaluaciones else None
                if informe == "final":
                    cumplimiento = "100%"
                else:
                    cumplimiento = "100%" if (cerrada and cerrada <= limite) else "0%"
                db.insertar(con, "actividades_informe", {
                    "informe": informe, "actividad": actividad["descripcion"],
                    "cumplimiento": cumplimiento,
                    "fecha": (cerrada.isoformat() if cerrada else ""),
                    "responsables": responsables,
                    "evidencia": "Anexo 6.1\nAnexo 7\nAnexo 8",
                    "observaciones": "Ninguna", "orden": i})

    # --- Resumen ------------------------------------------------------------
    print(f"Derivado del registro diario ({len(registro)} entradas):\n")
    print(f"  {'Mes':18s} {'Actividades':>12s} {'Horas':>7s}")
    print("  " + "-" * 40)
    total = 0.0
    for clave, grupo in meses.items():
        horas = sum(d["horas"] for d in grupo.values())
        total += horas
        desde = min(d["desde"] for d in grupo.values())
        print(f"  {etiqueta_mes(desde):18s} {len(grupo):>12d} {horas:>6.0f}h")
    print("  " + "-" * 40)
    print(f"  {'TOTAL':18s} {'':>12s} {total:>6.0f}h")
    objetivo = proyecto.get("total_horas") or 0
    if objetivo and abs(total - objetivo) > 0.01:
        print(f"\n  AVISO: el proyecto declara {objetivo} h y el registro suma {total:.0f} h.")
    print(f"\n  Jornadas de capacitación: {len(capacitaciones)}")
    print(f"  Visitas programadas: {len(visitas)} "
          f"({fecha_corta(visitas[0]['fecha'])} a {fecha_corta(visitas[-1]['fecha'])})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sin-evaluaciones", dest="sin_evaluaciones", action="store_true",
                    help="no rellena los anexos 6.1, 6.2 ni 11")
    cargar(**vars(ap.parse_args()))
