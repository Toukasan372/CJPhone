<div align="center">

**🇪🇸 Español** | [🇬🇧 English](README.en.md)

# 📱 CJ Phone — Twitch al móvil de CJ

### Lee el chat de Twitch en voz alta, dentro de GTA San Andreas, como si te llamaran al teléfono.

</div>

---

<div align="center">

## ⬇️⬇️ DESCARGAR EL INSTALADOR ⬇️⬇️

### Un solo `.exe`. No necesitas Python, ni CLEO, ni ffmpeg instalados: todo va dentro.

<br>

[![Descargar CJPhone.exe](https://img.shields.io/badge/DESCARGAR-CJPhone.exe-8B5CF6?style=for-the-badge&logo=windows&logoColor=white&labelColor=111120)](../../releases/latest/download/CJPhone.exe)

<br>

**[👉 Ir a la última versión en Releases](../../releases/latest)**

| | |
|---|---|
| 🖥️ Plataforma | Windows 10 / 11 (64-bit) |
| 📦 Peso aproximado | ~85 MB |
| 🧩 Requiere | GTA San Andreas (versión 1.0, la clásica de disco/Steam antiguo) |
| 🐍 Requiere Python | **No** — todo está empaquetado dentro del .exe |

</div>

---

## 📖 Índice

1. [¿Qué es esto?](#-qué-es-esto)
2. [Tutorial de instalación (paso a paso)](#-tutorial-de-instalación-paso-a-paso)
3. [Cómo usarlo en directo](#-cómo-usarlo-en-directo)
4. [Voces disponibles](#-voces-disponibles)
5. [Cómo funciona por dentro](#-cómo-funciona-por-dentro)
6. [Ejecutar desde el código fuente](#-ejecutar-desde-el-código-fuente-para-desarrolladores)
7. [Compilar tu propio .exe](#-compilar-tu-propio-exe)
8. [Estructura del repositorio](#-estructura-del-repositorio)
9. [Créditos y licencias de terceros](#-créditos-y-licencias-de-terceros)
10. [Aviso legal](#-aviso-legal)

---

## 🎮 ¿Qué es esto?

**CJ Phone** es un mod para GTA San Andreas pensado para streamers: conecta el
chat de tu canal de Twitch con el juego para que, cuando alguien escriba un
mensaje (por ejemplo mencionando la palabra clave `cj`), **suene el teléfono
de CJ** y al contestar se escuche el mensaje leído en voz alta con una voz
latina realista, con un filtro de "voz de teléfono" de fondo.

Todo el proyecto son **tres piezas que se hablan entre sí**, y las tres están
en este repo:

- 🖥️ **La app `CJPhone.exe`** — instalador + panel de control + bot de
  Twitch, todo en un único programa de escritorio.
- 🤖 **El bot de Twitch** (corre dentro de la misma app) — se conecta al
  chat en modo solo lectura, sin necesidad de cuenta ni token.
- 🎮 **El script de CLEO** dentro del juego — detecta el mensaje nuevo y usa
  la función real de llamadas de misión para que CJ conteste el móvil.

---

## 🚀 Tutorial de instalación (paso a paso)

> ⚠️ Necesitas tener **GTA San Andreas ya instalado** en tu PC (la carpeta
> donde está `gta_sa.exe`). El mod no incluye el juego.

### 1. Descarga el instalador

Usa el botón grande de arriba, o entra a la
**[página de Releases](../../releases/latest)** y descarga `CJPhone.exe`.

### 2. Ejecuta `CJPhone.exe`

Al abrirlo por primera vez es normal que **Windows SmartScreen** o tu
antivirus muestren una advertencia porque el .exe no está firmado
digitalmente (una firma de código cuesta dinero y este es un proyecto
gratuito de la comunidad). Dale a **"Más información" → "Ejecutar de
todas formas"**.

### 3. Elige la carpeta de tu GTA San Andreas

La primera vez que abres la app te pedirá seleccionar la carpeta donde
está `gta_sa.exe`. Por ejemplo:

```
C:\Program Files (x86)\Rockstar Games\GTA San Andreas
D:\Games\GTA San Andreas
```

### 4. Deja que el instalador copie todo

Con un clic, la app copia automáticamente en esa carpeta:

- `CLEO.asi` + `cleo_redux.asi` + `bass.dll` (el runtime de CLEO 5 / CLEO Redux)
- El "ASI Loader" (`vorbisFile.dll`), si tu instalación todavía no tiene uno
- Los plugins de CLEO Redux (`CLEO\CLEO_PLUGINS\`)
- El script del mod (`CLEO\twitch\`) y el tono de llamada
- `ffmpeg.exe` (se copia aparte, en tu carpeta de datos de usuario, no
  dentro del juego)

No tienes que copiar ni descomprimir nada a mano.

### 5. Configura el panel

Una vez instalado, la misma ventana pasa a ser el **panel de control**:

- **Canal de Twitch** al que te vas a conectar (el tuyo, o el que quieras escuchar)
- **Palabra clave** que debe llevar el mensaje para que se lea (por defecto `cj`; puedes dejarla vacía para leer todo el chat)
- **Voz** (elige entre 10 acentos latinos, ver [tabla de abajo](#-voces-disponibles))
- **Cooldown** por usuario, para que nadie sature el chat
- **Lista negra** de palabras que nunca se leerán en voz alta

### 6. Dale a "Iniciar"

Arranca el juego y entra a una partida. Con el panel corriendo y el bot
"Conectado", cualquier mensaje del chat que cumpla las reglas hará sonar
el teléfono de CJ dentro del juego.

✅ **Listo.** Cierra y vuelve a abrir `CJPhone.exe` cuando quieras: como ya
quedó instalado, la próxima vez abre directo en el panel, sin pasar por el
asistente.

---

## 🎬 Cómo usarlo en directo

1. Abre GTA San Andreas y `CJPhone.exe` (por separado, uno no depende del otro para arrancar).
2. En la app, confirma el canal de Twitch y pulsa **Iniciar**.
3. Juega con normalidad. Cuando alguien escriba `cj <mensaje>` en tu chat de Twitch, sonará el timbre del móvil en el juego.
4. Contesta la llamada en el juego (como cualquier llamada de misión) y se reproducirá el mensaje con la voz elegida.

---

## 🗣️ Voces disponibles

| Acento | Voz |
|---|---|
| 🇨🇺 Cubano | Manuel |
| 🇺🇸 Latino EEUU | Alonso |
| 🇲🇽 Mexicano | Jorge |
| 🇵🇷 Puertorriqueño | Victor |
| 🇩🇴 Dominicano | Emilio |
| 🇻🇪 Venezolano | Sebastian |
| 🇦🇷 Argentino | Tomas |
| 🇨🇴 Colombiano | Gonzalo |
| 🇨🇱 Chileno | Lorenzo |
| 🇪🇸 España | Alvaro |

Hay muestras de audio de varias de estas voces en [`muestras_voz/`](muestras_voz).

---

## ⚙️ Cómo funciona por dentro

```
Chat de Twitch (IRC, modo anónimo)
        │
        ▼
twitch_bot.py  →  filtra por palabra clave / cooldown / blacklist
        │
        ▼
tts_common.py  →  genera audio con edge-tts + filtro "voz de teléfono" con ffmpeg
        │           escribe current.mp3 + current.txt en ...\CLEO\twitch\
        ▼
payload/twitch_movil.js (CLEO Redux, dentro del juego)
        │  vigila esa carpeta, hace sonar el móvil y usa Task.UseMobilePhone
        ▼
   CJ contesta el teléfono y se escucha el mensaje
```

El protocolo entre Python y CLEO es deliberadamente simple: un único par de
archivos de nombre fijo (`current.mp3` / `current.txt`). Python espera a que
no existan (CLEO ya terminó de leer el anterior y los borró), genera el
audio con nombre temporal y lo renombra de forma atómica. CLEO ve ambos
archivos, reproduce la llamada, y al terminar los borra: esa es la señal de
"listo para el siguiente mensaje".

---

## 🐍 Ejecutar desde el código fuente (para desarrolladores)

Si prefieres correr los scripts de Python en vez del `.exe`:

```bash
git clone https://github.com/Toukasan372/CJPhone.git
cd CJPhone
pip install -r requirements.txt
```

`ffmpeg.exe` **no** viene incluido en el repo (pesa ~99 MB). Descárgalo de
[ffmpeg.org](https://ffmpeg.org/download.html) (build "essentials" para
Windows) y colócalo en:

```
payload/tools/ffmpeg.exe
```

Luego:

```bash
python cjphone_app.py       # app completa (instalador + panel + bot)
python panel_control.py     # panel alternativo, sin el asistente de instalación
python twitch_bot.py <canal>  # solo el bot, por consola
python probar_voces.py      # genera muestras de las distintas voces/tonos
```

---

## 🛠️ Compilar tu propio `.exe`

El `.exe` de Releases se genera con [PyInstaller](https://pyinstaller.org/)
usando el spec incluido en el repo ([`CJPhone.spec`](CJPhone.spec)):

```bash
pip install -r requirements.txt
pyinstaller CJPhone.spec
```

El resultado queda en `dist/CJPhone.exe`. El spec ya empaqueta la carpeta
`payload/` completa (incluido `ffmpeg.exe`, que debes haber colocado ahí
primero) dentro del ejecutable final.

---

## 📁 Estructura del repositorio

```
CJPhone/
├── cjphone_app.py          # App final: instalador + panel + bot (esto se compila a CJPhone.exe)
├── panel_control.py        # Panel de control alternativo (sin asistente de instalación)
├── twitch_bot.py           # Motor del bot de Twitch, reutilizable
├── tts_common.py           # Lógica compartida: config, TTS, cola de mensajes con CLEO
├── tts_consola.py          # Modo de prueba manual por consola
├── probar_voces.py         # Generador de muestras para comparar voces
├── probar_voces_naturales.py
├── config.json             # Configuración de ejemplo
├── CJPhone.spec            # Receta de PyInstaller para generar el .exe
├── requirements.txt
├── muestras_voz/           # Muestras .mp3 de las distintas voces
└── payload/                # Todo lo que el instalador copia dentro del juego
    ├── root/                # CLEO.asi, cleo_redux.asi, bass.dll, ASI loader
    ├── cleo_config/         # cleo.ini, sa.json
    ├── cleo_plugins/        # Plugins de CLEO Redux (.cleo)
    ├── twitch/              # Tono de llamada (ring.mp3)
    ├── tools/               # ffmpeg.exe (no incluido en git, ver arriba)
    └── twitch_movil.js      # Script CLEO que corre dentro del juego
```

---

## 🙏 Créditos y licencias de terceros

Este mod empaqueta, sin modificarlas, herramientas de terceros necesarias
para funcionar. El código propio de este repo está bajo licencia
[MIT](LICENSE); estas herramientas conservan su propia licencia:

- **[CLEO 5 / CLEO Redux](https://cleo.li/)** — runtime de scripts para GTA SA.
- **[FFmpeg](https://ffmpeg.org/)** — procesamiento de audio (licencia LGPL/GPL).
- **[edge-tts](https://github.com/rany2/edge-tts)** — cliente no oficial de Microsoft Edge TTS.
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** — interfaz gráfica del panel.

---

## ⚖️ Aviso legal

*Grand Theft Auto: San Andreas* es una marca registrada de **Rockstar
Games / Take-Two Interactive**. Este proyecto es un mod no oficial hecho
por fans, no está afiliado ni respaldado por Rockstar Games, y **requiere
que ya poseas una copia legítima del juego**. No se distribuye ningún
archivo del juego original en este repositorio.
