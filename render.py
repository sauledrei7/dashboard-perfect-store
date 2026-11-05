"""
Helper para renderizar HTML en Streamlit sin que sea interpretado como bloque de código.

PROBLEMA: Streamlit usa Markdown, y Markdown convierte cualquier línea que empieza
con 4+ espacios en un <code> block. Cuando construimos HTML multilínea en Python
con triple-quote y lo indentamos para legibilidad, esos espacios al inicio de cada
línea hacen que Markdown lo renderice como código en lugar de HTML.

SOLUCIÓN: pasar el HTML a través de textwrap.dedent() + strip() antes de
st.markdown(). Esto elimina la indentación común de todas las líneas.

SEGURIDAD (v26): todo texto que escribió una persona (comentarios, links, motivos)
o que viene de la base pasa por texto() antes de meterse en el HTML, y todo link
por url(). Streamlit sí pinta <style> y deja pasar links "javascript:": un
comentario malicioso podía dejar en blanco la pantalla del supervisor o correr
código al tocar el link de TRAX.
"""
import html as _html
import re
import textwrap

import streamlit as st

_URL = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)


def html(content: str):
    """Renderiza HTML limpio en Streamlit, eliminando la indentación que rompe Markdown."""
    # textwrap.dedent quita la indentación común
    # .strip() quita líneas en blanco al principio y final
    cleaned = textwrap.dedent(content).strip()
    st.markdown(cleaned, unsafe_allow_html=True)


def texto(valor) -> str:
    """Texto listo para ir dentro del HTML: escapado, sin NaN ni None.

    Un "$" se escribe como entidad para que Streamlit no lo pinte como fórmula.
    Los saltos de línea se respetan como <br>.
    """
    if valor is None:
        return ''
    try:
        if valor != valor:          # NaN
            return ''
    except Exception:
        pass
    limpio = _html.escape(str(valor).strip(), quote=True).replace('$', '&#36;')
    return '<br>'.join(limpio.splitlines())


def extraer_url(valor) -> str:
    """La primera URL http(s) del texto, tal cual, o '' si no trae.

    El promotor a veces pega el mensaje completo de TRAX ("Incidencia de Walmart
    ... https://..."): se toma solo la URL. Nunca regresa "javascript:" ni nada
    que no empiece con http:// o https://.
    """
    if valor is None:
        return ''
    m = _URL.search(str(valor))
    return m.group(0).rstrip('.,;)]') if m else ''


def url(valor) -> str:
    """El link listo para ir en un href (escapado), o '' si no es un http(s) válido."""
    return _html.escape(extraer_url(valor), quote=True)
