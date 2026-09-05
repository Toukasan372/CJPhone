"""
Logica compartida entre tts_consola.py (modo prueba manual), twitch_bot.py
(produccion) y panel_control.py (interfaz grafica de configuracion).

No se ejecuta directamente, solo se importa.

CONFIGURACION: se lee de config.json (misma carpeta). Si no existe, se crea
con valores por defecto la primera vez. El panel_control.py edita ese JSON;
esta lista de constantes se recarga cada vez que arranca tts_consola.py o
twitch_bot.py (los cambios se aplican en el SIGUIENTE arranque, no en
caliente mientras ya esta corriendo).

DISEÑO DE LA COLA (importante si tocas esto):
En vez de nombres numerados (msg_0000, msg_0001...) que obligaban a que
Python y CLEO llevaran la cuenta exactamente sincronizada -y se rompia en
cuanto se reiniciaba solo uno de los dos-, se usa un UNICO par de archivos
de nombre fijo: current.mp3 / current.txt.

Protocolo:
  1. Python espera a que NO existan current.mp3/current.txt (o sea, que
     CLEO ya termino de leer el mensaje anterior y los borro).
  2. Python genera el audio y lo escribe con nombre temporal, y solo al
     final lo renombra a current.mp3/current.txt (escritura atomica).
  3. CLEO ve current.txt + current.mp3, procesa la llamada, y al terminar
     BORRA los dos archivos. Eso es la señal de "listo para el siguiente".
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

import edge_tts

# ---------------------------------------------------------------------------
# RUTAS: funcionan igual en modo script que congelado en .exe (PyInstaller)
# ---------------------------------------------------------------------------

def recurso_bundle(rel_path):
    """Ruta a un archivo empaquetado DENTRO del .exe (solo lectura). En modo
    script normal, es la carpeta payload/ junto a este archivo."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel_path)


