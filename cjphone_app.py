"""
CJ Phone - App unica (instalador + panel + bot), pensada para congelarse
en un .exe con PyInstaller. No necesita que el cliente tenga Python, CLEO
ni ffmpeg: todo va empaquetado dentro del propio .exe.

Flujo:
  - Primera vez (o si la carpeta del juego configurada ya no es valida):
    pantalla de instalacion. Se elige la carpeta de GTA San Andreas
    (donde esta gta_sa.exe) y se copian ahi CLEO 5 + CLEO Redux + el
    script del mod + el tono de llamada. ffmpeg se copia a una carpeta
    de datos propia (no al juego).
  - Resto de veces: panel normal, con el bot de Twitch corriendo en un
    hilo dentro de este mismo proceso (no se lanza ningun Python aparte).
"""

import os
import queue
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

import tts_common as tts
import twitch_bot

ctk.set_appearance_mode("dark")

# --- paleta -------------------------------------------------------------
BG_APP        = "#0B0B14"
BG_SIDEBAR    = "#111120"
BG_CARD       = "#16162A"
BG_CARD_HOVER = "#1B1B33"
BORDE_CARD    = "#25253F"
ACENTO        = "#8B5CF6"
ACENTO_HOVER  = "#7C3AED"
ACENTO_2      = "#22D3EE"
TEXTO         = "#F1F1F6"
TEXTO_TENUE   = "#8A8AA3"
VERDE         = "#34D399"
ROJO          = "#F87171"
FUENTE        = "Segoe UI"

VOCES_DISPONIBLES = [
    ("es-CU-ManuelNeural",    "🇨🇺  Cubano · Manuel"),
    ("es-US-AlonsoNeural",    "🇺🇸  Latino EEUU · Alonso"),
    ("es-MX-JorgeNeural",     "🇲🇽  Mexicano · Jorge"),
    ("es-PR-VictorNeural",    "🇵🇷  Puertorriqueño · Victor"),
    ("es-DO-EmilioNeural",    "🇩🇴  Dominicano · Emilio"),
    ("es-VE-SebastianNeural", "🇻🇪  Venezolano · Sebastian"),
    ("es-AR-TomasNeural",     "🇦🇷  Argentino · Tomas"),
    ("es-CO-GonzaloNeural",   "🇨🇴  Colombiano · Gonzalo"),
    ("es-CL-LorenzoNeural",   "🇨🇱  Chileno · Lorenzo"),
    ("es-ES-AlvaroNeural",    "🇪🇸  España · Alvaro"),
]
NOMBRE_A_VOZ = {n: c for c, n in VOCES_DISPONIBLES}
VOZ_A_NOMBRE = {c: n for c, n in VOCES_DISPONIBLES}

TEXTO_COMO_SE_HIZO = """Son tres piezas que se hablan entre si a traves de archivos.

1 · ESTA APP
Instala CLEO en tu juego la primera vez y luego actua como panel de
control + bot de Twitch, todo en un solo proceso.

2 · EL BOT (dentro de esta misma app, en un hilo aparte)
Se conecta al chat de Twitch en modo solo-lectura (usuario anonimo, sin
cuenta ni token). Genera el audio con edge-tts, le aplica un filtro de
"voz de telefono" con ffmpeg, y escribe current.mp3 / current.txt en la
carpeta del juego.

3 · EL MOD DE CLEO, dentro del juego
Vigila esa carpeta. Cuando ve los dos archivos: suena el timbre, y al
contestar usa Task.UseMobilePhone (la funcion real del juego en las
llamadas de mision) para que CJ saque el movil de verdad. Al terminar
borra los archivos: esa es la señal para el siguiente mensaje.
"""


# =============================================================================
#  INSTALADOR
# =============================================================================

