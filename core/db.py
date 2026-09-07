"""
Capa de datos del Sistema de Anexos de Vinculación.

Fuente única de verdad: una base SQLite local (datos/anexos.db).
El sistema maneja UN proyecto activo a la vez (fila id=1 en la tabla `proyecto`),
pero el esquema ya soporta guardar históricos si más adelante hiciera falta.

Diseño: sin ORM. sqlite3 de la stdlib basta y evita una dependencia más.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

RAIZ = Path(__file__).resolve().parent.parent
RUTA_DB = RAIZ / "datos" / "anexos.db"

# --------------------------------------------------------------------------
# Esquema
# --------------------------------------------------------------------------

ESQUEMA = """
PRAGMA foreign_keys = ON;

-- Datos generales del proyecto y de la institución. Fila única (id = 1).
CREATE TABLE IF NOT EXISTS proyecto (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    nombre                  TEXT NOT NULL DEFAULT '',
    nombre_corto            TEXT NOT NULL DEFAULT '',
    fase                    TEXT NOT NULL DEFAULT '',
    ciudad                  TEXT NOT NULL DEFAULT 'Cuenca',
    codigo_convocatoria     TEXT NOT NULL DEFAULT '',

    -- Carrera / instituto
    instituto               TEXT NOT NULL DEFAULT 'INSTITUTO SUPERIOR UNIVERSITARIO TECNOLÓGICO DEL AZUAY',
    instituto_alt           TEXT NOT NULL DEFAULT 'INSTITUTO SUPERIOR TECNOLÓGICO DEL AZUAY CON CONDICIÓN DE SUPERIOR UNIVERSITARIO',
    carrera                 TEXT NOT NULL DEFAULT '',
    carrera_corta           TEXT NOT NULL DEFAULT '',
    periodo_academico       TEXT NOT NULL DEFAULT '',
    paralelo                TEXT NOT NULL DEFAULT '',
    jornada                 TEXT NOT NULL DEFAULT '',
    ciclo                   TEXT NOT NULL DEFAULT '',
    ciclo_minimo            TEXT NOT NULL DEFAULT 'cuarto',

    -- Entidad beneficiaria
    entidad                 TEXT NOT NULL DEFAULT '',
    entidad_corta           TEXT NOT NULL DEFAULT '',
    entidad_direccion       TEXT NOT NULL DEFAULT '',
    entidad_descripcion     TEXT NOT NULL DEFAULT '',
    entidad_telefono        TEXT NOT NULL DEFAULT '',
    entidad_email           TEXT NOT NULL DEFAULT '',

    -- Fechas y carga horaria
    total_horas             INTEGER NOT NULL DEFAULT 100,
    fecha_inicio            TEXT NOT NULL DEFAULT '',
    fecha_fin               TEXT NOT NULL DEFAULT '',
    fecha_evaluacion        TEXT NOT NULL DEFAULT '',
    fecha_convocatoria      TEXT NOT NULL DEFAULT '',
    fecha_max_solicitudes   TEXT NOT NULL DEFAULT '',
    fecha_elaboracion       TEXT NOT NULL DEFAULT '',
    lugar                   TEXT NOT NULL DEFAULT '',

    -- Campos propios de los formatos ISTA (informes de seguimiento y final)
    programa_vinculacion    TEXT NOT NULL DEFAULT '',
    plazo_ejecucion         TEXT NOT NULL DEFAULT '',
    fecha_seguimiento       TEXT NOT NULL DEFAULT '',
    fecha_entrega           TEXT NOT NULL DEFAULT '',
    enlace_anexos           TEXT NOT NULL DEFAULT '',
    director_carrera        TEXT NOT NULL DEFAULT ''
);

