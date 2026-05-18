"""
PANTALLA 3 — Detalle de tienda semana por semana.

NOTA TÉCNICA: Streamlit renderiza HTML como texto literal cuando hay loops
acumulando strings dentro de f-strings de varias líneas con triple-quote.
Solución: construir el HTML con concatenación de strings de UNA línea
(sin triple-quote ni newlines) y pasarlo en un solo st.markdown.
"""
import streamlit as st
import render as r
import pandas as pd
from styles.theme import (
    COLOR_PINK_PALE, COLOR_PINK_TEXT_LIGHT, COLOR_BLUE_PALE, COLOR_BLUE_BG,
    COLOR_BLUE_BORDER, COLOR_NAVY, COLOR_TEXT_SECONDARY,
    COLOR_GREEN, COLOR_GREEN_PALE, COLOR_GREEN_TEXT,
    COLOR_AMBER, COLOR_AMBER_PALE, COLOR_RED_DARK, COLOR_RED_PALE, COLOR_WHITE,
)
from data import get_detalle_tienda, get_tienda_info, adaptar_detalle, adaptar_tiendas


def render(periodo_id: str):
    """Renderiza el detalle de una tienda específica."""
    curt = st.session_state.get('curt_seleccionado')
    if not curt:
        st.error("No se seleccionó ninguna tienda")
        return

    info_raw = get_tienda_info(curt, periodo_id)
    info = adaptar_tiendas(__import__('pandas').DataFrame([info_raw]) if info_raw else __import__('pandas').DataFrame()).iloc[0].to_dict() if info_raw else None
    detalle = adaptar_detalle(get_detalle_tienda(curt, periodo_id))

    if info is None or len(detalle) == 0:
        st.error(f"No hay datos para CURT {curt}")
        return

    # Header
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Volver", key="back_to_tiendas_2"):
            origen = st.session_state.get('volver_a', 'tiendas_promotor')
            st.session_state.pantalla = origen
            st.rerun()
    with col2:
        st.caption("Detalle de tienda")

    # Tarjeta principal
    nombre = str(info.get('Tienda', 'Sin nombre'))
    canal = str(info.get('Canal', 'Autoservicio')).title()
    es_ps = info.get('PS FINAL') == 1
    carita = "😄" if es_ps else "😞"
    estado_bg = COLOR_GREEN_PALE if es_ps else COLOR_RED_PALE
    estado_color = COLOR_GREEN_TEXT if es_ps else COLOR_RED_DARK
    estado_texto = "Es PS" if es_ps else "No PS"

    header = (
        f'<div style="background:linear-gradient(135deg,{COLOR_PINK_PALE} 0%,{COLOR_BLUE_PALE} 100%);'
        f'border-radius:14px;padding:16px;margin:14px 0;border:0.5px solid {COLOR_BLUE_BORDER};">'
        f'<p style="font-size:17px;font-weight:500;margin:0;color:{COLOR_NAVY};">{nombre}</p>'
        f'<p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:4px 0 10px;">CURT {curt} · {canal}</p>'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:26px;">{carita}</span>'
        f'<span style="background:{estado_bg};color:{estado_color};font-size:13px;padding:4px 12px;border-radius:8px;font-weight:500;">{estado_texto}</span>'
        f'</div></div>'
    )
    r.html(header)

    detalle = detalle.sort_values('Semana')
    semanas = detalle['Semana'].tolist()

    _render_kpi(detalle, semanas, 'Total Whisky', "SOS Whisky", 35, es_pct=True)
    _render_kpi(detalle, semanas, 'Total tequila', "SOS Tequila", 30, es_pct=True)
    _render_kpi(detalle, semanas, 'Total vodka', "SOS Vodka", 25, es_pct=True)
    _render_kpi(detalle, semanas, 'Puntos Promedio Exhibición', "EXH Puntos", 4, es_pct=False)

    _render_tabla_exh(detalle, semanas)
    _render_visitas(detalle, semanas)

    incidencias = (detalle['Incidencia'] == 1).sum() if 'Incidencia' in detalle.columns else 0
    if incidencias > 0:
        note = (
            f'<div style="background:linear-gradient(135deg,{COLOR_PINK_PALE} 0%,{COLOR_BLUE_PALE} 100%);'
            f'border-radius:10px;padding:12px;margin-top:14px;border:0.5px solid {COLOR_BLUE_BORDER};">'
            f'<p style="font-size:12px;color:{COLOR_NAVY};margin:0;">'
            f'ℹ️ Hubo {int(incidencias)} semana(s) con incidencia. Esas no entraron al promedio.'
            f'</p></div>'
        )
        r.html(note)


