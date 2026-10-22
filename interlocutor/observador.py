# Observador: vigila la conversación sin hablar con la persona y, cuando toca, pasa una nota corta a NexUs.
# Mira cada mensaje de la persona y busca cuatro señales que se pueden contar,
# sin IA: cierre, autocorrección, mensaje en caliente y repetición.
# No habla con la persona ni con las puertas: solo lo llama el Núcleo.
#
# Lleva un contador por persona, solo con números (su línea base), en
#   data/usuarios/<persona>/observador/contador.json
# Crea esa subcarpeta si falta, pero nunca la carpeta de la persona.
#
# Su registro (logs/observador.log) apunta qué señal ha saltado y a quién,
# nunca el texto de los mensajes.

import json
import logging
import logging.handlers
import re
from pathlib import Path

# Registro: como el de Telegram, nunca pasa de unos cientos de KB.
ARCHIVO_REGISTRO = Path(__file__).resolve().parent.parent / "logs" / "observador.log"
TAMANO_REGISTRO = 200_000  # bytes por archivo
COPIAS_REGISTRO = 1        # cuántos archivos viejos se guardan

# Repetición (los números son el punto de partida; se ajustan con el uso).
MENSAJES_COMPARAR = 8      # con cuántos mensajes anteriores se compara
PARECIDO_MINIMO = 0.6      # parte de palabras con contenido que tienen que compartir
PALABRAS_MINIMAS = 4       # con menos palabras con contenido no se compara
MENSAJES_LINEA_BASE = 20   # antes de esto no hay nota de repetición: aún no se conoce a la persona
VENTANA_PATRON = 20        # últimos mensajes en los que se cuenta la repetición
VECES_PATRON = 3           # veces dentro de esa ventana para que sea patrón

# Palabras que no cuentan al comparar. "no", "nunca" y "ni" sí cuentan: cambian el sentido.
PALABRAS_VACIAS = {"que", "de", "del", "el", "la", "los", "las", "lo", "y", "a", "al", "en",
                   "un", "una", "es", "me", "te", "se", "por", "con", "para"}
NEGACIONES = {"no", "nunca", "ni"}

CIERRE = ("eso es", "eso", "ahora sí", "perfecto", "exacto", "ya está", "guárdalo",
          "apúntalo", "vale eso", "ok guárdalo")
CIERRE_PALABRAS_MAXIMAS = 6
CIERRE_POSICION_MAXIMA = 3  # la expresión empieza como tarde en la 4.ª palabra
CIERRE_PROHIBIDAS = {"no", "pero", "falta"}
AUTOCORRECCION = ("no espera", "mejor dicho", "quiero decir", "no mejor", "perdona digo", "me he liado")
PALABRAS_FUERTES = ("joder", "hostia", "mierda", "coño", "cabreo", "harto", "ya está bien", "no aguanto")
INSISTENCIA = ("te lo vuelvo a decir", "otra vez", "como te he dicho", "no me entiendes",
               "te lo explico otra vez")

# Una nota por señal. Si saltan varias, solo va la primera de esta lista.
NOTAS = {
    "caliente": "Mensaje en caliente. Tono tranquilo, corto y neutro. No tomes partido.",
    "autocorreccion": "Se está corrigiendo. Usa la última versión.",
    "cierre": "Hay cierre. Formaliza y no añadas más.",
    "repeticion": "Está repitiendo. Ayúdale a cerrar o cambia de ángulo.",
}

registro = logging.getLogger("observador")
registro.propagate = False


def _palabras(texto):
    # Las palabras del texto en minúscula, sin signos.
    return re.findall(r"[a-záéíóúüñ0-9]+", texto.lower())


def _contiene(palabras, frase):
    # Si la frase (una o varias palabras seguidas) está dentro de la lista de palabras.
    return f" {frase} " in f" {' '.join(palabras)} "


# ---------- Las cuatro señales ----------

