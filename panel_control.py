"""
Panel de control PREMIUM del mod "Twitch al movil de CJ" (GTA San Andreas).

Uso:
    python panel_control.py

Requiere: pip install customtkinter edge-tts
"""

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import tts_common as tts

DIR_SCRIPT = os.path.dirname(os.path.abspath(__file__))

ctk.set_appearance_mode("dark")

# --- paleta -----------------------------------------------------------------
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
NOMBRE_A_VOZ = {nombre: codigo for codigo, nombre in VOCES_DISPONIBLES}
VOZ_A_NOMBRE = {codigo: nombre for codigo, nombre in VOCES_DISPONIBLES}

TEXTO_COMO_SE_HIZO = """Son tres piezas separadas que se hablan entre si a traves de archivos.

1 · ESTE PANEL
Guarda tus ajustes en config.json. No hace nada por si solo: solo
configura lo que usan las otras dos piezas.

2 · EL BOT DE PYTHON  (twitch_bot.py / tts_consola.py)
Se conecta al chat de Twitch en modo solo-lectura (usuario anonimo
justinfanXXXXX, sin cuenta ni token). Cuando alguien escribe algo que
menciona la palabra clave:
   • Limpia el texto (quita URLs, repeticiones, lo recorta)
   • Genera el audio con Microsoft edge-tts (voz neuronal gratuita)
   • Aplica un filtro de "voz de telefono" con ffmpeg
   • Escribe current.mp3 y current.txt en la carpeta del juego

3 · EL MOD DE CLEO  (twitch_movil[fs].js), dentro del juego
Vigila esa carpeta sin parar. Cuando ve current.txt + current.mp3:
   • Hace sonar un tono de llamada
   • Muestra un aviso con el icono real de tu tecla de responder
   • Al contestar: usa Task.UseMobilePhone, la funcion REAL que usa
     el juego en las llamadas de la historia (Sweet, Woozie...)
   • Reproduce el audio y muestra el mensaje abajo, estilo subtitulo
     de mision
   • Al terminar, BORRA los dos archivos: esa es la señal para que
     Python mande el siguiente mensaje

No hay ningun contador que sincronizar entre las dos partes: reiniciar
cualquiera de las dos piezas por separado nunca las desincroniza.

HERRAMIENTAS USADAS
   CLEO 5 + CLEO Redux  ·  Python 3 + edge-tts  ·  ffmpeg  ·  IRC anonimo de Twitch
"""


# =============================================================================
#  WIDGETS REUTILIZABLES
# =============================================================================

class Tarjeta(ctk.CTkFrame):
    """Panel con esquinas redondeadas, borde sutil y un titulo arriba."""
    def __init__(self, master, titulo, icono="", **kwargs):
        super().__init__(
            master, fg_color=BG_CARD, corner_radius=16,
            border_width=1, border_color=BORDE_CARD, **kwargs
        )
        cab = ctk.CTkFrame(self, fg_color="transparent")
        cab.pack(fill="x", padx=22, pady=(18, 4))
        ctk.CTkLabel(
            cab, text=f"{icono}  {titulo}", font=(FUENTE, 15, "bold"),
            text_color=TEXTO, anchor="w",
        ).pack(side="left")

        self.cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        self.cuerpo.pack(fill="both", expand=True, padx=22, pady=(6, 20))