-- Personas con rol institucional (no estudiantes).
-- rol: director_proyecto | docente_apoyo | responsable_vinculacion |
--      coordinador_carrera | coordinador_vinculacion | representante_legal
CREATE TABLE IF NOT EXISTS personas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rol         TEXT NOT NULL,
    titulo      TEXT NOT NULL DEFAULT 'Mgtr.',
    tratamiento TEXT NOT NULL DEFAULT 'Magíster',
    nombre      TEXT NOT NULL,
    cedula      TEXT NOT NULL DEFAULT '',
    cargo       TEXT NOT NULL DEFAULT '',
    email       TEXT NOT NULL DEFAULT '',
    telefono    TEXT NOT NULL DEFAULT '',
    horas       TEXT NOT NULL DEFAULT '',   -- "2h/semana por 3 meses = 24h"
    orden       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS estudiantes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    cedula            TEXT NOT NULL UNIQUE,
    nombres           TEXT NOT NULL DEFAULT '',
    apellidos         TEXT NOT NULL DEFAULT '',
    nombre_completo   TEXT NOT NULL DEFAULT '',
    email             TEXT NOT NULL DEFAULT '',
    telefono          TEXT NOT NULL DEFAULT '',
    ciclo             TEXT NOT NULL DEFAULT '',
    paralelo          TEXT NOT NULL DEFAULT '',
    jornada           TEXT NOT NULL DEFAULT '',
    codigo            TEXT NOT NULL DEFAULT '',
    horas             TEXT NOT NULL DEFAULT '',
    sexo              TEXT NOT NULL DEFAULT 'M',   -- para "Señor / Señorita"
    docente_apoyo_id  INTEGER REFERENCES personas(id) ON DELETE SET NULL,
    activo            INTEGER NOT NULL DEFAULT 1,
    orden             INTEGER NOT NULL DEFAULT 0
);

-- Plan de aprendizaje del proyecto (Anexo 6). Es la columna vertebral:
-- de aquí salen también los anexos 2, 6.1, 6.2, 7, 9 y 10.
CREATE TABLE IF NOT EXISTS actividades (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    nro                    INTEGER NOT NULL,
    descripcion            TEXT NOT NULL DEFAULT '',
    descripcion_docente    TEXT NOT NULL DEFAULT '',
    asignatura             TEXT NOT NULL DEFAULT '',
    resultados_aprendizaje TEXT NOT NULL DEFAULT '',
    producto               TEXT NOT NULL DEFAULT '',
    horas                  INTEGER NOT NULL DEFAULT 0,
    horas_docente          INTEGER NOT NULL DEFAULT 0,
    detalle_especifico     TEXT NOT NULL DEFAULT ''   -- para el Anexo 10
);

-- Asignaturas requisito de la convocatoria (Anexo 2).
CREATE TABLE IF NOT EXISTS requisitos (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    orden  INTEGER NOT NULL DEFAULT 0
);

-- Cronograma del proceso de selección (Anexo 2).
CREATE TABLE IF NOT EXISTS cronograma (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    actividad TEXT NOT NULL,
    fecha     TEXT NOT NULL DEFAULT '',
    orden     INTEGER NOT NULL DEFAULT 0
);

-- Registro diario de actividades (Anexo 8). Si estudiante_id es NULL,
-- la fila aplica a todos los estudiantes.
CREATE TABLE IF NOT EXISTS registro_diario (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER REFERENCES estudiantes(id) ON DELETE CASCADE,
    fecha         TEXT NOT NULL DEFAULT '',
    descripcion   TEXT NOT NULL DEFAULT '',
    lugar         TEXT NOT NULL DEFAULT '',
    horas         REAL NOT NULL DEFAULT 0,
    orden         INTEGER NOT NULL DEFAULT 0
);

-- Meses del proyecto: gobiernan los anexos 7 (planificación) y 9 (seguimiento).
CREATE TABLE IF NOT EXISTS meses (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    nro                  INTEGER NOT NULL,
    etiqueta             TEXT NOT NULL,            -- "Septiembre 2025"
    fecha_planificacion  TEXT NOT NULL DEFAULT '',
    fecha_seguimiento    TEXT NOT NULL DEFAULT '',
    fecha_socializacion  TEXT NOT NULL DEFAULT '',
    observaciones        TEXT NOT NULL DEFAULT ''
);

-- Filas de planificación mensual (Anexo 7). tipo: docente | estudiante
CREATE TABLE IF NOT EXISTS planificacion (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    mes_id        INTEGER NOT NULL REFERENCES meses(id) ON DELETE CASCADE,
    tipo          TEXT NOT NULL,
    persona_id    INTEGER,                          -- personas.id o estudiantes.id según tipo
    actividad_id  INTEGER REFERENCES actividades(id) ON DELETE SET NULL,
    resultado     TEXT NOT NULL DEFAULT '',
    horas         REAL NOT NULL DEFAULT 0,
    fecha_inicio  TEXT NOT NULL DEFAULT '',
    fecha_fin     TEXT NOT NULL DEFAULT '',
    observaciones TEXT NOT NULL DEFAULT '',
    orden         INTEGER NOT NULL DEFAULT 0
);

