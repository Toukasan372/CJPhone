"""
Motor del bot de Twitch (modulo reutilizable). Se conecta al chat en modo
anonimo de solo lectura (usuario justinfanXXXXX, sin cuenta ni token) y
manda cada mensaje valido al mod via tts_common.encolar().

Se puede usar de dos formas:
  - Como script suelto:  python twitch_bot.py nombre_canal   (necesita Python)
  - Importado por cjphone_app.py, que lo corre en un hilo dentro del mismo
    proceso (asi el .exe final no necesita lanzar un Python aparte).
"""

import queue
import random
import re
import socket
import sys
import threading
import time

import tts_common as tts

IRC_SERVER = "irc.chat.twitch.tv"
IRC_PORT = 6667

PREFIJOS_IGNORADOS = ("!",)
TAMANO_MAXIMO_COLA = 5

_patron_privmsg = re.compile(
    r"^:(?P<autor>[^!]+)!\S+ PRIVMSG #\S+ :(?P<mensaje>.*)$"
)


class BotTwitch:
    """Instancia controlable: .iniciar(canal), .detener(). log_fn recibe
    cada linea de texto que antes se imprimia con print()."""

    def __init__(self, log_fn=print):
        self.log = log_fn
        self._evento_parar = None
        self._hilos = []
        self._cola = queue.Queue(maxsize=TAMANO_MAXIMO_COLA)
        self.nick = "justinfan{}".format(random.randint(10000, 99999))

    def esta_activo(self):
        return any(h.is_alive() for h in self._hilos)

    def iniciar(self, canal):
        if self.esta_activo():
            return
        canal = canal.lstrip("#")
        self._evento_parar = threading.Event()
        tts.preparar_carpeta()

        self.log("=" * 50)
        self.log("Conectando a #{}...".format(canal))
        self.log("Voz: {}   Palabra clave: {}".format(tts.VOZ, tts.PALABRA_CLAVE or "(ninguna, lee todo)"))
        self.log("=" * 50)

        self._hilos = [
            threading.Thread(target=self._hilo_escucha, args=(canal,), daemon=True),
            threading.Thread(target=self._hilo_trabajador, daemon=True),
        ]
        for h in self._hilos:
            h.start()

    def detener(self):
        if self._evento_parar:
            self._evento_parar.set()
        self._hilos = []

    # -----------------------------------------------------------------
    def _conectar(self, canal):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((IRC_SERVER, IRC_PORT))
        sock.send("NICK {}\r\n".format(self.nick).encode("utf-8"))
        sock.send("JOIN #{}\r\n".format(canal.lower()).encode("utf-8"))
        return sock

    def _hilo_escucha(self, canal):
        detener = self._evento_parar
        while not detener.is_set():
            try:
                sock = self._conectar(canal)
                self.log("Conectado al chat de #{} como {}".format(canal, self.nick))
                buffer = ""

                while not detener.is_set():
                    try:
                        datos = sock.recv(4096).decode("utf-8", errors="ignore")
                    except socket.timeout:
                        continue
                    if not datos:
                        raise ConnectionError("el servidor cerro la conexion")

                    buffer += datos
                    lineas = buffer.split("\r\n")
                    buffer = lineas.pop()

                    for linea in lineas:
                        linea = linea.strip("\r\n")
                        if linea.startswith("PING"):
                            sock.send(b"PONG :tmi.twitch.tv\r\n")
                            continue
                        m = _patron_privmsg.match(linea)
                        if m:
                            self._encolar_si_procede(m.group("autor"), m.group("mensaje"))

            except (ConnectionError, OSError) as e:
                if detener.is_set():
                    break
                self.log("[!] Conexion perdida ({}), reintentando en 5s...".format(e))
                time.sleep(5)

    def _encolar_si_procede(self, autor, mensaje):
        mensaje = mensaje.strip()
        if not mensaje or mensaje.startswith(PREFIJOS_IGNORADOS):
            return
        if not tts.menciona_palabra_clave(mensaje):
            return
        if tts.en_cooldown(autor):
            return
        limpio = tts.limpiar_texto(mensaje)
        if limpio is None:
            return
        try:
            self._cola.put_nowait((autor, limpio))
        except queue.Full:
            pass

    def _hilo_trabajador(self):
        detener = self._evento_parar
        while not detener.is_set():
            try:
                autor, mensaje = self._cola.get(timeout=0.5)
            except queue.Empty:
                continue
            self.log("  -> procesando mensaje de {}...".format(autor))
            tts.encolar(autor, mensaje, silencioso=True)
            self.log("  -> enviado ({}: {})".format(autor, mensaje))


# ---------------------------------------------------------------------------
# Uso como script suelto (requiere Python instalado; el .exe no pasa por aqui)
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) >= 2:
        canal = sys.argv[1]
    elif tts.CANAL_TWITCH:
        canal = tts.CANAL_TWITCH
    else:
        print("Uso: python twitch_bot.py nombre_del_canal")
        sys.exit(1)

    bot = BotTwitch(log_fn=print)
    bot.iniciar(canal)
    try:
        while bot.esta_activo():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nCerrando...")
        bot.detener()


if __name__ == "__main__":
    main()
