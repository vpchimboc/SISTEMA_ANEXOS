# Sistema de Anexos de Vinculación

Llena los datos una sola vez y genera el expediente completo de vinculación en
Word y PDF, con el mismo formato que aprueba la Coordinación, incluidos los
logos del encabezado:

- los **13 anexos** numerados (15 documentos, contando 6.1 y 6.2)
- los **5 documentos sin número** que exige la Constancia: proceso de selección,
  informe de seguimiento ISTA, informe final ISTA, socialización de resultados
  y la propia Constancia de recepción de anexos

**20 plantillas en total.**

---

## Instalación (Windows)

1. Copia esta carpeta dentro de la carpeta del proyecto, junto a `PLANTILLAS`.
2. Doble clic en **`instalar.bat`**. Crea el entorno, instala las librerías y
   construye las plantillas leyendo tus anexos oficiales de `PLANTILLAS\ANEXOS`.
3. Doble clic en **`iniciar.bat`**. Se abre el navegador con el sistema.

Requisito previo: Python 3.10 o superior, instalado con la casilla
*"Add Python to PATH"* marcada.

Si prefieres la consola:

```bash
pip install -r requirements.txt
python herramientas/construir_plantillas.py
streamlit run app.py
```

---

## Cómo funciona

```
Anexos oficiales (.docx)                 Tus datos
   PLANTILLAS/ANEXOS/                    datos/anexos.db
          │                                    │
          │  construir_plantillas.py           │
          ▼                                    │
   plantillas/*.docx  ────── docxtpl ──────────┘
   (los mismos documentos,        │
    con {{ etiquetas }})          ▼
                            salida/*.docx  →  *.pdf
                                   │
                            gestor de logos
```

La clave para que el formato salga idéntico es que **no se reconstruye ningún
documento**: se toma el .docx oficial y solo se sustituye el texto de las
etiquetas dentro de su propio XML. Estilos, márgenes, tablas, numeración y
encabezado quedan exactamente donde estaban.

---

## Las secciones de la app

| Sección | Para qué sirve | Alimenta a |
|---|---|---|
| **Proyecto** | Nombre, carrera, entidad beneficiaria, horas y fechas | Todos |
| **Personas** | Director, docentes de apoyo, responsable, coordinadores, representante legal | 1, 4, 5, 6, 8, 9, 11, 12, 13 |
| **Estudiantes** | Lista de participantes; se puede **subir desde Excel** | 3, 4, 5, 6, 8, 10, 11 |
| **Plan de aprendizaje** | Las actividades del proyecto con horas y asignaturas base | 2, 6, 6.1, 6.2, 7, 9, 10 |
| **Registro diario** | Bitácora de actividades y horas | 8 |
| **Meses y seguimiento** | Planificación mensual y su seguimiento | 7, 9 |
| **Evaluaciones** | Avance del plan y rúbrica del estudiante | 6.1, 6.2, 11 |
| **Jornadas y visitas** | Capacitaciones y visitas del docente | 12, 13 |
| **Informes (S/N)** | Redacción, casillas ☐/☒, listas, indicadores y constancia | S/N 1 a 5 |
| **Logos** | Reemplaza y redimensiona los logos del encabezado | Todos |
| **Generar anexos** | Produce los documentos, en lote, en Word y PDF | — |

### Qué se genera por cada uno

| Anexo | Se emite… | Nombre del archivo |
|---|---|---|
| 1 | por docente | `ANEXO 1 - <docente>.docx` |
| 2 | uno solo | `ANEXO 2 - Convocatoria.docx` |
| 3, 4, 6, 6.1, 6.2, 8, 10, 11 | por estudiante | `ANEXO n - <estudiante>.docx` |
| 5, 13 | por docente de apoyo | `ANEXO n - <docente>.docx` |
| 7 | por mes | `ANEXO 7 - Planificacion <mes>.docx` |
| 9 | por mes y docente de apoyo | `ANEXO 9 - <mes> - <docente>.docx` |
| 12 | por jornada de capacitación | `ANEXO 12 - <jornada>.docx` |
| S/N 1 a 5 | uno solo | `SN n - <nombre>.docx` |

### Los cinco documentos sin número

| Documento | Qué lleva del sistema |
|---|---|
| **S/N 1 · Proceso de selección** | Proyecto, director, carrera, firmas y cuatro bloques de redacción |
| **S/N 2 · Seguimiento ISTA** | Equipo docente y estudiantes, objetivos, situación, actividades con % de cumplimiento, conclusiones |
| **S/N 3 · Informe final ISTA** | Todo lo del seguimiento + impacto, indicadores, matriz de objetivos, productos y recomendaciones |
| **S/N 4 · Socialización** | Carrera, director de carrera, firmas y cuatro secciones libres |
| **S/N 5 · Constancia** | Checklist de los 17 documentos, **marcado automáticamente** con lo que generaste |

