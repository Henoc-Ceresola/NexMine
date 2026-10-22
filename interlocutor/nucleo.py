# Núcleo del Interlocutor.
# Recibe quién habla y qué dice, lee el perfil de esa persona
# y se lo pasa todo al motor. No sabe si el mensaje viene
# de la consola, de la pantalla o de Telegram: eso no es asunto suyo.
# También guarda la conversación (el hilo) de cada persona, para que
# el motor reciba los últimos mensajes junto con el nuevo.
#
# Cada persona tiene su carpeta en data/usuarios con piezas separadas:
#   principal/            conversación con el Interlocutor principal (hilo_*.jsonl)
#   hilos/                hilos con nombre (más adelante)
#   escritorio_personal/  lo suelto
#   perfil/perfil_D.md    su perfil
#   observador/           contador del Observador (lo crea él)

import json
import re
import threading
from datetime import datetime
from pathlib import Path

# El motor que se usa. Para cambiar a una IA de verdad,
# solo se cambia esta línea.
import motor_openrouter as motor
import observador

# Carpeta donde vive cada persona: NexMine.Core/data/usuarios
CARPETA_USUARIOS = Path(__file__).resolve().parent.parent / "data" / "usuarios"

# Memoria: cuántos intercambios (pregunta y respuesta) se le mandan al motor.
INTERCAMBIOS_MEMORIA = 20
# Tope de caracteres de esa memoria: si se pasa, se quita lo más antiguo.
CARACTERES_MEMORIA = 12000
# Observador (observador.py), interruptor de posiciones:
#   "apagado"     no se le llama
#   "vigilancia"  mira cada mensaje y apunta en logs/observador.log qué señal habría saltado;
#                 al Interlocutor no le llega ninguna nota (Paso 1a)
OBSERVADOR = "vigilancia"
# Mensaje que empieza un hilo en blanco.
ORDEN_HILO_NUEVO = "/nueva"
# Piezas de la carpeta de cada persona. Si falta alguna, el Núcleo la crea
# (pero nunca crea la carpeta de la persona: esa la da de alta quien la registra).
PIEZAS = ("principal", "hilos", "escritorio_personal", "perfil")
AVISO_FORMA_ANTIGUA = ("Aviso: los datos de esta persona aún tienen la forma antigua "
                       "(falta el traslado a la estructura nueva). No se ha cambiado nada.")

# Un candado por persona, para que dos mensajes a la vez no se pisen al escribir su hilo.
_candados = {}
_candado_general = threading.Lock()


def usuarios():
    # Devuelve los nombres de las personas registradas:
    # una por cada carpeta que hay dentro de data/usuarios.
    return sorted(c.name for c in CARPETA_USUARIOS.iterdir() if c.is_dir())


def _candado(nombre):
    with _candado_general:
        return _candados.setdefault(nombre, threading.Lock())


def _forma_antigua(nombre):
    # Protección para el cambio de estructura: perfil suelto y sin carpeta perfil/
    # quiere decir que estos datos aún no se han trasladado. Entonces no se toca nada.
    carpeta = CARPETA_USUARIOS / nombre
    return (carpeta / "perfil_D.md").exists() and not (carpeta / "perfil").exists()


def _preparar(nombre):
    # Crea las piezas que falten dentro de la carpeta de una persona que ya existe.
    for pieza in PIEZAS:
        (CARPETA_USUARIOS / nombre / pieza).mkdir(exist_ok=True)


def _hilos_principal(nombre):
    # Las conversaciones del principal: solo los hilo_*.jsonl sueltos de principal/, sin entrar en subcarpetas.
    carpeta = CARPETA_USUARIOS / nombre / "principal"
    return sorted(carpeta.glob("hilo_*.jsonl")) if carpeta.exists() else []


def _hilo_nuevo(nombre):
    # Crea un archivo de hilo vacío del principal, con la fecha y hora en el nombre.
    archivo = CARPETA_USUARIOS / nombre / "principal" / f"hilo_{datetime.now():%Y-%m-%d_%H%M%S}.jsonl"
    archivo.touch()
    return archivo


def _hilo_actual(nombre):
    # El hilo actual del principal es el más reciente; si no hay ninguno, se crea.
    hilos = _hilos_principal(nombre)
    return hilos[-1] if hilos else _hilo_nuevo(nombre)


def _leer_perfil(nombre):
    # El perfil de la persona; si todavía no tiene, se sigue sin perfil.
    archivo = CARPETA_USUARIOS / nombre / "perfil" / "perfil_D.md"
    return archivo.read_text(encoding="utf-8") if archivo.exists() else ""


def _leer_intercambios(archivo):
    # Lee todos los intercambios de un hilo, del más antiguo al más nuevo.
    intercambios = []
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        try:
            dato = json.loads(linea)
            intercambios.append({"persona": dato["persona"], "interlocutor": dato["interlocutor"]})
        except (ValueError, KeyError, TypeError):
            continue  # una línea estropeada no rompe el resto
    return intercambios


