# Pruebas del Observador: casos que deben saltar y casos que no.
# No usa IA ni toca los datos reales: todo pasa en una carpeta temporal que se borra al terminar.
# Se ejecuta con:  py interlocutor\pruebas_observador.py
# Resultado en pantalla y en logs/pruebas_observador_AAAA-MM-DD_HHMMSS.txt

import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA))
import observador

resultados = []


def comprobar(nombre, bien, detalle=""):
    resultados.append(("BIEN " if bien else "FALLO") + f"  {nombre}" + (f"  ({detalle})" if detalle else ""))


def persona_nueva(base, nombre):
    carpeta = base / nombre
    carpeta.mkdir()
    return carpeta


def conversar(carpeta, mensajes):
    # Manda los mensajes uno tras otro, como en una conversación; devuelve las señales de cada uno.
    anteriores, todas = [], []
    for texto in mensajes:
        senales, _nota = observador.observar(carpeta, texto, anteriores[-20:])
        todas.append(senales)
        anteriores.append(texto)
    return todas


VARIADOS = [f"mensaje normal número {n} sobre el cuadro {n} de la nave" for n in range(25)]
QUEJA = ["el horario del turno de noche no me cuadra con la entrega",
         "otra vez el horario del turno de noche no me cuadra con la entrega",
         "te lo vuelvo a decir, el horario del turno de noche no me cuadra con la entrega",
         "otra vez, el horario del turno de noche no me cuadra con la entrega"]


