"""
v22 — Selector de fotos de la galería.

Envuelve el componente de galeria_web/index.html, que corre en el celular:
abre la galería con accept="image/*", achica cada foto a 1280 px (el mismo
tamaño con el que se guarda), la convierte a JPG y la manda ya ligera (unos
300 KB en vez de 3 a 10 MB). Como llega del tamaño final, el servidor ya no la
vuelve a comprimir.

Por qué no st.file_uploader: ver el comentario al inicio de index.html.
"""
import base64
from pathlib import Path

import streamlit.components.v1 as components

_selector = components.declare_component(
    "atlas_galeria", path=str(Path(__file__).parent / "galeria_web"))

LADO = 1280       # lado mayor con el que sale del celular = el de data.comprimir_foto
CALIDAD = 0.8     # calidad JPG en el celular


def elegir_fotos(key: str, max_fotos: int, recibido: str = None):
    """Pinta el botón de la galería. Devuelve (id, [bytes JPG], aviso).

    id identifica cada selección, para no sumar dos veces la misma cuando
    Streamlit vuelve a correr el script. aviso es el texto a repetir en la app
    si alguna foto no se pudo abrir o no cupo (el componente lo pierde al
    refrescarse). Sin selección nueva: (None, [], '').

    recibido es el id de la última selección que la app ya procesó: con él el
    componente sabe que sus fotos llegaron y deja de reenviarlas.
    """
    valor = _selector(max_fotos=int(max_fotos), lado=LADO, calidad=CALIDAD, recibido=recibido,
                      key=key, default=None)
    if not isinstance(valor, dict) or not valor.get("fotos"):
        return None, [], ""
    fotos = []
    for foto in valor["fotos"]:
        try:
            fotos.append(base64.b64decode(foto["datos"]))
        except Exception as e:
            print(f"[GALERIA WARN] foto ilegible: {e}")
    avisos = []
    fallas, sobran = int(valor.get("fallas") or 0), int(valor.get("sobran") or 0)
    if fallas:
        avisos.append(("Una foto no se pudo abrir" if fallas == 1 else f"{fallas} fotos no se pudieron abrir")
                      + ". Si tu cámara guarda en HEIC o HEIF, cámbiala a JPG en los ajustes de la "
                        "cámara, o usa \"Tomar ahora\".")
    if sobran:
        avisos.append(f"Elegiste {sobran} de más: solo caben {max_fotos}, se tomaron las primeras.")
    return valor.get("id"), fotos, " ".join(avisos)
