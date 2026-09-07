"""
Sistema de Anexos de Vinculación — interfaz de captura y generación.

Se ejecuta con:      streamlit run app.py

La idea de fondo: los datos se escriben UNA vez (el nombre de un estudiante, la
fecha de inicio, el plan de aprendizaje) y de ahí salen todos los anexos que
los necesiten. Los documentos se generan sobre las plantillas oficiales, así
que el formato es el mismo que aprueba la Coordinación.
"""

from __future__ import annotations

import io
import re
import shutil
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from core import db, generador, logos as mod_logos

RAIZ = Path(__file__).resolve().parent
DIR_LOGOS = RAIZ / "recursos" / "logos"
DIR_SALIDA = RAIZ / "salida"

st.set_page_config(page_title="Anexos de Vinculación", page_icon="📄", layout="wide")

# Streamlit cambió `use_container_width=True` por `width="stretch"` en la 1.49.
# Se elige el argumento según la versión instalada para que la app funcione
# igual en equipos con Streamlit viejo y con el actual.
def _ancho_completo() -> dict:
    try:
        mayor, menor = (int(x) for x in st.__version__.split(".")[:2])
    except Exception:
        return {"use_container_width": True}
    return {"width": "stretch"} if (mayor, menor) >= (1, 49) else {"use_container_width": True}


ANCHO = _ancho_completo()
# Los botones aceptan el mismo argumento de ancho que las tablas.
ANCHO_BOTON = ANCHO


# --------------------------------------------------------------------------
# Utilidades de interfaz
# --------------------------------------------------------------------------

@st.cache_resource
def _arrancar():
    db.inicializar()
    DIR_LOGOS.mkdir(parents=True, exist_ok=True)
    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    return True


def leer(tabla: str, orden: str = "orden, id", donde: str = "", parametros=()) -> pd.DataFrame:
    with db.conexion() as con:
        filas = db.listar(con, tabla, orden=orden, donde=donde, parametros=parametros)
    return pd.DataFrame(filas)


def guardar_tabla(tabla: str, df: pd.DataFrame, columnas: list[str],
                  donde: str = "", parametros=()) -> None:
    """Vuelca un data_editor a la base, descartando filas totalmente vacías."""
    filas = []
    for _, fila in df.iterrows():
        datos = {c: (fila[c] if c in fila and pd.notna(fila[c]) else "") for c in columnas}
        if not any(str(v).strip() for v in datos.values()):
            continue
        if "id" in fila and pd.notna(fila["id"]):
            datos["id"] = int(fila["id"])
        filas.append(datos)
    with db.conexion() as con:
        db.reemplazar_tabla(con, tabla, [{k: v for k, v in f.items() if k != "id"}
                                         for f in filas], donde, parametros)


def editor(df: pd.DataFrame, columnas: list[str], clave: str,
           config: dict | None = None) -> pd.DataFrame:
    """data_editor con las columnas esperadas aunque la tabla venga vacía."""
    if df.empty:
        df = pd.DataFrame(columns=columnas)
    faltantes = [c for c in columnas if c not in df.columns]
    for c in faltantes:
        df[c] = ""
    return st.data_editor(df[columnas], num_rows="dynamic", **ANCHO,
                          key=clave, column_config=config or {})


def aviso_guardado():
    st.toast("Guardado", icon="✅")


_arrancar()


# --------------------------------------------------------------------------
# Página: Proyecto
# --------------------------------------------------------------------------

def pagina_proyecto():
    st.header("Datos del proyecto")
    with db.conexion() as con:
        p = db.obtener_proyecto(con)

    with st.form("form_proyecto"):
        st.subheader("Proyecto")
        c1, c2 = st.columns([3, 1])
        nombre = c1.text_area("Nombre del proyecto", p.get("nombre", ""), height=100,
                              help="Se escribe SIN comillas; la plantilla las pone.")
        fase = c2.text_input("Fase", p.get("fase", ""))
        nombre_corto = c2.text_input("Nombre corto", p.get("nombre_corto", ""))
        codigo = c2.text_input("Código de convocatoria", p.get("codigo_convocatoria", ""))

        st.subheader("Carrera")
        c1, c2, c3 = st.columns(3)
        carrera = c1.text_input("Carrera", p.get("carrera", ""))
        carrera_corta = c2.text_input("Siglas", p.get("carrera_corta", ""))
        periodo = c3.text_input("Periodo académico", p.get("periodo_academico", ""))
        c1, c2, c3, c4 = st.columns(4)
        paralelo = c1.text_input("Paralelo", p.get("paralelo", ""))
        jornada = c2.text_input("Jornada", p.get("jornada", ""))
        ciclo = c3.text_input("Ciclo", p.get("ciclo", ""))
        ciclo_min = c4.text_input("Ciclo mínimo (convocatoria)", p.get("ciclo_minimo", ""))

        st.subheader("Entidad beneficiaria")
        c1, c2 = st.columns(2)
        entidad = c1.text_input("Nombre", p.get("entidad", ""))
        entidad_corta = c2.text_input("Nombre corto / lugar", p.get("entidad_corta", ""))
        direccion = c1.text_input("Dirección", p.get("entidad_direccion", ""))
        telefono = c2.text_input("Teléfono", p.get("entidad_telefono", ""))
        email = c1.text_input("Correo", p.get("entidad_email", ""))
        ciudad = c2.text_input("Ciudad", p.get("ciudad", ""))
        descripcion = st.text_area("Descripción de la institución (Anexo 10)",
                                   p.get("entidad_descripcion", ""), height=90)

        st.subheader("Carga horaria y fechas")
        c1, c2, c3, c4 = st.columns(4)
        horas = c1.number_input("Total de horas", value=int(p.get("total_horas") or 100), step=10)
        f_inicio = c2.text_input("Fecha de inicio", p.get("fecha_inicio", ""),
                                 help="Formato AAAA-MM-DD")
        f_fin = c3.text_input("Fecha de finalización", p.get("fecha_fin", ""))
        f_eval = c4.text_input("Fecha de evaluación", p.get("fecha_evaluacion", ""))

        if st.form_submit_button("Guardar", type="primary"):
            with db.conexion() as con:
                db.guardar_proyecto(con, {
                    "nombre": nombre.strip(), "nombre_corto": nombre_corto, "fase": fase,
                    "codigo_convocatoria": codigo, "carrera": carrera,
                    "carrera_corta": carrera_corta, "periodo_academico": periodo,
                    "paralelo": paralelo, "jornada": jornada, "ciclo": ciclo,
                    "ciclo_minimo": ciclo_min, "entidad": entidad,
                    "entidad_corta": entidad_corta, "entidad_direccion": direccion,
                    "entidad_telefono": telefono, "entidad_email": email,
                    "entidad_descripcion": descripcion, "ciudad": ciudad,
                    "total_horas": int(horas), "fecha_inicio": f_inicio,
                    "fecha_fin": f_fin, "fecha_evaluacion": f_eval,
                })
            aviso_guardado()
            st.rerun()

    st.divider()
    st.subheader("Fechas de cada anexo")
    st.caption("Cada oficio lleva su propia fecha. Formato AAAA-MM-DD.")
    ETIQUETAS = {
        "anexo1": "Anexo 1 · Delegación de docentes",
        "anexo2": "Anexo 2 · Convocatoria",
        "anexo2_limite": "Anexo 2 · Fecha límite de solicitudes",
        "anexo3": "Anexo 3 · Solicitud del estudiante",
        "anexo4": "Anexo 4 · Respuesta al estudiante",
        "anexo5": "Anexo 5 · Delegación de estudiantes",
        "anexo6": "Anexo 6 · Plan de aprendizaje",
        "anexo6_1": "Anexo 6.1 · Seguimiento parcial",
        "anexo6_2": "Anexo 6.2 · Seguimiento final",
        "seleccion": "S/N · Informe de proceso de selección",
        "socializacion": "S/N · Socialización (elaborado)",
        "socializacion_aprobacion": "S/N · Socialización (aprobado)",
        "constancia": "S/N · Constancia de anexos",
    }
    with db.conexion() as con:
        actuales = {f["clave"]: f["valor"] for f in db.listar(con, "fechas", orden="clave")}

    with st.form("form_fechas"):
        valores = {}
        columnas = st.columns(3)
        for i, (clave, etiqueta) in enumerate(ETIQUETAS.items()):
            valores[clave] = columnas[i % 3].text_input(etiqueta, actuales.get(clave, ""))
        if st.form_submit_button("Guardar fechas", type="primary"):
            with db.conexion() as con:
                for clave, valor in valores.items():
                    con.execute("INSERT OR REPLACE INTO fechas (clave, valor) VALUES (?, ?)",
                                (clave, valor.strip()))
            aviso_guardado()