Tres cosas que conviene saber de estos cinco:

- **La redacción se guarda, no se inventa.** El texto largo (antecedentes,
  situación inicial, conclusiones, impacto) vive en la sección *Informes* y se
  edita ahí. El sistema lo coloca en el formato oficial, nada más.
- **Las imágenes del cuerpo no se tocan.** Estos informes llevan evidencias
  fotográficas y cronogramas pegados como imagen. La sustitución es párrafo a
  párrafo y respeta los párrafos que contienen dibujos.
- **Las casillas ☐/☒** de línea de acción, alcance territorial e impacto se
  eligen con botones en la app.

En el informe de proceso de selección, el logo del encabezado es la **misma
imagen** que una del cuerpo del documento. El sistema lo detecta y conserva el
original en lugar de arriesgarse a alterar el contenido; lo avisa al generar.

---

## Los logos

Los documentos llevan **dos logos**: el institucional (TEC.AZUAY) y el de la
SENESCYT. Hay dos trampas en el formato oficial que el sistema resuelve solo:

- **No están siempre en el mismo orden.** En el Anexo 1 el institucional va a la
  izquierda; en el Anexo 8, a la derecha (y en el XML aparece incluso en orden
  inverso al visual). Identificarlos por posición cruzaría los logos, así que el
  sistema los reconoce **por su huella** y usa `plantillas/manifiesto.json`, que
  registra qué logo ocupa cada hueco de cada plantilla.
- **El Anexo 5 no tiene encabezado**: lleva los dos logos incrustados en el
  cuerpo. El sistema los detecta ahí, pero solo acepta como logo una imagen cuya
  huella coincide con una conocida — así una foto de evidencia nunca se
  confunde con un logo.

En la sección **Logos** puedes:

- **Reemplazar** un logo subiendo un PNG o JPG. Se convierte al formato que
  espera el documento y se coloca en su sitio.
- **Mantener la proporción** (activado por defecto): respeta el ancho del
  formato y recalcula el alto según la imagen, para que no salga deformada.
- **Redimensionarlo** con el control de escala (1.00 = tamaño oficial exacto).
- **Desactivarlo** o **volver al original** con un botón.

Los archivos se guardan en `recursos/logos/`.

Un detalle importante: **si dejas un logo sin archivo, cada documento conserva
el que trae su formato oficial.** En cuanto subes uno, ese mismo archivo se usa
en los 20 documentos, incluidos los que traían otra variante de la misma marca
(la SENESCYT aparece en cuatro versiones distintas en los formatos originales).

En el informe de proceso de selección el logo del encabezado es la **misma
imagen** que una del cuerpo. El sistema lo detecta, conserva el original para no
alterar el contenido, y lo avisa al generar.

---

## PDF

Marca *"Generar también en PDF"* al generar.

- En Windows usa **Word** (`docx2pdf`), que respeta la paginación al 100 %.
- Si no hay Word, intenta con **LibreOffice**.
- Si no hay ninguno, genera solo los .docx y te avisa.

---

## Empezar un proyecto nuevo

```bash
python herramientas/nuevo_proyecto.py --conservar-plan --conservar-personas
```

Hace una copia de seguridad de la base y limpia los datos operativos. Las
opciones te permiten conservar el plan de aprendizaje y las personas, que casi
siempre se repiten entre fases del mismo proyecto.

Hay dos proyectos de ejemplo cargables:

```bash
# TAIPT / U.E. Luis Monsalve Pozo — llena los 13 anexos numerados
python herramientas/cargar_ejemplo.py --reiniciar

# Big Data / Fundación Mensajeros de la Paz Fase 2 — llena también los cinco S/N
python herramientas/cargar_bigdata.py --reiniciar
```

Ojo: cada uno **reemplaza** al otro, porque el sistema maneja un proyecto activo
a la vez.

---

## El registro diario (Anexo 8)

Las 35 entradas del mantenimiento de laboratorios se repiten fase tras fase y
suman exactamente las 100 horas, así que viven en su propio cargador:

```bash
python herramientas/cargar_registro.py              # con las fechas de la lista
python herramientas/cargar_registro.py --reubicar   # dentro de las fechas del proyecto
python herramientas/cargar_registro.py --agregar    # sin borrar lo que ya hubiera
```