def _carpeta_datos_app():
    """Carpeta persistente y con permiso de escritura para config.json y
    para las copias de herramientas (ffmpeg). No depende de donde este
    instalado el .exe (puede estar en Program Files, de solo lectura)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    carpeta = os.path.join(base, "CJPhone")
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


_DIR_SCRIPT = os.path.dirname(os.path.abspath(__file__))
RUTA_CONFIG = os.path.join(_carpeta_datos_app(), "config.json")

VALORES_POR_DEFECTO = {
    "instalado": False,          # lo pone True el asistente tras copiar CLEO
    "carpeta_juego_raiz": "",    # carpeta del gta_sa.exe elegido en el asistente
    "carpeta_juego": "",         # ...\CLEO\twitch dentro de esa carpeta
    "ffmpeg_path": "",           # ruta al ffmpeg propio copiado por el instalador
    "canal_twitch": "",
    "palabra_clave": "cj",
    "voz": "es-CU-ManuelNeural",
    "velocidad": "+0%",
    "tono": "+0Hz",
    "usar_efecto_telefono": True,
    "filtro_telefono": "highpass=f=250,lowpass=f=3800,volume=1.8",
    "max_caracteres": 150,
    "cooldown_segundos": 15,
    "espera_maxima_segundos": 40,
    "blacklist": [],
}


def cargar_config():
    """Lee config.json. Si no existe o le faltan claves, las rellena con
    los valores por defecto y lo reescribe (asi el panel siempre encuentra
    todas las claves, aunque se haya actualizado el mod despues)."""
    datos = dict(VALORES_POR_DEFECTO)
    if os.path.exists(RUTA_CONFIG):
        try:
            with open(RUTA_CONFIG, "r", encoding="utf-8") as f:
                guardado = json.load(f)
            datos.update(guardado)
        except (json.JSONDecodeError, OSError):
            pass
    guardar_config(datos)
    return datos


def guardar_config(datos):
    with open(RUTA_CONFIG, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)


_cfg = cargar_config()

INSTALADO = _cfg["instalado"]
CARPETA = _cfg["carpeta_juego"]
FFMPEG_PATH = _cfg["ffmpeg_path"] or "ffmpeg"   # si no hay ruta propia, prueba el PATH del sistema
CANAL_TWITCH = _cfg["canal_twitch"]
PALABRA_CLAVE = _cfg["palabra_clave"] or None
VOZ = _cfg["voz"]
VELOCIDAD = _cfg["velocidad"]
TONO = _cfg["tono"]
USAR_EFECTO_TELEFONO = _cfg["usar_efecto_telefono"]
FILTRO_TELEFONO = _cfg["filtro_telefono"]
MAX_CARACTERES = _cfg["max_caracteres"]
COOLDOWN_SEGUNDOS = _cfg["cooldown_segundos"]
ESPERA_MAXIMA_SEGUNDOS = _cfg["espera_maxima_segundos"]
BLACKLIST = set(p.lower() for p in _cfg["blacklist"])

RUTA_MP3 = os.path.join(CARPETA, "current.mp3") if CARPETA else ""
RUTA_TXT = os.path.join(CARPETA, "current.txt") if CARPETA else ""


def recargar_config():
    """Vuelve a leer config.json y actualiza las variables del modulo.
    Hace falta llamarla justo despues del asistente de instalacion, porque
    CARPETA (y por tanto RUTA_MP3/RUTA_TXT) esta vacia hasta que el usuario
    elige la carpeta del juego por primera vez."""
    global INSTALADO, CARPETA, FFMPEG_PATH, CANAL_TWITCH, PALABRA_CLAVE
    global VOZ, VELOCIDAD, TONO, USAR_EFECTO_TELEFONO, FILTRO_TELEFONO
    global MAX_CARACTERES, COOLDOWN_SEGUNDOS, ESPERA_MAXIMA_SEGUNDOS
    global BLACKLIST, RUTA_MP3, RUTA_TXT

    cfg = cargar_config()
    INSTALADO = cfg["instalado"]
    CARPETA = cfg["carpeta_juego"]
    FFMPEG_PATH = cfg["ffmpeg_path"] or "ffmpeg"
    CANAL_TWITCH = cfg["canal_twitch"]
    PALABRA_CLAVE = cfg["palabra_clave"] or None
    VOZ = cfg["voz"]
    VELOCIDAD = cfg["velocidad"]
    TONO = cfg["tono"]
    USAR_EFECTO_TELEFONO = cfg["usar_efecto_telefono"]
    FILTRO_TELEFONO = cfg["filtro_telefono"]
    MAX_CARACTERES = cfg["max_caracteres"]
    COOLDOWN_SEGUNDOS = cfg["cooldown_segundos"]
    ESPERA_MAXIMA_SEGUNDOS = cfg["espera_maxima_segundos"]
    BLACKLIST = set(p.lower() for p in cfg["blacklist"])
    RUTA_MP3 = os.path.join(CARPETA, "current.mp3") if CARPETA else ""
    RUTA_TXT = os.path.join(CARPETA, "current.txt") if CARPETA else ""

_ultimo_envio = {}  # autor (minuscula) -> timestamp del ultimo mensaje enviado


def preparar_carpeta():
    """Borra cualquier mensaje pendiente de una sesion anterior (incluidos
    restos .tmp), sin tocar ring.mp3 ni nada mas."""
    os.makedirs(CARPETA, exist_ok=True)
    for nombre in ("current.mp3", "current.txt",
                   "current.mp3.tmp", "current.txt.tmp"):
        ruta = os.path.join(CARPETA, nombre)
        if os.path.exists(ruta):
            try:
                os.remove(ruta)
            except OSError:
                pass
    for nombre in os.listdir(CARPETA):
        if nombre.startswith("msg_"):
            try:
                os.remove(os.path.join(CARPETA, nombre))
            except OSError:
                pass


def limpiar_texto(texto):
    """Filtra lo que no queremos que el TTS lea en voz alta. Devuelve None
    si el mensaje debe descartarse por completo."""
    texto = texto.strip()

    texto = re.sub(r"https?://\S+|www\.\S+", "", texto)          # URLs fuera
    texto = re.sub(r"(.)\1{3,}", r"\1\1\1", texto)                # aaaaa -> aaa
    texto = re.sub(r"\s+", " ", texto).strip()                     # espacios

    if not texto:
        return None
    if any(p in texto.lower() for p in BLACKLIST):
        return None

    return texto[:MAX_CARACTERES]


def en_cooldown(autor):
    """True si este autor escribio hace muy poco y hay que ignorarlo."""
    clave = autor.lower()
    ahora = time.time()
    ultimo = _ultimo_envio.get(clave, 0)
    if ahora - ultimo < COOLDOWN_SEGUNDOS:
        return True
    _ultimo_envio[clave] = ahora
    return False


def menciona_palabra_clave(texto):
    """True si el mensaje menciona PALABRA_CLAVE (o si el filtro esta
    desactivado con PALABRA_CLAVE vacia). Coincide como palabra suelta."""
    if not PALABRA_CLAVE:
        return True
    patron = r"\b" + re.escape(PALABRA_CLAVE) + r"\b"
    return re.search(patron, texto, re.IGNORECASE) is not None


def _esperar_hueco_libre(silencioso):
    inicio = time.time()
    while os.path.exists(RUTA_TXT) or os.path.exists(RUTA_MP3):
        if time.time() - inicio > ESPERA_MAXIMA_SEGUNDOS:
            if not silencioso:
                print("  [!] CLEO no responde, se sobreescribe el mensaje anterior")
            break
        time.sleep(0.3)


async def _generar_audio(texto, ruta_mp3):
    comunicador = edge_tts.Communicate(
        text=texto, voice=VOZ, rate=VELOCIDAD, pitch=TONO,
    )
    await comunicador.save(ruta_mp3)


def _aplicar_efecto_telefono(ruta_mp3):
    if not USAR_EFECTO_TELEFONO:
        return
    temporal = ruta_mp3 + ".efecto.mp3"
    try:
        subprocess.run(
            [
                FFMPEG_PATH, "-y", "-loglevel", "error",
                "-i", ruta_mp3,
                "-af", FILTRO_TELEFONO,
                "-codec:a", "libmp3lame", "-b:a", "96k",
                temporal,
            ],
            check=True,
            timeout=15,
        )
        os.replace(temporal, ruta_mp3)
    except Exception as e:
        print("  [!] No se pudo aplicar el efecto de telefono:", e)
        if os.path.exists(temporal):
            os.remove(temporal)


def plano(s):
    """Quita acentos: el juego no los muestra bien en pantalla."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.encode("ascii", "ignore").decode("ascii")


def encolar(autor, mensaje, silencioso=False):
    """Genera el mp3 y el txt de UN mensaje y espera su turno si CLEO
    todavia esta ocupado con el anterior. Devuelve True si se envio.

    La voz SOLO dice el mensaje, nunca el nombre del autor."""
    texto_hablado = mensaje

    tmp_mp3 = RUTA_MP3 + ".tmp"
    tmp_txt = RUTA_TXT + ".tmp"

    try:
        asyncio.run(_generar_audio(texto_hablado, tmp_mp3))
        _aplicar_efecto_telefono(tmp_mp3)
    except Exception as e:
        if not silencioso:
            print("  [!] Fallo el TTS:", e)
        if os.path.exists(tmp_mp3):
            os.remove(tmp_mp3)
        return False

    with open(tmp_txt, "w", encoding="ascii", errors="ignore", newline="\n") as f:
        f.write(plano(autor) + "\n")
        f.write(plano(mensaje) + "\n")

    _esperar_hueco_libre(silencioso)

    os.replace(tmp_mp3, RUTA_MP3)
    os.replace(tmp_txt, RUTA_TXT)

    if not silencioso:
        print("  -> enviado ({}: {})".format(autor, mensaje))
    return True