# --------------------------------------------------------------------------
# Página: Personas
# --------------------------------------------------------------------------

ROLES = {
    "director_proyecto": "Director del proyecto",
    "docente_apoyo": "Docentes de apoyo",
    "responsable_vinculacion": "Responsable de vinculación de la carrera",
    "coordinador_carrera": "Coordinador/a de la carrera",
    "coordinador_vinculacion": "Coordinador/a de vinculación",
    "representante_legal": "Representante legal de la entidad beneficiaria",
}

COLS_PERSONA = ["rol", "titulo", "tratamiento", "nombre", "cedula", "cargo",
                "email", "telefono", "horas", "orden"]


def pagina_personas():
    st.header("Personas del proyecto")
    st.caption("El **título** es cómo se firma (Ing., Mgtr.). El **tratamiento** es "
               "el encabezado del oficio (Ingeniero, Magíster).")

    df = leer("personas", orden="rol, orden, id")
    if df.empty:
        df = pd.DataFrame(columns=COLS_PERSONA)

    editado = st.data_editor(
        df[COLS_PERSONA] if not df.empty else df,
        num_rows="dynamic", **ANCHO, key="ed_personas",
        column_config={
            "rol": st.column_config.SelectboxColumn("Rol", options=list(ROLES), width="medium"),
            "titulo": st.column_config.TextColumn("Título", width="small"),
            "tratamiento": st.column_config.TextColumn("Tratamiento", width="small"),
            "nombre": st.column_config.TextColumn("Nombre completo", width="large"),
            "cedula": st.column_config.TextColumn("Cédula", width="small"),
            "cargo": st.column_config.TextColumn("Cargo (como sale en el oficio)", width="large"),
            "horas": st.column_config.TextColumn(
                "Horas de vinculación", width="medium",
                help="Como sale en los informes ISTA: 2h/semana por 3 meses = 24h"),
            "orden": st.column_config.NumberColumn("Orden", width="small"),
        },
    )
    if st.button("Guardar personas", type="primary"):
        guardar_tabla("personas", editado, COLS_PERSONA)
        aviso_guardado()
        st.rerun()

    with st.expander("¿Para qué sirve cada rol?"):
        for clave, nombre in ROLES.items():
            st.markdown(f"- **{nombre}** (`{clave}`)")


# --------------------------------------------------------------------------
# Página: Estudiantes
# --------------------------------------------------------------------------

COLS_EST = ["cedula", "nombres", "apellidos", "email", "telefono",
            "ciclo", "paralelo", "jornada", "codigo", "horas", "sexo",
            "docente_apoyo_id", "activo", "orden"]


def pagina_estudiantes():
    st.header("Estudiantes")

    docentes = leer("personas", donde="rol = 'docente_apoyo'")
    opciones = {int(r["id"]): r["nombre"] for _, r in docentes.iterrows()} if not docentes.empty else {}

    tab_lista, tab_carga = st.tabs(["Lista", "Cargar desde Excel"])

    with tab_lista:
        df = leer("estudiantes")
        editado = editor(df, COLS_EST, "ed_estudiantes", config={
            "cedula": st.column_config.TextColumn("Cédula", width="small"),
            "codigo": st.column_config.TextColumn("Código", width="small",
                                                  help="Código de estudiante (informe final ISTA)"),
            "horas": st.column_config.TextColumn("Horas", width="small"),
            "sexo": st.column_config.SelectboxColumn("Sexo", options=["M", "F"], width="small",
                                                     help="Define si el oficio dice Señor o Señorita"),
            "docente_apoyo_id": st.column_config.SelectboxColumn(
                "Docente de apoyo", options=list(opciones), format_func=lambda x: opciones.get(x, "—")),
            "activo": st.column_config.CheckboxColumn("Activo", width="small"),
        })
        if st.button("Guardar estudiantes", type="primary"):
            filas = []
            for _, fila in editado.iterrows():
                if not str(fila.get("cedula") or "").strip():
                    continue
                datos = {c: (fila[c] if pd.notna(fila.get(c)) else "") for c in COLS_EST}
                datos["nombre_completo"] = f"{datos['nombres']} {datos['apellidos']}".strip()
                datos["activo"] = 1 if datos["activo"] in (True, 1, "1", "True") else 0
                datos["docente_apoyo_id"] = (int(datos["docente_apoyo_id"])
                                             if str(datos["docente_apoyo_id"]).strip().isdigit()
                                             else None)
                filas.append(datos)
            with db.conexion() as con:
                con.execute("DELETE FROM estudiantes")
                for i, f in enumerate(filas):
                    f["orden"] = i
                    db.insertar(con, "estudiantes", f)
            aviso_guardado()
            st.rerun()

    with tab_carga:
        st.caption("Sube el Excel con la lista de estudiantes. Después indicas qué "
                   "columna corresponde a cada dato: no hace falta que el archivo "
                   "tenga un formato fijo.")
        archivo = st.file_uploader("Archivo .xlsx o .csv", type=["xlsx", "xls", "csv"])
        if archivo:
            try:
                if archivo.name.lower().endswith(".csv"):
                    entrada = pd.read_csv(archivo, dtype=str)
                else:
                    hojas = pd.read_excel(archivo, sheet_name=None, dtype=str)
                    hoja = st.selectbox("Hoja", list(hojas))
                    entrada = hojas[hoja]
            except Exception as e:
                st.error(f"No se pudo leer el archivo: {e}")
                return

            entrada = entrada.fillna("")
            st.dataframe(entrada.head(10), **ANCHO)

            columnas = ["— ninguna —"] + list(entrada.columns)
            st.subheader("Correspondencia de columnas")
            c1, c2, c3 = st.columns(3)
            mapa = {
                "cedula": c1.selectbox("Cédula", columnas, key="m_cedula"),
                "nombres": c2.selectbox("Nombres", columnas, key="m_nombres"),
                "apellidos": c3.selectbox("Apellidos", columnas, key="m_apellidos"),
                "email": c1.selectbox("Correo", columnas, key="m_email"),
                "telefono": c2.selectbox("Teléfono", columnas, key="m_tel"),
                "ciclo": c3.selectbox("Ciclo", columnas, key="m_ciclo"),
            }
            reemplazar = st.checkbox("Reemplazar la lista actual", value=False)

            if st.button("Importar", type="primary"):
                with db.conexion() as con:
                    proyecto = db.obtener_proyecto(con)
                    if reemplazar:
                        con.execute("DELETE FROM estudiantes")
                    existentes = {e["cedula"] for e in db.listar(con, "estudiantes")}
                    nuevos = actualizados = 0
                    for i, fila in entrada.iterrows():
                        def valor(campo):
                            col = mapa[campo]
                            return str(fila[col]).strip() if col != "— ninguna —" else ""

                        cedula = valor("cedula")
                        if not cedula:
                            continue
                        datos = {
                            "cedula": cedula,
                            "nombres": valor("nombres"),
                            "apellidos": valor("apellidos"),
                            "nombre_completo": f"{valor('nombres')} {valor('apellidos')}".strip(),
                            "email": valor("email"),
                            "telefono": valor("telefono"),
                            "ciclo": valor("ciclo") or proyecto.get("ciclo", ""),
                            "paralelo": proyecto.get("paralelo", ""),
                            "jornada": proyecto.get("jornada", ""),
                            "orden": int(i),
                        }
                        if cedula in existentes:
                            fila_db = con.execute(
                                "SELECT id FROM estudiantes WHERE cedula = ?", (cedula,)).fetchone()
                            db.actualizar(con, "estudiantes", fila_db["id"], datos)
                            actualizados += 1
                        else:
                            db.insertar(con, "estudiantes", datos)
                            nuevos += 1
                st.success(f"{nuevos} estudiantes nuevos, {actualizados} actualizados. "
                           "Revisa la pestaña Lista para asignar el docente de apoyo.")


