# Puerta de consola: la forma más sencilla de hablar con NexUs, desde la terminal.
# Pasa al Núcleo quién habla y qué dice, y enseña la respuesta. No guarda nada por su cuenta:
# la conversación la guarda el Núcleo, en data/usuarios/<nombre>/.
#
# Uso:  py interlocutor/puertas/consola.py tu_nombre      (en Mac o Linux: python3 ...)
# Si esa persona no existe todavía, pregunta si se crea a partir de la plantilla vacía.
# Dentro: /nueva empieza una conversación en blanco; /salir (o Ctrl+C) termina.

import re
import shutil
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA.parent))
import nucleo

PLANTILLA = nucleo.CARPETA_USUARIOS.parent / "plantillas" / "usuario_nuevo"
NOMBRE_VALIDO = re.compile(r"[a-z0-9_-]{1,30}")
ORDEN_SALIR = "/salir"


def dar_de_alta(nombre):
    # Crea la carpeta de una persona nueva copiando la plantilla vacía, solo si quien escribe lo confirma.
    if not NOMBRE_VALIDO.fullmatch(nombre):
        print("El nombre solo puede llevar letras minúsculas sin tilde, números, '-' o '_' (como mucho 30).")
        return False
    if input(f"'{nombre}' no existe todavía. ¿La creo a partir de la plantilla vacía? (s/n): ").strip().lower() != "s":
        return False
    shutil.copytree(PLANTILLA, nucleo.CARPETA_USUARIOS / nombre)
    print(f"Creada: data/usuarios/{nombre}/")
    return True


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print("Uso: py interlocutor/puertas/consola.py tu_nombre")
        return
    nombre = sys.argv[1].strip().lower()
    nucleo.CARPETA_USUARIOS.mkdir(parents=True, exist_ok=True)
    if nombre not in nucleo.usuarios() and not dar_de_alta(nombre):
        return

    print(f"Hablas con NexUs como '{nombre}'. /nueva empieza en blanco; /salir termina.")
    for intercambio in nucleo.ultimos(nombre, 3):
        print(f"\nTú: {intercambio['persona']}\nNexUs: {intercambio['interlocutor']}")
    while True:
        try:
            texto = input("\nTú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not texto:
            continue
        if texto.lower() == ORDEN_SALIR:
            break
        print("(NexUs está pensando...)")
        print("NexUs: " + nucleo.hablar(nombre, texto))


if __name__ == "__main__":
    main()