-- Seguimiento mensual según planificación (Anexo 9).
CREATE TABLE IF NOT EXISTS seguimiento (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    mes_id         INTEGER NOT NULL REFERENCES meses(id) ON DELETE CASCADE,
    estudiante_id  INTEGER REFERENCES estudiantes(id) ON DELETE CASCADE,
    actividad_id   INTEGER REFERENCES actividades(id) ON DELETE SET NULL,
    descripcion    TEXT NOT NULL DEFAULT '',
    fecha_planificada TEXT NOT NULL DEFAULT '',
    finalizada     TEXT NOT NULL DEFAULT 'SI',
    fecha_fin_prevista TEXT NOT NULL DEFAULT '',
    avance         TEXT NOT NULL DEFAULT '100%',
    orden          INTEGER NOT NULL DEFAULT 0
);

-- Evaluación del plan de aprendizaje por estudiante (Anexos 6.1 parcial y 6.2 final).
-- corte: parcial | final ; valoracion: poco | satisfactorio | muy
CREATE TABLE IF NOT EXISTS evaluacion_plan (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    actividad_id  INTEGER NOT NULL REFERENCES actividades(id) ON DELETE CASCADE,
    corte         TEXT NOT NULL,
    avance        TEXT NOT NULL DEFAULT '0%',
    valoracion    TEXT NOT NULL DEFAULT '',
    logro         TEXT NOT NULL DEFAULT '',        -- 'si' | 'no' | ''
    UNIQUE (estudiante_id, actividad_id, corte)
);

-- Fechas de corte de los anexos 6.1 y 6.2.
CREATE TABLE IF NOT EXISTS cortes (
    corte TEXT PRIMARY KEY,                        -- parcial | final
    fecha TEXT NOT NULL DEFAULT ''
);

-- Evaluación al estudiante (Anexo 11). item: '1.1' .. '2.4'
CREATE TABLE IF NOT EXISTS evaluacion_estudiante (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id) ON DELETE CASCADE,
    evaluador     TEXT NOT NULL,                   -- docente_apoyo | director
    item          TEXT NOT NULL,
    puntaje       INTEGER NOT NULL DEFAULT 5,      -- 1..5
    UNIQUE (estudiante_id, evaluador, item)
);

-- Jornadas de capacitación / socialización (Anexo 12).
CREATE TABLE IF NOT EXISTS jornadas (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nro       INTEGER NOT NULL,
    asunto    TEXT NOT NULL DEFAULT '',
    fecha     TEXT NOT NULL DEFAULT '',
    horas     TEXT NOT NULL DEFAULT '',
    lugar     TEXT NOT NULL DEFAULT ''
);

-- Beneficiarios asistentes a cada jornada (Anexo 12).
CREATE TABLE IF NOT EXISTS beneficiarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    jornada_id INTEGER NOT NULL REFERENCES jornadas(id) ON DELETE CASCADE,
    nombre     TEXT NOT NULL DEFAULT '',
    cedula     TEXT NOT NULL DEFAULT '',
    cargo      TEXT NOT NULL DEFAULT '',
    telefono   TEXT NOT NULL DEFAULT '',
    email      TEXT NOT NULL DEFAULT '',
    orden      INTEGER NOT NULL DEFAULT 0
);

-- Visitas a la institución (Anexo 13).
CREATE TABLE IF NOT EXISTS visitas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha         TEXT NOT NULL DEFAULT '',
    hora_inicio   TEXT NOT NULL DEFAULT '',
    hora_fin      TEXT NOT NULL DEFAULT '',
    asunto        TEXT NOT NULL DEFAULT '',
    actividades   TEXT NOT NULL DEFAULT '',
    observaciones TEXT NOT NULL DEFAULT '',
    orden         INTEGER NOT NULL DEFAULT 0
);

-- Evidencias semanales del informe del estudiante (Anexo 10).
CREATE TABLE IF NOT EXISTS evidencias (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER REFERENCES estudiantes(id) ON DELETE CASCADE,
    semana        INTEGER NOT NULL DEFAULT 1,
    fecha_desde   TEXT NOT NULL DEFAULT '',
    fecha_hasta   TEXT NOT NULL DEFAULT '',
    actividad     TEXT NOT NULL DEFAULT '',
    orden         INTEGER NOT NULL DEFAULT 0
);