# --------------------------------------------------------------------------
# Página: Plan de aprendizaje
# --------------------------------------------------------------------------

COLS_ACT = ["nro", "descripcion", "descripcion_docente", "asignatura",
            "resultados_aprendizaje", "producto", "horas", "horas_docente",
            "detalle_especifico"]


def pagina_plan():
    st.header("Plan de aprendizaje")
    st.caption("Es la columna vertebral del expediente: de estas actividades salen "
               "los anexos 2, 6, 6.1, 6.2, 7, 9 y 10.")

    df = leer("actividades", orden="nro, id")
    editado = editor(df, COLS_ACT, "ed_actividades", config={
        "nro": st.column_config.NumberColumn("N.º", width="small"),
        "descripcion": st.column_config.TextColumn("Actividad (estudiantes)", width="large"),
        "descripcion_docente": st.column_config.TextColumn("Actividad (docentes)", width="large"),
        "asignatura": st.column_config.TextColumn("Asignatura base"),
        "resultados_aprendizaje": st.column_config.TextColumn("Resultados de aprendizaje", width="large"),
        "producto": st.column_config.TextColumn("Producto / resultado"),
        "horas": st.column_config.NumberColumn("Horas est.", width="small"),
        "horas_docente": st.column_config.NumberColumn("Horas doc.", width="small"),
        "detalle_especifico": st.column_config.TextColumn("Detalle (Anexo 10)", width="large"),
    })

    total = pd.to_numeric(editado["horas"], errors="coerce").fillna(0).sum()
    with db.conexion() as con:
        objetivo = db.obtener_proyecto(con).get("total_horas") or 0
    if total and objetivo and int(total) != int(objetivo):
        st.warning(f"Las horas de las actividades suman **{int(total)}** y el proyecto "
                   f"declara **{int(objetivo)}**. Revisa antes de generar.")
    else:
        st.info(f"Total de horas de las actividades: **{int(total)}**")

    if st.button("Guardar plan", type="primary"):
        guardar_tabla("actividades", editado, COLS_ACT)
        aviso_guardado()
        st.rerun()

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Asignaturas requisito (Anexo 2)")
        req = editor(leer("requisitos"), ["nombre", "orden"], "ed_requisitos")
        if st.button("Guardar requisitos"):
            guardar_tabla("requisitos", req, ["nombre", "orden"])
            aviso_guardado()
    with c2:
        st.subheader("Cronograma de selección (Anexo 2)")
        cro = editor(leer("cronograma"), ["actividad", "fecha", "orden"], "ed_cronograma")
        if st.button("Guardar cronograma"):
            guardar_tabla("cronograma", cro, ["actividad", "fecha", "orden"])
            aviso_guardado()


# --------------------------------------------------------------------------
# Página: Registro diario
# --------------------------------------------------------------------------

COLS_REG = ["fecha", "descripcion", "lugar", "horas", "estudiante_id", "orden"]


def pagina_registro():
    st.header("Registro diario de actividades (Anexo 8)")
    st.caption("Las filas sin estudiante asignado se incluyen en el registro de "
               "todos. Asigna un estudiante solo cuando la actividad sea suya.")

    estudiantes = leer("estudiantes", donde="activo = 1")
    opciones = ({int(r["id"]): r["nombre_completo"] for _, r in estudiantes.iterrows()}
                if not estudiantes.empty else {})

    df = leer("registro_diario")
    editado = editor(df, COLS_REG, "ed_registro", config={
        "fecha": st.column_config.TextColumn("Fecha", width="small", help="AAAA-MM-DD"),
        "descripcion": st.column_config.TextColumn("Descripción de la actividad", width="large"),
        "horas": st.column_config.NumberColumn("Horas", width="small"),
        "estudiante_id": st.column_config.SelectboxColumn(
            "Solo para", options=list(opciones), format_func=lambda x: opciones.get(x, "Todos")),
    })

    total = pd.to_numeric(editado["horas"], errors="coerce").fillna(0).sum()
    st.info(f"Horas registradas: **{int(total)}**")

    if st.button("Guardar registro", type="primary"):
        filas = []
        for i, (_, fila) in enumerate(editado.iterrows()):
            if not str(fila.get("descripcion") or "").strip():
                continue
            eid = fila.get("estudiante_id")
            filas.append({
                "fecha": fila.get("fecha") or "", "descripcion": fila["descripcion"],
                "lugar": fila.get("lugar") or "",
                "horas": float(fila.get("horas") or 0),
                "estudiante_id": int(eid) if str(eid).strip().isdigit() else None,
                "orden": i,
            })
        with db.conexion() as con:
            db.reemplazar_tabla(con, "registro_diario", filas)
        aviso_guardado()
        st.rerun()


# --------------------------------------------------------------------------
# Página: Meses (anexos 7 y 9)
# --------------------------------------------------------------------------

COLS_MES = ["nro", "etiqueta", "fecha_planificacion", "fecha_seguimiento",
            "fecha_socializacion", "observaciones"]


