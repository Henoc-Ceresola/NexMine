# Lector de claves: la única pieza que lee config/CLAVES.txt.
# Los motores y las puertas le piden aquí lo que necesitan.
# Se lee el archivo cada vez, así los cambios valen sin reiniciar.

from pathlib import Path

ARCHIVO_CLAVES = Path(__file__).resolve().parent.parent / "config" / "CLAVES.txt"


def leer():
    # Devuelve todas las claves como {NOMBRE: valor}.
    # Si el archivo no existe, devuelve un diccionario vacío.
    claves = {}
    if not ARCHIVO_CLAVES.exists():
        return claves
    # utf-8-sig: aguanta la marca invisible que añade el Bloc de notas al guardar.
    for linea in ARCHIVO_CLAVES.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        # Saltar líneas vacías, comentarios y líneas sin igual.
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = linea.split("=", 1)
        # Quitar espacios y comillas alrededor del valor.
        valor = valor.strip().strip('"').strip("'").strip()
        claves[nombre.strip()] = valor
    return claves


def clave(nombre):
    # Devuelve el valor de una clave, o vacío si falta o está vacía.
    return leer().get(nombre, "")