-- ------------------------------------------------------------------------
-- Informes narrativos (Proceso de selección, Seguimiento ISTA, Informe final
-- ISTA, Socialización y Constancia de anexos).
--
-- A diferencia de los anexos, estos documentos son en su mayor parte texto
-- redactado. No tiene sentido "calcularlo": el sistema lo guarda, lo deja
-- editable y lo coloca en el formato oficial.
-- ------------------------------------------------------------------------

-- Bloques de redacción. clave: sel_antecedentes, situacion_inicial, etc.
CREATE TABLE IF NOT EXISTS narrativa (
    clave TEXT PRIMARY KEY,
    texto TEXT NOT NULL DEFAULT ''
);

-- Listas de viñetas de los informes (objetivos específicos, conclusiones,
-- recomendaciones, productos obtenidos, resultados de indicadores...).
CREATE TABLE IF NOT EXISTS listas (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    clave TEXT NOT NULL,
    texto TEXT NOT NULL DEFAULT '',
    orden INTEGER NOT NULL DEFAULT 0
);

-- Casillas ☐/☒ de los formatos ISTA: línea de acción, alcance territorial e
-- impacto generado. Se guarda la opción elegida y el generador dibuja la
-- casilla marcada donde corresponde.
CREATE TABLE IF NOT EXISTS opciones (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL DEFAULT ''
);

-- Tabla de actividades de los informes ISTA. informe: seguimiento | final.
CREATE TABLE IF NOT EXISTS actividades_informe (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    informe       TEXT NOT NULL,
    actividad     TEXT NOT NULL DEFAULT '',
    cumplimiento  TEXT NOT NULL DEFAULT '100%',
    fecha         TEXT NOT NULL DEFAULT '',
    responsables  TEXT NOT NULL DEFAULT '',
    evidencia     TEXT NOT NULL DEFAULT '',
    observaciones TEXT NOT NULL DEFAULT 'Ninguna',
    orden         INTEGER NOT NULL DEFAULT 0
);

-- Indicadores de impacto (informe final).
CREATE TABLE IF NOT EXISTS indicadores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nro         INTEGER NOT NULL DEFAULT 1,
    descripcion TEXT NOT NULL DEFAULT '',
    tipo        TEXT NOT NULL DEFAULT 'Cualitativo',
    orden       INTEGER NOT NULL DEFAULT 0
);

-- Matriz de verificación de indicadores de objetivos (informe final).
CREATE TABLE IF NOT EXISTS matriz_objetivos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    objetivo      TEXT NOT NULL DEFAULT '',
    indicador     TEXT NOT NULL DEFAULT '',
    planificado   TEXT NOT NULL DEFAULT '',
    obtenido      TEXT NOT NULL DEFAULT '',
    observaciones TEXT NOT NULL DEFAULT '',
    orden         INTEGER NOT NULL DEFAULT 0
);

-- Checklist de la constancia de recepción de anexos.
CREATE TABLE IF NOT EXISTS constancia (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    numero       TEXT NOT NULL DEFAULT '',
    nombre       TEXT NOT NULL DEFAULT '',
    presentacion TEXT NOT NULL DEFAULT '',
    anexo        TEXT NOT NULL DEFAULT '',   -- clave del anexo que lo satisface
    marcado      INTEGER NOT NULL DEFAULT 0,
    orden        INTEGER NOT NULL DEFAULT 0
);

-- Fechas propias de cada anexo (clave libre: anexo1, anexo2, anexo2_limite...).
-- Se guardan en ISO (AAAA-MM-DD) y el generador las formatea larga y corta.
CREATE TABLE IF NOT EXISTS fechas (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL DEFAULT ''
);

