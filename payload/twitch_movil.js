// ===========================================================================
//  TWITCH MOVIL v4 - GTA San Andreas
//  El movil suena, pulsas la tecla de responder llamada, y suena el mensaje.
//  Si no contestas en X segundos, es llamada perdida y se descarta.
// ===========================================================================

var CARPETA   = "CLEO/twitch/";
var RINGTONE  = CARPETA + "ring.mp3";

var TECLA_CONTESTAR_RESPALDO = 9;   // solo si falla leer el control real (TAB)
var SEG_MAX_TIMBRE  = 20;     // cuanto suena antes de darse por perdida
var VOL_TONO        = 0.5;
var VOL_VOZ         = 1.0;
var INTERVALO       = 300;

var USAR_ANIMACION = true;    // CJ saca el movil con la funcion nativa del juego
var MODELO_MOVIL   = 330;     // modelo del movil de SA (el que usa Task.UseMobilePhone)

var player = new Player(0);

// --------------------------- UTILIDADES ------------------------------------

function cargarAudio(ruta) {
    try { return AudioStream.Load(ruta); }
    catch (e) { log("[twitch] audio: " + e); return null; }
}

function sonar(stream, vol, bucle) {
    if (!stream) return;
    try { stream.setVolume(vol); } catch (e) {}
    try { if (bucle) stream.setLooped(true); } catch (e) {}
    try { stream.setState(1); } catch (e) { log("[twitch] setState: " + e); }
}

function parar(stream) {
    if (!stream) return;
    try { stream.setState(0); } catch (e) {}
    try { stream.remove(); } catch (e) {}
}

function hayArchivo(ruta) {
    try { return Fs.DoesFileExist(ruta); } catch (e) { return false; }
}

function borrarArchivo(ruta) {
    try { Fs.DeleteFile(ruta); } catch (e) {}
}

// Cuadro de ayuda NEGRO del juego (el mismo de "Presiona X para entrar al
// coche"), para el AVISO de llamada entrante.
function mostrarAyuda(texto) {
    try { Text.PrintHelpString(texto); return; } catch (e) {}
    try { showTextBox(texto); } catch (e2) {}
}

// Subtitulo ABAJO en pantalla, mismo estilo que los dialogos de mision
// (PrintStringNow), para el MENSAJE cuando ya se contesto. Texto literal,
// asi que un '%' en el mensaje de alguien no rompe nada.
function mostrarSub(texto, ms) {
    try { Text.PrintStringNow(texto, ms); return; } catch (e) {}
    try { showTextBox(texto); } catch (e2) {}
}

// Averigua la tecla que el JUGADOR tiene configurada de verdad para
// "Responder llamada" (ControllerAction.PedAnswerPhone = 16), en vez de
// asumir un TAB fijo. Si el jugador remapeo la tecla, esto lo respeta.
function obtenerTeclaContestar() {
    try {
        var codigo = Pad.GetControllerKey(16, 0);  // 16=PedAnswerPhone, 0=Primary
        if (codigo !== undefined && codigo !== null) return codigo;
    } catch (e) { log("[twitch] GetControllerKey: " + e); }
    return TECLA_CONTESTAR_RESPALDO;
}

function esperar(ms) {
    while (ms > 0) { var p = ms > 100 ? 100 : ms; wait(p); ms -= p; }
}

// readString() esta roto en esta version, asi que leemos byte a byte.
function leerTexto(ruta) {
    var f = null;
    try {
        f = File.Open(ruta, "r");
        if (!f) return null;
        var s = "";
        for (var i = 0; i < 200; i++) {
            if (f.isEndReached()) break;
            var b = f.read(1);
            if (b === undefined || b === null || b <= 0) break;
            s += String.fromCharCode(b);
            if (i % 50 === 49) wait(0);   // cede control, no bloquear el juego
        }
        f.close();
        return s;
    } catch (e) {
        log("[twitch] leerTexto: " + e);
        if (f) { try { f.close(); } catch (e2) {} }
        return null;
    }
}

function parsear(bruto) {
    var autor = "Desconocido", mensaje = "";
    if (bruto) {
        var lineas = bruto.split(/\r?\n/);
        if (lineas.length > 0 && lineas[0]) autor = lineas[0];
        if (lineas.length > 1 && lineas[1]) mensaje = lineas[1];
    }
    return { autor: autor, mensaje: mensaje };
}

function jugadorListo() {
    try {
        if (!player.isPlaying()) return false;
        var ch = player.getChar();
        if (Char.IsDead(ch)) return false;
    } catch (e) {}
    return true;
}

