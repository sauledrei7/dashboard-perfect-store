"""
PANTALLA 2 — Lista de tiendas del promotor.
Cada tienda con carita + estado PS + 4 mini-semáforos (Whisky/Tequila/Vodka/EXH).
"""
import streamlit as st
import render as r
import pandas as pd
from styles.theme import (
    COLOR_PINK_PALE, COLOR_PINK_TEXT, COLOR_BLUE_PALE, COLOR_BLUE_BG,
    COLOR_BLUE_BORDER, COLOR_BLUE_PRIMARY, COLOR_NAVY, COLOR_TEXT_SECONDARY,
    COLOR_GREEN, COLOR_GREEN_PALE, COLOR_GREEN_TEXT,
    COLOR_AMBER, COLOR_RED, COLOR_RED_DARK, COLOR_RED_PALE, COLOR_RED_BORDER,
    COLOR_WHITE,
)
from data import get_tiendas_de_ruta, adaptar_tiendas, get_periodo_corto


def render(usuario: dict, periodo_id: str):
    """Renderiza la lista de tiendas del promotor."""
    ruta = usuario['identificador']
    periodo_corto = get_periodo_corto(periodo_id)
    tiendas = adaptar_tiendas(get_tiendas_de_ruta(ruta, periodo_id))

    # Header con back button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Volver", key="back_to_resumen"):
            st.session_state.pantalla = 'resumen_promotor'
            st.rerun()
    with col2:
        r.html(f"""
        <div>
            <p style="font-size:17px;font-weight:500;margin:0;color:{COLOR_NAVY};">Mis tiendas</p>
            <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{len(tiendas)} tiendas · {periodo_corto}</p>
        </div>
        """)

    st.write("")

    # Lista de tiendas
    for _, t in tiendas.iterrows():
        _render_tarjeta_tienda(t)


def _render_tarjeta_tienda(tienda):
    """Tarjeta de una tienda con carita + estado + 4 mini-semáforos."""
    curt = str(tienda['Store Number'])
    nombre = str(tienda.get('Tienda', 'Sin nombre'))[:40]
    canal = str(tienda.get('CANAL', tienda.get('Canal', ''))).strip().upper()

    visitada = tienda.get('Tienda Visitada') == 1
    es_ps = tienda.get('PS FINAL') == 1
    es_mayo_depto = canal in ('MAYORISTAS', 'DEPARTAMENTALES')

    # Estado visual
    if not visitada:
        carita = "😶"
        estado_bg = "#F4F7FE"
        estado_color = COLOR_TEXT_SECONDARY
        estado_texto = "Sin datos"
    elif es_ps:
        carita = "😄"
        estado_bg = COLOR_GREEN_PALE
        estado_color = COLOR_GREEN_TEXT
        estado_texto = "Es PS"
    else:
        carita = "😞"
        estado_bg = COLOR_RED_PALE
        estado_color = COLOR_RED_DARK
        estado_texto = "No PS"

    # Etiqueta canal: bonita y específica por canal
    if es_mayo_depto:
        canal_short = "Mayorista" if canal == 'MAYORISTAS' else "Departamental"
        canal_html = f'<span style="background:{COLOR_PINK_PALE};color:{COLOR_PINK_TEXT};padding:2px 6px;border-radius:6px;font-size:10px;font-weight:500;">{canal_short} · BONUS</span>'
    elif canal == 'AUTOSERVICIOS':
        canal_html = f'<span style="background:{COLOR_BLUE_BG};color:{COLOR_BLUE_PRIMARY};padding:2px 6px;border-radius:6px;font-size:10px;">Autoservicio</span>'
    elif canal == 'CASH&CARRY' or canal == 'CASH & CARRY':
        canal_html = f'<span style="background:{COLOR_BLUE_BG};color:{COLOR_BLUE_PRIMARY};padding:2px 6px;border-radius:6px;font-size:10px;">Cash &amp; Carry</span>'
    else:
        canal_html = f'<span style="color:{COLOR_TEXT_SECONDARY};font-size:11px;">{canal.title() if canal else "Sin canal"}</span>'

    # Mini semáforos (4 categorías)
    sos_w = float(tienda.get('Total Whisky', 0) or 0) * 100
    sos_t = float(tienda.get('Total tequila', 0) or 0) * 100
    sos_v = float(tienda.get('Total vodka', 0) or 0) * 100
    exh = float(tienda.get('Puntos Promedio Exhibición', 0) or 0)

    border_color = COLOR_RED_BORDER if (visitada and not es_ps) else COLOR_BLUE_BORDER
    opacity = "0.85" if es_mayo_depto else "1"

    r.html(f"""
    <div style="background:{COLOR_WHITE};border-radius:12px;padding:14px;margin-bottom:10px;border:0.5px solid {border_color};opacity:{opacity};">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px;">
            <span style="font-size:32px;">{carita}</span>
            <div style="flex:1;min-width:0;">
                <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{nombre}</p>
                <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{canal_html}</p>
            </div>
            <span style="background:{estado_bg};color:{estado_color};font-size:12px;padding:3px 10px;border-radius:8px;font-weight:500;">{estado_texto}</span>
        </div>
        {_render_mini_semaforos(sos_w, sos_t, sos_v, exh) if visitada else ''}
    </div>
    """)

    # Botón invisible para click → detalle (Streamlit nativo)
    if st.button(f"Ver {nombre[:25]}", key=f"tienda_{curt}", help="Ver detalle"):
        st.session_state.curt_seleccionado = curt
        st.session_state.tienda_nombre = nombre
        st.session_state.pantalla = 'detalle_tienda'
        st.rerun()