def instalar_en_carpeta(carpeta_raiz, log):
    """Copia CLEO 5 + CLEO Redux + el mod + ffmpeg. Devuelve True si ok."""
    try:
        gta_exe = os.path.join(carpeta_raiz, "gta_sa.exe")
        if not os.path.isfile(gta_exe):
            log("✗ No se encontro gta_sa.exe en esa carpeta.")
            return False

        cleo_dir = os.path.join(carpeta_raiz, "CLEO")
        config_dir = os.path.join(cleo_dir, ".config")
        plugins_dir = os.path.join(cleo_dir, "CLEO_PLUGINS")
        twitch_dir = os.path.join(cleo_dir, "twitch")
        for d in (cleo_dir, config_dir, plugins_dir, twitch_dir):
            os.makedirs(d, exist_ok=True)

        log("Copiando CLEO 5 y CLEO Redux...")
        shutil.copy2(tts.recurso_bundle("payload/root/CLEO.asi"), carpeta_raiz)
        shutil.copy2(tts.recurso_bundle("payload/root/cleo_redux.asi"), carpeta_raiz)
        shutil.copy2(tts.recurso_bundle("payload/root/bass.dll"), carpeta_raiz)

        log("Comprobando el ASI Loader...")
        vorbis_destino = os.path.join(carpeta_raiz, "vorbisFile.dll")
        necesita_loader = True
        if os.path.isfile(vorbis_destino):
            if os.path.getsize(vorbis_destino) > 20_000:
                log("  ya hay un ASI Loader instalado, no se toca.")
                necesita_loader = False
            else:
                shutil.copy2(vorbis_destino, vorbis_destino + ".vanilla_backup")
        if necesita_loader:
            shutil.copy2(tts.recurso_bundle("payload/root/vorbisFile_loader.dll"), vorbis_destino)
            log("  ASI Loader instalado (vorbisFile.dll).")

        log("Copiando configuracion y plugins de CLEO Redux...")
        shutil.copy2(tts.recurso_bundle("payload/cleo_config/cleo.ini"), config_dir)
        shutil.copy2(tts.recurso_bundle("payload/cleo_config/sa.json"), config_dir)
        for nombre in os.listdir(tts.recurso_bundle("payload/cleo_plugins")):
            shutil.copy2(tts.recurso_bundle("payload/cleo_plugins/" + nombre), plugins_dir)

        log("Copiando el mod y el tono de llamada...")
        shutil.copy2(tts.recurso_bundle("payload/twitch_movil.js"),
                     os.path.join(cleo_dir, "twitch_movil[fs].js"))
        shutil.copy2(tts.recurso_bundle("payload/twitch/ring.mp3"), twitch_dir)

        log("Copiando ffmpeg (para el efecto de voz de telefono)...")
        carpeta_datos = tts._carpeta_datos_app()
        herramientas_dir = os.path.join(carpeta_datos, "tools")
        os.makedirs(herramientas_dir, exist_ok=True)
        ruta_ffmpeg = os.path.join(herramientas_dir, "ffmpeg.exe")
        if not os.path.isfile(ruta_ffmpeg):
            shutil.copy2(tts.recurso_bundle("payload/tools/ffmpeg.exe"), ruta_ffmpeg)

        cfg = tts.cargar_config()
        cfg.update({
            "instalado": True,
            "carpeta_juego_raiz": carpeta_raiz,
            "carpeta_juego": twitch_dir,
            "ffmpeg_path": ruta_ffmpeg,
        })
        tts.guardar_config(cfg)
        tts.recargar_config()

        log("✓ Instalacion completa.")
        return True

    except Exception as e:
        log("✗ Error durante la instalacion: {}".format(e))
        return False


# =============================================================================
#  WIDGETS REUTILIZABLES
# =============================================================================

class Tarjeta(ctk.CTkFrame):
    def __init__(self, master, titulo, icono="", **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=16,
                          border_width=1, border_color=BORDE_CARD, **kwargs)
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.pack(fill="x", padx=22, pady=(18, 4))
        ctk.CTkLabel(cab, text=f"{icono}  {titulo}", font=(FUENTE, 15, "bold"),
                     text_color=TEXTO, anchor="w").pack(side="left")
        self.cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        self.cuerpo.pack(fill="both", expand=True, padx=22, pady=(6, 20))