def pagina_meses():
    st.header("Meses, planificación y seguimiento")

    st.subheader("Meses del proyecto")
    meses = editor(leer("meses", orden="nro, id"), COLS_MES, "ed_meses", config={
        "nro": st.column_config.NumberColumn("N.º", width="small"),
        "etiqueta": st.column_config.TextColumn("Mes", help="Como sale en el anexo: Septiembre 2025"),
        "fecha_planificacion": st.column_config.TextColumn("Fecha planificación (Anexo 7)"),
        "fecha_seguimiento": st.column_config.TextColumn("Fecha seguimiento (Anexo 9)"),
        "fecha_socializacion": st.column_config.TextColumn("Fecha socialización"),
    })
    if st.button("Guardar meses", type="primary"):
        guardar_tabla("meses", meses, COLS_MES)
        aviso_guardado()
        st.rerun()

    df_meses = leer("meses", orden="nro, id")
    if df_meses.empty:
        st.info("Registra al menos un mes para planificar.")
        return

    st.divider()
    etiquetas = {int(r["id"]): r["etiqueta"] for _, r in df_meses.iterrows()}
    mes_id = st.selectbox("Mes a editar", list(etiquetas),
                          format_func=lambda x: etiquetas[x])

    actividades = leer("actividades", orden="nro, id")
    act_op = ({int(r["id"]): f"{r['nro']}. {r['descripcion'][:60]}"
               for _, r in actividades.iterrows()} if not actividades.empty else {})
    docentes = leer("personas", donde="rol = 'docente_apoyo'")
    estudiantes = leer("estudiantes", donde="activo = 1")
    doc_op = ({int(r["id"]): r["nombre"] for _, r in docentes.iterrows()}
              if not docentes.empty else {})
    est_op = ({int(r["id"]): r["nombre_completo"] for _, r in estudiantes.iterrows()}
              if not estudiantes.empty else {})

    COLS_PLAN = ["persona_id", "actividad_id", "resultado", "horas",
                 "fecha_inicio", "fecha_fin", "observaciones", "orden"]

    tab_doc, tab_est, tab_seg = st.tabs(
        ["Anexo 7 · horas docentes", "Anexo 7 · horas estudiantes", "Anexo 9 · seguimiento"])

    with tab_doc:
        df = leer("planificacion", donde="mes_id = ? AND tipo = 'docente'", parametros=(mes_id,))
        ed = editor(df, COLS_PLAN, f"ed_plan_doc_{mes_id}", config={
            "persona_id": st.column_config.SelectboxColumn(
                "Docente", options=list(doc_op), format_func=lambda x: doc_op.get(x, "—")),
            "actividad_id": st.column_config.SelectboxColumn(
                "Actividad", options=list(act_op), format_func=lambda x: act_op.get(x, "—"),
                width="large"),
            "resultado": st.column_config.TextColumn("Resultado", width="large",
                                                     help="Si se deja vacío se usa el producto de la actividad"),
        })
        if st.button("Guardar horas docentes", key="b_plan_doc"):
            _guardar_planificacion(mes_id, "docente", ed, COLS_PLAN)

    with tab_est:
        df = leer("planificacion", donde="mes_id = ? AND tipo = 'estudiante'", parametros=(mes_id,))
        ed = editor(df, COLS_PLAN, f"ed_plan_est_{mes_id}", config={
            "persona_id": st.column_config.SelectboxColumn(
                "Estudiante", options=list(est_op), format_func=lambda x: est_op.get(x, "—")),
            "actividad_id": st.column_config.SelectboxColumn(
                "Actividad", options=list(act_op), format_func=lambda x: act_op.get(x, "—"),
                width="large"),
        })
        if st.button("Guardar horas estudiantes", key="b_plan_est"):
            _guardar_planificacion(mes_id, "estudiante", ed, COLS_PLAN)

    with tab_seg:
        COLS_SEG = ["estudiante_id", "actividad_id", "descripcion", "fecha_planificada",
                    "finalizada", "fecha_fin_prevista", "avance", "orden"]
        df = leer("seguimiento", donde="mes_id = ?", parametros=(mes_id,))
        ed = editor(df, COLS_SEG, f"ed_seg_{mes_id}", config={
            "estudiante_id": st.column_config.SelectboxColumn(
                "Estudiante", options=list(est_op), format_func=lambda x: est_op.get(x, "—")),
            "actividad_id": st.column_config.SelectboxColumn(
                "Actividad base", options=list(act_op), format_func=lambda x: act_op.get(x, "—")),
            "descripcion": st.column_config.TextColumn("Actividades según planificación", width="large"),
            "finalizada": st.column_config.SelectboxColumn("Finalizada", options=["SI", "NO"], width="small"),
            "avance": st.column_config.TextColumn("Avance", width="small"),
        })
        if st.button("Guardar seguimiento", key="b_seg"):
            filas = []
            for i, (_, fila) in enumerate(ed.iterrows()):
                eid = fila.get("estudiante_id")
                if not str(eid).strip().isdigit():
                    continue
                filas.append({
                    "mes_id": mes_id, "estudiante_id": int(eid),
                    "actividad_id": (int(fila["actividad_id"])
                                     if str(fila.get("actividad_id")).strip().isdigit() else None),
                    "descripcion": fila.get("descripcion") or "",
                    "fecha_planificada": fila.get("fecha_planificada") or "",
                    "finalizada": fila.get("finalizada") or "SI",
                    "fecha_fin_prevista": fila.get("fecha_fin_prevista") or "",
                    "avance": fila.get("avance") or "100%", "orden": i,
                })
            with db.conexion() as con:
                db.reemplazar_tabla(con, "seguimiento", filas, "mes_id = ?", (mes_id,))
            aviso_guardado()
            st.rerun()


def _guardar_planificacion(mes_id: int, tipo: str, ed: pd.DataFrame, columnas: list[str]):
    filas = []
    for i, (_, fila) in enumerate(ed.iterrows()):
        pid = fila.get("persona_id")
        if not str(pid).strip().isdigit():
            continue
        filas.append({
            "mes_id": mes_id, "tipo": tipo, "persona_id": int(pid),
            "actividad_id": (int(fila["actividad_id"])
                             if str(fila.get("actividad_id")).strip().isdigit() else None),
            "resultado": fila.get("resultado") or "",
            "horas": float(fila.get("horas") or 0),
            "fecha_inicio": fila.get("fecha_inicio") or "",
            "fecha_fin": fila.get("fecha_fin") or "",
            "observaciones": fila.get("observaciones") or "", "orden": i,
        })
    with db.conexion() as con:
        db.reemplazar_tabla(con, "planificacion", filas,
                            "mes_id = ? AND tipo = ?", (mes_id, tipo))
    aviso_guardado()
    st.rerun()


# --------------------------------------------------------------------------
# Página: Evaluaciones
# --------------------------------------------------------------------------

ITEMS_11 = {
    "1.1": "Control de avance de actividades",
    "1.2": "Resultados alcanzados",
    "1.3": "Demuestra conocimientos en el área",
    "1.4": "Aplicación y manejo de destrezas",
    "2.1": "Adaptabilidad e integración",
    "2.2": "Liderazgo y trabajo en equipo",
    "2.3": "Asiste puntualmente",
    "2.4": "Trabajo en equipo / presión",
}


def pagina_evaluaciones():
    st.header("Evaluaciones")
    estudiantes = leer("estudiantes", donde="activo = 1")
    if estudiantes.empty:
        st.info("Registra estudiantes primero.")
        return
    opciones = {int(r["id"]): r["nombre_completo"] for _, r in estudiantes.iterrows()}
    est_id = st.selectbox("Estudiante", list(opciones), format_func=lambda x: opciones[x])

    actividades = leer("actividades", orden="nro, id")
    if actividades.empty:
        st.info("Registra el plan de aprendizaje primero.")
        return

    tab_plan, tab_rubrica = st.tabs(["Anexos 6.1 y 6.2 · plan", "Anexo 11 · rúbrica"])

    with tab_plan:
        corte = st.radio("Corte", ["parcial", "final"], horizontal=True,
                         format_func=lambda c: "Parcial (6.1)" if c == "parcial" else "Final (6.2)")
        actual = leer("evaluacion_plan", orden="id",
                      donde="estudiante_id = ? AND corte = ?", parametros=(est_id, corte))
        por_act = ({int(r["actividad_id"]): r for _, r in actual.iterrows()}
                   if not actual.empty else {})

        filas = []
        for _, act in actividades.iterrows():
            ev = por_act.get(int(act["id"]), {})
            filas.append({
                "actividad_id": int(act["id"]),
                "N.º": act["nro"],
                "Actividad": act["descripcion"],
                "Avance": ev.get("avance", "0%"),
                "Valoración": ev.get("valoracion", ""),
                "Logró el resultado": ev.get("logro", ""),
            })
        ed = st.data_editor(
            pd.DataFrame(filas), **ANCHO, hide_index=True,
            key=f"ed_plan_{est_id}_{corte}",
            disabled=["actividad_id", "N.º", "Actividad"],
            column_config={
                "actividad_id": None,
                "N.º": st.column_config.NumberColumn(width="small"),
                "Actividad": st.column_config.TextColumn(width="large"),
                "Avance": st.column_config.TextColumn(width="small"),
                "Valoración": st.column_config.SelectboxColumn(
                    options=["", "poco", "satisfactorio", "muy"], width="medium"),
                "Logró el resultado": st.column_config.SelectboxColumn(
                    options=["", "si", "no"], width="small"),
            })
        if st.button("Guardar evaluación del plan", type="primary"):
            with db.conexion() as con:
                con.execute("DELETE FROM evaluacion_plan WHERE estudiante_id = ? AND corte = ?",
                            (est_id, corte))
                for _, fila in ed.iterrows():
                    db.insertar(con, "evaluacion_plan", {
                        "estudiante_id": est_id, "actividad_id": int(fila["actividad_id"]),
                        "corte": corte, "avance": fila["Avance"] or "0%",
                        "valoracion": fila["Valoración"] or "",
                        "logro": fila["Logró el resultado"] or ""})
            aviso_guardado()
            st.rerun()

    with tab_rubrica:
        st.caption("Puntaje de 1 a 5 por ítem. El sistema calcula el total y el promedio.")
        actual = leer("evaluacion_estudiante", orden="id",
                      donde="estudiante_id = ?", parametros=(est_id,))
        puntajes = ({r["item"]: int(r["puntaje"]) for _, r in actual.iterrows()}
                    if not actual.empty else {})
        nuevos = {}
        c1, c2 = st.columns(2)
        for item, texto in ITEMS_11.items():
            col = c1 if item.startswith("1") else c2
            nuevos[item] = col.slider(f"{item} · {texto}", 1, 5,
                                      puntajes.get(item, 5), key=f"sl_{est_id}_{item}")
        b1 = sum(nuevos[i] for i in ("1.1", "1.2", "1.3", "1.4"))
        b2 = sum(nuevos[i] for i in ("2.1", "2.2", "2.3", "2.4"))
        st.metric("Puntaje", f"{b1}/20 · {b2}/20 → promedio {round((b1 + b2) / 2)}/20")
        if st.button("Guardar rúbrica", type="primary"):
            with db.conexion() as con:
                con.execute("DELETE FROM evaluacion_estudiante WHERE estudiante_id = ?", (est_id,))
                for item, puntaje in nuevos.items():
                    db.insertar(con, "evaluacion_estudiante", {
                        "estudiante_id": est_id,
                        "evaluador": "docente_apoyo" if item.startswith("1") else "director",
                        "item": item, "puntaje": int(puntaje)})
            aviso_guardado()