def cierre(texto):
    # Mensaje corto que empieza confirmando: "eso, guárdalo", "perfecto", "ahora sí".
    palabras = _palabras(texto)
    if not palabras or len(palabras) > CIERRE_PALABRAS_MAXIMAS:
        return False
    if CIERRE_PROHIBIDAS & set(palabras) or _contiene(palabras, "otra vez"):
        return False  # "eso no es", "perfecto pero...", "ya está otra vez fallando"
    for frase in CIERRE:
        trozo = frase.split()
        for inicio in range(min(CIERRE_POSICION_MAXIMA, len(palabras) - len(trozo)) + 1):
            if palabras[inicio:inicio + len(trozo)] == trozo:
                return True
    return False


def autocorreccion(texto):
    # Se corrige dentro del mismo mensaje: "no, espera", "mejor dicho".
    palabras = _palabras(texto)
    return any(_contiene(palabras, frase) for frase in AUTOCORRECCION)


def _mayusculas(texto):
    # Parte de las letras que van en mayúscula, sin contar la primera de cada frase.
    # Con muy pocas letras no se mide (un "OK" no es gritar).
    letras = mayusculas = 0
    inicio = True
    for c in texto:
        if c.isalpha():
            if not inicio:
                letras += 1
                mayusculas += c.isupper()
            inicio = False
        elif c in ".!?¡¿\n":
            inicio = True
    return mayusculas / letras if letras >= 8 else 0.0


def _signos(texto):
    # Signos de exclamación e interrogación (solo los de cierre, para no contar dos veces "¿...?").
    return texto.count("!") + texto.count("?")


def caliente(texto):
    # Hacen falta al menos dos de estas cuatro cosas en el mismo mensaje.
    palabras = _palabras(texto)
    cortes = texto.count("...") + texto.count("…") + texto.count("\n")
    condiciones = (
        _mayusculas(texto) > 0.30,
        _signos(texto) >= 3,
        len(palabras) < 12 and any(_contiene(palabras, frase) for frase in PALABRAS_FUERTES),
        len(palabras) < 25 and cortes > 2,
    )
    return sum(condiciones) >= 2


def _con_contenido(texto):
    return {p for p in _palabras(texto) if p not in PALABRAS_VACIAS}


def _parecido(a, b):
    # Parte de palabras con contenido que comparten dos mensajes, de 0 a 1.
    # Si uno niega y el otro no ("lo quiero" / "no lo quiero"), no es repetir: es lo contrario.
    if not a or not b or (a & NEGACIONES) != (b & NEGACIONES):
        return 0.0
    return len(a & b) / max(len(a), len(b))


