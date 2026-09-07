#!/usr/bin/env python
"""
Añade los correos de una lista externa (Moodle, secretaría) a los estudiantes.

Por qué no vale la carga de Excel de la app: esa reemplaza la lista completa, y
la lista del aula virtual no trae cédulas ni horas. Aquí solo se rellena el
correo de quien ya está registrado, emparejando por nombre, y no se toca nada
más.

El emparejamiento normaliza tildes, mayúsculas y espacios dobles, y compara el
conjunto de palabras del nombre completo. Así "NAYELY DE LOS ANGELES /
ANGUISACA CRESPO" encaja con "Nayely De Los Angeles Anguisaca Crespo" aunque la
lista traiga nombres y apellidos en columnas separadas y en otro orden.

Si una fila del archivo no corresponde a ningún estudiante, se avisa en vez de
inventar: puede ser el docente, un oyente o alguien dado de baja.

Uso:
    python herramientas/cargar_correos.py lista.xlsx
    python herramientas/cargar_correos.py lista.xlsx --aplicar
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from core import db  # noqa: E402

# Nombres de columna habituales en las listas del aula virtual y de secretaría.
COLUMNAS_NOMBRE = ("nombre", "nombres", "first name", "firstname")
COLUMNAS_APELLIDO = ("apellido", "apellidos", "apellido(s)", "last name", "surname")
COLUMNAS_EMAIL = ("email", "correo", "e-mail", "dirección email", "direccion email",
                  "email address")


def normalizar(texto: str) -> str:
    """Sin tildes, en minúsculas y sin espacios de más."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def palabras(texto: str) -> frozenset[str]:
    return frozenset(normalizar(texto).split())


def _columna(df: pd.DataFrame, candidatas) -> str | None:
    for col in df.columns:
        if normalizar(col) in [normalizar(c) for c in candidatas]:
            return col
    # Segunda pasada: por contención, para "Dirección Email (institucional)".
    for col in df.columns:
        if any(normalizar(c) in normalizar(col) for c in candidatas):
            return col
    return None


def leer_lista(ruta: Path) -> list[dict]:
    if ruta.suffix.lower() == ".csv":
        df = pd.read_csv(ruta, dtype=str)
    else:
        df = pd.read_excel(ruta, dtype=str)
    df = df.fillna("")

    col_nom = _columna(df, COLUMNAS_NOMBRE)
    col_ape = _columna(df, COLUMNAS_APELLIDO)
    col_mail = _columna(df, COLUMNAS_EMAIL)
    if col_mail is None:
        raise ValueError(f"No encuentro la columna de correo. Columnas: {list(df.columns)}")

    filas = []
    for _, fila in df.iterrows():
        completo = " ".join(x for x in ((fila[col_nom] if col_nom else ""),
                                        (fila[col_ape] if col_ape else "")) if x)
        correo = str(fila[col_mail]).strip()
        if completo.strip() and correo:
            filas.append({"nombre": completo.strip(), "email": correo})
    return filas


def emparejar(con, lista: list[dict]) -> tuple[list[dict], list[dict]]:
    """(coincidencias, sobrantes)."""
    estudiantes = db.listar(con, "estudiantes", orden="orden, id")
    indice = {palabras(e["nombre_completo"]): dict(e) for e in estudiantes}

    coincidencias, sobrantes = [], []
    for fila in lista:
        clave = palabras(fila["nombre"])
        estudiante = indice.get(clave)
        if estudiante is None:
            # Coincidencia parcial: la lista puede traer un nombre de más o de
            # menos. Se acepta solo si no hay ambigüedad.
            posibles = [e for k, e in indice.items()
                        if k & clave and len(k & clave) >= min(len(k), len(clave)) - 1]
            estudiante = posibles[0] if len(posibles) == 1 else None
        if estudiante is None:
            sobrantes.append(fila)
        else:
            coincidencias.append({**fila, "id": estudiante["id"],
                                  "actual": estudiante["email"],
                                  "registrado": estudiante["nombre_completo"]})
    return coincidencias, sobrantes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivo", help="lista .xlsx o .csv con nombres y correos")
    ap.add_argument("--aplicar", action="store_true",
                    help="escribir los correos; por defecto solo muestra")
    ap.add_argument("--sobrescribir", action="store_true",
                    help="reemplazar también los correos que ya estén puestos")
    args = ap.parse_args()

    ruta = Path(args.archivo)
    if not ruta.exists():
        print(f"No existe: {ruta}")
        return 1

    lista = leer_lista(ruta)
    print(f"{len(lista)} fila(s) con nombre y correo en {ruta.name}\n")

    with db.conexion() as con:
        coincidencias, sobrantes = emparejar(con, lista)

        cambios = [c for c in coincidencias
                   if (not c["actual"].strip() or args.sobrescribir)
                   and c["actual"].strip() != c["email"]]

        print(f"{len(coincidencias)} estudiante(s) identificado(s):")
        for c in coincidencias:
            if c["actual"].strip() and c["actual"].strip() != c["email"]:
                marca = "ya tiene otro" if not args.sobrescribir else "se reemplaza"
            elif c["actual"].strip():
                marca = "sin cambio"
            else:
                marca = "se añade"
            print(f"   {c['registrado'][:38]:40} {c['email']:42} [{marca}]")

        if sobrantes:
            print(f"\n{len(sobrantes)} fila(s) del archivo sin estudiante registrado:")
            for s in sobrantes:
                print(f"   {s['nombre']:40} {s['email']}")

        sin_correo = [e for e in db.listar(con, "estudiantes")
                      if not (e["email"] or "").strip()
                      and e["id"] not in {c["id"] for c in cambios}]
        if sin_correo:
            print(f"\n{len(sin_correo)} estudiante(s) se quedan sin correo:")
            for e in sin_correo:
                print(f"   {e['nombre_completo']}")

        if args.aplicar and cambios:
            for c in cambios:
                con.execute("UPDATE estudiantes SET email = ? WHERE id = ?",
                            (c["email"], c["id"]))
            print(f"\nAplicado: {len(cambios)} correo(s) escrito(s).")
        elif not args.aplicar:
            print(f"\n(Vista previa. {len(cambios)} cambio(s) pendiente(s); "
                  "use --aplicar.)")
        else:
            print("\nNo había nada que cambiar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