class Campo(ctk.CTkFrame):
    def __init__(self, master, etiqueta, ayuda=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=etiqueta, font=(FUENTE, 12), text_color=TEXTO).pack(anchor="w")
        if ayuda:
            ctk.CTkLabel(self, text=ayuda, font=(FUENTE, 10), text_color=TEXTO_TENUE).pack(anchor="w", pady=(0, 6))
        else:
            ctk.CTkFrame(self, height=6, fg_color="transparent").pack()


def entrada(master, textvariable, width=280, placeholder=""):
    return ctk.CTkEntry(master, textvariable=textvariable, width=width, height=36,
                         corner_radius=10, fg_color="#0F0F1E", border_color=BORDE_CARD,
                         border_width=1, font=(FUENTE, 12), placeholder_text=placeholder)


# =============================================================================
#  PANTALLA DE INSTALACION
# =============================================================================

class PantallaInstalacion(ctk.CTkFrame):
    def __init__(self, master, al_terminar):
        super().__init__(master, fg_color=BG_APP)
        self.al_terminar = al_terminar

        centro = ctk.CTkFrame(self, fg_color="transparent")
        centro.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(centro, text="📱", font=(FUENTE, 46)).pack()
        ctk.CTkLabel(centro, text="Bienvenido a CJ Phone", font=(FUENTE, 22, "bold"), text_color=TEXTO).pack(pady=(8, 2))
        ctk.CTkLabel(
            centro, text="Vamos a instalar CLEO 5, CLEO Redux y el mod\nen tu carpeta de GTA San Andreas.",
            font=(FUENTE, 12), text_color=TEXTO_TENUE, justify="center",
        ).pack(pady=(0, 24))

        fila = ctk.CTkFrame(centro, fg_color="transparent")
        fila.pack()
        self.var_carpeta = tk.StringVar()
        entrada(fila, self.var_carpeta, width=380, placeholder=r"C:\...\GTA San Andreas").pack(side="left")
        ctk.CTkButton(
            fila, text="Examinar...", width=110, height=36, corner_radius=10,
            fg_color=BG_CARD_HOVER, hover_color=BORDE_CARD, text_color=TEXTO,
            command=self._elegir_carpeta,
        ).pack(side="left", padx=(8, 0))

        self.btn_instalar = ctk.CTkButton(
            centro, text="Instalar",  height=44, width=200, corner_radius=12,
            fg_color=ACENTO, hover_color=ACENTO_HOVER, font=(FUENTE, 13, "bold"),
            command=self._instalar,
        )
        self.btn_instalar.pack(pady=24)

        self.txt_log = ctk.CTkTextbox(
            centro, width=520, height=160, corner_radius=10,
            fg_color="#07070D", text_color="#4ADE80", font=("Consolas", 10),
        )
        self.txt_log.pack()
        self.txt_log.configure(state="disabled")

    def _elegir_carpeta(self):
        carpeta = filedialog.askdirectory(title="Selecciona la carpeta de GTA San Andreas")
        if carpeta:
            self.var_carpeta.set(carpeta)

    def _log(self, texto):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", texto + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")
        self.update_idletasks()

    def _instalar(self):
        carpeta = self.var_carpeta.get().strip()
        if not carpeta:
            messagebox.showwarning("Falta la carpeta", "Elige la carpeta de GTA San Andreas primero.")
            return
        self.btn_instalar.configure(state="disabled", text="Instalando...")
        threading.Thread(target=self._instalar_hilo, args=(carpeta,), daemon=True).start()

    def _instalar_hilo(self, carpeta):
        ok = instalar_en_carpeta(carpeta, self._log)
        if ok:
            self._log("")
            self._log("Listo. Abriendo el panel...")
            self.after(1200, self.al_terminar)
        else:
            self.btn_instalar.configure(state="normal", text="Reintentar")


# =============================================================================
#  DASHBOARD
# =============================================================================

