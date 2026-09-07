#!/usr/bin/env python
"""
Genera todos los documentos desde la consola, sin Streamlit.

Por qué existe: la generación completa son ~121 documentos y varios minutos.
Dentro de Streamlit cualquier clic en la página reinicia el script y mata la
tanda a mitad sin mostrar ningún error, que es exactamente lo que pasaba. Aquí
no hay página que reiniciar: el proceso corre hasta el final y va informando.

Uso:
    python generar_todo.py                 todos los anexos e informes
    python generar_todo.py --continuar     no rehace los que ya están
    python generar_todo.py --pdf           además convierte a PDF
    python generar_todo.py --solo 7 8 9    solo esos anexos

Los archivos quedan en salida/ y la app los ofrece para descargar sin más:
la zona de descarga lee del disco, no de la última generación.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from core import db, generador  # noqa: E402

# Tablas que, vacías, dejan secciones en blanco sin avisar. Se revisan antes de
# gastar varios minutos generando.
REVISION = [
    ("estudiantes", "casi todos los anexos", "Estudiantes"),
    ("actividades", "anexos 6, 7 y 10", "Plan de aprendizaje"),
    ("registro_diario", "anexo 8", "Registro diario"),
    ("planificacion", "anexo 7", "Meses y seguimiento"),
    ("seguimiento", "anexo 9", "Meses y seguimiento"),
    ("evaluacion_plan", "anexos 6.1 y 6.2", "Evaluaciones"),
    ("evaluacion_estudiante", "anexo 11", "Evaluaciones"),
]


def revisar_datos() -> list[str]:
    with db.conexion() as con:
        return [f"{t} (vacía) -> afecta a {a}; se llena en «{s}»"
                for t, a, s in REVISION
                if not con.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone()]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--continuar", action="store_true",
                   help="no rehacer los documentos que ya estén en salida/")
    p.add_argument("--pdf", action="store_true", help="convertir también a PDF")
    p.add_argument("--solo", nargs="+", metavar="CLAVE",
                   help="claves a generar (1 2 6.1 S3 …); por defecto, todas")
    p.add_argument("--forzar", action="store_true",
                   help="generar aunque haya tablas vacías")
    args = p.parse_args()

    disponibles = [a.clave for a in generador.anexos_disponibles()]
    if not disponibles:
        print("No hay plantillas en plantillas/. Ejecute primero "
              "herramientas/construir_plantillas.py")
        return 1

    claves = args.solo or disponibles
    desconocidas = [c for c in claves if c not in disponibles]
    if desconocidas:
        print("Claves sin plantilla:", ", ".join(desconocidas))
        print("Disponibles:", ", ".join(disponibles))
        return 1

    problemas = revisar_datos()
    if problemas:
        print("\nAVISO · hay tablas sin datos:")
        for linea in problemas:
            print("   -", linea)
        if not args.forzar:
            print("\nEsos documentos saldrán con la sección en blanco.")
            print("Continúe con --forzar, o llene los datos en la app.")
            print("Si acaba de recargar el proyecto con un script de carga, "
                  "ejecute antes:  python herramientas/cargar_actividades.py")
            return 1

    carpeta = generador.DIR_SALIDA
    carpeta.mkdir(parents=True, exist_ok=True)
    if not args.continuar:
        for viejo in carpeta.glob("*.*"):
            viejo.unlink()

    print(f"\nGenerando {len(claves)} anexos en {carpeta}")
    print("Esto tarda varios minutos. No cierre esta ventana.\n")
    inicio = time.time()

    resultado = generador.generar(claves, carpeta, a_pdf=args.pdf,
                                  saltar_existentes=args.continuar)

    archivos = resultado["archivos"]
    docx = [a for a in archivos if a.suffix == ".docx"]
    pdfs = [a for a in archivos if a.suffix == ".pdf"]

    print(f"\n{len(docx)} documentos Word"
          + (f" y {len(pdfs)} PDF" if pdfs else "")
          + f" en {time.time() - inicio:.0f} s")

    # Recuento por anexo: es la forma rápida de ver si falta alguno.
    print("\nPor documento:")
    for clave in claves:
        pref = generador.prefijo(clave)
        n = sum(1 for a in docx if a.name.startswith(pref))
        marca = "  <-- SIN ARCHIVOS" if n == 0 else ""
        print(f"   {pref.rstrip(' -'):38} {n:3}{marca}")

    if resultado["errores"]:
        print("\nAvisos:")
        for e in resultado["errores"]:
            print("   -", e)

    print(f"\nBitácora detallada: {carpeta / '_registro_generacion.txt'}")
    print("Abra la app y use el botón de descargar el ZIP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