# --------------------------------------------------------------------------
# Página: Jornadas y visitas
# --------------------------------------------------------------------------

def pagina_jornadas():
    st.header("Jornadas de capacitación y visitas")

    st.subheader("Jornadas (Anexo 12)")
    cols = ["nro", "asunto", "fecha", "horas", "lugar"]
    ed = editor(leer("jornadas", orden="nro, id"), cols, "ed_jornadas", config={
        "nro": st.column_config.NumberColumn("N.º", width="small"),
        "asunto": st.column_config.TextColumn("Asunto", width="large"),
        "fecha": st.column_config.TextColumn("Fecha", width="small"),
        "horas": st.column_config.TextColumn("Horas", width="small"),
    })
    if st.button("Guardar jornadas", type="primary"):
        with db.conexion() as con:
            filas = [{c: (fila[c] if pd.notna(fila[c]) else "") for c in cols}
                     for _, fila in ed.iterrows() if str(fila.get("asunto") or "").strip()]
            con.execute("DELETE FROM jornadas")
            for f in filas:
                f["nro"] = int(f["nro"] or 0)
                db.insertar(con, "jornadas", f)
        aviso_guardado()
        st.rerun()

    st.divider()
    st.subheader("Visitas a la institución (Anexo 13)")
    cols_v = ["fecha", "hora_inicio", "hora_fin", "asunto", "actividades",
              "observaciones", "orden"]
    ed_v = editor(leer("visitas"), cols_v, "ed_visitas", config={
        "fecha": st.column_config.TextColumn("Fecha", width="small"),
        "hora_inicio": st.column_config.TextColumn("Hora inicio", width="small"),
        "hora_fin": st.column_config.TextColumn("Hora fin", width="small"),
        "asunto": st.column_config.TextColumn("Asunto", width="large"),
        "actividades": st.column_config.TextColumn("Actividades", width="large"),
    })
    if st.button("Guardar visitas", type="primary"):
        guardar_tabla("visitas", ed_v, cols_v)
        aviso_guardado()
        st.rerun()


# --------------------------------------------------------------------------
# Página: Informes narrativos (documentos S/N)
# --------------------------------------------------------------------------

BLOQUES_NARRATIVA = {
    "Proceso de selección": [
        ("sel_antecedentes", "Antecedentes", 200),
        ("sel_objetivo", "Objetivo general", 140),
        ("sel_desarrollo", "Desarrollo", 200),
        ("sel_evidencias", "Evidencias (texto; las imágenes se mantienen)", 120),
    ],
    "Informes ISTA (seguimiento y final)": [
        ("objetivo_general", "Objetivo general del proyecto", 120),
        ("situacion_inicial", "Situación al inicio de la ejecución", 240),
        ("situacion_beneficiarios", "Situación actual de los beneficiarios", 240),
        ("observaciones_informe", "Observaciones", 120),
        ("impacto_descripcion", "Descripción del impacto generado (informe final)", 200),
    ],
    "Socialización de resultados": [
        ("soc_antecedentes", "Antecedentes", 160),
        ("soc_objetivo", "Objetivo", 120),
        ("soc_desarrollo", "Desarrollo", 200),
        ("soc_conclusiones", "Conclusiones y recomendaciones", 160),
    ],
}

LISTAS_INFORME = {
    "objetivos_especificos": "Objetivos específicos",
    "conclusiones_seguimiento": "Conclusiones · informe de seguimiento",
    "conclusiones_final": "Conclusiones · informe final",
    "recomendaciones": "Recomendaciones · informe final",
    "resultados_indicadores": "Resultados de los indicadores de impacto",
    "productos": "Resultados alcanzados / productos obtenidos",
    "a10_conclusiones": "Conclusiones · Anexo 10 (informe del estudiante)",
    "a10_recomendaciones": "Recomendaciones · Anexo 10 (informe del estudiante)",
}

GRUPOS_CASILLAS = {
    "linea_accion": ("Línea de acción",
                     {"asesoria": "Asesoría Técnica",
                      "comunitario": "Trabajo Comunitario",
                      "capacitacion": "Capacitación"}),
    "alcance": ("Alcance territorial",
                {"nacional": "Nacional", "provincial": "Provincial",
                 "cantonal": "Cantonal", "parroquial": "Parroquial",
                 "institucional": "Institucional", "internacional": "Internacional"}),
    "impacto": ("Impacto generado",
                {"social": "Impacto Social", "cientifico": "Impacto Científico",
                 "economico": "Impacto Económico", "politico": "Impacto Político",
                 "otro": "Otro Impacto"}),
}


