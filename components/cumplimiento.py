"""
v23 — Qué categorías cumple una tienda, con el veredicto del pipeline.

Antes cada pantalla lo volvía a calcular a su manera, y en algunas tiendas la
pantalla decía una cosa y el bono otra:
  - Exhibiciones: la app comparaba los puntos contra el objetivo. El pipeline
    además deja cumplir a la tienda que se queda entre 3 y 4 puntos si las
    exhibiciones de licor y ron le completan los 4 (o entre 1 y 2 en Sams y
    City Club), y Walmart Express cumple siempre. Esas tiendas salían en
    amarillo o rojo aunque ya cumplían. Aquí manda CUMPLIO 4, que es lo del bono.
  - SOS: la base guarda el SOS y el objetivo con 2 decimales, pero el pipeline
    decide con todos. En un empate a 2 decimales (10.62 contra 10.62) la app
    no puede saber, por sí sola, si cumplió. Lo resuelve cumplio_wtv, que sí
    viene del pipeline: si cumplió las 3, cumplió cada una. Si no, el empate
    cuenta como no cumplido: así salió en los 2 casos de julio a septiembre
    (31235 en agosto, 33183 en septiembre); los otros 11 empates tenían las 3.
  - En un mes ya cerrado, una incidencia aprobada puede dar por cumplida una
    categoría sin objetivo; cumplio_wtv también lo trae.

Solo pandas, nada de Streamlit. Recibe una fila de resumen_tienda ya pasada por
adaptar_tiendas() (SOS en 0-1, objetivos en 0-100).
"""
import pandas as pd

CATS_SOS = (('Whisky', 'Total Whisky', 'Objetivo Whisky'),
            ('Tequila', 'Total tequila', 'Objetivo Tequila'),
            ('Vodka', 'Total vodka', 'Objetivo Vodka'))
EMPATE = 0.005          # a 2 decimales, esto ya es "igual"


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(v) else v


def _si(v) -> bool:
    return str(v).strip().lower() in ('1', '1.0', 'true')


def categorias(t) -> dict:
    """{'Whisky': bool, 'Tequila': bool, 'Vodka': bool, 'EXH': bool}."""
    wtv = _si(t.get('cumplio_wtv'))
    out = {}
    for cat, col, col_obj in CATS_SOS:
        sos, obj = _num(t.get(col)), _num(t.get(col_obj))
        if wtv:
            out[cat] = True
        elif sos is None or obj is None or obj <= 0:
            out[cat] = False
        else:
            sos *= 100
            out[cat] = sos >= obj + EMPATE      # un empate a 2 decimales no alcanza
    out['EXH'] = _si(t.get('CUMPLIO 4'))
    return out


def empata(t, cat) -> bool:
    """El SOS y el objetivo son iguales a 2 decimales."""
    col, col_obj = next((c, o) for k, c, o in CATS_SOS if k == cat)
    sos, obj = _num(t.get(col)), _num(t.get(col_obj))
    return sos is not None and obj is not None and obj > 0 and abs(sos * 100 - obj) < EMPATE


def sin_objetivo(t, cat) -> bool:
    """La categoría no trae objetivo cargado (0 o vacío): así no se puede cumplir."""
    col_obj = next(o for c, _, o in CATS_SOS if c == cat)
    obj = _num(t.get(col_obj))
    return obj is None or obj <= 0


def nota_exh(t) -> str:
    """Por qué cumple exhibiciones una tienda que no llega a sus puntos."""
    if not _si(t.get('CUMPLIO 4')):
        return ''
    pts, obj = _num(t.get('Puntos Promedio Exhibición')), _num(t.get('Objetivo Puntos HS'))
    if pts is None or obj is None or pts >= obj:
        return ''
    if str(t.get('Cadena', '')).strip().upper() == 'WALMART EXPRESS':
        return 'Walmart Express cumple exhibiciones por regla de cadena.'
    return 'Cumple: las exhibiciones de licor y ron completan sus puntos.'