// Devuelve true si contesto, false si la dejo perder.
function timbrar(autor) {
    var limite = SEG_MAX_TIMBRE * 1000;
    var pasado = 0;
    var contesto = false;

    var teclaContestar = obtenerTeclaContestar();

    // No hay ID de sonido de telefono expuesto para AddOneOffSound (el que
    // probe antes era de otra tabla, CoronaType). Usamos el mp3 propio.
    var tono = cargarAudio(RINGTONE);
    sonar(tono, VOL_TONO, true);

    while (pasado < limite) {
        // Cuadro NEGRO de ayuda mientras suena, con el icono real de la
        // tecla configurada (~k~~PED_ANSWER_PHONE~~h~).
        if (pasado % 1500 === 0) {
            mostrarAyuda(autor + " te llama.~n~Presiona ~k~~PED_ANSWER_PHONE~~h~ para contestar");
        }
        if (pasado > 800) {
            try {
                if (Pad.IsKeyPressed(teclaContestar)) { contesto = true; break; }
            } catch (e) { log("[twitch] tecla: " + e); }
        }
        wait(100);
        pasado += 100;
    }

    parar(tono);
    return contesto;
}

function sacarMovil(ch) {
    try {
        // Task.UseMobilePhone es la funcion REAL que usa el juego en las
        // llamadas de la historia. La primera vez no aparecia el modelo:
        // esta funcion espera que el modelo YA este cargado en memoria, no
        // lo pide ella sola. Por eso se precarga aqui antes de llamarla.
        Streaming.RequestModel(MODELO_MOVIL);
        var j = 0;
        while (!Streaming.HasModelLoaded(MODELO_MOVIL) && j < 40) { wait(50); j++; }
        if (!Streaming.HasModelLoaded(MODELO_MOVIL)) {
            log("[twitch] el modelo del movil no cargo a tiempo");
        }

        Task.UseMobilePhone(ch, true);
        log("[twitch] movil nativo: iniciado (modelo precargado)");
        return true;
    } catch (e) { log("[twitch] movil nativo: " + e); return null; }
}

function guardarMovil(ch) {
    try {
        Task.UseMobilePhone(ch, false);
        Streaming.MarkModelAsNoLongerNeeded(MODELO_MOVIL);
        log("[twitch] movil nativo: colgado");
    } catch (e) { log("[twitch] guardarMovil: " + e); }
}

function escuchar(autor, mensaje, rutaMp3) {
    var ch = null, movil = null;
    try { ch = player.getChar(); } catch (e) {}
    if (USAR_ANIMACION && ch) movil = sacarMovil(ch);

    // Saludo NO forzado (setSayContext, no el "Important"): la version
    // forzada cancelaba la animacion del movil justo al empezar.
    if (ch) {
        esperar(700);
        try { ch.setSayContext(108); } catch (e) { log("[twitch] saludo: " + e); }
        esperar(1000);
    }

    var voz = cargarAudio(rutaMp3);
    var ms = 4000;
    if (voz) {
        sonar(voz, VOL_VOZ, false);
        try {
            var d = voz.getLength();
            if (d && d > 0) ms = Math.floor(d * 1000) + 500;
        } catch (e) {}
    }

    // Subtitulo abajo, mismo estilo que los dialogos de mision.
    mostrarSub("~y~" + autor + "~w~: " + mensaje, ms);
    esperar(ms);

    parar(voz);
    if (movil && ch) guardarMovil(ch);
}

// --------------------------- BUCLE PRINCIPAL -------------------------------

log("[twitch v4] iniciado, vigilando " + CARPETA);

// Archivo de nombre FIJO en vez de numerado: elimina cualquier problema de
// contadores desincronizados si se reinicia Python o el juego por separado.
var rutaTxt = CARPETA + "current.txt";
var rutaMp3 = CARPETA + "current.mp3";

while (true) {
    wait(INTERVALO);

    if (!hayArchivo(rutaTxt) || !hayArchivo(rutaMp3)) continue;
    if (!jugadorListo()) continue;

    var d = parsear(leerTexto(rutaTxt));
    log("[twitch] mensaje de '" + d.autor + "': " + d.mensaje);

    var respondio = timbrar(d.autor);
    log("[twitch] timbre terminado, contesto=" + respondio);

    if (respondio) {
        escuchar(d.autor, d.mensaje, rutaMp3);
        log("[twitch] escuchar terminado");
    } else {
        mostrarAyuda("~r~Llamada perdida~w~ de " + d.autor);
    }

    // Borrar estos dos archivos es la SEÑAL para Python de que ya puede
    // escribir el siguiente mensaje. Sin esto, Python se queda esperando.
    borrarArchivo(rutaTxt);
    borrarArchivo(rutaMp3);
    wait(1500);   // respiro entre llamadas
}