def pagina_informes():
    st.header("Informes del proyecto")
    st.caption("Alimentan los cinco documentos sin número de anexo: proceso de "
               "selección, seguimiento ISTA, informe final ISTA, socialización "
               "y constancia.")

    tabs = st.tabs(["Datos y casillas", "Redacción", "Listas",
                    "Actividades de los informes", "Indicadores", "Constancia"])

    # ---------------- Datos generales y casillas ---------------------------
    with tabs[0]:
        with db.conexion() as con:
            p = db.obtener_proyecto(con)
            opciones = {o["clave"]: o["valor"] for o in db.listar(con, "opciones", orden="clave")}

        with st.form("form_informes_datos"):
            c1, c2 = st.columns(2)
            programa = c1.text_area("Programa de Vinculación",
                                    p.get("programa_vinculacion", ""), height=80)
            dir_carrera = c2.text_input("Director/a de carrera", p.get("director_carrera", ""))
            plazo = c2.text_input("Plazo de ejecución", p.get("plazo_ejecucion", ""),
                                  help="Como sale en el formato: 3 Meses")
            c1, c2, c3 = st.columns(3)
            f_seg = c1.text_input("Fecha de seguimiento", p.get("fecha_seguimiento", ""))
            f_ent = c2.text_input("Fecha de entrega", p.get("fecha_entrega", ""))
            enlace = c3.text_input("Enlace a los anexos (informe final)",
                                   p.get("enlace_anexos", ""))

            st.subheader("Casillas de los formatos ISTA")
            elegidas = {}
            columnas = st.columns(3)
            for i, (clave, (titulo, valores)) in enumerate(GRUPOS_CASILLAS.items()):
                actual = opciones.get(clave, "")
                lista = list(valores)
                indice = lista.index(actual) if actual in lista else 0
                elegidas[clave] = columnas[i].radio(
                    titulo, lista, index=indice,
                    format_func=lambda x, v=valores: v[x], key=f"cas_{clave}")

            if st.form_submit_button("Guardar", type="primary"):
                with db.conexion() as con:
                    db.guardar_proyecto(con, {
                        "programa_vinculacion": programa, "director_carrera": dir_carrera,
                        "plazo_ejecucion": plazo, "fecha_seguimiento": f_seg,
                        "fecha_entrega": f_ent, "enlace_anexos": enlace})
                    for clave, valor in elegidas.items():
                        con.execute("INSERT OR REPLACE INTO opciones (clave, valor) VALUES (?, ?)",
                                    (clave, valor))
                aviso_guardado()
                st.rerun()

    # ---------------- Bloques de redacción ---------------------------------
    with tabs[1]:
        st.caption("Cada bloque sale tal cual en su informe. Los saltos de línea "
                   "se respetan. Las imágenes que ya tiene el documento (evidencias, "
                   "cronogramas) no se tocan.")
        with db.conexion() as con:
            actuales = {n["clave"]: n["texto"]
                        for n in db.listar(con, "narrativa", orden="clave")}

        with st.form("form_narrativa"):
            nuevos = {}
            for grupo, campos in BLOQUES_NARRATIVA.items():
                st.subheader(grupo)
                for clave, etiqueta, alto in campos:
                    nuevos[clave] = st.text_area(etiqueta, actuales.get(clave, ""),
                                                 height=alto, key=f"nar_{clave}")
            if st.form_submit_button("Guardar redacción", type="primary"):
                with db.conexion() as con:
                    for clave, texto in nuevos.items():
                        con.execute("INSERT OR REPLACE INTO narrativa (clave, texto) VALUES (?, ?)",
                                    (clave, texto))
                aviso_guardado()

    # ---------------- Listas de viñetas ------------------------------------
    with tabs[2]:
        clave = st.selectbox("Lista", list(LISTAS_INFORME),
                             format_func=lambda x: LISTAS_INFORME[x])
        df = leer("listas", donde="clave = ?", parametros=(clave,))
        ed = editor(df, ["texto", "orden"], f"ed_lista_{clave}", config={
            "texto": st.column_config.TextColumn(LISTAS_INFORME[clave], width="large"),
        })
        if st.button("Guardar lista", type="primary", key=f"b_lista_{clave}"):
            filas = [{"clave": clave, "texto": f["texto"], "orden": i}
                     for i, (_, f) in enumerate(ed.iterrows())
                     if str(f.get("texto") or "").strip()]
            with db.conexion() as con:
                db.reemplazar_tabla(con, "listas", filas, "clave = ?", (clave,))
            aviso_guardado()
            st.rerun()

    # ---------------- Actividades de los informes --------------------------
    with tabs[3]:
        informe = st.radio("Informe", ["seguimiento", "final"], horizontal=True,
                           format_func=lambda x: ("Seguimiento (S/N 2)" if x == "seguimiento"
                                                  else "Final (S/N 3)"))
        cols = ["actividad", "cumplimiento", "fecha", "responsables",
                "evidencia", "observaciones", "orden"]
        df = leer("actividades_informe", donde="informe = ?", parametros=(informe,))
        ed = editor(df, cols, f"ed_actinf_{informe}", config={
            "actividad": st.column_config.TextColumn("Actividad planificada", width="large"),
            "cumplimiento": st.column_config.TextColumn("% cumplimiento", width="small"),
            "fecha": st.column_config.TextColumn("Fecha de ejecución", width="small"),
            "responsables": st.column_config.TextColumn("Responsables", width="medium"),
            "evidencia": st.column_config.TextColumn("Documento de evidencia", width="medium"),
        })
        if st.button("Guardar actividades", type="primary", key=f"b_actinf_{informe}"):
            filas = []
            for i, (_, f) in enumerate(ed.iterrows()):
                if not str(f.get("actividad") or "").strip():
                    continue
                fila = {c: (f[c] if pd.notna(f.get(c)) else "") for c in cols}
                fila.update({"informe": informe, "orden": i})
                filas.append(fila)
            with db.conexion() as con:
                db.reemplazar_tabla(con, "actividades_informe", filas,
                                    "informe = ?", (informe,))
            aviso_guardado()
            st.rerun()

    # ---------------- Indicadores y matriz ---------------------------------
    with tabs[4]:
        st.subheader("Indicadores de impacto")
        ind = editor(leer("indicadores", orden="orden, id"),
                     ["nro", "descripcion", "tipo", "orden"], "ed_indicadores", config={
                         "nro": st.column_config.NumberColumn("N.º", width="small"),
                         "descripcion": st.column_config.TextColumn("Descripción", width="large"),
                         "tipo": st.column_config.SelectboxColumn(
                             "Tipo", options=["Cualitativo", "Cuantitativo"]),
                     })
        if st.button("Guardar indicadores", type="primary"):
            guardar_tabla("indicadores", ind, ["nro", "descripcion", "tipo", "orden"])
            aviso_guardado()
            st.rerun()

        st.divider()
        st.subheader("Matriz de verificación de objetivos")
        cols_m = ["objetivo", "indicador", "planificado", "obtenido",
                  "observaciones", "orden"]
        mat = editor(leer("matriz_objetivos"), cols_m, "ed_matriz", config={
            "objetivo": st.column_config.TextColumn("Objetivo específico", width="large"),
            "planificado": st.column_config.TextColumn("Resultado planificado", width="medium"),
            "obtenido": st.column_config.TextColumn("Resultado obtenido", width="medium"),
        })
        if st.button("Guardar matriz", type="primary"):
            guardar_tabla("matriz_objetivos", mat, cols_m)
            aviso_guardado()
            st.rerun()

    # ---------------- Constancia -------------------------------------------
    with tabs[5]:
        st.caption("Al generar, el sistema marca automáticamente las filas cuyos "
                   "anexos entran en esa generación. Marca aquí las que quieras "
                   "dejar fijas, por ejemplo si entregaste algo fuera del sistema.")
        cols_c = ["numero", "nombre", "presentacion", "anexo", "marcado", "orden"]
        claves = [""] + list(generador.CATALOGO)
        con_ed = editor(leer("constancia"), cols_c, "ed_constancia", config={
            "numero": st.column_config.TextColumn("N.º", width="small"),
            "nombre": st.column_config.TextColumn("Nombre del anexo", width="large"),
            "presentacion": st.column_config.TextColumn("Presentación", width="medium"),
            "anexo": st.column_config.SelectboxColumn(
                "Anexo del sistema", options=claves, width="small",
                help="Con qué documento del sistema se corresponde esta fila"),
            "marcado": st.column_config.CheckboxColumn("Marcado fijo", width="small"),
        })
        if st.button("Guardar constancia", type="primary"):
            filas = []
            for i, (_, f) in enumerate(con_ed.iterrows()):
                if not str(f.get("nombre") or "").strip():
                    continue
                filas.append({
                    "numero": f.get("numero") or "", "nombre": f["nombre"],
                    "presentacion": f.get("presentacion") or "",
                    "anexo": f.get("anexo") or "",
                    "marcado": 1 if f.get("marcado") in (True, 1, "1", "True") else 0,
                    "orden": i})
            with db.conexion() as con:
                db.reemplazar_tabla(con, "constancia", filas)
            aviso_guardado()
            st.rerun()


