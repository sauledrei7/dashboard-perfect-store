"""
ATLAS v17 — sesión que sobrevive a que el celular suspenda la pestaña.

EL PROBLEMA QUE RESUELVE
    st.session_state vive en la RAM del servidor, atada a la conexión abierta
    con el celular. Cuando el promotor se sale a la cámara, a Trax o a
    WhatsApp, el sistema operativo suspende la pestaña para ahorrar memoria: la
    conexión se corta y al volver Streamlit lo ve como un visitante nuevo.
    Resultado, pantalla de login.

    Aquí se guarda en el celular una cookie firmada que dice "este es fulano y
    vence tal día". Al recargar, la app la lee y lo deja pasar sin contraseña.

CÓMO ESTÁ PARTIDO, Y POR QUÉ
    LEER     -> st.context.cookies, nativo de Streamlit y síncrono.
                Ya viene en los encabezados de la petición, así que está listo
                desde el primer instante del script. Restaurar la sesión no
                parpadea ni necesita reruns.
    ESCRIBIR -> CookieManager, un componente que corre en el navegador.
    BORRAR      Solo se tocan al entrar y al salir, donde un ciclo extra no se
                nota.

    Esa división es lo que evita el parpadeo de login que arrastran casi todas
    las implementaciones de cookies en Streamlit, que leen con el componente y
    por eso necesitan un rerun antes de saber quién eres.

QUÉ LLEVA LA COOKIE
    Solo el username y la fecha de vencimiento, firmados con HMAC. NO lleva la
    contraseña, ni el rol, ni la ruta: al restaurar esos datos se releen de la
    base. Así, si a alguien lo dan de baja o le cambian la ruta, una cookie
    vieja no lo revive con datos viejos.

SI ALGO FALLA, NO PASA NADA
    Si la llave no está configurada, si el paquete no está instalado o si el
    componente truena, todas estas funciones se vuelven mudas y la app se
    comporta exactamente como antes: pide contraseña. Ninguna debe tirar la
    app ni dejar a un promotor sin poder entrar.
"""
import base64
import datetime
import hashlib
import hmac
import json
import time

import streamlit as st


COOKIE_NOMBRE = "atlas_sesion"

# Cuánto dura la sesión sin volver a pedir contraseña.
#
# 12 horas cubre un turno completo y vence en la noche. Se renueva cada vez que
# el promotor abre la app, así que mientras siga trabajando no lo saca.
#
# Si lo quieres de una semana, pon 24 * 7. Ese es el techo real: iOS no respeta
# más de 7 días en cookies puestas desde JavaScript, aunque le pidas más.
HORAS_VIGENCIA = 12

# Mínimo de la llave. Una llave corta es peor que no tener ninguna, porque da
# la impresión de que hay firma cuando en realidad se puede adivinar.
LARGO_MINIMO_LLAVE = 32

_aviso_dado = False


# ============================================================
# LLAVE
# ============================================================
def _secreto():
    """La llave con la que se firma la cookie. Sin ella, todo esto queda
    apagado y la app pide contraseña como siempre."""
    global _aviso_dado
    try:
        llave = st.secrets["sesion"]["cookie_secret"]
    except Exception:
        llave = None

    llave = (llave or "").strip()
    if len(llave) < LARGO_MINIMO_LLAVE:
        if not _aviso_dado:
            _aviso_dado = True
            print("[SESION WARN] Falta [sesion].cookie_secret en secrets, o mide "
                  f"menos de {LARGO_MINIMO_LLAVE} caracteres. La sesión persistente "
                  "queda DESACTIVADA: la app va a pedir contraseña en cada recarga.")
        return None
    return llave


def disponible() -> bool:
    """True si la sesión persistente puede funcionar. Sirve para diagnóstico."""
    return _secreto() is not None


# ============================================================
# TOKEN  (payload.firma, ambos en base64url sin relleno)
# ============================================================
def _b64(crudo: bytes) -> str:
    return base64.urlsafe_b64encode(crudo).decode().rstrip("=")


def _des_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firma(payload: str, llave: str) -> str:
    return _b64(hmac.new(llave.encode(), payload.encode(), hashlib.sha256).digest())


def crear_token(username: str, horas: int = None):
    """Arma el token firmado. None si no hay llave configurada."""
    llave = _secreto()
    if not llave or not username:
        return None
    horas = HORAS_VIGENCIA if horas is None else horas
    cuerpo = {"u": username, "exp": int(time.time()) + int(horas) * 3600}
    payload = _b64(json.dumps(cuerpo, separators=(",", ":")).encode())
    return payload + "." + _firma(payload, llave)


