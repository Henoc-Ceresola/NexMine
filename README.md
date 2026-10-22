<p align="center"><img src="portada.jpg" alt="NexMine" width="480"></p>

# NexMine

**An "Interlocutor" between a person and AI.**

NexMine is an AI assistant. Its job is to understand **exactly** what you want — no more, no less — and turn it into a **clear, well-organized text**. Then **you** take that text to whatever tool you choose.

> *"The Interlocutor doesn't learn projects. It learns intention."*

**The problem:** AI often doesn't respect the exact scope of what you ask: it either goes too far or falls short.

**What exists today:** **NexUs**, the first public version of the Interlocutor. You talk to it from the terminal (console). It remembers each person's conversation, only on your own computer.

**In the future:** it is designed to work alongside other AI tools.

**Status:** 🚧 Early stage. First public version (console only). License: [MIT](LICENSE).

## How to try it

1. **You need:** Python 3.10 or newer. Nothing else to install.
2. **Download** this project (green **Code** button → **Download ZIP**, or `git clone`).
3. **Your key:** copy `config/CLAVES.ejemplo.txt` as `config/CLAVES.txt` and paste your own OpenRouter key after `IA_CLAVE=` (free at [openrouter.ai/keys](https://openrouter.ai/keys)). A free model is already set. If it stops working, choose another one ending in `:free`.
4. **Talk to NexUs**, from the project folder:
   - Windows: `py interlocutor/puertas/consola.py your_name`
   - Mac or Linux: `python3 interlocutor/puertas/consola.py your_name`

   The first time, it asks if it can create your folder (s/n = yes/no). Inside: `/nueva` starts a new conversation; `/salir` exits.
5. **Test its behavior** (uses your key; takes a few minutes):
   - NexUs test set: `py -B interlocutor/pruebas_ejecutar.py` → results in `logs/`
   - Observer (no AI, no key): `py -B interlocutor/pruebas_observador.py`

Your conversations stay only on your computer (`data/usuarios/your_name/`). Your key, your conversations and the logs are never uploaded (`.gitignore`).

**Good to know:**
- The free model is sometimes slow or says "too many requests". That is not a bug in NexUs.
- The AI follows the rules almost always, but not always. That is why the test set exists: sharing your results (without personal data) is a great way to help.

## How to take part

- 💡 Ideas and questions → [Discussions](../../discussions)
- 🐞 Bugs you find → [Issues](../../issues)

English and Spanish are both welcome.

> ⚠️ **Important:** never post passwords, keys or personal data in this project.

---

# NexMine (Español)

**Un "Interlocutor" entre una persona y la IA.**

NexMine es un asistente de IA. Su trabajo es entender **exactamente** lo que quieres, ni más ni menos, y dejarlo **ordenado en un texto claro**. Después, **tú** llevas ese texto a la herramienta que quieras.

> *"El Interlocutor no aprende proyectos. Aprende intención."*

**El problema:** la IA muchas veces no respeta lo que le pides exactamente: o se pasa, o se queda corta.

**Qué existe hoy:** **NexUs**, la primera versión pública del Interlocutor. Se habla con él desde la terminal (consola). Recuerda la conversación de cada persona, solo en tu propio ordenador.

**En el futuro:** está pensado para trabajar junto a otras herramientas de IA.

**Estado:** 🚧 Está empezando. Primera versión pública (solo consola). Licencia: [MIT](LICENSE).

## Cómo probarlo

1. **Necesitas:** Python 3.10 o más nuevo. No hay que instalar nada más.
2. **Descarga** este proyecto (botón verde **Code** → **Download ZIP**, o `git clone`).
3. **Tu clave:** copia `config/CLAVES.ejemplo.txt` como `config/CLAVES.txt` y pon tu propia clave de OpenRouter después de `IA_CLAVE=` (gratis en [openrouter.ai/keys](https://openrouter.ai/keys)). Ya viene puesto un modelo gratuito. Si deja de funcionar, elige otro que termine en `:free`.
4. **Habla con NexUs**, desde la carpeta del proyecto:
   - Windows: `py interlocutor/puertas/consola.py tu_nombre`
   - Mac o Linux: `python3 interlocutor/puertas/consola.py tu_nombre`

   La primera vez pregunta si crea tu carpeta (s/n). Dentro: `/nueva` empieza una conversación nueva; `/salir` termina.
5. **Prueba su comportamiento** (usa tu clave; tarda unos minutos):
   - Batería de NexUs: `py -B interlocutor/pruebas_ejecutar.py` → resultados en `logs/`
   - Observador (sin IA ni clave): `py -B interlocutor/pruebas_observador.py`

Tus conversaciones se quedan solo en tu ordenador (`data/usuarios/tu_nombre/`). Tu clave, tus conversaciones y los registros nunca se suben (`.gitignore`).

**Bueno saber:**
- El modelo gratuito a veces tarda o dice "demasiadas peticiones". No es un fallo de NexUs.
- La IA cumple las reglas casi siempre, pero no siempre. Por eso existe la batería: compartir tus resultados (sin datos personales) es una gran forma de ayudar.

## Cómo participar

- 💡 Ideas y preguntas → [Discussions](../../discussions) (Conversaciones)
- 🐞 Fallos que encuentres → [Issues](../../issues) (Avisos)

Se puede escribir en inglés o en español.

> ⚠️ **Importante:** nunca escribas contraseñas, claves ni datos personales en este proyecto.
