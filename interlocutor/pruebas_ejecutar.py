# Batería fija de pruebas del Interlocutor.
# Lee los casos de pruebas_bateria.json, los manda al motor de IA tal cual (con un perfil vacío,
# sin leer ni escribir ningún hilo) y comprueba cada respuesta con los criterios del caso.
# Guarda el resultado en logs/pruebas_interlocutor_AAAA-MM-DD_HHMMSS.json (completo) y .txt (para leer),
# junto con la versión probada (huellas de las instrucciones, del motor y de la batería, y el modelo),
# y lo compara con la ejecución anterior.
#
# Se ejecuta con:  py -B interlocutor\pruebas_ejecutar.py   (en Mac o Linux: python3 -B interlocutor/pruebas_ejecutar.py)

import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
RAIZ = CARPETA.parent
sys.path.insert(0, str(CARPETA))
import claves
import motor_openrouter as motor

BATERIA = CARPETA / "pruebas_bateria.json"
INSTRUCCIONES = CARPETA / "instrucciones.md"
CARPETA_RESULTADOS = RAIZ / "logs"
INTENTOS = 3  # la IA gratuita a veces no devuelve nada

INGLES_FRASES = ["i'm sorry", "i’m sorry", "i can't", "i can’t", "i cannot", "as an ai", "i am sorry"]
INGLES_PALABRAS = {"the", "and", "you", "to", "of", "is", "that", "it", "with", "for", "this", "are"}
MARCAS_CODIGO = [
    r"```", r"<html", r"<!doctype", r"<div", r"<body", r"<button", r"<script", r"<style",
    r"^\s*(import|from)\s+\w+", r"^\s*def\s+\w+\s*\(", r"print\(", r"function\s*\(",
    r"\{[^{}]*:[^{}]*;[^{}]*\}",
]


