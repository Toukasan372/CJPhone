<div align="center">

[🇪🇸 Español](README.md) | **🇬🇧 English**

# 📱 CJ Phone — Twitch to CJ's mobile

### Reads your Twitch chat out loud, inside GTA San Andreas, as if CJ were getting a phone call.

</div>

---

<div align="center">

## ⬇️⬇️ DOWNLOAD THE INSTALLER ⬇️⬇️

### Just one `.exe`. No need to install Python, CLEO, or ffmpeg: everything is bundled inside.

<br>

[![Download CJPhone.exe](https://img.shields.io/badge/DOWNLOAD-CJPhone.exe-8B5CF6?style=for-the-badge&logo=windows&logoColor=white&labelColor=111120)](../../releases/latest/download/CJPhone.exe)

<br>

**[👉 Go to the latest release](../../releases/latest)**

| | |
|---|---|
| 🖥️ Platform | Windows 10 / 11 (64-bit) |
| 📦 Approx. size | ~85 MB |
| 🧩 Requires | GTA San Andreas (version 1.0, the classic disc/old Steam release) |
| 🐍 Requires Python | **No** — everything is bundled inside the .exe |

</div>

---

## 📖 Table of contents

1. [What is this?](#-what-is-this)
2. [Installation tutorial (step by step)](#-installation-tutorial-step-by-step)
3. [How to use it live](#-how-to-use-it-live)
4. [Available voices](#-available-voices)
5. [How it works under the hood](#-how-it-works-under-the-hood)
6. [Running from source](#-running-from-source-for-developers)
7. [Building your own .exe](#-building-your-own-exe)
8. [Repository structure](#-repository-structure)
9. [Credits and third-party licenses](#-credits-and-third-party-licenses)
10. [Legal notice](#-legal-notice)

---

## 🎮 What is this?

**CJ Phone** is a mod for GTA San Andreas built for streamers: it connects
your Twitch chat to the game so that whenever someone writes a message
(for example one that mentions the keyword `cj`), **CJ's phone rings**,
and once he picks up, the message is read out loud with a realistic
Latin-American voice, with a "phone call" audio filter applied.

The whole project is **three pieces talking to each other**, and all three
live in this repo:

- 🖥️ **The `CJPhone.exe` app** — installer + control panel + Twitch bot,
  all in a single desktop program.
- 🤖 **The Twitch bot** (runs inside the same app) — connects to the chat
  in read-only mode, no account or token required.
- 🎮 **The CLEO script** running inside the game — detects the new message
  and uses the game's real mission-call function so CJ actually answers
  the phone.

---

## 🚀 Installation tutorial (step by step)

> ⚠️ You need **GTA San Andreas already installed** on your PC (the folder
> where `gta_sa.exe` lives). The mod does not include the game itself.

### 1. Download the installer

Use the big button above, or go to the
**[Releases page](../../releases/latest)** and download `CJPhone.exe`.

### 2. Run `CJPhone.exe`

The first time you open it, it's normal for **Windows SmartScreen** or
your antivirus to show a warning, because the .exe isn't digitally
signed (a code-signing certificate costs money, and this is a free
community project). Click **"More info" → "Run anyway"**.

### 3. Pick your GTA San Andreas folder

The first time you open the app, it will ask you to select the folder
where `gta_sa.exe` is located. For example:

```
C:\Program Files (x86)\Rockstar Games\GTA San Andreas
D:\Games\GTA San Andreas
```

### 4. Let the installer copy everything

With a single click, the app automatically copies into that folder:

- `CLEO.asi` + `cleo_redux.asi` + `bass.dll` (the CLEO 5 / CLEO Redux runtime)
- The "ASI Loader" (`vorbisFile.dll`), if your install doesn't have one yet
- The CLEO Redux plugins (`CLEO\CLEO_PLUGINS\`)
- The mod script (`CLEO\twitch\`) and the ringtone
- `ffmpeg.exe` (copied separately, into your user data folder, not inside
  the game folder)

You don't have to copy or extract anything by hand.

### 5. Configure the panel

Once installed, the same window becomes the **control panel**:

- **Twitch channel** to connect to (yours, or any channel you want to listen to)
- **Keyword** a message must contain to be read aloud (`cj` by default; leave it empty to read the whole chat)
- **Voice** (choose from 10 Latin-American accents, see the [table below](#-available-voices))
- **Per-user cooldown**, so no one can spam the chat
- **Blacklist** of words that will never be read aloud

### 6. Click "Start"

Launch the game and load into a session. With the panel running and the
bot "Connected", any chat message that matches the rules will make CJ's
phone ring inside the game.

✅ **Done.** Close and reopen `CJPhone.exe` whenever you want: since it's
already installed, next time it opens straight into the control panel,
skipping the setup wizard.

---

## 🎬 How to use it live

1. Open GTA San Andreas and `CJPhone.exe` (separately — neither depends on the other to start).
2. In the app, confirm your Twitch channel and click **Start**.
3. Play normally. Whenever someone writes `cj <message>` in your Twitch chat, the phone will ring in-game.
4. Answer the call in-game (just like any mission call) and the message will be read out loud in the voice you picked.

---

## 🗣️ Available voices

| Accent | Voice |
|---|---|
| 🇨🇺 Cuban | Manuel |
| 🇺🇸 US Latino | Alonso |
| 🇲🇽 Mexican | Jorge |
| 🇵🇷 Puerto Rican | Victor |
| 🇩🇴 Dominican | Emilio |
| 🇻🇪 Venezuelan | Sebastian |
| 🇦🇷 Argentinian | Tomas |
| 🇨🇴 Colombian | Gonzalo |
| 🇨🇱 Chilean | Lorenzo |
| 🇪🇸 Spain | Alvaro |

Audio samples for several of these voices are in [`muestras_voz/`](muestras_voz).

---

## ⚙️ How it works under the hood

```
Twitch chat (IRC, anonymous mode)
        │
        ▼
twitch_bot.py  →  filters by keyword / cooldown / blacklist
        │
        ▼
tts_common.py  →  generates audio with edge-tts + "phone voice" filter via ffmpeg
        │           writes current.mp3 + current.txt to ...\CLEO\twitch\
        ▼
payload/twitch_movil.js (CLEO Redux, running inside the game)
        │  watches that folder, rings the phone and calls Task.UseMobilePhone
        ▼
   CJ answers the phone and the message is heard
```

The protocol between Python and CLEO is deliberately simple: a single
fixed-name file pair (`current.mp3` / `current.txt`). Python waits until
neither exists (CLEO already finished reading the previous one and
deleted them), generates the audio under a temporary name, then renames
it atomically. CLEO sees both files, plays the call, and deletes them
when done — that's the "ready for the next message" signal.

---

## 🐍 Running from source (for developers)

If you'd rather run the Python scripts directly instead of the `.exe`:

```bash
git clone https://github.com/Toukasan372/CJPhone.git
cd CJPhone
pip install -r requirements.txt
```

`ffmpeg.exe` is **not** included in the repo (it's ~99 MB). Download it
from [ffmpeg.org](https://ffmpeg.org/download.html) (the "essentials"
Windows build) and place it at:

```
payload/tools/ffmpeg.exe
```

Then:

```bash
python cjphone_app.py       # full app (installer + panel + bot)
python panel_control.py     # alternative panel, without the install wizard
python twitch_bot.py <channel>  # bot only, from the console
python probar_voces.py      # generates samples of the different voices/pitches
```

---

## 🛠️ Building your own `.exe`

The `.exe` published in Releases is built with
[PyInstaller](https://pyinstaller.org/) using the spec included in this
repo ([`CJPhone.spec`](CJPhone.spec)):

```bash
pip install -r requirements.txt
pyinstaller CJPhone.spec
```

The result lands in `dist/CJPhone.exe`. The spec already bundles the
whole `payload/` folder (including `ffmpeg.exe`, which you must place
there first) inside the final executable.

---

## 📁 Repository structure

```
CJPhone/
├── cjphone_app.py          # Final app: installer + panel + bot (this is what gets built into CJPhone.exe)
├── panel_control.py        # Alternative control panel (no install wizard)
├── twitch_bot.py           # Reusable Twitch bot engine
├── tts_common.py           # Shared logic: config, TTS, CLEO message queue
├── tts_consola.py          # Manual console test mode
├── probar_voces.py         # Sample generator to compare voices
├── probar_voces_naturales.py
├── config.json             # Example configuration
├── CJPhone.spec            # PyInstaller recipe used to build the .exe
├── requirements.txt
├── muestras_voz/           # .mp3 samples of the different voices
└── payload/                # Everything the installer copies into the game
    ├── root/                # CLEO.asi, cleo_redux.asi, bass.dll, ASI loader
    ├── cleo_config/         # cleo.ini, sa.json
    ├── cleo_plugins/        # CLEO Redux plugins (.cleo)
    ├── twitch/              # Ringtone (ring.mp3)
    ├── tools/               # ffmpeg.exe (not included in git, see above)
    └── twitch_movil.js      # CLEO script that runs inside the game
```

---

## 🙏 Credits and third-party licenses

This mod bundles, unmodified, third-party tools it needs to work. This
repo's own code is under the [MIT license](LICENSE); these tools keep
their own licenses:

- **[CLEO 5 / CLEO Redux](https://cleo.li/)** — scripting runtime for GTA SA.
- **[FFmpeg](https://ffmpeg.org/)** — audio processing (LGPL/GPL license).
- **[edge-tts](https://github.com/rany2/edge-tts)** — unofficial client for Microsoft Edge's TTS service.
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** — GUI toolkit for the control panel.

---

## ⚖️ Legal notice

*Grand Theft Auto: San Andreas* is a registered trademark of **Rockstar
Games / Take-Two Interactive**. This is an unofficial fan-made mod, not
affiliated with or endorsed by Rockstar Games, and it **requires you to
already own a legitimate copy of the game**. No game files are
distributed in this repository.