def _datos(texto):
    # Lo que en este paso cuenta como dato nuevo: números y nombres propios
    # (palabras con mayúscula que no empiezan frase).
    datos = set(re.findall(r"\d+", texto))
    for m in re.finditer(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", texto):
        antes = texto[:m.start()].rstrip()
        if antes and antes[-1] not in ".!?¡¿" and m.group()[0].isupper():
            datos.add(m.group().lower())
    return datos


def repeticion(texto, anteriores):
    # Vuelve a decir lo mismo que en algún mensaje reciente de esta conversación,
    # y además insiste ("otra vez", "no me entiendes") o es el tercero seguido sin dato nuevo.
    actual = _con_contenido(texto)
    if len(actual) < PALABRAS_MINIMAS:
        return False
    recientes = anteriores[-MENSAJES_COMPARAR:]
    if max((_parecido(actual, _con_contenido(p)) for p in recientes), default=0.0) <= PARECIDO_MINIMO:
        return False
    if any(_contiene(_palabras(texto), frase) for frase in INSISTENCIA):
        return True
    if len(anteriores) >= 2:
        uno, dos = anteriores[-1], anteriores[-2]
        seguidos = (_parecido(actual, _con_contenido(uno)) > PARECIDO_MINIMO
                    and _parecido(_con_contenido(uno), _con_contenido(dos)) > PARECIDO_MINIMO)
        return seguidos and not (_datos(texto) - _datos(uno) - _datos(dos))
    return False


# ---------- Contador (línea base de cada persona) ----------

def _contador_vacio():
    return {"mensajes": 0, "mayusculas_media": 0.0, "signos_media": 0.0,
            "cierre": 0, "autocorreccion": 0, "caliente": 0, "repeticion": 0,
            "ultimas_repeticiones": []}


def leer_contador(carpeta_persona):
    # Si no hay contador o está estropeado, se empieza de cero.
    contador = _contador_vacio()
    try:
        guardado = json.loads((carpeta_persona / "observador" / "contador.json").read_text(encoding="utf-8"))
        contador.update({k: guardado[k] for k in contador if k in guardado})
    except (OSError, ValueError, TypeError):
        pass
    return contador


def _guardar_contador(carpeta_persona, contador):
    carpeta = carpeta_persona / "observador"
    carpeta.mkdir(exist_ok=True)
    (carpeta / "contador.json").write_text(json.dumps(contador, ensure_ascii=False, indent=1), encoding="utf-8")


def _sumar(contador, texto, senales, repite):
    # Añade este mensaje a la línea base: medias, veces de cada señal y las últimas repeticiones.
    n = contador["mensajes"]
    contador["mayusculas_media"] = (contador["mayusculas_media"] * n + _mayusculas(texto)) / (n + 1)
    contador["signos_media"] = (contador["signos_media"] * n + _signos(texto)) / (n + 1)
    contador["mensajes"] = n + 1
    for senal in senales:
        contador[senal] += 1
    contador["repeticion"] += repite
    contador["ultimas_repeticiones"] = (contador["ultimas_repeticiones"] + [int(repite)])[-VENTANA_PATRON:]


def _patron_repeticion(contador):
    # La repetición solo es patrón si ya se conoce a la persona, si ha salido VECES_PATRON veces
    # en los últimos mensajes y si sale al menos el doble de lo que es normal en ella.
    if contador["mensajes"] < MENSAJES_LINEA_BASE:
        return False
    ultimas = contador["ultimas_repeticiones"]
    veces = sum(ultimas)
    fuera = contador["mensajes"] - len(ultimas)
    normal = (contador["repeticion"] - veces) / fuera if fuera else 0.0
    return veces >= VECES_PATRON and veces / len(ultimas) >= 2 * normal


# ---------- Lo que usa el Núcleo ----------

def observar(carpeta_persona, texto, anteriores):
    # carpeta_persona: data/usuarios/<persona> (ya comprobada por el Núcleo).
    # anteriores: mensajes anteriores de la persona en esta misma conversación, del más antiguo al más nuevo.
    # Devuelve las señales que han saltado y la nota para el Interlocutor ("" si no hay).
    contador = leer_contador(carpeta_persona)
    senales = [s for s, salta in (("caliente", caliente(texto)),
                                  ("autocorreccion", autocorreccion(texto)),
                                  ("cierre", cierre(texto))) if salta]
    repite = repeticion(texto, anteriores)
    _sumar(contador, texto, senales, repite)
    if repite and _patron_repeticion(contador):
        senales.append("repeticion")
    _guardar_contador(carpeta_persona, contador)
    return senales, (NOTAS[senales[0]] if senales else "")


def _preparar_registro():
    if registro.handlers:
        return
    ARCHIVO_REGISTRO.parent.mkdir(exist_ok=True)
    manejador = logging.handlers.RotatingFileHandler(
        ARCHIVO_REGISTRO, maxBytes=TAMANO_REGISTRO, backupCount=COPIAS_REGISTRO, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%Y-%m-%d %H:%M:%S"))
    registro.addHandler(manejador)
    registro.setLevel(logging.INFO)


def anotar(nombre, senales, modo):
    # Una línea por mensaje: quién, qué señales y en qué modo. Nunca el texto.
    _preparar_registro()
    registro.info(f"{nombre}  {', '.join(senales) or '-'}  ({modo})")


def anotar_error(nombre, error):
    # Si el Observador falla, se apunta el tipo de error y la conversación sigue sin él.
    _preparar_registro()
    registro.info(f"{nombre}  ERROR del Observador: {type(error).__name__}")