class Campo(ctk.CTkFrame):
    """Etiqueta + control, alineados en fila, estilo formulario premium."""
    def __init__(self, master, etiqueta, ayuda=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(
            self, text=etiqueta, font=(FUENTE, 12), text_color=TEXTO,
        ).pack(anchor="w")
        if ayuda:
            ctk.CTkLabel(
                self, text=ayuda, font=(FUENTE, 10), text_color=TEXTO_TENUE,
            ).pack(anchor="w", pady=(0, 6))
        else:
            ctk.CTkFrame(self, height=6, fg_color="transparent").pack()


def entrada(master, textvariable, width=280, placeholder=""):
    return ctk.CTkEntry(
        master, textvariable=textvariable, width=width, height=36,
        corner_radius=10, fg_color="#0F0F1E", border_color=BORDE_CARD,
        border_width=1, font=(FUENTE, 12), placeholder_text=placeholder,
    )


# =============================================================================
#  APP PRINCIPAL
# =============================================================================

class Panel(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CJ Phone")
        self.geometry("880x680")
        self.minsize(820, 620)
        self.configure(fg_color=BG_APP)

        self.proceso_bot = None
        self.cola_log = queue.Queue()

        self._construir_sidebar()
        self._construir_contenido()
        self._cargar_valores()
        self._mostrar_pagina("config")
        self.after(200, self._bombear_log)

    # -----------------------------------------------------------------
    #  SIDEBAR
    # -----------------------------------------------------------------
    def _construir_sidebar(self):
        barra = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, width=210, corner_radius=0)
        barra.pack(side="left", fill="y")
        barra.pack_propagate(False)

        logo = ctk.CTkFrame(barra, fg_color="transparent")
        logo.pack(fill="x", padx=22, pady=(28, 6))
        ctk.CTkLabel(
            logo, text="📱", font=(FUENTE, 26),
        ).pack(side="left")
        marca = ctk.CTkFrame(logo, fg_color="transparent")
        marca.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(marca, text="CJ Phone", font=(FUENTE, 17, "bold"), text_color=TEXTO).pack(anchor="w")
        ctk.CTkLabel(marca, text="Twitch → GTA SA", font=(FUENTE, 10), text_color=TEXTO_TENUE).pack(anchor="w")

        ctk.CTkFrame(barra, height=1, fg_color=BORDE_CARD).pack(fill="x", padx=18, pady=18)

        self.botones_nav = {}
        for clave, icono, texto in [
            ("config", "⚙", "Configuración"),
            ("bot", "📡", "Bot en vivo"),
            ("info", "✦", "Cómo se hizo"),
        ]:
            b = ctk.CTkButton(
                barra, text=f"  {icono}   {texto}", anchor="w",
                fg_color="transparent", hover_color=BG_CARD_HOVER,
                text_color=TEXTO_TENUE, font=(FUENTE, 13),
                corner_radius=10, height=42,
                command=lambda c=clave: self._mostrar_pagina(c),
            )
            b.pack(fill="x", padx=14, pady=3)
            self.botones_nav[clave] = b

        # --- estado abajo del todo ------------------------------------------
        pie = ctk.CTkFrame(barra, fg_color="transparent")
        pie.pack(side="bottom", fill="x", padx=18, pady=22)
        ctk.CTkFrame(pie, height=1, fg_color=BORDE_CARD).pack(fill="x", pady=(0, 14))

        fila_estado = ctk.CTkFrame(pie, fg_color="transparent")
        fila_estado.pack(fill="x")
        self.punto_estado = ctk.CTkLabel(fila_estado, text="●", font=(FUENTE, 14), text_color=TEXTO_TENUE)
        self.punto_estado.pack(side="left")
        self.lbl_estado_sidebar = ctk.CTkLabel(
            fila_estado, text="Detenido", font=(FUENTE, 11), text_color=TEXTO_TENUE,
        )
        self.lbl_estado_sidebar.pack(side="left", padx=(6, 0))

    # -----------------------------------------------------------------
    #  CONTENEDOR DE PAGINAS
    # -----------------------------------------------------------------
    def _construir_contenido(self):
        self.contenedor = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0)
        self.contenedor.pack(side="left", fill="both", expand=True)

        self.paginas = {
            "config": self._pagina_config(self.contenedor),
            "bot": self._pagina_bot(self.contenedor),
            "info": self._pagina_info(self.contenedor),
        }

    def _mostrar_pagina(self, clave):
        for k, pagina in self.paginas.items():
            pagina.pack_forget()
        self.paginas[clave].pack(fill="both", expand=True)
        for k, boton in self.botones_nav.items():
            activo = k == clave
            boton.configure(
                fg_color=ACENTO if activo else "transparent",
                text_color=TEXTO if activo else TEXTO_TENUE,
            )

    # -----------------------------------------------------------------
    #  PAGINA: CONFIGURACION
    # -----------------------------------------------------------------
    def _pagina_config(self, master):
        wrap = ctk.CTkScrollableFrame(master, fg_color=BG_APP, corner_radius=0)

        ctk.CTkLabel(wrap, text="Configuración", font=(FUENTE, 24, "bold"), text_color=TEXTO).pack(anchor="w", padx=8, pady=(6, 2))
        ctk.CTkLabel(wrap, text="Ajusta cómo lee el chat y cómo suena CJ", font=(FUENTE, 12), text_color=TEXTO_TENUE).pack(anchor="w", padx=8, pady=(0, 20))

        # --- Twitch ----------------------------------------------------
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

        # --- Voz ----------------------------------------------------------
        card2 = Tarjeta(wrap, "Voz de CJ", "🎙")
        card2.pack(fill="x", padx=8, pady=(0, 16))

        Campo(card2.cuerpo, "Acento").pack(anchor="w")
        self.var_voz_nombre = tk.StringVar()
        ctk.CTkOptionMenu(
            card2.cuerpo, variable=self.var_voz_nombre,
            values=[n for _, n in VOCES_DISPONIBLES],
            width=320, height=36, corner_radius=10,
            fg_color="#0F0F1E", button_color=ACENTO, button_hover_color=ACENTO_HOVER,
            dropdown_fg_color=BG_CARD, font=(FUENTE, 12),
        ).pack(anchor="w", pady=(0, 16))

        fila_switch = ctk.CTkFrame(card2.cuerpo, fg_color="transparent")
        fila_switch.pack(fill="x")
        self.var_efecto = tk.BooleanVar()
        ctk.CTkSwitch(
            fila_switch, text="Efecto de voz de teléfono", variable=self.var_efecto,
            font=(FUENTE, 12), progress_color=ACENTO, button_color="#FFFFFF",
        ).pack(anchor="w")

        # --- Filtros --------------------------------------------------------
        card3 = Tarjeta(wrap, "Filtros y límites", "🛡")
        card3.pack(fill="x", padx=8, pady=(0, 16))

        fila2 = ctk.CTkFrame(card3.cuerpo, fg_color="transparent")
        fila2.pack(fill="x")
        c3 = Campo(fila2, "Cooldown por usuario", "En segundos")
        c3.pack(side="left")
        self.var_cooldown = tk.IntVar()
        ctk.CTkSlider(
            c3, from_=0, to=60, variable=self.var_cooldown, width=200,
            progress_color=ACENTO, button_color=ACENTO, button_hover_color=ACENTO_HOVER,
        ).pack(anchor="w")
        self.lbl_cooldown_val = ctk.CTkLabel(c3, text="15 s", font=(FUENTE, 10), text_color=TEXTO_TENUE)
        self.lbl_cooldown_val.pack(anchor="w")
        self.var_cooldown.trace_add("write", lambda *a: self.lbl_cooldown_val.configure(text=f"{self.var_cooldown.get()} s"))

        c4 = Campo(fila2, "Límite de caracteres", "Por mensaje leído")
        c4.pack(side="left", padx=(40, 0))
        self.var_max_car = tk.IntVar()
        entrada(c4, self.var_max_car, width=100).pack(anchor="w")

        Campo(card3.cuerpo, "Palabras prohibidas", "Separadas por comas").pack(anchor="w", pady=(16, 0))
        self.txt_blacklist = ctk.CTkTextbox(
            card3.cuerpo, width=500, height=60, corner_radius=10,
            fg_color="#0F0F1E", border_color=BORDE_CARD, border_width=1,
            font=(FUENTE, 11),
        )
        self.txt_blacklist.pack(anchor="w", pady=(4, 0))

        # --- Avanzado ---------------------------------------------------
        card4 = Tarjeta(wrap, "Avanzado", "🧩")
        card4.pack(fill="x", padx=8, pady=(0, 16))
        Campo(card4.cuerpo, "Carpeta del juego").pack(anchor="w")
        self.var_carpeta = tk.StringVar()
        entrada(card4.cuerpo, self.var_carpeta, width=520).pack(anchor="w")

        # --- botones ------------------------------------------------------
        fila_botones = ctk.CTkFrame(wrap, fg_color="transparent")
        fila_botones.pack(fill="x", padx=8, pady=(4, 30))
        ctk.CTkButton(
            fila_botones, text="💾  Guardar cambios", command=self._guardar,
            fg_color=ACENTO, hover_color=ACENTO_HOVER, height=42, width=200,
            corner_radius=12, font=(FUENTE, 13, "bold"),
        ).pack(side="left")
        ctk.CTkButton(
            fila_botones, text="↺  Restaurar", command=self._cargar_valores,
            fg_color="transparent", hover_color=BG_CARD_HOVER, border_width=1,
            border_color=BORDE_CARD, height=42, width=140, corner_radius=12,
            text_color=TEXTO_TENUE, font=(FUENTE, 12),
        ).pack(side="left", padx=10)

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

        self.btn_iniciar = ctk.CTkButton(
            fila, text="▶  Iniciar bot", command=self._iniciar_bot,
            fg_color=VERDE, hover_color="#28B383", text_color="#0B0B14",
            height=42, width=170, corner_radius=12, font=(FUENTE, 13, "bold"),
        )
        self.btn_iniciar.pack(side="left")

        self.btn_parar = ctk.CTkButton(
            fila, text="■  Detener", command=self._parar_bot, state="disabled",
            fg_color="transparent", hover_color=BG_CARD_HOVER, border_width=1,
            border_color=ROJO, text_color=ROJO, height=42, width=140, corner_radius=12,
            font=(FUENTE, 13),
        )
        self.btn_parar.pack(side="left", padx=10)

        ctk.CTkButton(
            fila, text="🖥  Consola de pruebas", command=self._abrir_consola,
            fg_color="transparent", hover_color=BG_CARD_HOVER, border_width=1,
            border_color=ACENTO_2, text_color=ACENTO_2, height=42, width=190,
            corner_radius=12, font=(FUENTE, 13),
        ).pack(side="left", padx=10)

        estado = ctk.CTkFrame(card.cuerpo, fg_color="transparent")
        estado.pack(fill="x", pady=(20, 0))
        self.punto_estado_bot = ctk.CTkLabel(estado, text="●", font=(FUENTE, 16), text_color=TEXTO_TENUE)
        self.punto_estado_bot.pack(side="left")
        self.lbl_estado_bot = ctk.CTkLabel(estado, text="Bot detenido", font=(FUENTE, 13, "bold"), text_color=TEXTO_TENUE)
        self.lbl_estado_bot.pack(side="left", padx=(8, 0))

        card_log = Tarjeta(wrap, "Registro en vivo", "📜")
        card_log.pack(fill="both", expand=True, padx=30, pady=(0, 24))

        self.txt_log = ctk.CTkTextbox(
            card_log.cuerpo, fg_color="#07070D", text_color="#4ADE80",
            corner_radius=10, font=("Consolas", 11), border_width=1,
            border_color=BORDE_CARD,
        )
        self.txt_log.pack(fill="both", expand=True)
        self.txt_log.configure(state="disabled")

        return wrap

    # -----------------------------------------------------------------
    #  PAGINA: COMO SE HIZO
    # -----------------------------------------------------------------
    def _pagina_info(self, master):
        wrap = ctk.CTkFrame(master, fg_color=BG_APP, corner_radius=0)

        ctk.CTkLabel(wrap, text="Cómo se hizo", font=(FUENTE, 24, "bold"), text_color=TEXTO).pack(anchor="w", padx=30, pady=(24, 2))
        ctk.CTkLabel(wrap, text="La arquitectura completa del mod, explicada", font=(FUENTE, 12), text_color=TEXTO_TENUE).pack(anchor="w", padx=30, pady=(0, 20))

        card = Tarjeta(wrap, "Arquitectura", "✦")
        card.pack(fill="both", expand=True, padx=30, pady=(0, 24))

        caja = ctk.CTkTextbox(
            card.cuerpo, fg_color="transparent", text_color=TEXTO,
            font=(FUENTE, 12), wrap="word", border_width=0,
        )
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
        self.var_carpeta.set(cfg["carpeta_juego"])
        self.txt_blacklist.delete("1.0", "end")
        self.txt_blacklist.insert("1.0", ", ".join(cfg["blacklist"]))
        self.lbl_estado_guardado.configure(text="✓  Valores cargados desde config.json")

    def _guardar(self):
        blacklist_texto = self.txt_blacklist.get("1.0", "end").strip()
        blacklist = [p.strip() for p in blacklist_texto.split(",") if p.strip()]

        cfg = tts.cargar_config()
        cfg.update({
            "canal_twitch": self.var_canal.get().strip(),
            "palabra_clave": self.var_palabra.get().strip(),
            "voz": NOMBRE_A_VOZ.get(self.var_voz_nombre.get(), self.var_voz_nombre.get()),
            "usar_efecto_telefono": bool(self.var_efecto.get()),
            "cooldown_segundos": int(self.var_cooldown.get()),
            "max_caracteres": int(self.var_max_car.get()),
            "carpeta_juego": self.var_carpeta.get().strip(),
            "blacklist": blacklist,
        })
        tts.guardar_config(cfg)
        self.lbl_estado_guardado.configure(
            text="✓  Guardado. Se aplicará la próxima vez que inicies el bot o la consola."
        )

    # -----------------------------------------------------------------
    #  CONTROL DEL BOT
    # -----------------------------------------------------------------
    def _iniciar_bot(self):
        if self.proceso_bot is not None:
            return
        canal = self.var_canal.get().strip()
        if not canal:
            messagebox.showwarning("Falta el canal", "Escribe un canal de Twitch antes de iniciar.")
            return

        self._guardar()

        self.proceso_bot = subprocess.Popen(
            [sys.executable, os.path.join(DIR_SCRIPT, "twitch_bot.py"), canal],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, cwd=DIR_SCRIPT,
        )
        threading.Thread(target=self._leer_salida_bot, daemon=True).start()

        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.lbl_estado_bot.configure(text=f"Conectado a #{canal}", text_color=VERDE)
        self.punto_estado_bot.configure(text_color=VERDE)
        self.lbl_estado_sidebar.configure(text="En vivo", text_color=VERDE)
        self.punto_estado.configure(text_color=VERDE)

    def _leer_salida_bot(self):
        for linea in self.proceso_bot.stdout:
            self.cola_log.put(linea.rstrip())
        self.cola_log.put("[proceso terminado]")

    def _parar_bot(self):
        if self.proceso_bot is not None:
            self.proceso_bot.terminate()
            self.proceso_bot = None
        self.btn_iniciar.configure(state="normal")
        self.btn_parar.configure(state="disabled")
        self.lbl_estado_bot.configure(text="Bot detenido", text_color=TEXTO_TENUE)
        self.punto_estado_bot.configure(text_color=TEXTO_TENUE)
        self.lbl_estado_sidebar.configure(text="Detenido", text_color=TEXTO_TENUE)
        self.punto_estado.configure(text_color=TEXTO_TENUE)

    def _abrir_consola(self):
        self._guardar()
        subprocess.Popen(
            'start "TTS consola" cmd /k python "{}"'.format(
                os.path.join(DIR_SCRIPT, "tts_consola.py")
            ),
            shell=True, cwd=DIR_SCRIPT,
        )

    def _bombear_log(self):
        while not self.cola_log.empty():
            linea = self.cola_log.get_nowait()
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", linea + "\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        self.after(200, self._bombear_log)


if __name__ == "__main__":
    Panel().mainloop()