-- Logos del encabezado.
-- La clave es LÓGICA, no posicional: en unos anexos el logo institucional va a
-- la izquierda y en otros a la derecha, así que identificarlos por posición
-- daría resultados cruzados. El manifiesto de plantillas dice, para cada
-- anexo, qué slot del encabezado corresponde a qué clave.
-- archivo vacío = se conserva la imagen que ya trae la plantilla.
-- escala = factor sobre el tamaño original del slot (1.0 = sin cambio).
CREATE TABLE IF NOT EXISTS logos (
    clave    TEXT PRIMARY KEY,                    -- institucional | senescyt
    nombre   TEXT NOT NULL DEFAULT '',
    archivo  TEXT NOT NULL DEFAULT '',            -- ruta relativa dentro de recursos/logos
    escala      REAL NOT NULL DEFAULT 1.0,
    proporcion  INTEGER NOT NULL DEFAULT 1,   -- 1 = no deformar el logo subido
    activo      INTEGER NOT NULL DEFAULT 1
);
"""


# --------------------------------------------------------------------------
# Conexión
# --------------------------------------------------------------------------

def _fila_a_dict(cursor: sqlite3.Cursor, fila: tuple) -> dict:
    return {col[0]: fila[i] for i, col in enumerate(cursor.description)}


@contextmanager
def conexion(ruta: Path | str | None = None):
    """Abre una conexión con filas tipo dict y foreign keys activas."""
    ruta = Path(ruta) if ruta else RUTA_DB
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta)
    con.row_factory = _fila_a_dict
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def inicializar(ruta: Path | str | None = None) -> None:
    """Crea el esquema si no existe y garantiza la fila única de proyecto."""
    with conexion(ruta) as con:
        con.executescript(ESQUEMA)
        existe = con.execute("SELECT 1 FROM proyecto WHERE id = 1").fetchone()
        if not existe:
            con.execute("INSERT INTO proyecto (id) VALUES (1)")
        for clave, nombre in (("institucional", "Logo institucional (TEC.AZUAY)"),
                              ("senescyt", "Logo SENESCYT")):
            hay = con.execute("SELECT 1 FROM logos WHERE clave = ?", (clave,)).fetchone()
            if not hay:
                con.execute("INSERT INTO logos (clave, nombre) VALUES (?, ?)",
                            (clave, nombre))


# --------------------------------------------------------------------------
# Utilidades genéricas de lectura/escritura
# --------------------------------------------------------------------------

def obtener_proyecto(con: sqlite3.Connection) -> dict:
    return con.execute("SELECT * FROM proyecto WHERE id = 1").fetchone() or {}


def guardar_proyecto(con: sqlite3.Connection, datos: dict) -> None:
    """Actualiza solo las columnas que existen en la tabla."""
    columnas = {c["name"] for c in con.execute("PRAGMA table_info(proyecto)")}
    campos = {k: v for k, v in datos.items() if k in columnas and k != "id"}
    if not campos:
        return
    asignaciones = ", ".join(f"{k} = ?" for k in campos)
    con.execute(f"UPDATE proyecto SET {asignaciones} WHERE id = 1", tuple(campos.values()))


def listar(con: sqlite3.Connection, tabla: str, orden: str = "orden, id",
           donde: str = "", parametros: Iterable[Any] = ()) -> list[dict]:
    sql = f"SELECT * FROM {tabla}"
    if donde:
        sql += f" WHERE {donde}"
    sql += f" ORDER BY {orden}"
    return con.execute(sql, tuple(parametros)).fetchall()


def insertar(con: sqlite3.Connection, tabla: str, datos: dict) -> int:
    columnas = {c["name"] for c in con.execute(f"PRAGMA table_info({tabla})")}
    campos = {k: v for k, v in datos.items() if k in columnas and k != "id"}
    if not campos:
        raise ValueError(f"No hay campos válidos para insertar en {tabla}")
    marcas = ", ".join("?" for _ in campos)
    cur = con.execute(
        f"INSERT INTO {tabla} ({', '.join(campos)}) VALUES ({marcas})",
        tuple(campos.values()),
    )
    return cur.lastrowid


def actualizar(con: sqlite3.Connection, tabla: str, id_: int, datos: dict) -> None:
    columnas = {c["name"] for c in con.execute(f"PRAGMA table_info({tabla})")}
    campos = {k: v for k, v in datos.items() if k in columnas and k != "id"}
    if not campos:
        return
    asignaciones = ", ".join(f"{k} = ?" for k in campos)
    con.execute(f"UPDATE {tabla} SET {asignaciones} WHERE id = ?",
                (*campos.values(), id_))


def eliminar(con: sqlite3.Connection, tabla: str, id_: int) -> None:
    con.execute(f"DELETE FROM {tabla} WHERE id = ?", (id_,))


def reemplazar_tabla(con: sqlite3.Connection, tabla: str, filas: list[dict],
                     donde: str = "", parametros: Iterable[Any] = ()) -> None:
    """Borra el contenido (opcionalmente filtrado) y reinserta. Útil para editores de tabla."""
    sql = f"DELETE FROM {tabla}"
    if donde:
        sql += f" WHERE {donde}"
    con.execute(sql, tuple(parametros))
    for i, fila in enumerate(filas):
        fila = dict(fila)
        fila.setdefault("orden", i)
        insertar(con, tabla, fila)