class Dashboard(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=BG_APP)
        self.bot = twitch_bot.BotTwitch(log_fn=self._log_desde_hilo)
        self.cola_log = queue.Queue()

        self._construir_sidebar()
        self._construir_contenido()
        self._cargar_valores()
        self._mostrar_pagina("config")
        self.after(200, self._bombear_log)

    # -----------------------------------------------------------------
    def _construir_sidebar(self):
        barra = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, width=210, corner_radius=0)
        barra.pack(side="left", fill="y")
        barra.pack_propagate(False)

        logo = ctk.CTkFrame(barra, fg_color="transparent")
        logo.pack(fill="x", padx=22, pady=(28, 6))
        ctk.CTkLabel(logo, text="📱", font=(FUENTE, 26)).pack(side="left")
        marca = ctk.CTkFrame(logo, fg_color="transparent")
        marca.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(marca, text="CJ Phone", font=(FUENTE, 17, "bold"), text_color=TEXTO).pack(anchor="w")
        ctk.CTkLabel(marca, text="Twitch → GTA SA", font=(FUENTE, 10), text_color=TEXTO_TENUE).pack(anchor="w")

        ctk.CTkFrame(barra, height=1, fg_color=BORDE_CARD).pack(fill="x", padx=18, pady=18)

        self.botones_nav = {}
        for clave, icono, texto in [("config", "⚙", "Configuración"),
                                     ("bot", "📡", "Bot en vivo"),
                                     ("prueba", "🧪", "Consola de pruebas"),
                                     ("info", "✦", "Cómo se hizo")]:
            b = ctk.CTkButton(
                barra, text=f"  {icono}   {texto}", anchor="w",
                fg_color="transparent", hover_color=BG_CARD_HOVER,
                text_color=TEXTO_TENUE, font=(FUENTE, 13), corner_radius=10, height=42,
                command=lambda c=clave: self._mostrar_pagina(c),
            )
            b.pack(fill="x", padx=14, pady=3)
            self.botones_nav[clave] = b

        pie = ctk.CTkFrame(barra, fg_color="transparent")
        pie.pack(side="bottom", fill="x", padx=18, pady=22)
        ctk.CTkFrame(pie, height=1, fg_color=BORDE_CARD).pack(fill="x", pady=(0, 14))
        fila_estado = ctk.CTkFrame(pie, fg_color="transparent")
        fila_estado.pack(fill="x")
        self.punto_estado = ctk.CTkLabel(fila_estado, text="●", font=(FUENTE, 14), text_color=TEXTO_TENUE)
        self.punto_estado.pack(side="left")
        self.lbl_estado_sidebar = ctk.CTkLabel(fila_estado, text="Detenido", font=(FUENTE, 11), text_color=TEXTO_TENUE)
        self.lbl_estado_sidebar.pack(side="left", padx=(6, 0))

    def _construir_contenido(self):
        self.contenedor = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0)
        self.contenedor.pack(side="left", fill="both", expand=True)
        self.paginas = {
            "config": self._pagina_config(self.contenedor),
            "bot": self._pagina_bot(self.contenedor),
            "prueba": self._pagina_prueba(self.contenedor),
            "info": self._pagina_info(self.contenedor),
        }

    def _mostrar_pagina(self, clave):
        for pagina in self.paginas.values():
            pagina.pack_forget()
        self.paginas[clave].pack(fill="both", expand=True)
        for k, boton in self.botones_nav.items():
            activo = k == clave
            boton.configure(fg_color=ACENTO if activo else "transparent",
                             text_color=TEXTO if activo else TEXTO_TENUE)

    # -----------------------------------------------------------------
    #  PAGINA: CONFIGURACION
    # -----------------------------------------------------------------
    def _pagina_config(self, master):
        wrap = ctk.CTkScrollableFrame(master, fg_color=BG_APP, corner_radius=0)

        ctk.CTkLabel(wrap, text="Configuración", font=(FUENTE, 24, "bold"), text_color=TEXTO).pack(anchor="w", padx=8, pady=(6, 2))
        ctk.CTkLabel(wrap, text="Ajusta cómo lee el chat y cómo suena CJ", font=(FUENTE, 12), text_color=TEXTO_TENUE).pack(anchor="w", padx=8, pady=(0, 20))

        card = Tarjeta(wrap, "Twitch", "🟣")
        card.pack(fill="x", padx=8, pady=(0, 16))
        fila = ctk.CTkFrame(card.cuerpo, fg_color="transparent")
        fila.pack(fill="x")
        c1 = Campo(fila, "Canal a leer", "El nombre que va después de twitch.tv/")
        c1.pack(side="left")
        self.var_canal = tk.StringVar()
        entrada(c1, self.var_canal, placeholder="iLLoJuan").pack(anchor="w")
        c2 = Campo(fila, "Palabra clave", "Vacío = leer todo el chat")
        c2.pack(side="left", padx=(40, 0))
        self.var_palabra = tk.StringVar()
        entrada(c2, self.var_palabra, width=180, placeholder="cj").pack(anchor="w")

        card2 = Tarjeta(wrap, "Voz de CJ", "🎙")
        card2.pack(fill="x", padx=8, pady=(0, 16))
        Campo(card2.cuerpo, "Acento").pack(anchor="w")
        self.var_voz_nombre = tk.StringVar()
        ctk.CTkOptionMenu(
            card2.cuerpo, variable=self.var_voz_nombre, values=[n for _, n in VOCES_DISPONIBLES],
            width=320, height=36, corner_radius=10, fg_color="#0F0F1E",
            button_color=ACENTO, button_hover_color=ACENTO_HOVER,
            dropdown_fg_color=BG_CARD, font=(FUENTE, 12),
        ).pack(anchor="w", pady=(0, 16))
        self.var_efecto = tk.BooleanVar()
        ctk.CTkSwitch(card2.cuerpo, text="Efecto de voz de teléfono", variable=self.var_efecto,
                      font=(FUENTE, 12), progress_color=ACENTO, button_color="#FFFFFF").pack(anchor="w")

        card3 = Tarjeta(wrap, "Filtros y límites", "🛡")
        card3.pack(fill="x", padx=8, pady=(0, 16))
        fila2 = ctk.CTkFrame(card3.cuerpo, fg_color="transparent")
        fila2.pack(fill="x")
        c3 = Campo(fila2, "Cooldown por usuario", "En segundos")
        c3.pack(side="left")
        self.var_cooldown = tk.IntVar()
        ctk.CTkSlider(c3, from_=0, to=60, variable=self.var_cooldown, width=200,
                      progress_color=ACENTO, button_color=ACENTO, button_hover_color=ACENTO_HOVER).pack(anchor="w")
        self.lbl_cooldown_val = ctk.CTkLabel(c3, text="15 s", font=(FUENTE, 10), text_color=TEXTO_TENUE)
        self.lbl_cooldown_val.pack(anchor="w")
        self.var_cooldown.trace_add("write", lambda *a: self.lbl_cooldown_val.configure(text=f"{self.var_cooldown.get()} s"))
        c4 = Campo(fila2, "Límite de caracteres", "Por mensaje leído")
        c4.pack(side="left", padx=(40, 0))
        self.var_max_car = tk.IntVar()
        entrada(c4, self.var_max_car, width=100).pack(anchor="w")
        Campo(card3.cuerpo, "Palabras prohibidas", "Separadas por comas").pack(anchor="w", pady=(16, 0))
        self.txt_blacklist = ctk.CTkTextbox(card3.cuerpo, width=500, height=60, corner_radius=10,
                                             fg_color="#0F0F1E", border_color=BORDE_CARD, border_width=1, font=(FUENTE, 11))
        self.txt_blacklist.pack(anchor="w", pady=(4, 0))

        card4 = Tarjeta(wrap, "Instalación", "🧩")
        card4.pack(fill="x", padx=8, pady=(0, 16))
        Campo(card4.cuerpo, "Carpeta del juego instalada").pack(anchor="w")
        self.lbl_carpeta_instalada = ctk.CTkLabel(card4.cuerpo, text="", font=(FUENTE, 11), text_color=TEXTO_TENUE)
        self.lbl_carpeta_instalada.pack(anchor="w", pady=(0, 10))
        ctk.CTkButton(card4.cuerpo, text="Reinstalar en otra carpeta", height=34, corner_radius=10,
                      fg_color="transparent", hover_color=BG_CARD_HOVER, border_width=1, border_color=BORDE_CARD,
                      text_color=TEXTO_TENUE, command=self._reinstalar).pack(anchor="w")

        fila_botones = ctk.CTkFrame(wrap, fg_color="transparent")
        fila_botones.pack(fill="x", padx=8, pady=(4, 30))
        ctk.CTkButton(fila_botones, text="💾  Guardar cambios", command=self._guardar, fg_color=ACENTO,
                      hover_color=ACENTO_HOVER, height=42, width=200, corner_radius=12, font=(FUENTE, 13, "bold")).pack(side="left")
        ctk.CTkButton(fila_botones, text="↺  Restaurar", command=self._cargar_valores, fg_color="transparent",
                      hover_color=BG_CARD_HOVER, border_width=1, border_color=BORDE_CARD, height=42, width=140,
                      corner_radius=12, text_color=TEXTO_TENUE, font=(FUENTE, 12)).pack(side="left", padx=10)

        self.lbl_estado_guardado = ctk.CTkLabel(wrap, text="", font=(FUENTE, 11), text_color=VERDE)
        self.lbl_estado_guardado.pack(anchor="w", padx=8)
        return wrap

    # -----------------------------------------------------------------
    #  PAGINA: BOT EN VIVO
    # -----------------------------------------------------------------
    def _pagina_bot(self, master):
        wrap = ctk.CTkFrame(master, fg_color=BG_APP, corner_radius=0)
        ctk.CTkLabel(wrap, text="Bot en vivo", font=(FUENTE, 24, "bold"), text_color=TEXTO).pack(anchor="w", padx=30, pady=(24, 2))
        ctk.CTkLabel(wrap, text="Conecta al chat real y controla el mod desde aquí", font=(FUENTE, 12), text_color=TEXTO_TENUE).pack(anchor="w", padx=30, pady=(0, 20))

        card = Tarjeta(wrap, "Control", "🎛")
        card.pack(fill="x", padx=30, pady=(0, 16))
        fila = ctk.CTkFrame(card.cuerpo, fg_color="transparent")
        fila.pack(fill="x")
        self.btn_iniciar = ctk.CTkButton(fila, text="▶  Iniciar bot", command=self._iniciar_bot, fg_color=VERDE,
                                          hover_color="#28B383", text_color="#0B0B14", height=42, width=170,
                                          corner_radius=12, font=(FUENTE, 13, "bold"))
        self.btn_iniciar.pack(side="left")
        self.btn_parar = ctk.CTkButton(fila, text="■  Detener", command=self._parar_bot, state="disabled",
                                        fg_color="transparent", hover_color=BG_CARD_HOVER, border_width=1,
                                        border_color=ROJO, text_color=ROJO, height=42, width=140, corner_radius=12,
                                        font=(FUENTE, 13))
        self.btn_parar.pack(side="left", padx=10)

        estado = ctk.CTkFrame(card.cuerpo, fg_color="transparent")
        estado.pack(fill="x", pady=(20, 0))
        self.punto_estado_bot = ctk.CTkLabel(estado, text="●", font=(FUENTE, 16), text_color=TEXTO_TENUE)
        self.punto_estado_bot.pack(side="left")
        self.lbl_estado_bot = ctk.CTkLabel(estado, text="Bot detenido", font=(FUENTE, 13, "bold"), text_color=TEXTO_TENUE)
        self.lbl_estado_bot.pack(side="left", padx=(8, 0))

        card_log = Tarjeta(wrap, "Registro en vivo", "📜")
        card_log.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        self.txt_log = ctk.CTkTextbox(card_log.cuerpo, fg_color="#07070D", text_color="#4ADE80",
                                       corner_radius=10, font=("Consolas", 11), border_width=1, border_color=BORDE_CARD)
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.configure(state="disabled")
        return wrap

    # -----------------------------------------------------------------
    #  PAGINA: CONSOLA DE PRUEBAS
    # -----------------------------------------------------------------
    def _pagina_prueba(self, master):
        wrap = ctk.CTkFrame(master, fg_color=BG_APP, corner_radius=0)
        ctk.CTkLabel(wrap, text="Consola de pruebas", font=(FUENTE, 24, "bold"), text_color=TEXTO).pack(anchor="w", padx=30, pady=(24, 2))
        ctk.CTkLabel(wrap, text="Manda un mensaje de prueba sin necesidad de Twitch", font=(FUENTE, 12), text_color=TEXTO_TENUE).pack(anchor="w", padx=30, pady=(0, 20))

        card = Tarjeta(wrap, "Enviar mensaje", "🧪")
        card.pack(fill="x", padx=30, pady=(0, 16))

        fila = ctk.CTkFrame(card.cuerpo, fg_color="transparent")
        fila.pack(fill="x")
        c1 = Campo(fila, "Autor")
        c1.pack(side="left")
        self.var_prueba_autor = tk.StringVar(value="Pepito")
        entrada(c1, self.var_prueba_autor, width=160).pack(anchor="w")
        c2 = Campo(fila, "Mensaje (recuerda incluir la palabra clave)")
        c2.pack(side="left", padx=(20, 0))
        self.var_prueba_msg = tk.StringVar(value="oye cj que tal")
        entrada(c2, self.var_prueba_msg, width=320).pack(anchor="w")

        self.btn_prueba = ctk.CTkButton(card.cuerpo, text="📞  Enviar llamada de prueba", command=self._enviar_prueba,
                                         fg_color=ACENTO, hover_color=ACENTO_HOVER, height=40, corner_radius=12,
                                         font=(FUENTE, 12, "bold"))
        self.btn_prueba.pack(anchor="w", pady=(16, 0))

        self.lbl_prueba_estado = ctk.CTkLabel(card.cuerpo, text="", font=(FUENTE, 11), text_color=TEXTO_TENUE)
        self.lbl_prueba_estado.pack(anchor="w", pady=(10, 0))
        return wrap

    def _enviar_prueba(self):
        autor = self.var_prueba_autor.get().strip() or "Anonimo"
        mensaje = self.var_prueba_msg.get().strip()
        if not mensaje:
            return
        limpio = tts.limpiar_texto(mensaje)
        if limpio is None:
            self.lbl_prueba_estado.configure(text="✗ Descartado por el filtro (URL, vacío...)", text_color=ROJO)
            return
        if not tts.menciona_palabra_clave(limpio):
            self.lbl_prueba_estado.configure(text=f"✗ No menciona la palabra clave '{tts.PALABRA_CLAVE}'", text_color=ROJO)
            return
        self.btn_prueba.configure(state="disabled", text="Generando...")
        self.lbl_prueba_estado.configure(text="Generando audio y esperando turno...", text_color=TEXTO_TENUE)
        threading.Thread(target=self._enviar_prueba_hilo, args=(autor, limpio), daemon=True).start()

    def _enviar_prueba_hilo(self, autor, mensaje):
        ok = tts.encolar(autor, mensaje, silencioso=True)
        texto = "✓ Enviado, contesta la llamada en el juego" if ok else "✗ Fallo al generar el audio"
        color = VERDE if ok else ROJO
        self.after(0, lambda: (
            self.lbl_prueba_estado.configure(text=texto, text_color=color),
            self.btn_prueba.configure(state="normal", text="📞  Enviar llamada de prueba"),
        ))

    # -----------------------------------------------------------------
    def _pagina_info(self, master):
        wrap = ctk.CTkFrame(master, fg_color=BG_APP, corner_radius=0)
        ctk.CTkLabel(wrap, text="Cómo se hizo", font=(FUENTE, 24, "bold"), text_color=TEXTO).pack(anchor="w", padx=30, pady=(24, 2))
        ctk.CTkLabel(wrap, text="La arquitectura completa del mod, explicada", font=(FUENTE, 12), text_color=TEXTO_TENUE).pack(anchor="w", padx=30, pady=(0, 20))
        card = Tarjeta(wrap, "Arquitectura", "✦")
        card.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        caja = ctk.CTkTextbox(card.cuerpo, fg_color="transparent", text_color=TEXTO, font=(FUENTE, 12), wrap="word", border_width=0)
        caja.pack(fill="both", expand=True)
        caja.insert("1.0", TEXTO_COMO_SE_HIZO)
        caja.configure(state="disabled")
        return wrap

    # -----------------------------------------------------------------
    #  DATOS
    # -----------------------------------------------------------------
    def _cargar_valores(self):
        cfg = tts.cargar_config()
        self.var_canal.set(cfg["canal_twitch"])
        self.var_palabra.set(cfg["palabra_clave"])
        self.var_voz_nombre.set(VOZ_A_NOMBRE.get(cfg["voz"], cfg["voz"]))
        self.var_efecto.set(cfg["usar_efecto_telefono"])
        self.var_cooldown.set(cfg["cooldown_segundos"])
        self.var_max_car.set(cfg["max_caracteres"])
        self.lbl_carpeta_instalada.configure(text=cfg["carpeta_juego_raiz"] or "(no instalado)")
        self.txt_blacklist.delete("1.0", "end")
        self.txt_blacklist.insert("1.0", ", ".join(cfg["blacklist"]))
        self.lbl_estado_guardado.configure(text="✓  Valores cargados")

    def _guardar(self):
        blacklist = [p.strip() for p in self.txt_blacklist.get("1.0", "end").strip().split(",") if p.strip()]
        cfg = tts.cargar_config()
        cfg.update({
            "canal_twitch": self.var_canal.get().strip(),
            "palabra_clave": self.var_palabra.get().strip(),
            "voz": NOMBRE_A_VOZ.get(self.var_voz_nombre.get(), self.var_voz_nombre.get()),
            "usar_efecto_telefono": bool(self.var_efecto.get()),
            "cooldown_segundos": int(self.var_cooldown.get()),
            "max_caracteres": int(self.var_max_car.get()),
            "blacklist": blacklist,
        })
        tts.guardar_config(cfg)
        tts.recargar_config()
        self.lbl_estado_guardado.configure(text="✓  Guardado. Reinicia el bot si ya estaba corriendo.")

    def _reinstalar(self):
        cfg = tts.cargar_config()
        cfg["instalado"] = False
        tts.guardar_config(cfg)
        messagebox.showinfo("Reinstalar", "Cierra y vuelve a abrir CJ Phone para elegir otra carpeta.")

    # -----------------------------------------------------------------
    #  CONTROL DEL BOT (en proceso, sin lanzar Python aparte)
    # -----------------------------------------------------------------
    def _log_desde_hilo(self, texto):
        self.cola_log.put(texto)

    def _iniciar_bot(self):
        canal = self.var_canal.get().strip()
        if not canal:
            messagebox.showwarning("Falta el canal", "Escribe un canal de Twitch antes de iniciar.")
            return
        self._guardar()
        self.bot.iniciar(canal)
        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.lbl_estado_bot.configure(text=f"Conectado a #{canal}", text_color=VERDE)
        self.punto_estado_bot.configure(text_color=VERDE)
        self.lbl_estado_sidebar.configure(text="En vivo", text_color=VERDE)
        self.punto_estado.configure(text_color=VERDE)

    def _parar_bot(self):
        self.bot.detener()
        self.btn_iniciar.configure(state="normal")
        self.btn_parar.configure(state="disabled")
        self.lbl_estado_bot.configure(text="Bot detenido", text_color=TEXTO_TENUE)
        self.punto_estado_bot.configure(text_color=TEXTO_TENUE)
        self.lbl_estado_sidebar.configure(text="Detenido", text_color=TEXTO_TENUE)
        self.punto_estado.configure(text_color=TEXTO_TENUE)

    def _bombear_log(self):
        while not self.cola_log.empty():
            linea = self.cola_log.get_nowait()
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", linea + "\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        self.after(200, self._bombear_log)


# =============================================================================
#  VENTANA PRINCIPAL
# =============================================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CJ Phone")
        self.geometry("880x680")
        self.minsize(820, 620)
        self.configure(fg_color=BG_APP)

        carpeta_valida = tts.INSTALADO and os.path.isdir(tts.CARPETA)
        if carpeta_valida:
            Dashboard(self).pack(fill="both", expand=True)
        else:
            PantallaInstalacion(self, self._al_instalar).pack(fill="both", expand=True)

    def _al_instalar(self):
        for w in self.winfo_children():
            w.destroy()
        Dashboard(self).pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