# --------------------------------------------------------------------------
# Página: Logos
# --------------------------------------------------------------------------

def pagina_logos():
    st.header("Logos del encabezado")
    st.caption("Los anexos llevan dos logos. Ojo con dos detalles: no siempre "
               "van en el mismo orden —en unos el institucional está a la "
               "izquierda y en otros a la derecha—, y el Anexo 5 los lleva en el "
               "cuerpo porque no tiene encabezado. El sistema los identifica por "
               "su papel, no por su posición, así que cada uno cae donde toca.")
    st.info("Si dejas un logo **sin archivo**, cada documento conserva el que "
            "trae su formato oficial. En cuanto subes uno, ese mismo archivo se "
            "usa en los 20 documentos — incluidos los que traían una variante "
            "distinta de la misma marca.")

    with db.conexion() as con:
        registros = {l["clave"]: l for l in db.listar(con, "logos", orden="clave")}

    manifiesto = generador.cargar_manifiesto()
    usos = {}
    for anexo, datos in manifiesto.items():
        for slot in datos.get("logos", []):
            usos.setdefault(slot["logico"], []).append(anexo)

    for clave, registro in registros.items():
        st.divider()
        c1, c2 = st.columns([1, 2])

        with c1:
            actual = DIR_LOGOS / registro["archivo"] if registro["archivo"] else None
            if actual and actual.exists():
                st.image(str(actual), width=220)
                st.caption(f"Archivo actual: `{registro['archivo']}`")
            else:
                st.info("Sin logo propio: se usa el que trae la plantilla oficial.")

        with c2:
            st.markdown(f"### {registro['nombre'] or clave}")
            anexos_uso = sorted(set(usos.get(clave, [])))
            if anexos_uso:
                st.caption("Aparece en: " + ", ".join(anexos_uso))

            subido = st.file_uploader("Reemplazar logo", type=["png", "jpg", "jpeg"],
                                      key=f"up_{clave}")
            escala = st.slider("Tamaño respecto al original", 0.5, 1.6,
                               float(registro["escala"] or 1.0), 0.05, key=f"esc_{clave}",
                               help="1.00 mantiene exactamente el tamaño del formato oficial.")
            c_p, c_a = st.columns(2)
            proporcion = c_p.checkbox(
                "Mantener la proporción del logo", bool(registro.get("proporcion", 1)),
                key=f"prop_{clave}",
                help="Respeta el ancho del formato y ajusta el alto para no deformar la imagen.")
            activo = c_a.checkbox("Aplicar este logo al generar", bool(registro["activo"]),
                                  key=f"act_{clave}")

            c_a, c_b = st.columns(2)
            if c_a.button("Guardar", key=f"g_{clave}", type="primary"):
                archivo = registro["archivo"]
                if subido is not None:
                    destino = DIR_LOGOS / f"{clave}{Path(subido.name).suffix.lower()}"
                    destino.write_bytes(subido.getbuffer())
                    archivo = destino.name
                with db.conexion() as con:
                    con.execute(
                        "UPDATE logos SET archivo = ?, escala = ?, proporcion = ?, "
                        "activo = ? WHERE clave = ?",
                        (archivo, float(escala), 1 if proporcion else 0,
                         1 if activo else 0, clave))
                aviso_guardado()
                st.rerun()

            if c_b.button("Volver al original", key=f"r_{clave}"):
                with db.conexion() as con:
                    con.execute(
                        "UPDATE logos SET archivo = '', escala = 1.0 WHERE clave = ?", (clave,))
                st.rerun()

    st.divider()
    with st.expander("Ver los logos que traen las plantillas"):
        for anexo, datos in sorted(manifiesto.items()):
            slots = ", ".join(f"{s['logico']} ({s['ancho_cm']}×{s['alto_cm']} cm)"
                              for s in datos.get("logos", []))
            st.markdown(f"- **{anexo}**: {slots}")


# --------------------------------------------------------------------------
# Página: Generar
# --------------------------------------------------------------------------

def _revision_previa():
    """
    Avisa de tablas vacías antes de generar.

    Hace falta porque un documento con su tabla vacía sale igual y sin error:
    el problema solo se ve abriendo el Word. Pasa sobre todo tras volver a
    correr un script de carga, que rehace meses, estudiantes y actividades con
    identificadores nuevos y deja sin dueño a las tablas derivadas.
    """
    REVISION = [
        ("seguimiento", "Anexo 9", "Meses y seguimiento"),
        ("evaluacion_plan", "Anexos 6.1 y 6.2", "Evaluaciones"),
        ("evaluacion_estudiante", "Anexo 11", "Evaluaciones"),
        ("planificacion", "Anexo 7", "Meses y seguimiento"),
        ("registro_diario", "Anexo 8", "Registro diario"),
        ("actividades", "Anexos 6, 7 y 10", "Plan de aprendizaje"),
        ("estudiantes", "casi todos los anexos", "Estudiantes"),
    ]
    with db.conexion() as con:
        vacias = [(t, a, s) for t, a, s in REVISION
                  if not con.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone()]
    if not vacias:
        return
    st.error("Hay tablas sin datos. Los documentos saldrán con esas secciones "
             "en blanco:\n\n"
             + "\n".join(f"- **{t}** (vacía) → afecta a {a}; se llena en «{s}»"
                         for t, a, s in vacias)
             + "\n\nSi acaba de volver a cargar el proyecto con un script, "
               "ejecute después `python herramientas/cargar_actividades.py` "
               "para volver a derivar el seguimiento y las evaluaciones.")