def _render_kpi(detalle, semanas, columna, titulo, objetivo, es_pct=True):
    """Tarjeta con valores por semana + promedio."""
    if columna not in detalle.columns:
        return

    valores = []
    for s in semanas:
        fila = detalle[detalle['Semana'] == s]
        if len(fila) == 0:
            valores.append(None)
            continue
        v = fila.iloc[0][columna]
        inc = fila.iloc[0].get('Incidencia', 0) == 1
        if inc or pd.isna(v):
            valores.append(None)
        else:
            valores.append(float(v) * 100 if es_pct else float(v))

    validos = [v for v in valores if v is not None]
    if not validos:
        return
    prom = sum(validos) / len(validos)

    if prom >= objetivo:
        emoji = "😄"
    elif prom >= objetivo * 0.85:
        emoji = "😐"
    else:
        emoji = "😞"

    # Construir cuadritos como UNA SOLA STRING
    cuadros = ""
    for s, v in zip(semanas, valores):
        if v is None:
            cuadros += (
                f'<div style="text-align:center;">'
                f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{int(s)}</p>'
                f'<div style="background:{COLOR_BLUE_BG};border-radius:8px;padding:6px;">'
                f'<p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_TEXT_SECONDARY};">—</p>'
                f'</div></div>'
            )
        else:
            cumple = v >= objetivo
            if cumple:
                bg, text_c = COLOR_GREEN_PALE, COLOR_GREEN_TEXT
            elif v >= objetivo * 0.85:
                bg, text_c = COLOR_AMBER_PALE, COLOR_AMBER
            else:
                bg, text_c = COLOR_RED_PALE, COLOR_RED_DARK
            valor_txt = f"{v:.0f}%" if es_pct else f"{v:.0f}"
            cuadros += (
                f'<div style="text-align:center;">'
                f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{int(s)}</p>'
                f'<div style="background:{bg};border-radius:8px;padding:6px;">'
                f'<p style="font-size:13px;font-weight:500;margin:0;color:{text_c};">{valor_txt}</p>'
                f'</div></div>'
            )

    prom_txt = f"{prom:.1f}%" if es_pct else f"{prom:.1f}"
    obj_txt = f"objetivo {objetivo}%" if es_pct else f"objetivo {objetivo}"
    n_sem = len(semanas)

    titulo_html = (
        f'<p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:14px 4px 8px;font-weight:500;">'
        f'{titulo} <span style="color:{COLOR_PINK_TEXT_LIGHT};font-weight:400;">· {obj_txt}</span>'
        f'</p>'
    )
    r.html(titulo_html)

    tarjeta = (
        f'<div style="background:{COLOR_WHITE};border-radius:12px;padding:14px;margin-bottom:10px;border:0.5px solid {COLOR_BLUE_BORDER};">'
        f'<div style="display:grid;grid-template-columns:repeat({n_sem}, 1fr);gap:6px;margin-bottom:12px;">'
        f'{cuadros}'
        f'</div>'
        f'<div style="border-top:0.5px solid {COLOR_BLUE_BORDER};padding-top:10px;display:flex;justify-content:space-between;align-items:center;">'
        f'<div>'
        f'<span style="font-size:12px;color:{COLOR_TEXT_SECONDARY};">Promedio </span>'
        f'<span style="font-size:16px;font-weight:500;color:{COLOR_NAVY};">{prom_txt}</span>'
        f'</div>'
        f'<span style="font-size:22px;">{emoji}</span>'
        f'</div>'
        f'</div>'
    )
    r.html(tarjeta)


