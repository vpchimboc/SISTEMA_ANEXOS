"""
Construye el diccionario que se inyecta en las plantillas Jinja2.

Todo lo que las plantillas pueden usar sale de aquí. Si una plantilla pide una
variable que este módulo no entrega, docxtpl la deja vacía en silencio; por eso
al final hay `verificar_contexto`, que compara las etiquetas de una plantilla
con las claves disponibles y avisa de las que faltan.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any

from . import db

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


# --------------------------------------------------------------------------
# Fechas
# --------------------------------------------------------------------------

def _a_fecha(valor: Any) -> date | None:
    if isinstance(valor, date):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    if not valor:
        return None
    texto = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def fecha_larga(valor: Any) -> str:
    """22 de septiembre de 2025"""
    f = _a_fecha(valor)
    return f"{f.day} de {MESES_ES[f.month - 1]} de {f.year}" if f else ""


def fecha_corta(valor: Any) -> str:
    """22/09/2025"""
    f = _a_fecha(valor)
    return f.strftime("%d/%m/%Y") if f else ""


def mes_anio(valor: Any) -> str:
    """Septiembre 2025"""
    f = _a_fecha(valor)
    return f"{MESES_ES[f.month - 1].capitalize()} {f.year}" if f else ""


class Fecha(dict):
    """
    Fecha lista para la plantilla. Se usa como {{ f.anexo1.larga }} o
    {{ f.anexo1.corta }}; escrita sola, {{ f.anexo1 }}, sale en formato corto.
    """

    def __init__(self, valor: Any):
        super().__init__(
            larga=fecha_larga(valor),
            corta=fecha_corta(valor),
            mes=mes_anio(valor),
            iso=(_a_fecha(valor).isoformat() if _a_fecha(valor) else ""),
        )

    def __str__(self) -> str:
        return self["corta"]

    __getattr__ = dict.get


# --------------------------------------------------------------------------
# Personas
# --------------------------------------------------------------------------

def _persona(fila: dict | None) -> dict:
    """Normaliza una persona y le añade la forma en que se firma."""
    fila = dict(fila or {})
    titulo = (fila.get("titulo") or "").strip()
    nombre = (fila.get("nombre") or "").strip()
    fila.setdefault("cargo", "")
    fila["nombre"] = nombre
    fila["titulo"] = titulo
    fila["firma"] = f"{titulo} {nombre}".strip()
    fila.setdefault("tratamiento", "Magíster")
    fila.setdefault("email", "")
    fila.setdefault("cedula", "")
    fila.setdefault("telefono", "")
    return fila


def _estudiante(fila: dict, docentes: dict[int, dict],
                docente_defecto: dict | None = None) -> dict:
    fila = dict(fila)
    nombres = (fila.get("nombres") or "").strip()
    apellidos = (fila.get("apellidos") or "").strip()
    completo = (fila.get("nombre_completo") or "").strip()
    fila["nombre_completo"] = completo or f"{nombres} {apellidos}".strip()
    fila["nombre_apellido"] = f"{apellidos} {nombres}".strip() or fila["nombre_completo"]
    fila["tratamiento"] = "Señorita" if (fila.get("sexo") or "M").upper() == "F" else "Señor"
    asignado = docentes.get(fila.get("docente_apoyo_id"))
    # Si no se asignó docente y el proyecto tiene uno solo, todos son suyos.
    # Sin esto el Anexo 9 (que se emite por docente) sale vacío y se omite.
    fila["docente_apoyo"] = _persona(asignado or docente_defecto)
    return fila


# --------------------------------------------------------------------------
# Contexto base (lo que comparten todos los anexos)
# --------------------------------------------------------------------------

def construir(con: sqlite3.Connection) -> dict:
    proyecto = dict(db.obtener_proyecto(con))

    personas = db.listar(con, "personas", orden="orden, id")
    por_id = {p["id"]: _persona(p) for p in personas}
    por_rol: dict[str, list[dict]] = {}
    for p in personas:
        por_rol.setdefault(p["rol"], []).append(_persona(p))

    def uno(rol: str) -> dict:
        lista = por_rol.get(rol) or []
        return lista[0] if lista else _persona(None)

    docentes_apoyo = por_rol.get("docente_apoyo", [])

    docente_defecto = docentes_apoyo[0] if len(docentes_apoyo) == 1 else None
    estudiantes = [_estudiante(e, por_id, docente_defecto)
                   for e in db.listar(con, "estudiantes", donde="activo = 1")]

    actividades = db.listar(con, "actividades", orden="nro, id")
    for a in actividades:
        a["horas_texto"] = f"{int(a['horas'])}h" if a["horas"] else ""

    fechas = {f["clave"]: Fecha(f["valor"]) for f in db.listar(con, "fechas", orden="clave")}

    # Fechas del proyecto también disponibles con formato.
    for campo in ("fecha_inicio", "fecha_fin", "fecha_evaluacion",
                  "fecha_convocatoria", "fecha_max_solicitudes", "fecha_elaboracion"):
        proyecto[campo + "_larga"] = fecha_larga(proyecto.get(campo))
        proyecto[campo + "_corta"] = fecha_corta(proyecto.get(campo))

    for campo in ("fecha_seguimiento", "fecha_entrega"):
        proyecto[campo + "_corta"] = fecha_corta(proyecto.get(campo))
        proyecto[campo + "_larga"] = fecha_larga(proyecto.get(campo))

    proyecto["total_horas_texto"] = f"{proyecto.get('total_horas') or 0} horas"
    # Los formatos ISTA escriben el nombre del proyecto en mayúsculas.
    proyecto["nombre_mayusculas"] = (proyecto.get("nombre") or "").upper()

    contexto = {
        "p": proyecto,
        "f": _FechasFaltantes(fechas),
        "director": uno("director_proyecto"),
        "responsable": uno("responsable_vinculacion"),
        "coord_carrera": uno("coordinador_carrera"),
        "coord_vinculacion": uno("coordinador_vinculacion"),
        "representante": uno("representante_legal"),
        "docentes": docentes_apoyo,
        "docentes_apoyo": docentes_apoyo,
        "personas": por_rol,
        "estudiantes": estudiantes,
        "actividades": actividades,
        "requisitos": db.listar(con, "requisitos"),
        "cronograma": db.listar(con, "cronograma"),
        "registro": db.listar(con, "registro_diario"),
        "meses": db.listar(con, "meses", orden="nro, id"),
        "jornadas": db.listar(con, "jornadas", orden="nro, id"),
        "visitas": [dict(v, fecha=fecha_corta(v["fecha"]) or v["fecha"])
                    for v in db.listar(con, "visitas")],
        "hoy": Fecha(date.today()),
        # Tablas crudas: el generador las filtra por estudiante, mes o jornada.
        "_registro": db.listar(con, "registro_diario"),
        "_evaluacion_plan": db.listar(con, "evaluacion_plan", orden="id"),
        "_evaluacion_estudiante": db.listar(con, "evaluacion_estudiante", orden="id"),
        "_planificacion": db.listar(con, "planificacion"),
        "_seguimiento": db.listar(con, "seguimiento"),
        "_cortes": {c["corte"]: c["fecha"] for c in db.listar(con, "cortes", orden="corte")},

        # --- Informes narrativos (selección, seguimiento, final, socialización)
        "n": _Blandas({r["clave"]: r["texto"]
                       for r in db.listar(con, "narrativa", orden="clave")}),
        "o": _casillas({r["clave"]: r["valor"]
                        for r in db.listar(con, "opciones", orden="clave")}),
        "docentes_informe": _docentes_informe(por_rol),
        "indicadores": db.listar(con, "indicadores", orden="orden, id"),
        "matriz_objetivos": db.listar(con, "matriz_objetivos"),
        "constancia": [dict(c, marca=(MARCA_CHECK if c["marcado"] else ""))
                       for c in db.listar(con, "constancia")],
        "_listas": db.listar(con, "listas"),
        "_actividades_informe": db.listar(con, "actividades_informe"),
        # El estudiante y el docente "actuales" los fija el generador según el
        # anexo; se dejan vacíos para que la plantilla nunca reviente.
        "estudiante": _estudiante({"cedula": ""}, por_id),
        "docente": _persona(None),
        "mes": {},
        "jornada": {},
    }
    return contexto


# --------------------------------------------------------------------------
# Informes narrativos: casillas, listas y bloques de texto
# --------------------------------------------------------------------------

CASILLA_MARCADA = "☒"
CASILLA_VACIA = "☐"
MARCA_CHECK = "X"

# Cada grupo de casillas de los formatos ISTA: clave guardada -> opciones.
GRUPOS_CASILLAS = {
    "linea_accion": ("linea", ["asesoria", "comunitario", "capacitacion"]),
    "alcance": ("alcance", ["nacional", "provincial", "cantonal",
                            "parroquial", "institucional", "internacional"]),
    "impacto": ("impacto", ["social", "cientifico", "economico",
                            "politico", "otro"]),
}


class _Blandas(dict):
    """Diccionario que devuelve cadena vacía en vez de fallar por clave ausente."""

    def __missing__(self, clave):
        return ""

    __getattr__ = dict.get


def _casillas(valores: dict) -> _Blandas:
    """
    Traduce la opción elegida de cada grupo a las casillas ☒/☐ que espera la
    plantilla. Por ejemplo, con linea_accion = "comunitario" se obtiene
    o.linea_asesoria = ☐, o.linea_comunitario = ☒, o.linea_capacitacion = ☐.
    """
    salida = _Blandas()
    for clave, (prefijo, opciones) in GRUPOS_CASILLAS.items():
        elegida = (valores.get(clave) or "").strip().lower()
        for opcion in opciones:
            salida[f"{prefijo}_{opcion}"] = (
                CASILLA_MARCADA if opcion == elegida else CASILLA_VACIA)
    return salida


def _docentes_informe(por_rol: dict) -> list[dict]:
    """
    Equipo docente para los informes ISTA: el director más los docentes de
    apoyo, sin repetir a quien cumple los dos papeles (pasa a menudo).
    """
    equipo, vistos = [], set()
    for rol in ("director_proyecto", "docente_apoyo"):
        for persona in por_rol.get(rol, []):
            clave = (persona.get("cedula") or persona.get("nombre") or "").strip().lower()
            if clave in vistos:
                continue
            vistos.add(clave)
            equipo.append(persona)
    return equipo


def lista_de(base: dict, clave: str) -> list[dict]:
    """Viñetas de una lista concreta (objetivos, conclusiones, productos…)."""
    return [{"texto": x["texto"]} for x in base["_listas"] if x["clave"] == clave]


def actividades_informe_de(base: dict, informe: str) -> list[dict]:
    filas = [dict(a) for a in base["_actividades_informe"] if a["informe"] == informe]
    for fila in filas:
        fila["fecha"] = fecha_corta(fila["fecha"]) or fila["fecha"]
    return filas


# --------------------------------------------------------------------------
# Datos derivados por anexo
# --------------------------------------------------------------------------

MARCA = "x"


def preparar_mes(mes: dict) -> dict:
    mes = dict(mes)
    for campo in ("fecha_planificacion", "fecha_seguimiento", "fecha_socializacion"):
        mes[campo + "_corta"] = fecha_corta(mes.get(campo))
        mes[campo + "_larga"] = fecha_larga(mes.get(campo))
    return mes


def registro_de(base: dict, estudiante: dict) -> tuple[list[dict], float]:
    """
    Registro diario del estudiante. Las filas sin estudiante asignado son
    comunes a todo el grupo, que es como se llevan en la práctica.
    """
    eid = estudiante.get("id")
    filas = [dict(r) for r in base["_registro"]
             if not r.get("estudiante_id") or r["estudiante_id"] == eid]
    for r in filas:
        r["fecha"] = fecha_corta(r["fecha"]) or r["fecha"]
        r["horas"] = int(r["horas"]) if float(r["horas"]).is_integer() else r["horas"]
    total = sum(float(r["horas"]) for r in filas)
    return filas, (int(total) if float(total).is_integer() else total)


def plan_de(base: dict, estudiante: dict, corte: str) -> list[dict]:
    """
    Filas del Anexo 6.1 / 6.2: cada actividad con su avance y su valoración.
    Si no hay evaluación cargada para una actividad, sale en blanco (que es
    justo lo que hace el documento oficial con las actividades no iniciadas).
    """
    eid = estudiante.get("id")
    por_actividad = {e["actividad_id"]: e for e in base["_evaluacion_plan"]
                     if e["estudiante_id"] == eid and e["corte"] == corte}
    filas = []
    for act in base["actividades"]:
        ev = por_actividad.get(act["id"], {})
        valoracion = (ev.get("valoracion") or "").lower()
        logro = (ev.get("logro") or "").lower()
        filas.append({
            "nro": act["nro"],
            "descripcion": act["descripcion"],
            "avance": ev.get("avance") or "0%",
            "poco": MARCA if valoracion == "poco" else "",
            "satisfactorio": MARCA if valoracion == "satisfactorio" else "",
            "muy": MARCA if valoracion == "muy" else "",
            "si": MARCA if logro == "si" else "",
            "no": MARCA if logro == "no" else "",
        })
    return filas


ITEMS_11 = {"1": ["1.1", "1.2", "1.3", "1.4"], "2": ["2.1", "2.2", "2.3", "2.4"]}


def evaluacion_de(base: dict, estudiante: dict) -> tuple[dict, Any]:
    """
    Anexo 11. Devuelve (resumen, función `marca`).

    El puntaje de cada bloque se expresa como el original: "20/20", es decir
    la suma de los cuatro ítems sobre el máximo posible (4 ítems x 5 = 20).
    """
    eid = estudiante.get("id")
    puntajes = {e["item"]: int(e["puntaje"])
                for e in base["_evaluacion_estudiante"] if e["estudiante_id"] == eid}

    def marca(item: str, columna: int) -> str:
        return MARCA if puntajes.get(item, 5) == columna else ""

    resumen = {}
    totales = []
    for bloque, items in ITEMS_11.items():
        suma = sum(puntajes.get(i, 5) for i in items)
        maximo = len(items) * 5
        resumen[f"bloque{bloque}"] = f"{suma}/{maximo}"
        totales.append((suma, maximo))

    suma_total = sum(s for s, _ in totales)
    max_total = sum(m for _, m in totales)
    promedio = round(suma_total / len(totales))
    resumen["promedio"] = f"{promedio}/{totales[0][1]}"
    resumen["total"] = f"{suma_total}/{max_total}"
    resumen["resultado"] = "APRUEBA" if suma_total >= max_total * 0.7 else "NO APRUEBA"
    return resumen, marca


def planificacion_de(base: dict, mes: dict, tipo: str) -> list[dict]:
    """Filas del Anexo 7 para un mes, resolviendo nombres y cédulas."""
    personas = {}
    for lista in base["personas"].values():
        for persona in lista:
            personas[persona["id"]] = persona
    estudiantes = {e["id"]: e for e in base["estudiantes"]}
    actividades = {a["id"]: a for a in base["actividades"]}

    filas = []
    for fila in base["_planificacion"]:
        if fila["mes_id"] != mes.get("id") or fila["tipo"] != tipo:
            continue
        fuente = personas if tipo == "docente" else estudiantes
        persona = fuente.get(fila["persona_id"], {})
        actividad = actividades.get(fila["actividad_id"], {})
        filas.append({
            "resultado": fila["resultado"] or actividad.get("producto", ""),
            "actividad": (actividad.get("descripcion_docente") if tipo == "docente"
                          else actividad.get("descripcion", "")) or actividad.get("descripcion", ""),
            "nombre": persona.get("nombre_completo") or persona.get("nombre", ""),
            "cedula": persona.get("cedula", ""),
            "horas": int(fila["horas"]) if float(fila["horas"]).is_integer() else fila["horas"],
            "fecha_inicio": fecha_corta(fila["fecha_inicio"]) or fila["fecha_inicio"],
            "fecha_fin": fecha_corta(fila["fecha_fin"]) or fila["fecha_fin"],
            "observaciones": fila["observaciones"],
        })
    return filas


def seguimiento_de(base: dict, mes: dict, docente: dict | None = None) -> list[dict]:
    """Filas del Anexo 9 para un mes; si se pasa docente, solo sus estudiantes."""
    estudiantes = {e["id"]: e for e in base["estudiantes"]}
    actividades = {a["id"]: a for a in base["actividades"]}
    permitidos = None
    if docente and docente.get("id"):
        permitidos = {e["id"] for e in base["estudiantes"]
                      if (e.get("docente_apoyo") or {}).get("id") == docente["id"]}

    filas = []
    for fila in base["_seguimiento"]:
        if fila["mes_id"] != mes.get("id"):
            continue
        if permitidos is not None and fila["estudiante_id"] not in permitidos:
            continue
        estudiante = estudiantes.get(fila["estudiante_id"], {})
        actividad = actividades.get(fila["actividad_id"], {})
        filas.append({
            "descripcion": fila["descripcion"] or actividad.get("descripcion", ""),
            "estudiante": estudiante.get("nombre_completo", ""),
            "fecha_planificada": fecha_corta(fila["fecha_planificada"]) or fila["fecha_planificada"],
            "finalizada": fila["finalizada"],
            "fecha_fin_prevista": fecha_corta(fila["fecha_fin_prevista"]) or fila["fecha_fin_prevista"],
            "avance": fila["avance"],
        })
    return filas


def preparar_jornada(jornada: dict) -> dict:
    jornada = dict(jornada)
    jornada["fecha"] = fecha_corta(jornada.get("fecha")) or jornada.get("fecha", "")
    horas = str(jornada.get("horas") or "").strip()
    if horas and not horas.lower().endswith("hora") and "hora" not in horas.lower():
        horas = f"{horas} horas"
    jornada["horas"] = horas
    return jornada


class _FechasFaltantes(dict):
    """Devuelve una fecha vacía en lugar de fallar si la clave no existe."""

    def __missing__(self, clave):  # pragma: no cover - defensivo
        return Fecha(None)

    __getattr__ = dict.get


# --------------------------------------------------------------------------
# Verificación
# --------------------------------------------------------------------------

def verificar_contexto(plantilla_vars: set[str], contexto: dict) -> list[str]:
    """
    Devuelve las variables de primer nivel que la plantilla usa y el contexto
    no entrega. docxtpl las dejaría en blanco sin avisar.
    """
    disponibles = set(contexto)
    return sorted(v for v in plantilla_vars if v.split(".")[0] not in disponibles)