def normalizar(texto):
    # Minúsculas y sin tildes, para comparar palabras de forma estable.
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def huella(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def huellas_datos():
    base = RAIZ / "data" / "usuarios"
    return {str(p.relative_to(base)): huella(p) for p in base.rglob("*") if p.is_file()}


def evaluar(respuesta, criterios):
    # Devuelve la lista de comprobaciones [(nombre, se_cumple, detalle)] y las observaciones que no cuentan.
    t = normalizar(respuesta)
    palabras = re.findall(r"[a-z']+", t)
    comprobaciones = []

    ingles = [f for f in INGLES_FRASES if f in t]
    proporcion = sum(p in INGLES_PALABRAS for p in palabras) / max(len(palabras), 1)
    comprobaciones.append(("en_espanol", not ingles and proporcion < 0.10,
                           f"frases en inglés: {ingles or 'ninguna'}; palabras inglesas comunes: {proporcion:.0%}"))
    codigo = [m for m in MARCAS_CODIGO if re.search(m, respuesta, re.IGNORECASE | re.MULTILINE)]
    comprobaciones.append(("sin_codigo", not codigo, f"marcas de código: {codigo or 'ninguna'}"))

    if criterios.get("debe_preguntar"):
        comprobaciones.append(("debe_preguntar", "?" in respuesta, "lleva signo de pregunta" if "?" in respuesta else "no hace ninguna pregunta"))
    for i, grupo in enumerate(criterios.get("debe_contener_de_cada_grupo", []), 1):
        hallado = [p for p in grupo if p in t]
        comprobaciones.append((f"grupo_{i}", bool(hallado), f"encontrado: {hallado or 'nada'} (de {grupo})"))
    if criterios.get("debe_contener_alguno"):
        hallado = [p for p in criterios["debe_contener_alguno"] if p in t]
        comprobaciones.append(("debe_contener_alguno", bool(hallado), f"encontrado: {hallado or 'nada'}"))
    if criterios.get("no_debe_contener"):
        prohibido = [p for p in criterios["no_debe_contener"] if p in t]
        comprobaciones.append(("no_debe_contener", not prohibido, f"encontrado: {prohibido or 'nada'}"))

    observaciones = {"texto_plano": not ("**" in respuesta or "`" in respuesta)}
    return comprobaciones, observaciones


def preguntar_a_la_ia(caso):
    # Manda el caso al motor tal cual: nombre "prueba", perfil vacío y la memoria del caso.
    # Si la IA no contesta, devuelve el último aviso del motor (por ejemplo, demasiadas peticiones).
    for intento in range(1, INTENTOS + 1):
        respuesta = motor.responder("prueba", caso["mensaje"], "", caso.get("memoria", []))
        if not respuesta.startswith("Aviso:"):
            return respuesta, intento, None
    return None, INTENTOS, respuesta


def ejecucion_anterior(ahora):
    anteriores = sorted(p for p in CARPETA_RESULTADOS.glob("pruebas_interlocutor_*.json") if p.stem != ahora)
    if not anteriores:
        return None
    return json.loads(anteriores[-1].read_text(encoding="utf-8"))


def main():
    bateria = json.loads(BATERIA.read_text(encoding="utf-8"))
    marca = f"{datetime.now():%Y-%m-%d_%H%M%S}"
    nombre = f"pruebas_interlocutor_{marca}"
    datos_antes = huellas_datos()
    version = {
        "fecha": f"{datetime.now():%Y-%m-%d %H:%M:%S}",
        "modelo": claves.clave("IA_MODELO"),
        "instrucciones_sha256": huella(INSTRUCCIONES),
        "motor_sha256": huella(CARPETA / "motor_openrouter.py"),
        "bateria_sha256": huella(BATERIA),
        "version_bateria": bateria.get("version_bateria"),
        "repeticiones": bateria["repeticiones"],
        "instrucciones_texto": INSTRUCCIONES.read_text(encoding="utf-8"),
    }

    resultados = []
    for caso in bateria["casos"]:
        if not caso.get("listo"):
            resultados.append({"id": caso["id"], "estado": "pendiente", "motivo": "falta: " + caso.get("falta", "el texto del caso"), "ejecuciones": []})
            print(f"- {caso['id']}: PENDIENTE (falta el texto original)")
            continue
        ejecuciones = []
        for vez in range(1, bateria["repeticiones"] + 1):
            respuesta, intentos, aviso = preguntar_a_la_ia(caso)
            if respuesta is None:
                ejecuciones.append({"vez": vez, "resultado": "sin respuesta", "intentos": intentos, "aviso": aviso})
                print(f"- {caso['id']} (vez {vez}): sin respuesta de la IA ({aviso})")
                continue
            comprobaciones, observaciones = evaluar(respuesta, caso.get("criterios", {}))
            superada = all(c[1] for c in comprobaciones)
            ejecuciones.append({
                "vez": vez, "intentos": intentos, "resultado": "superada" if superada else "fallida",
                "respuesta": respuesta,
                "comprobaciones": [{"criterio": n, "cumple": ok, "detalle": d} for n, ok, d in comprobaciones],
                "observaciones": observaciones,
            })
            print(f"- {caso['id']} (vez {vez}): {'SUPERADA' if superada else 'FALLIDA'}")
        hechas = [e for e in ejecuciones if e["resultado"] in ("superada", "fallida")]
        if not hechas:
            estado, motivo = "pendiente", "la IA no respondió en ninguna ejecución"
        elif any(e["resultado"] == "fallida" for e in hechas):
            estado, motivo = "fallido", f"{sum(e['resultado'] == 'fallida' for e in hechas)} de {len(hechas)} ejecuciones fallidas"
        else:
            estado, motivo = "superado", f"{len(hechas)} de {len(hechas)} ejecuciones superadas"
        resultados.append({"id": caso["id"], "estado": estado, "motivo": motivo, "esperado": caso["esperado"], "mensaje": caso["mensaje"], "ejecuciones": ejecuciones})

    resumen = {
        "casos": len(resultados),
        "ejecutados": sum(r["estado"] in ("superado", "fallido") for r in resultados),
        "superados": sum(r["estado"] == "superado" for r in resultados),
        "fallidos": sum(r["estado"] == "fallido" for r in resultados),
        "pendientes": sum(r["estado"] == "pendiente" for r in resultados),
    }
    datos_intactos = huellas_datos() == datos_antes
    salida = {"version": version, "resumen": resumen, "datos_de_personas_sin_cambios": datos_intactos, "resultados": resultados}

    # Comparación con la ejecución anterior.
    anterior = ejecucion_anterior(nombre)
    comparacion = []
    if anterior:
        antes = {r["id"]: r["estado"] for r in anterior["resultados"]}
        comparacion.append(f"Comparado con la ejecución del {anterior['version']['fecha']} "
                           f"(instrucciones {'IGUALES' if anterior['version']['instrucciones_sha256'] == version['instrucciones_sha256'] else 'DISTINTAS'}, "
                           f"modelo {'igual' if anterior['version']['modelo'] == version['modelo'] else 'distinto'}, "
                           f"batería {'igual' if anterior['version']['bateria_sha256'] == version['bateria_sha256'] else 'DISTINTA: v' + str(anterior['version'].get('version_bateria')) + ' -> v' + str(version['version_bateria'])}):")
        for r in resultados:
            previo = antes.get(r["id"], "no existía")
            marca_cambio = "" if previo == r["estado"] else "   <-- CAMBIA"
            comparacion.append(f"  {r['id']}: {previo} -> {r['estado']}{marca_cambio}")
    else:
        comparacion.append("No hay ninguna ejecución anterior con la que comparar.")
    salida["comparacion"] = comparacion

    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    (CARPETA_RESULTADOS / f"{nombre}.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")

    # Versión para leer.
    lineas = [f"Batería de pruebas del Interlocutor — {version['fecha']}",
              f"Modelo: {version['modelo']}",
              f"Instrucciones: huella {version['instrucciones_sha256'][:12]}  |  Motor: {version['motor_sha256'][:12]}  |  Batería: v{version['version_bateria']} {version['bateria_sha256'][:12]}",
              f"Repeticiones por caso: {version['repeticiones']}",
              f"Resumen: {resumen['casos']} casos, {resumen['ejecutados']} ejecutados, {resumen['superados']} superados, {resumen['fallidos']} fallidos, {resumen['pendientes']} pendientes",
              f"Datos de las personas sin cambios: {'sí' if datos_intactos else 'NO'}", ""]
    for r in resultados:
        lineas.append(f"[{r['estado'].upper()}] {r['id']} — {r['motivo']}")
        if r["estado"] == "pendiente" and not r["ejecuciones"]:
            lineas.append("")
            continue
        lineas.append(f"  Esperado: {r['esperado']}")
        for e in r["ejecuciones"]:
            if e["resultado"] == "sin respuesta":
                lineas.append(f"  Vez {e['vez']}: sin respuesta de la IA — {e.get('aviso') or 'sin aviso'}")
                continue
            lineas.append(f"  Vez {e['vez']}: {e['resultado'].upper()}" + ("" if e["observaciones"]["texto_plano"] else "  (observación: trae ** o `)"))
            lineas.append("    Respuesta: " + e["respuesta"].replace("\n", " "))
            for c in e["comprobaciones"]:
                lineas.append(f"    {'ok ' if c['cumple'] else 'NO '} {c['criterio']}: {c['detalle']}")
        lineas.append("")
    lineas += comparacion
    (CARPETA_RESULTADOS / f"{nombre}.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    print()
    print(lineas[4])
    print("\n".join(comparacion))
    print(f"Resultados guardados en logs\\{nombre}.json y .txt")


if __name__ == "__main__":
    main()
