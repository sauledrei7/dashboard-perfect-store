"""
Helper para renderizar HTML en Streamlit sin que sea interpretado como bloque de código.

PROBLEMA: Streamlit usa Markdown, y Markdown convierte cualquier línea que empieza
con 4+ espacios en un <code> block. Cuando construimos HTML multilínea en Python
con triple-quote y lo indentamos para legibilidad, esos espacios al inicio de cada
línea hacen que Markdown lo renderice como código en lugar de HTML.

SOLUCIÓN: pasar el HTML a través de textwrap.dedent() + strip() antes de
st.markdown(). Esto elimina la indentación común de todas las líneas.
"""
import textwrap
import streamlit as st


def html(content: str):
    """Renderiza HTML limpio en Streamlit, eliminando la indentación que rompe Markdown."""
    # textwrap.dedent quita la indentación común
    # .strip() quita líneas en blanco al principio y final
    cleaned = textwrap.dedent(content).strip()
    st.markdown(cleaned, unsafe_allow_html=True)