def _leer_memoria(archivo):
    # Los últimos intercambios del hilo, sin pasarse del tope de caracteres.
    # Lo más antiguo sigue guardado en el archivo; solo no se manda al motor.
    memoria = _leer_intercambios(archivo)[-INTERCAMBIOS_MEMORIA:]
    while memoria and sum(len(i["persona"]) + len(i["interlocutor"]) for i in memoria) > CARACTERES_MEMORIA:
        memoria.pop(0)
    return memoria


def _guardar(archivo, texto, respuesta):
    # Añade el intercambio al final del hilo, en una sola línea.
    linea = json.dumps({"hora": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "persona": texto, "interlocutor": respuesta}, ensure_ascii=False)
    with archivo.open("a", encoding="utf-8") as hilo:
        hilo.write(linea + "\n")


def ultimos(nombre, cantidad=10):
    # Devuelve los últimos intercambios del hilo actual de una persona,
    # para que una puerta pueda enseñar lo que el Interlocutor recuerda.
    # Si el nombre no es de una persona registrada o no tiene hilo, devuelve una lista vacía.
    # Solo lee: no crea nada.
    if nombre not in usuarios():
        return []
    hilos = _hilos_principal(nombre)
    if not hilos:
        return []
    with _candado(nombre):
        return _leer_intercambios(hilos[-1])[-cantidad:]


def _limpiar_formato(respuesta):
    # La pantalla y Telegram enseñan el texto tal cual, así que los símbolos de formato
    # se verían sueltos. Se quitan solo dos cosas de la respuesta de la IA:
    #   **texto**  ->  texto    (negrita)
    #   `texto`    ->  texto    (comillas inversas, también los bloques ```)
    # No se tocan los asteriscos sueltos (2*3), ni los guiones, ni lo que escribe la persona.
    respuesta = re.sub(r"\*\*(.+?)\*\*", r"\1", respuesta)
    respuesta = re.sub(r"```[A-Za-z0-9_+-]*[ \t]*\n?", "", respuesta)  # abre o cierra un bloque, con su nombre de lenguaje
    return respuesta.replace("`", "")


def hablar(nombre, texto):
    # 1. Comprobar el nombre antes de abrir nada.
    #    Solo vale si coincide exactamente con una carpeta de data/usuarios.
    #    Así, algo como "../docs" nunca puede salirse de esa carpeta.
    carpetas = [c.name for c in CARPETA_USUARIOS.iterdir() if c.is_dir()]
    if nombre not in carpetas:
        return f"Aviso: '{nombre}' no es una persona registrada. No se ha abierto ningún archivo."
    if _forma_antigua(nombre):
        return AVISO_FORMA_ANTIGUA

    # 2. Crear las piezas que falten (principal/, hilos/, escritorio_personal/, perfil/).
    with _candado(nombre):
        _preparar(nombre)

    # 3. "/nueva" empieza un hilo en blanco del principal. El anterior queda guardado.
    if texto.strip().lower() == ORDEN_HILO_NUEVO:
        with _candado(nombre):
            _hilo_nuevo(nombre)
        return "Hilo nuevo: empiezo en blanco. Lo anterior queda guardado."

    # 4. Leer el perfil y la memoria de esa persona.
    #    Se apunta ya en qué hilo va este mensaje: aunque la respuesta tarde,
    #    se guardará en este mismo hilo y de esta misma persona.
    perfil = _leer_perfil(nombre)
    with _candado(nombre):
        archivo = _hilo_actual(nombre)
        memoria = _leer_memoria(archivo)

    # 4b. El Observador mira el mensaje, comparándolo con los anteriores de esta conversación.
    #     Si falla, se sigue sin él: la conversación nunca se para por el Observador.
    if OBSERVADOR == "vigilancia":
        with _candado(nombre):
            try:
                senales, _nota = observador.observar(CARPETA_USUARIOS / nombre, texto, [i["persona"] for i in memoria])
                observador.anotar(nombre, senales, OBSERVADOR)
            except Exception as error:
                observador.anotar_error(nombre, error)

    # 5. Pasarle al motor quién habla, qué dice, su perfil y la memoria.
    respuesta = motor.responder(nombre, texto, perfil, memoria)
    # Limpieza de formato en un solo sitio: antes de guardar y de enseñar (sirve para todas las puertas).
    respuesta = _limpiar_formato(respuesta)

    # 6. Guardar el intercambio. Los avisos (sin internet, falta la clave...)
    #    no son respuestas de verdad y no se guardan.
    if not respuesta.startswith("Aviso:"):
        with _candado(nombre):
            _guardar(archivo, texto, respuesta)
    return respuesta
