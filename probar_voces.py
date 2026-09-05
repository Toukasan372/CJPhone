"""
Genera varias muestras de voz para comparar cual pega mas con el rollo
GTA San Andreas. No toca el mod, solo crea mp3 de prueba.

Uso:
    python probar_voces.py

Luego abre la carpeta y escuchalos. Dime cual te gusta (el numero o el
nombre) y dejo esa fija en tts_consola.py.
"""

import asyncio
import os
import subprocess

import edge_tts

CARPETA = r"D:\gta\files\muestras_voz"
FRASE = "Que onda vato, aqui esta tu mensaje del chat de Twitch"

# (nombre_archivo, voz, tono, velocidad)
CANDIDATOS = [
    ("1_alonso_actual",      "es-US-AlonsoNeural",   "-15Hz", "-5%"),
    ("2_alonso_mas_duro",    "es-US-AlonsoNeural",   "-30Hz", "-12%"),
    ("3_jorge_mexicano",     "es-MX-JorgeNeural",    "-15Hz", "-5%"),
    ("4_victor_puertorico",  "es-PR-VictorNeural",   "-10Hz", "+0%"),
    ("5_emilio_dominicano",  "es-DO-EmilioNeural",   "-10Hz", "+0%"),
    ("6_sebastian_venezuela","es-VE-SebastianNeural","-15Hz", "+0%"),
    ("7_manuel_cubano",      "es-CU-ManuelNeural",   "-10Hz", "-5%"),
    ("8_tomas_argentino",    "es-AR-TomasNeural",    "-10Hz", "+0%"),
    ("9_tomas_argentino_duro","es-AR-TomasNeural",   "-25Hz", "-8%"),
]


async def generar(texto, voz, tono, velocidad, ruta):
    com = edge_tts.Communicate(text=texto, voice=voz, rate=velocidad, pitch=tono)
    await com.save(ruta)


def efecto_telefono(ruta):
    tmp = ruta + ".tmp.mp3"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", ruta,
             "-af", "highpass=f=300,lowpass=f=3400,volume=2.5",
             "-codec:a", "libmp3lame", "-b:a", "96k", tmp],
            check=True, timeout=15,
        )
        os.replace(tmp, ruta)
    except Exception as e:
        print("  [!] sin efecto telefono en este:", e)


def main():
    os.makedirs(CARPETA, exist_ok=True)
    print("Generando", len(CANDIDATOS), "muestras en", CARPETA)
    print()

    for nombre, voz, tono, velocidad in CANDIDATOS:
        ruta = os.path.join(CARPETA, nombre + ".mp3")
        try:
            asyncio.run(generar(FRASE, voz, tono, velocidad, ruta))
            efecto_telefono(ruta)
            print("  OK  ", nombre, " (", voz, tono, velocidad, ")")
        except Exception as e:
            print("  FALLO", nombre, ":", e)

    print()
    print("Listo. Abre la carpeta y escuchalos:")
    print(" ", CARPETA)
    os.startfile(CARPETA)


if __name__ == "__main__":
    main()
