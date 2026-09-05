import asyncio, os
import edge_tts

CARPETA = r"D:\gta\files\muestras_voz\naturales"
FRASE = "Que onda vato, aqui esta tu mensaje del chat de Twitch"

# Sin tocar pitch ni rate, y SIN filtro de telefono: la voz tal cual sale
# del motor, para juzgar solo naturalidad.
VOCES = [
    "es-US-AlonsoNeural",
    "es-MX-JorgeNeural",
    "es-PR-VictorNeural",
    "es-DO-EmilioNeural",
    "es-VE-SebastianNeural",
    "es-CU-ManuelNeural",
    "es-AR-TomasNeural",
    "es-CO-GonzaloNeural",
    "es-CL-LorenzoNeural",
]

async def generar(voz, ruta):
    com = edge_tts.Communicate(text=FRASE, voice=voz)
    await com.save(ruta)

def main():
    os.makedirs(CARPETA, exist_ok=True)
    for voz in VOCES:
        ruta = os.path.join(CARPETA, voz + ".mp3")
        try:
            asyncio.run(generar(voz, ruta))
            print("OK", voz)
        except Exception as e:
            print("FALLO", voz, e)
    print()
    print("Carpeta:", CARPETA)
    os.startfile(CARPETA)

if __name__ == "__main__":
    main()
