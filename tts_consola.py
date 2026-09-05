"""
TTS de prueba para el mod del movil de GTA:SA. Escribes tu por consola,
no se conecta a Twitch (para eso esta twitch_bot.py).

Instalacion:
    pip install edge-tts

Uso:
    python tts_consola.py
    > Pepito: hola CJ

Formato de entrada:
    "autor: mensaje"   -> se lee "hola CJ" (el autor solo sale en pantalla)
    "mensaje"          -> se lee tal cual, autor = "Anonimo"

Solo se procesan mensajes que mencionen "cj" (ver PALABRA_CLAVE en
tts_common.py). Si escribes algo sin "cj" se descarta, para probar el
filtro tal cual funcionara en produccion.

Comandos:
    /salir      cierra el programa
    /limpiar    borra la cola pendiente y reinicia el contador
"""

import sys

import tts_common as tts


def separar_autor(linea):
    """'Pepito: hola' -> ('Pepito', 'hola'). Sin dos puntos -> 'Anonimo'."""
    if ":" in linea:
        autor, _, mensaje = linea.partition(":")
        autor = autor.strip()
        mensaje = mensaje.strip()
        if autor and mensaje and len(autor) <= 25:
            return autor, mensaje
    return "Anonimo", linea.strip()


def main():
    tts.preparar_carpeta()

    print("=" * 55)
    print(" TTS movil GTA:SA  |  modo consola (sin Twitch)")
    print(" Carpeta:", tts.CARPETA)
    print(" Voz:", tts.VOZ)
    print(" Escribe 'autor: mensaje'  |  /salir para cerrar")
    print("=" * 55)

    while True:
        try:
            linea = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCerrando.")
            break

        if not linea:
            continue

        if linea.lower() in ("/salir", "/exit", "/quit"):
            print("Cerrando.")
            break

        if linea.lower() == "/limpiar":
            tts.preparar_carpeta()
            print("  -> cola vaciada")
            continue

        autor, mensaje = separar_autor(linea)
        mensaje = tts.limpiar_texto(mensaje)

        if mensaje is None:
            print("  [x] mensaje descartado por el filtro")
            continue

        if not tts.menciona_palabra_clave(mensaje):
            print("  [x] descartado: no menciona 'cj'")
            continue

        tts.encolar(autor, mensaje)


if __name__ == "__main__":
    if sys.version_info < (3, 7):
        sys.exit("Necesitas Python 3.7 o superior.")
    main()
