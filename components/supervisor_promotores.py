"""
PANTALLA 2 — Lista de promotores del supervisor.
Cada tarjeta con 4 mini-indicadores (Bono, %PS, Candado, OOS).
Al hacer click → entra al detalle de tiendas del promotor seleccionado.
"""
import streamlit as st
import render as r
import pandas as pd
from styles.theme import (
    COLOR_PINK_PALE, COLOR_PINK_TEXT, COLOR_BLUE_PALE, COLOR_BLUE_BG,
    COLOR_BLUE_BORDER, COLOR_NAVY, COLOR_TEXT_SECONDARY,
    COLOR_GREEN, COLOR_GREEN_PALE,
    COLOR_AMBER, COLOR_RED, COLOR_RED_DARK, COLOR_RED_PALE, COLOR_RED_BORDER,
    COLOR_WHITE,
)
from data import get_promotores_de_supervisor, adaptar_promotor, get_periodo_corto


def render(usuario: dict, periodo_id: str):
    """Lista de promotores del supervisor."""
    supervisor = usuario['identificador']
    periodo_corto = get_periodo_corto(periodo_id)
    promotores_raw = get_promotores_de_supervisor(supervisor, periodo_id)
    if len(promotores_raw)==0:
        st.info('No hay promotores para este periodo')
        return
    import pandas as pd
    promotores = pd.DataFrame([adaptar_promotor(r) for _, r in promotores_raw.iterrows()])

    # Header
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Volver", key="back_sup_resumen"):
            st.session_state.pantalla = 'resumen_supervisor'
            st.rerun()
    with col2:
        r.html(f"""
        <div>
            <p style="font-size:17px;font-weight:500;margin:0;color:{COLOR_NAVY};">Mis promotores</p>
            <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{len(promotores)} promotores · {periodo_corto}</p>
        </div>
        """)

    st.write("")

    # Ordenar por bono descendente (mejores arriba)
    promotores = promotores.sort_values('BONO_FINAL_PCT', ascending=False)

    for _, p in promotores.iterrows():
        _render_tarjeta_promotor(p)


def _render_tarjeta_promotor(p):
    """Tarjeta de un promotor con 4 mini-indicadores."""
    ruta = p['RUTA']
    candado = bool(p['CANDADO_ABIERTO'])
    bono_final = p['BONO_FINAL_PCT']
    bono_potencial = p.get('BONO_POTENCIAL_PCT', bono_final)
    pct_ps = p['PCT_PS_RUTA']
    mult_oos = p['MULT_OOS_PCT']
    tiendas_tot = int(p['TIENDAS_TOTALES'])
    elegibles = int(p['TIENDAS_ELEGIBLES'])

    # Si el candado está cerrado, mostramos el bono POTENCIAL (lo que ganaría
    # si abriera el candado) en lugar de un 0% sin contexto.
    if not candado:
        bono_label = "Bono pot."
        bono_mostrar = bono_potencial
    else:
        bono_label = "Bono"
        bono_mostrar = bono_final

    # Color del bono
    if not candado:
        bono_color = COLOR_RED_DARK
        bono_bg = COLOR_RED_PALE
    elif bono_final >= 80:
        bono_color = COLOR_GREEN
        bono_bg = COLOR_GREEN_PALE
    elif bono_final >= 50:
        bono_color = COLOR_AMBER
        bono_bg = "#FDF0E8"
    else:
        bono_color = COLOR_RED_DARK
        bono_bg = COLOR_RED_PALE

    # Color del PS
    ps_color = COLOR_GREEN if pct_ps >= 80 else (COLOR_AMBER if pct_ps >= 60 else COLOR_RED_DARK)
    oos_color = COLOR_GREEN if mult_oos >= 90 else (COLOR_AMBER if mult_oos >= 70 else COLOR_RED_DARK)

    # Subtitle
    if not candado:
        subtitle = f'<p style="font-size:11px;color:{COLOR_RED_DARK};margin:2px 0 0;">{tiendas_tot} tiendas · ⚠️ candado cerrado</p>'
        border = COLOR_RED_BORDER
    else:
        subtitle = f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{tiendas_tot} tiendas · {elegibles} elegibles</p>'
        border = COLOR_BLUE_BORDER

    # Candado icono y color
    candado_icon = "🔓" if candado else "🔒"
    candado_color = COLOR_GREEN if candado else COLOR_RED_DARK
    candado_bg = COLOR_GREEN_PALE if candado else COLOR_RED_PALE

    r.html(f"""
    <div style="background:{COLOR_WHITE};border-radius:12px;padding:12px;margin-bottom:10px;border:0.5px solid {border};">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px;">
            <div style="flex:1;min-width:0;">
                <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};">{ruta}</p>
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

    # Botón para entrar al detalle del promotor
    if st.button(f"Ver tiendas de {ruta}", key=f"sup_promo_{ruta}", help="Ver tiendas del promotor"):
        st.session_state.ruta_seleccionada = ruta
        st.session_state.pantalla = 'tiendas_de_promotor'
        st.session_state.volver_a = 'lista_promotores'
        st.rerun()
