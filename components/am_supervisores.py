"""
PANTALLA AM 2 — Lista de supervisores del Area Manager (v9).
Cada tarjeta con 4 mini-indicadores (Bono, %PS, Candado, OOS).
Click → lista de promotores de ese supervisor (reutiliza supervisor_promotores.render_lista).
"""
import streamlit as st
import render as r
import pandas as pd
from styles.theme import (
    COLOR_PINK_TEXT, COLOR_BLUE_BG, COLOR_BLUE_BORDER, COLOR_NAVY,
    COLOR_TEXT_SECONDARY, COLOR_GREEN, COLOR_GREEN_PALE, COLOR_AMBER,
    COLOR_RED_DARK, COLOR_RED_PALE, COLOR_RED_BORDER, COLOR_WHITE,
)
from data import get_supervisores_de_am, adaptar_supervisor, get_periodo_corto


def render(usuario: dict, periodo_id: str):
    am = usuario['identificador']
    periodo_corto = get_periodo_corto(periodo_id)
    sups_raw = get_supervisores_de_am(am, periodo_id)

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Volver", key="back_am_resumen"):
            st.session_state.pantalla = 'resumen_am'
            st.rerun()
    with col2:
        r.html(f"""
        <div>
            <p style="font-size:17px;font-weight:500;margin:0;color:{COLOR_NAVY};">Mis supervisores</p>
            <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{len(sups_raw)} supervisores · {periodo_corto}</p>
        </div>
        """)

    if len(sups_raw) == 0:
        st.info('No hay supervisores para este periodo')
        return

    st.write("")
    sups = pd.DataFrame([adaptar_supervisor(s) for _, s in sups_raw.iterrows()])
    sups = sups.sort_values('BONO_FINAL_PCT', ascending=False)

    for _, s in sups.iterrows():
        _render_tarjeta_supervisor(s)


def _render_tarjeta_supervisor(s):
    sup_id = s['SUPERVISOR']                       # email → llave para queries
    nombre = s.get('EJECUTIVO') or sup_id          # etiqueta amigable (SUPERVISOR_16)
    candado = bool(s['CANDADO_ABIERTO'])
    bono_final = s['BONO_FINAL_PCT']
    bono_potencial = s.get('BONO_POTENCIAL_PCT', bono_final)
    pct_ps = s['PCT_PS']
    mult_oos = s['MULT_OOS_PCT']
    rutas = int(s.get('RUTAS_A_CARGO', 0))
    tiendas = int(s.get('TIENDAS_TOTALES', 0))

    if not candado:
        bono_label, bono_mostrar = "Bono pot.", bono_potencial
        bono_color, bono_bg = COLOR_RED_DARK, COLOR_RED_PALE
        subtitle = f'<p style="font-size:11px;color:{COLOR_RED_DARK};margin:2px 0 0;">{rutas} promotores · {tiendas} tiendas · ⚠️ candado cerrado</p>'
        border = COLOR_RED_BORDER
    else:
        bono_label, bono_mostrar = "Bono", bono_final
        if bono_final >= 50:
            bono_color, bono_bg = COLOR_GREEN, COLOR_GREEN_PALE
        elif bono_final >= 35:
            bono_color, bono_bg = COLOR_AMBER, "#FDF0E8"
        else:
            bono_color, bono_bg = COLOR_RED_DARK, COLOR_RED_PALE
        subtitle = f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{rutas} promotores · {tiendas} tiendas</p>'
        border = COLOR_BLUE_BORDER

    ps_color = COLOR_GREEN if pct_ps >= 80 else (COLOR_AMBER if pct_ps >= 60 else COLOR_RED_DARK)
    oos_color = COLOR_GREEN if mult_oos >= 90 else (COLOR_AMBER if mult_oos >= 70 else COLOR_RED_DARK)
    candado_icon = "🔓" if candado else "🔒"
    candado_bg = COLOR_GREEN_PALE if candado else COLOR_RED_PALE

    r.html(f"""
    <div style="background:{COLOR_WHITE};border-radius:12px;padding:12px;margin-bottom:10px;border:0.5px solid {border};">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px;">
            <div style="flex:1;min-width:0;">
                <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};">{nombre}</p>
                {subtitle}
            </div>
            <span style="font-size:18px;color:{COLOR_PINK_TEXT};">›</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;">
            <div style="text-align:center;background:{bono_bg};border-radius:8px;padding:6px 4px;">
                <p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:0;">{bono_label}</p>
                <p style="font-size:14px;font-weight:500;margin:2px 0 0;color:{bono_color};">{bono_mostrar:.0f}%{'' if candado else ' 🔒'}</p>
            </div>
            <div style="text-align:center;background:{COLOR_BLUE_BG};border-radius:8px;padding:6px 4px;">
                <p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:0;">% PS</p>
                <p style="font-size:14px;font-weight:500;margin:2px 0 0;color:{ps_color};">{pct_ps:.0f}%</p>
            </div>
            <div style="text-align:center;background:{candado_bg};border-radius:8px;padding:6px 4px;">
                <p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:0;">Candado</p>
                <div style="font-size:18px;margin-top:2px;">{candado_icon}</div>
            </div>
            <div style="text-align:center;background:{COLOR_BLUE_BG};border-radius:8px;padding:6px 4px;">
                <p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:0;">OOS</p>
                <p style="font-size:14px;font-weight:500;margin:2px 0 0;color:{oos_color};">{mult_oos:.0f}%</p>
            </div>
        </div>
    </div>
    """)

    if st.button(f"Ver promotores de {nombre}", key=f"am_sup_{sup_id}"):
        st.session_state.supervisor_seleccionado = sup_id
        st.session_state.supervisor_seleccionado_nombre = nombre
        st.session_state.pantalla = 'promotores_de_supervisor_am'
        st.rerun()