`--reubicar` traslada las jornadas a la ventana del proyecto activo conservando
el orden y la separación relativa entre ellas, y saltando fines de semana. El
**lugar** siempre se toma del proyecto activo, nunca de la lista: las entradas
vienen de una fase anterior y arrastrarían el nombre de la unidad educativa
equivocada.

### Derivar el resto de los anexos del registro

```bash
python herramientas/cargar_actividades.py
```

Toma el registro diario como única fuente y construye la planificación mensual
(Anexo 7), el seguimiento (Anexo 9), las jornadas (Anexo 12), las visitas
(Anexo 13), las evaluaciones del plan (6.1 y 6.2), la rúbrica (Anexo 11) y la
tabla de actividades de los informes ISTA.

Se deriva en vez de copiarlo de la fase anterior por dos razones: las fechas y
la unidad educativa serían las de esa fase, y las horas no siempre cuadran
entre documentos —en el Anexo 7 original, octubre declara 73 h por estudiante
mientras el Anexo 8 registra 67—. Derivando, las horas del Anexo 7 suman
exactamente las del Anexo 8.

---

## Si cambia el formato oficial de un anexo

1. Reemplaza el .docx en `PLANTILLAS/ANEXOS/`.
2. Ejecuta `python herramientas/construir_plantillas.py`.
3. Si alguna regla ya no encuentra su texto, el script lo dice con un **AVISO**
   indicando el anexo y la cadena exacta. Se corrige en `REGLAS` dentro de
   `herramientas/construir_plantillas.py`.

Ese aviso es intencional: es la forma de enterarse de que un formato cambió
antes de entregar un documento incompleto.

---

## Verificación

```bash
python herramientas/verificar.py
```

El riesgo real de un sistema así no es que falle, sino que un documento salga
"bien" con el nombre de un estudiante del proyecto anterior incrustado, porque
ese texto no llegó a convertirse en variable. Un vistazo no lo detecta.

La verificación carga un proyecto **canario** donde cada dato tiene un valor
inconfundible (`CANARIO PROYECTO NOMBRE`, `9991110001`…), genera los 20
documentos y comprueba cuatro cosas:

1. que las 20 plantillas existan y produzcan archivo;
2. que **ningún** rastro de los proyectos originales sobreviva (nombres,
   cédulas, correos, fechas y entidades de los tres proyectos que pasaron por
   estos formatos);
3. que no queden etiquetas `{{ }}` sin resolver;
4. que los logos sigan en su sitio y que los datos del sistema lleguen de verdad
   al documento.

Conviene correrla después de tocar una plantilla o una regla.

---

## Estructura

```
app.py                              Interfaz Streamlit
core/
  db.py                             Esquema SQLite y acceso a datos
  contexto.py                       Arma el diccionario para las plantillas
  generador.py                      Renderiza, aplica logos y exporta a PDF
  logos.py                          Reemplaza las imágenes del encabezado
  docx_utils.py                     Manipulación fina del XML de Word
herramientas/
  construir_plantillas.py           Convierte los anexos oficiales en plantillas
  cargar_ejemplo.py                 Ejemplo: proyecto TAIPT (Luis Monsalve Pozo)
  cargar_bigdata.py                 Ejemplo: proyecto Big Data (Mensajeros de la Paz)
  cargar_zoila.py                   Séptima fase: U.E. Zoila Aurora Palacios
  cargar_registro.py                Registro diario del Anexo 8 (100 horas)
  cargar_actividades.py             Deriva anexos 7, 9, 12, 13, 6.1, 6.2 y 11
  verificar.py                      Prueba canario: detecta datos no parametrizados
  nuevo_proyecto.py                 Limpia la base para empezar de cero
plantillas/                         Plantillas generadas + manifiesto.json
recursos/logos/                     Logos que subes desde la app
datos/anexos.db                     Tus datos (SQLite)
salida/                             Documentos generados
```

---

## Cosas que conviene saber

- **Las fechas se escriben en formato `AAAA-MM-DD`.** El sistema decide solo si
  el documento las necesita como `22/09/2025` o como `22 de septiembre de 2025`.
- **El nombre del proyecto se escribe sin comillas**: la plantilla las coloca.
- **El Anexo 10** genera la ficha de datos y la tabla de actividades; las
  evidencias fotográficas semanales se completan en Word, porque son propias de
  cada estudiante.
- **El Anexo 12** genera la hoja con los datos de la jornada y las filas de
  firmas en blanco, tal como el formato oficial: los beneficiarios firman a mano.
- En **Registro diario**, una fila sin estudiante asignado entra en el registro
  de todos. Asigna estudiante solo cuando la actividad sea de una sola persona.