def _render_tabla_exh(detalle, semanas):
    """Tabla EXH Whisky/Tequila/Vodka × semana."""
    cats = {
        'Whisky': ['EXH AI W', 'EXH BI W'],
        'Tequila': ['EXH AI T', 'EXH BI T'],
        'Vodka': ['EXH AI V', 'EXH BI V'],
    }
    cols_disp = set(detalle.columns)
    if not any(c in cols_disp for cs in cats.values() for c in cs):
        return

    n_sem = len(semanas)
    grid_cols = "1fr " + " ".join(['1fr'] * n_sem)

    header = '<div style="text-align:center;"></div>'
    for s in semanas:
        header += f'<div style="text-align:center;color:{COLOR_NAVY};">S{int(s)}</div>'

    filas = ""
    for cat, cols in cats.items():
        cells = f'<div style="font-weight:500;padding-left:8px;text-align:left;color:{COLOR_NAVY};">{cat}</div>'
        for s in semanas:
            fila = detalle[detalle['Semana'] == s]
            if len(fila) == 0:
                cells += f'<div style="color:{COLOR_TEXT_SECONDARY};">—</div>'
                continue
            inc = fila.iloc[0].get('Incidencia', 0) == 1
            if inc:
                cells += f'<div style="color:{COLOR_TEXT_SECONDARY};">—</div>'
            else:
                total = 0
                for col in cols:
                    if col in fila.columns:
                        v = fila.iloc[0][col]
                        if pd.notna(v):
                            total += int(v)
                cells += f'<div style="color:{COLOR_NAVY};">{total}</div>'
        filas += (
            f'<div style="display:grid;grid-template-columns:{grid_cols};gap:0;padding:10px 0;'
            f'font-size:12px;text-align:center;border-bottom:0.5px solid {COLOR_BLUE_BORDER};">'
            f'{cells}</div>'
        )

    titulo = (
        f'<p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:14px 4px 8px;font-weight:500;">'
        f'Exhibiciones por categoría</p>'
    )
    r.html(titulo)

    tabla = (
        f'<div style="background:{COLOR_WHITE};border-radius:12px;padding:0;margin-bottom:10px;'
        f'border:0.5px solid {COLOR_BLUE_BORDER};overflow:hidden;">'
        f'<div style="display:grid;grid-template-columns:{grid_cols};gap:0;'
        f'background:linear-gradient(135deg,{COLOR_PINK_PALE} 0%,{COLOR_BLUE_PALE} 100%);'
        f'padding:10px 0;font-size:11px;font-weight:500;">'
        f'{header}</div>'
        f'{filas}'
        f'</div>'
    )
    r.html(tabla)


def _render_visitas(detalle, semanas):
    n_sem = len(semanas)
    cuadros = ""
    for s in semanas:
        fila = detalle[detalle['Semana'] == s]
        if len(fila) == 0:
            cuadros += (
                f'<div style="text-align:center;">'
                f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{int(s)}</p>'
                f'<div style="background:{COLOR_BLUE_BG};border-radius:8px;padding:6px;">'
                f'<span style="font-size:18px;color:{COLOR_TEXT_SECONDARY};">—</span>'
                f'</div></div>'
            )
            continue
        inc = fila.iloc[0].get('Incidencia', 0) == 1
        if inc:
            cuadros += (
                f'<div style="text-align:center;">'
                f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{int(s)}</p>'
                f'<div style="background:{COLOR_AMBER_PALE};border-radius:8px;padding:6px;">'
                f'<span style="font-size:18px;">⚠️</span>'
                f'</div></div>'
            )
        else:
            cuadros += (
                f'<div style="text-align:center;">'
                f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{int(s)}</p>'
                f'<div style="background:{COLOR_GREEN_PALE};border-radius:8px;padding:6px;">'
                f'<span style="font-size:18px;color:{COLOR_GREEN};">✓</span>'
                f'</div></div>'
            )

    titulo = (
        f'<p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:14px 4px 8px;font-weight:500;">'
        f'Visitas</p>'
    )
    r.html(titulo)

    tarjeta = (
        f'<div style="background:{COLOR_WHITE};border-radius:12px;padding:14px;margin-bottom:10px;'
        f'border:0.5px solid {COLOR_BLUE_BORDER};">'
        f'<div style="display:grid;grid-template-columns:repeat({n_sem}, 1fr);gap:6px;">'
        f'{cuadros}'
        f'</div></div>'
    )
    r.html(tarjeta)