def main():
    base = Path(tempfile.mkdtemp(prefix="pruebas_observador_"))
    try:
        p = persona_nueva(base, "prueba")

        # Deben saltar
        comprobar("1 'eso, guárdalo' es cierre", observador.cierre("eso, guárdalo"))
        comprobar("2 'no, espera, mejor dicho' es autocorrección",
                  observador.autocorreccion("pon tres motores, no, espera, mejor dicho cuatro"))
        comprobar("3 mayúsculas y signos es caliente", observador.caliente("¡¡¡YA ESTÁ BIEN, ESTO NO FUNCIONA!!!"))

        con_historial = persona_nueva(base, "con_historial")
        senales = conversar(con_historial, VARIADOS + QUEJA)
        comprobar("4 con historial, la misma queja repetida es repetición",
                  "repeticion" in senales[-1], f"señales del último: {senales[-1]}")

        # No deben saltar
        comprobar("7 'eso no es lo que quiero' no es cierre", not observador.cierre("eso no es lo que quiero"))
        comprobar("8 'ya está otra vez fallando' no es cierre", not observador.cierre("ya está otra vez fallando"))
        comprobar("9 'el motor gira al revés' no es autocorrección", not observador.autocorreccion("el motor gira al revés"))
        comprobar("10 'joder, qué bien ha quedado' no es caliente", not observador.caliente("joder, qué bien ha quedado"))
        senales, _ = observador.observar(p, "estoy cansado del turno de noche", [])
        comprobar("11 'estoy cansado del turno de noche' no da señal", senales == [], str(senales))
        comprobar("12 afirmar y luego negar no es repetición",
                  not observador.repeticion("no quiero el motor grande en la entrada otra vez",
                                            ["quiero el motor grande en la entrada"]))
        comprobar("13 'sí, vale' no se compara", not observador.repeticion("sí, vale", ["sí, vale"]))

        nueva = persona_nueva(base, "nueva")
        senales = conversar(nueva, QUEJA)
        comprobar("14 persona nueva: sin nota de repetición aunque repita",
                  all("repeticion" not in s for s in senales), str(senales))

        # 15: quien repite siempre (es su forma de hablar) no da nota: no sale el doble de lo normal en ella.
        habitual = persona_nueva(base, "habitual")
        senales = conversar(habitual, QUEJA * 15)
        comprobar("15 quien repite por costumbre no da nota de repetición",
                  all("repeticion" not in s for s in senales[30:]), f"con nota: {sum('repeticion' in s for s in senales[30:])} de 30")
        resultados.append("PENDIENTE  16 corregir un apunte del cuaderno (llega con el cuaderno, Paso 2)")

        # Más casos de cierre que deben saltar
        for texto in ("perfecto", "ahora sí, guárdalo", "vale, eso", "exacto, eso es"):
            comprobar(f"cierre: '{texto}'", observador.cierre(texto))
        for texto in ("perfecto pero cambia el color", "eso es lo que hay que revisar mañana por la tarde",
                      "o sea, que el motor va bien"):
            comprobar(f"sin cierre ni autocorrección: '{texto}'",
                      not observador.cierre(texto) and not observador.autocorreccion(texto))

        # Contador: se guarda, solo lleva números y no lleva texto de nadie.
        archivo = con_historial / "observador" / "contador.json"
        contador = json.loads(archivo.read_text(encoding="utf-8"))
        comprobar("contador guardado con los mensajes contados", contador["mensajes"] == len(VARIADOS + QUEJA),
                  f"{contador['mensajes']} mensajes")
        comprobar("el contador no guarda texto", "horario" not in archivo.read_text(encoding="utf-8"))
        archivo.write_text("estropeado", encoding="utf-8")
        senales, _ = observador.observar(con_historial, "hola", [])
        comprobar("un contador estropeado no rompe nada (empieza de cero)",
                  observador.leer_contador(con_historial)["mensajes"] == 1)

        # Con el Núcleo, en una copia temporal y con el motor de mentira.
        import nucleo
        import motor_prueba
        usuarios = base / "usuarios"
        (usuarios / "ana" / "perfil").mkdir(parents=True)
        nucleo.CARPETA_USUARIOS = usuarios
        nucleo.motor = motor_prueba
        observador.ARCHIVO_REGISTRO = base / "observador.log"
        respuesta = nucleo.hablar("ana", "¡¡¡YA ESTÁ BIEN, ESTO NO FUNCIONA!!!")
        nucleo.hablar("ana", "vale, eso")
        registro = (base / "observador.log").read_text(encoding="utf-8")
        comprobar("Núcleo: contesta igual con el Observador en vigilancia", bool(respuesta) and not respuesta.startswith("Aviso"))
        comprobar("Núcleo: el registro apunta las señales", "ana  caliente  (vigilancia)" in registro and "ana  cierre  (vigilancia)" in registro)
        comprobar("Núcleo: el registro no guarda el texto", "FUNCIONA" not in registro and "vale" not in registro)
        hilo = next((usuarios / "ana" / "principal").glob("hilo_*.jsonl")).read_text(encoding="utf-8")
        comprobar("Núcleo: la conversación se guarda igual, sin notas", hilo.count("\n") == 2 and "Observador" not in hilo)

        observar_bueno = observador.observar
        def observar_roto(*_):
            raise ValueError("fallo de prueba")
        observador.observar = observar_roto
        respuesta = nucleo.hablar("ana", "otra cosa")
        observador.observar = observar_bueno
        comprobar("Núcleo: si el Observador falla, se contesta igual", not respuesta.startswith("Aviso"))
        comprobar("Núcleo: el fallo queda apuntado", "ERROR del Observador: ValueError" in (base / "observador.log").read_text(encoding="utf-8"))

        nucleo.OBSERVADOR = "apagado"
        antes = (base / "observador.log").read_text(encoding="utf-8")
        nucleo.hablar("ana", "perfecto")
        comprobar("Núcleo: apagado no apunta nada", (base / "observador.log").read_text(encoding="utf-8") == antes)
    finally:
        for manejador in list(observador.registro.handlers):
            manejador.close()
            observador.registro.removeHandler(manejador)
        shutil.rmtree(base, ignore_errors=True)

    bien = sum(r.startswith("BIEN") for r in resultados)
    fallos = sum(r.startswith("FALLO") for r in resultados)
    texto = "\n".join(resultados) + f"\n\n{bien} bien, {fallos} fallos.\n"
    print(texto)
    logs = CARPETA.parent / "logs"
    logs.mkdir(exist_ok=True)
    (logs / f"pruebas_observador_{datetime.now():%Y-%m-%d_%H%M%S}.txt").write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    main()