def pagina_generar():
    st.header("Generar documentos")

    disponibles = generador.anexos_disponibles()
    if not disponibles:
        st.error("No hay plantillas. Ejecuta `herramientas/construir_plantillas.py` primero.")
        return

    # Un anexo sin plantilla no aparecía y ya está: no salía casilla ni aviso,
    # y desde fuera parecía que el sistema no lo contemplaba. Ahora se nombra.
    sin_plantilla = [a for a in generador.CATALOGO.values()
                     if not (generador.DIR_PLANTILLAS / a.plantilla).exists()]
    if sin_plantilla:
        st.error(
            f"Faltan {len(sin_plantilla)} plantillas en `{generador.DIR_PLANTILLAS}`. "
            "Esos documentos no se pueden generar y por eso no aparecen abajo:\n\n"
            + "\n".join(f"- **{a.titulo}** → falta `{a.plantilla}`"
                        for a in sin_plantilla)
            + "\n\nSe recrean con "
              "`python herramientas/construir_plantillas.py --origen <carpeta ANEXOS>`.")

    _revision_previa()

    numerados = [a for a in disponibles if not a.clave.startswith("S")]
    informes = [a for a in disponibles if a.clave.startswith("S")]

    # Streamlit no permite escribir en session_state la clave de un widget que
    # ya se instanció en esta pasada. Por eso "Seleccionar todos" no puede
    # tocar `chk_<anexo>` directamente: se guarda la decisión y se renumeran
    # las claves con un contador, de modo que en la siguiente pasada son
    # widgets nuevos y sí aceptan el valor por defecto.
    st.session_state.setdefault("gen_ronda", 0)
    st.session_state.setdefault("gen_defecto", {})

    def marcar(valor: bool, claves=None):
        objetivo = claves if claves is not None else [a.clave for a in disponibles]
        defecto = dict(st.session_state["gen_defecto"])
        if claves is None:
            defecto = {a.clave: valor for a in disponibles}
        else:
            for c in objetivo:
                defecto[c] = valor
        st.session_state["gen_defecto"] = defecto
        st.session_state["gen_ronda"] += 1

    c1, c2, c3, c4 = st.columns([1.1, 1.2, 1, 1.4])
    if c1.button("Marcar todo", **ANCHO_BOTON):
        marcar(True)
        st.rerun()
    if c2.button("Solo los 13 anexos", **ANCHO_BOTON):
        marcar(False)
        marcar(True, [a.clave for a in numerados])
        st.rerun()
    if c3.button("Solo informes", **ANCHO_BOTON):
        marcar(False)
        marcar(True, [a.clave for a in informes])
        st.rerun()
    if c4.button("Limpiar", **ANCHO_BOTON):
        marcar(False)
        st.rerun()

    ronda = st.session_state["gen_ronda"]
    defecto = st.session_state["gen_defecto"]
    seleccion = []

    def rejilla(lista, prefijo):
        columnas = st.columns(3)
        for i, anexo in enumerate(lista):
            etiqueta = (f"**Anexo {anexo.clave}** · {anexo.titulo}"
                        if not anexo.clave.startswith("S")
                        else f"**S/N {anexo.clave[1:]}** · {anexo.titulo}")
            marcado = columnas[i % 3].checkbox(
                etiqueta, value=bool(defecto.get(anexo.clave, False)),
                key=f"chk_{prefijo}_{anexo.clave}_{ronda}", help=anexo.descripcion)
            if marcado:
                seleccion.append(anexo.clave)

    st.subheader(f"Anexos numerados ({len(numerados)})")
    rejilla(numerados, "num")

    st.subheader(f"Informes sin número ({len(informes)})")
    st.caption("Son los que la Constancia lista como S/N. Se entregan junto con los anexos.")
    rejilla(informes, "inf")

    st.divider()
    c1, c2 = st.columns(2)
    a_pdf = c1.checkbox("Generar también en PDF",
                        help="Usa Word si está instalado; si no, LibreOffice.")
    continuar = c2.checkbox(
        "Continuar (no rehacer los que ya están)",
        help="Retoma una tanda que se cortó a mitad. Déjelo sin marcar si "
             "cambió datos y quiere rehacer todo.")
    st.caption(f"Seleccionados: **{len(seleccion)}** de {len(disponibles)} documentos. "
               "La tanda completa tarda varios minutos: **no cambie de sección ni "
               "pulse otro botón mientras corre**, porque eso reinicia la página y "
               "corta la generación.")

    if st.button("Generar", type="primary", disabled=not seleccion):
        carpeta = DIR_SALIDA
        if carpeta.exists() and not continuar:
            shutil.rmtree(carpeta)
        carpeta.mkdir(parents=True, exist_ok=True)

        with st.spinner(f"Generando… ({len(seleccion)} anexos; puede tardar "
                        "varios minutos, no toque la página)"):
            resultado = generador.generar(seleccion, carpeta, a_pdf=a_pdf,
                                          saltar_existentes=continuar)

        docx = [a for a in resultado["archivos"] if a.suffix == ".docx"]
        pdfs = [a for a in resultado["archivos"] if a.suffix == ".pdf"]
        # Se avisa arriba y en rojo si alguno de los seleccionados no produjo
        # ni un archivo: antes había que contarlos a mano para darse cuenta.
        vacios = [c for c in seleccion
                  if not any(a.name.startswith(generador.prefijo(c)) for a in docx)]
        if vacios:
            st.error("No se generó ningún archivo de: "
                     + ", ".join(vacios)
                     + ". Abra la bitácora de abajo para ver el motivo.")
        st.success(f"{len(docx)} documentos Word" +
                   (f" y {len(pdfs)} PDF" if pdfs else "") + " generados.")
        for error in resultado["errores"]:
            st.warning(error)
        st.session_state["gen_ultima"] = [str(a) for a in resultado["archivos"]]

    _zona_descarga()


def _zona_descarga():
    """
    Descarga de lo que haya en la carpeta de salida.

    Se lee del disco y no de la última generación: así el ZIP sigue disponible
    aunque se cambie de sección o se recargue la página, que es cuando antes
    desaparecía el botón.
    """
    todos = sorted(DIR_SALIDA.glob("*.*")) if DIR_SALIDA.exists() else []
    # La bitácora empieza por "_" y no es un documento de entrega.
    bitacora = DIR_SALIDA / "_registro_generacion.txt"
    existentes = [a for a in todos if not a.name.startswith("_")]

    if bitacora.exists():
        st.divider()
        texto = bitacora.read_text(encoding="utf-8", errors="replace")
        fallos = [l for l in texto.splitlines() if "ERROR" in l or "0 documentos" in l]
        cortada = "FIN ·" not in texto
        if cortada:
            fallos.append("La bitácora no llega al final: el proceso se cortó "
                          "mientras generaba. Vuelva a pulsar Generar; si se "
                          "vuelve a cortar en el mismo punto, reinicie la app.")
        titulo = ("Bitácora de la última generación"
                  + (f"  ·  {len(fallos)} problema(s)" if fallos else "  ·  sin problemas"))
        with st.expander(titulo, expanded=bool(fallos)):
            if fallos:
                st.error("\n\n".join(fallos))
            st.code(texto, language="text")
            st.caption("Si la generación se corta a medias, la última línea dice "
                       "en qué documento se quedó.")

    if not existentes:
        return

    st.divider()
    st.subheader(f"Documentos generados ({len(existentes)})")
    st.caption(f"Carpeta: `{DIR_SALIDA}`")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for archivo in existentes:
            z.write(archivo, archivo.name)
    st.download_button(f"⬇ Descargar los {len(existentes)} en un ZIP",
                       buffer.getvalue(), file_name="anexos_vinculacion.zip",
                       mime="application/zip", type="primary", **ANCHO_BOTON)

    # Agrupados por documento, para ver de un vistazo qué salió y qué falta.
    grupos = {}
    for archivo in existentes:
        etiqueta = archivo.name.split(" - ")[0]
        grupos.setdefault(etiqueta, []).append(archivo)

    def orden(clave: str):
        m = re.match(r"(?:ANEXO|SN)\s*([\d.]+)", clave)
        return (0 if clave.startswith("ANEXO") else 1,
                float(m.group(1)) if m else 999)

    for etiqueta in sorted(grupos, key=orden):
        archivos = grupos[etiqueta]
        with st.expander(f"{etiqueta}  ·  {len(archivos)} archivo(s)"):
            for archivo in archivos:
                c1, c2 = st.columns([4, 1])
                c1.write(archivo.name)
                c2.download_button("Descargar", archivo.read_bytes(),
                                   file_name=archivo.name, key=f"dl_{archivo.name}")


# --------------------------------------------------------------------------
# Navegación
# --------------------------------------------------------------------------

PAGINAS = {
    "Proyecto": pagina_proyecto,
    "Personas": pagina_personas,
    "Estudiantes": pagina_estudiantes,
    "Plan de aprendizaje": pagina_plan,
    "Registro diario": pagina_registro,
    "Meses y seguimiento": pagina_meses,
    "Evaluaciones": pagina_evaluaciones,
    "Jornadas y visitas": pagina_jornadas,
    "Informes (S/N)": pagina_informes,
    "Logos": pagina_logos,
    "Generar anexos": pagina_generar,
}

with st.sidebar:
    st.title("📄 Anexos de Vinculación")
    eleccion = st.radio("Sección", list(PAGINAS), label_visibility="collapsed")
    st.divider()
    with db.conexion() as con:
        proyecto = db.obtener_proyecto(con)
        n_est = con.execute("SELECT COUNT(*) c FROM estudiantes WHERE activo = 1").fetchone()["c"]
        n_act = con.execute("SELECT COUNT(*) c FROM actividades").fetchone()["c"]
    st.caption(f"**Proyecto:** {proyecto.get('nombre_corto') or proyecto.get('nombre') or '— sin nombre —'}")
    st.caption(f"{n_est} estudiantes · {n_act} actividades")
    st.caption(f"Plantillas: {len(generador.anexos_disponibles())}/{len(generador.CATALOGO)}")

PAGINAS[eleccion]()
