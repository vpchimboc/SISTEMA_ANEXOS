#!/usr/bin/env python3
"""
Carga el registro diario de actividades del Anexo 8.

Son las 35 entradas del mantenimiento de laboratorios, que suman exactamente
las 100 horas de vinculación. Como el detalle se repite fase tras fase, vive
aquí para poder recargarlo en cualquier proyecto.

    # tal cual, con las fechas que trae la lista
    python herramientas/cargar_registro.py

    # reubicadas dentro de las fechas del proyecto activo
    python herramientas/cargar_registro.py --reubicar

    # sin borrar lo que ya hubiera
    python herramientas/cargar_registro.py --agregar

El lugar se toma del proyecto activo, no de la lista: las entradas vienen de
una fase anterior y arrastrarían el nombre de la unidad educativa equivocada.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import db  # noqa: E402
from core.contexto import _a_fecha  # noqa: E402

# (fecha original, descripción, horas)
REGISTRO = [
    ("2025-09-29", "Recorrido por los Laboratorios de la U.E. con los estudiantes para la distribución de actividades.", 2),
    ("2025-09-29", "Reunión entre docentes, estudiantes y representantes de la unidad educativa para recopilar información previa al mantenimiento y establecer los requerimientos de software.", 2),
    ("2025-09-30", "Inspección de hardware y periféricos: Examinar visualmente las computadoras en busca de desgaste, daños físicos, componentes sueltos, cables deteriorados o periféricos faltantes.", 4),
    ("2025-10-01", "Pruebas de operación: Encendido de equipos y evaluación de su comportamiento a fin de determinar el estado y posterior revisión de características.", 4),
    ("2025-10-02", "Inventario inicial: Registro de características e identificativos (códigos, modelo, seriales, etc) y evaluación de estado del disco duro empleando CrystalDiskInfo", 4),
    ("2025-10-03", "Inventario inicial: Registro de características e identificativos (códigos, modelo, seriales, etc) y evaluación de estado del disco duro empleando CrystalDiskInfo", 4),
    ("2025-10-08", "Creación de copias de seguridad: Se verifica la operatividad de los equipos y se realizan copias de seguridad del disco de datos de los estudiantes, se emplea medios de almacenamiento externos como memorias USB y discos duros extraíbles.", 5),
    ("2025-10-09", "Creación de copias de seguridad: Se verifica la operatividad de los equipos y se realizan copias de seguridad del disco de datos de los estudiantes, se emplea medios de almacenamiento externos como memorias USB y discos duros extraíbles.", 5),
    ("2025-10-13", "Desarmado y limpieza de equipos: Se desarma los CPU y se realiza limpieza interna y externa de computadora, se emplea sopladoras de aire, eliminando el polvo y la suciedad; para luego volver a armarlas y probar operatividad.", 5),
    ("2025-10-14", "Desarmado y limpieza de equipos: Se desarma los CPU y se realiza limpieza interna y externa de computadora, se emplea sopladoras de aire, eliminando el polvo y la suciedad; para luego volver a armarlas y probar operatividad.", 5),
    ("2025-10-15", "Desarmado y limpieza de equipos: Se desarma los CPU y se realiza limpieza interna y externa de computadora, se emplea sopladoras de aire, eliminando el polvo y la suciedad; para luego volver a armarlas y probar operatividad.", 5),
    ("2025-10-16", "Selección y pruebas de sistema operativo y programas requeridos: Se realiza memorias USB booteables con una versión liviana de Windows, adaptada para las características de las PCs, se prueba la instalación y se selecciona los programas complementarios a la instalación.", 3),
    ("2025-10-17", "Selección y pruebas de sistema operativo y programas requeridos: Se realiza memorias USB booteables con una versión liviana de Windows, adaptada para las características de las PCs, se prueba la instalación y se selecciona los programas complementarios a la instalación.", 2),
    ("2025-10-20", "Instalación y configuración inicial del Sistema Operativo: Se instala el sistema operativo y se establecen las configuraciones ajustadas a las características del hardware, además se personalizan los identificadores y fondos de escritorio con pertinencia institucional.", 2),
    ("2025-10-21", "Instalación de programas complementarios: De acuerdo a los solicitado por la institución, se instalación programas de la Suite Office, lenguajes e IDEs de programación y de productividad en general", 3),
    ("2025-10-22", "Activación de licencias y pruebas de configuraciones de programas: Se activan licencias disponibles del sistema operativo y de los programas, además se cargan las configuraciones iniciales, de modo que estén disponibles los programas directamente para su uso.", 3),
    ("2025-10-23", "Restauración de copias de seguridad: Las copias de seguridad almacenadas previamente se restauran en los equipos correspondientes.", 3),
    ("2025-10-24", "Mantenimiento y reemplazo de periféricos: Dada la adquisición de periféricos por parte de la UE y existentes algunos en bodega, se reemplazan aquellos que presentan alguna novedad, así como cables o reparaciones menores en pines.", 2),
    ("2025-10-27", "Mantenimiento a tomacorrientes: Se revisan tomacorrientes que alimentan los UPS de las PCs y se da mantenimiento correspondiente, a limpieza y verificación de conexiones en buen estado y aseguramiento a sus soportes.", 2),
    ("2025-10-28", "Revisión de equipos que presentan fallas luego de la instalación: Por la antigüedad, algunos equipos no responden favorablemente luego de la instalación del sistema operativo, se diagnostica el motivo de falla y se procura solventarlo.", 2),
    ("2025-10-29", "Etiquetado de equipos y aseguramiento de cables: Se realiza etiquetas, las mismas que se imprimen y se colocan correspondientemente en las máquinas de acuerdo a su identificativo, además empleando amarras se aseguran los cables y se acomodan conexiones. Se agrega advertencias impresas en A4 sobre cuidado y reglas de uso en laboratorios.", 2),
    ("2025-10-29", "Actualización de inventario: Tras el mantenimiento y cambio de diversos periféricos, se actualiza el inventario en las fichas de operaciones anotando las nuevas novedades y el estado actual en el cual se entrega.", 1),
    ("2025-10-30", "Revisión de cables y conexiones: Inspeccionar cables de red y conexiones para detectar problemas físicos en la red de datos, además se adquiere información sobre el etiquetado actual y los equipos intermediarios en la red.", 3),
    ("2025-10-31", "Pruebas de conectividad de red: Se verifica la conectividad de cada equipo a la red local e internet así como se evalúa la velocidad disponible en cada uno, registrando el medio por el cual accede a la red (WiFi o Ethernet).", 2),
    ("2025-11-05", "Mantenimiento a puntos de red: Ponchado de nuevos cables, configuración de políticas de seguridad en equipos intermediarios de red para filtrado MAC y bloqueo del levantamiento de redes WiFi de red compartida desde PCs.", 3),
    ("2025-11-06", "Mantenimiento a puntos de red: Ponchado de nuevos cables, configuración de políticas de seguridad en equipos intermediarios de red para filtrado MAC y bloqueo del levantamiento de redes WiFi de red compartida desde PCs.", 3),
    ("2025-11-07", "Mantenimiento a puntos de red: Ponchado de nuevos cables, configuración de políticas de seguridad en equipos intermediarios de red para filtrado MAC y bloqueo del levantamiento de redes WiFi de red compartida desde PCs.", 3),
    ("2025-11-10", "Mantenimiento a puntos de red: Ponchado de nuevos cables, configuración de políticas de seguridad en equipos intermediarios de red para filtrado MAC y bloqueo del levantamiento de redes WiFi de red compartida desde PCs.", 1),
    ("2025-11-17", "Revisión de los requerimientos y expectativas de capacitación de docentes y estudiantes.", 2),
    ("2025-11-18", "Desarrollo de planes de estudio detallados para cada taller, así como la preparación de material de capacitación, (presentaciones y guía), se programa las fechas y horario para las capacitaciones teóricas prácticas y se define el espacio y recursos necesarios para la capacitación.", 2),
    ("2025-11-19", "Desarrollo de planes de estudio detallados para cada taller, así como la preparación de material de capacitación, (presentaciones y guía), se programa las fechas y horario para las capacitaciones teóricas prácticas y se define el espacio y recursos necesarios para la capacitación.", 2),
    ("2025-11-20", "Desarrollo de planes de estudio detallados para cada taller, así como la preparación de material de capacitación, (presentaciones y guía), se programa las fechas y horario para las capacitaciones teóricas prácticas y se define el espacio y recursos necesarios para la capacitación.", 2),
    ("2025-11-24", "Desarrollo de planes de estudio detallados para cada taller, así como la preparación de material de capacitación, (presentaciones y guía), se programa las fechas y horario para las capacitaciones teóricas prácticas y se define el espacio y recursos necesarios para la capacitación.", 2),
    ("2025-12-05", "Impartición de jornada de capacitación.", 3),
    ("2025-12-12", "Impartición de jornada de capacitación.", 2),
]


def _dia_habil(dia: date) -> date:
    """Empuja al lunes siguiente si cae en sábado o domingo."""
    while dia.weekday() >= 5:
        dia += timedelta(days=1)
    return dia


def reubicar(filas: list[tuple[str, str, int]],
             inicio: date, fin: date) -> dict[str, str]:
    """
    Traslada las fechas originales a la ventana del proyecto conservando el
    orden y la separación relativa entre jornadas.

    Se escala la distancia de cada fecha respecto a la primera, se lleva a día
    hábil y, si el resultado se solapa con la jornada anterior, se empuja al
    siguiente día hábil. Así no se pierde el ritmo del cronograma ni se
    invierte el orden de las actividades.
    """
    originales = sorted({f for f, _, _ in filas})
    prim, ult = _a_fecha(originales[0]), _a_fecha(originales[-1])
    span_origen = max((ult - prim).days, 1)
    span_destino = max((fin - inicio).days, 1)
    factor = span_destino / span_origen

    mapa: dict[str, str] = {}
    anterior: date | None = None
    for original in originales:
        desplazamiento = round((_a_fecha(original) - prim).days * factor)
        nueva = _dia_habil(inicio + timedelta(days=desplazamiento))
        if anterior is not None and nueva <= anterior:
            nueva = _dia_habil(anterior + timedelta(days=1))
        if nueva > fin:
            nueva = fin
        mapa[original] = nueva.isoformat()
        anterior = nueva
    return mapa


def cargar(reubicar_fechas: bool = False, agregar: bool = False) -> None:
    with db.conexion() as con:
        proyecto = db.obtener_proyecto(con)
        lugar = (proyecto.get("entidad_corta") or proyecto.get("entidad")
                 or proyecto.get("lugar") or "")

        mapa = {}
        if reubicar_fechas:
            inicio = _a_fecha(proyecto.get("fecha_inicio"))
            fin = _a_fecha(proyecto.get("fecha_fin"))
            if not inicio or not fin:
                print("El proyecto no tiene fecha de inicio o de fin: no se puede reubicar.")
                return
            mapa = reubicar(REGISTRO, inicio, fin)

        if not agregar:
            con.execute("DELETE FROM registro_diario")
        desde = con.execute(
            "SELECT COALESCE(MAX(orden), -1) + 1 AS n FROM registro_diario").fetchone()["n"]

        for i, (fecha, descripcion, horas) in enumerate(REGISTRO):
            db.insertar(con, "registro_diario", {
                "fecha": mapa.get(fecha, fecha), "descripcion": descripcion,
                "lugar": lugar, "horas": horas, "orden": desde + i})

    total = sum(h for _, _, h in REGISTRO)
    print(f"{len(REGISTRO)} actividades cargadas · {total} horas · lugar: {lugar}")
    if mapa:
        print(f"Fechas reubicadas: {list(mapa.values())[0]} → {list(mapa.values())[-1]}")
    else:
        print("Fechas: las originales de la lista (sin reubicar).")
    objetivo = proyecto.get("total_horas") or 0
    if objetivo and total != objetivo:
        print(f"AVISO: el proyecto declara {objetivo} horas y el registro suma {total}.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reubicar", dest="reubicar_fechas", action="store_true",
                    help="traslada las fechas a la ventana del proyecto activo")
    ap.add_argument("--agregar", action="store_true",
                    help="no borra el registro existente")
    cargar(**vars(ap.parse_args()))