def leer_token(token: str):
    """Username si la firma cuadra y no ha vencido. None en cualquier otro caso."""
    llave = _secreto()
    if not llave or not token or "." not in token:
        return None

    payload, _, firma = token.partition(".")

    # compare_digest y no ==, para que el tiempo que tarda la comparación no
    # vaya soltando pistas de cómo es la firma correcta.
    if not hmac.compare_digest(firma, _firma(payload, llave)):
        return None

    try:
        cuerpo = json.loads(_des_b64(payload))
        vence = int(cuerpo.get("exp", 0))
    except Exception:
        return None

    if vence < time.time():
        return None

    return (cuerpo.get("u") or "").strip() or None


# ============================================================
# COOKIE
# ============================================================
def restaurar():
    """Username guardado en el celular, o None.

    Es síncrono: lee de los encabezados que el navegador ya mandó, así que
    sirve en el primer render — justo cuando la pestaña se acaba de recargar,
    que es el momento que nos interesa.
    """
    try:
        token = st.context.cookies.get(COOKIE_NOMBRE)
    except Exception:
        return None
    if not token:
        return None
    return leer_token(token)


def _manager():
    """El componente que escribe cookies. None si no se puede usar."""
    try:
        import extra_streamlit_components as stx
    except Exception:
        if not _aviso_dado:
            print("[SESION WARN] falta el paquete extra-streamlit-components. "
                  "La sesión persistente queda desactivada.")
        return None
    try:
        return stx.CookieManager(key="atlas_cookie_mgr")
    except Exception as e:
        print(f"[SESION WARN] no se pudo crear el CookieManager: {e}")
        return None


def _esconder_iframe():
    """Esconde el iframe invisible del componente de cookies.

    El componente ya trae su propio CSS, pero usa `:has()`, que no existe en
    Chrome anterior a 2022. En un celular viejo eso dejaría una franja en
    blanco arriba de la pantalla. La primera regla no usa `:has()` y funciona
    en todos lados; la segunda es la buena donde sí se puede.
    """
    st.markdown(
        '<style>iframe[height="0"]{display:none!important;}'
        '.element-container:has(iframe[height="0"]){display:none!important;}</style>',
        unsafe_allow_html=True,
    )


def guardar(username) -> bool:
    """Deja la cookie en el celular. True si se alcanzó a mandar la orden.

    OJO con dónde se llama: el componente necesita que el render llegue al
    navegador. Si justo después hay un st.rerun(), la orden se puede quedar en
    el camino. Por eso en app.py esto va en un render normal, no pegado al
    rerun del login.
    """
    token = crear_token(username)
    if not token:
        return False

    mgr = _manager()
    if mgr is None:
        return False

    _esconder_iframe()
    try:
        mgr.set(
            COOKIE_NOMBRE, token,
            key="atlas_cookie_set",
            expires_at=datetime.datetime.now() + datetime.timedelta(hours=HORAS_VIGENCIA),
            path="/",
            # lax y NO strict: con strict el navegador no manda la cookie
            # cuando el promotor llega desde un link externo, que es
            # exactamente como abren la app (el link que traen en WhatsApp).
            # Con strict, el arreglo no serviría en el caso más común.
            same_site="lax",
        )
        return True
    except Exception as e:
        print(f"[SESION WARN] no se pudo guardar la cookie: {e}")
        return False


def borrar():
    """Quita la cookie del celular. Se llama al cerrar sesión.

    Va en try/except porque delete() del componente hace un `del` directo
    sobre su diccionario interno, y ese diccionario viene vacío en el primer
    render: sin esto, cerrar sesión tronaría con KeyError.
    """
    mgr = _manager()
    if mgr is None:
        return
    # set() del componente esconde su iframe solo; delete() no, y si no se
    # esconde deja un hueco en blanco justo en la pantalla de login.
    _esconder_iframe()
    try:
        mgr.delete(COOKIE_NOMBRE, key="atlas_cookie_del")
    except Exception as e:
        # KeyError aquí es lo esperado y no es un problema: significa que el
        # componente todavía no había leído las cookies. La orden de borrado
        # igual se mandó al navegador.
        print(f"[SESION INFO] delete de cookie: {e}")
