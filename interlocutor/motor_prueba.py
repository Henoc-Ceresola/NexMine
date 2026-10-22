# Motor de prueba: una IA de mentira.
# Sirve para probar el Núcleo sin conectar todavía una IA de verdad.
# Para cambiarlo por una IA real, basta con crear otro motor
# que tenga la misma función "responder" con las mismas entradas.


def responder(nombre, texto, perfil, memoria=None):
    # No piensa nada: solo repite lo que le llega, para comprobar que llega bien.
    return f"Motor de prueba. Has dicho: {texto}. Perfil de {nombre} leído."
