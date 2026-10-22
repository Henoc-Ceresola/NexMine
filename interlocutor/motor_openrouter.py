# Motor OpenRouter: el motor de IA de verdad.
# Recibe lo mismo que el motor de prueba (nombre, texto y perfil)
# y se lo manda a una IA a través de OpenRouter.
# Solo usa lo que trae Python: no hay que instalar nada.

import json
import urllib.error
import urllib.request
from pathlib import Path

# La clave y el modelo viven en config/CLAVES.txt, nunca en el código.
# Los lee el lector de claves, no este motor.
import claves

CARPETA = Path(__file__).resolve().parent
# La personalidad del Interlocutor vive en su propio archivo.
ARCHIVO_INSTRUCCIONES = CARPETA / "instrucciones.md"
DIRECCION = "https://openrouter.ai/api/v1/chat/completions"


def responder(nombre, texto, perfil, memoria=None):
    # memoria: los últimos intercambios de esta persona, del más antiguo al más nuevo.
    # 1. Pedir la clave y el modelo. Si falta algo, avisar sin romperse.
    clave = claves.clave("IA_CLAVE")
    modelo = claves.clave("IA_MODELO")
    if not clave:
        return "Aviso: falta la clave de la IA. Ponla en config/CLAVES.txt, después de IA_CLAVE= (mira config/CLAVES.ejemplo.txt)."
    if not modelo:
        return "Aviso: falta el nombre del modelo de la IA. Ponlo en config/CLAVES.txt, después de IA_MODELO=."

    # 2. Preparar el paquete: instrucciones y perfil por un lado,
    #    luego la memoria (los últimos intercambios, en orden),
    #    y al final el mensaje nuevo de la persona, una sola vez.
    instrucciones = ARCHIVO_INSTRUCCIONES.read_text(encoding="utf-8")
    contexto = f"{instrucciones}\n\nNombre de la persona: {nombre}\n\nSu perfil:\n{perfil}"
    mensajes = [{"role": "system", "content": contexto}]
    for intercambio in memoria or []:
        mensajes.append({"role": "user", "content": intercambio["persona"]})
        mensajes.append({"role": "assistant", "content": intercambio["interlocutor"]})
    mensajes.append({"role": "user", "content": texto})
    paquete = {"model": modelo, "messages": mensajes}

    # 3. Enviarlo a OpenRouter y esperar la respuesta.
    peticion = urllib.request.Request(
        DIRECCION,
        data=json.dumps(paquete).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {clave}",
            "Content-Type": "application/json",
            "X-Title": "NexMine Interlocutor",
        },
    )
    try:
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        # La IA contestó, pero con un error (clave mala, demasiadas peticiones...).
        if error.code == 401:
            return "Aviso: OpenRouter no acepta la clave. Puede que haya que cambiarla (config/CLAVES.txt, línea IA_CLAVE)."
        if error.code == 429:
            return "Aviso: OpenRouter dice que hay demasiadas peticiones. Espera un poco y vuelve a probar."
        return f"Aviso: OpenRouter ha devuelto un error ({error.code}). Vuelve a probar más tarde."
    except (urllib.error.URLError, TimeoutError):
        return "Aviso: no hay conexión con OpenRouter. Revisa internet y vuelve a probar."

    # 4. Sacar el texto de la respuesta.
    try:
        contenido = datos["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        contenido = None
    if not contenido:
        return "Aviso: la IA no ha devuelto ninguna respuesta. Vuelve a probar."
    return contenido.strip()