def _render_mini_semaforos(sos_w, sos_t, sos_v, exh):
    """4 cápsulas pequeñas con semáforos."""
    def color(val, obj):
        if obj == 0: return COLOR_RED
        pct = val / obj
        if pct >= 1.0: return COLOR_GREEN
        if pct >= 0.80: return COLOR_AMBER
        return COLOR_RED

    c_w = color(sos_w, 35)
    c_t = color(sos_t, 30)
    c_v = color(sos_v, 25)
    c_e = color(exh, 4)

    return f"""
    <div style="display:flex;gap:6px;padding-top:10px;border-top:0.5px solid {COLOR_BLUE_BORDER};">
        <div style="flex:1;text-align:center;background:{COLOR_BLUE_BG};border-radius:8px;padding:6px 4px;">
            <div style="width:8px;height:8px;border-radius:50%;background:{c_w};margin:0 auto 3px;"></div>
            <p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:0;">Wh</p>
            <p style="font-size:11px;font-weight:500;margin:1px 0 0;color:{COLOR_NAVY};">{sos_w:.0f}%</p>
        </div>
        <div style="flex:1;text-align:center;background:{COLOR_BLUE_BG};border-radius:8px;padding:6px 4px;">
            <div style="width:8px;height:8px;border-radius:50%;background:{c_t};margin:0 auto 3px;"></div>
            <p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:0;">Te</p>
            <p style="font-size:11px;font-weight:500;margin:1px 0 0;color:{COLOR_NAVY};">{sos_t:.0f}%</p>
        </div>
        <div style="flex:1;text-align:center;background:{COLOR_BLUE_BG};border-radius:8px;padding:6px 4px;">
            <div style="width:8px;height:8px;border-radius:50%;background:{c_v};margin:0 auto 3px;"></div>
            <p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:0;">Vo</p>
            <p style="font-size:11px;font-weight:500;margin:1px 0 0;color:{COLOR_NAVY};">{sos_v:.0f}%</p>
        </div>
        <div style="flex:1;text-align:center;background:{COLOR_BLUE_BG};border-radius:8px;padding:6px 4px;">
            <div style="width:8px;height:8px;border-radius:50%;background:{c_e};margin:0 auto 3px;"></div>
            <p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:0;">EXH</p>
            <p style="font-size:11px;font-weight:500;margin:1px 0 0;color:{COLOR_NAVY};">{exh:.0f}</p>
        </div>
    </div>
    """
