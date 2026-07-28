"""
PANTALLA AM 1 — Resumen del Area Manager (v9).

Nivel ejecutivo: cómo va el ÁREA completa.
- KPIs agregados: %PS, OOS, tiendas capturadas
- Estado del equipo: supervisores con candado abierto/cerrado, promotores que cobran
- Ranking: mejor y menor supervisor
- Drill: botón hacia la lista de supervisores
"""
import streamlit as st
import render as r
import pandas as pd
from styles.theme import (
    COLOR_PINK_PRIMARY, COLOR_PINK_LIGHT, COLOR_PINK_PALE, COLOR_PINK_BORDER,
    COLOR_PINK_TEXT, COLOR_PINK_TEXT_LIGHT,
    COLOR_BLUE_PRIMARY, COLOR_BLUE_DARK, COLOR_BLUE_PALE, COLOR_BLUE_BG,
    COLOR_BLUE_BORDER, COLOR_BLUE_BORDER_DARK, COLOR_NAVY, COLOR_TEXT_SECONDARY,
    COLOR_GREEN, COLOR_GREEN_PALE, COLOR_GREEN_BORDER, COLOR_GREEN_TEXT,
    COLOR_AMBER, COLOR_RED_DARK, COLOR_RED_PALE, COLOR_RED_BORDER, COLOR_WHITE,
)
from data import (
    get_resumen_am, get_supervisores_de_am, get_promotores_de_am,
    adaptar_supervisor, get_periodo_descripcion,
)


def render(usuario: dict, periodo_id: str):
    am = usuario['identificador']
    periodo_desc = get_periodo_descripcion(periodo_id)
    resumen = get_resumen_am(am, periodo_id)

    if resumen is None:
        r.html(f"""
        <div style="background:{COLOR_PINK_PALE};border-radius:14px;padding:30px;margin:30px 0;text-align:center;border:0.5px solid {COLOR_BLUE_BORDER};">
            <div style="font-size:42px;margin-bottom:10px;">📅</div>
            <p style="font-size:16px;color:{COLOR_NAVY};font-weight:500;margin:0 0 8px;">Aún no hay datos para {periodo_desc}</p>
            <p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:0;line-height:1.5;">
                Si crees que es un error, contacta al administrador.<br>
                Mientras tanto, prueba cambiar el periodo arriba.
            </p>
        </div>
        """)
        return

    n_sup = resumen['N_SUPERVISORES']
    n_promo = resumen['N_PROMOTORES']
    pct_ps = resumen['PCT_PS']
    mult_oos = resumen['MULT_OOS_PCT']

    # ===== HEADER =====
    col1, col2 = st.columns([4, 1])
    with col1:
        r.html(f"""
        <div>
            <p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:0;">Hola {usuario['nombre']}</p>
            <p style="font-size:17px;font-weight:500;margin:2px 0 0;color:{COLOR_NAVY};">Area Manager</p>
            <p style="font-size:11px;color:{COLOR_PINK_TEXT_LIGHT};margin:2px 0 0;">{n_sup} supervisores · {n_promo} promotores · {resumen['TIENDAS_TOTALES']} tiendas</p>
        </div>
        """)
    with col2:
        if st.button("Salir", key="logout_am_btn"):
            from auth import cerrar_sesion
            cerrar_sesion()
            st.rerun()

    r.html(f"""
    <div style="background:{COLOR_BLUE_BG};border-radius:10px;padding:10px 12px;margin:14px 0 12px 0;border:0.5px solid {COLOR_BLUE_BORDER};">
        <span style="font-size:13px;color:{COLOR_TEXT_SECONDARY};">📅 Periodo:</span>
        <span style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin-left:6px;">{periodo_desc}</span>
    </div>
    """)

    # ===== HERO: %PS del área =====
    emoji = "😄" if pct_ps >= 80 else ("🙂" if pct_ps >= 60 else "😐")
    msg = "¡El área va bien!" if pct_ps >= 80 else ("Va cerca, empuja a los que faltan" if pct_ps >= 60 else "El área necesita atención")
    r.html(f"""
    <div style="background:linear-gradient(135deg,{COLOR_PINK_PRIMARY} 0%,{COLOR_PINK_LIGHT} 50%,{COLOR_BLUE_PRIMARY} 100%);border-radius:16px;padding:22px;margin-bottom:14px;text-align:center;color:white;">
        <p style="font-size:14px;opacity:0.95;margin:0 0 6px;">Perfect Store del área</p>
        <p style="font-size:52px;font-weight:500;margin:0;line-height:1;">{pct_ps:.0f}%</p>
        <div style="margin-top:10px;font-size:14px;">{emoji} {msg}</div>
        <div style="border-top:0.5px solid rgba(255,255,255,0.3);margin-top:14px;padding-top:12px;font-size:11px;opacity:0.9;">
            {resumen['PS_TOTAL']} tiendas PS de {resumen['TIENDAS_CAPTURADAS']} capturadas
        </div>
    </div>
    """)

    # ===== KPIs: PS + OOS =====
    ps_color = COLOR_GREEN if pct_ps >= 80 else (COLOR_AMBER if pct_ps >= 60 else COLOR_RED_DARK)
    oos_color = COLOR_GREEN if mult_oos >= 95 else (COLOR_AMBER if mult_oos >= 85 else COLOR_RED_DARK)
    col1, col2 = st.columns(2, gap="small")
    with col1:
        r.html(f"""
        <div style="background:{COLOR_PINK_PALE};border:0.5px solid {COLOR_PINK_BORDER};border-radius:12px;padding:14px;text-align:center;margin-bottom:12px;">
            <p style="font-size:12px;color:{COLOR_PINK_TEXT};margin:0 0 4px;">% PS del área</p>
            <p style="font-size:26px;font-weight:500;margin:4px 0;color:{ps_color};">{pct_ps:.0f}%</p>
            <p style="font-size:11px;color:{COLOR_PINK_TEXT_LIGHT};margin:0;">{resumen['PS_TOTAL']} de {resumen['TIENDAS_CAPTURADAS']} capturadas</p>
        </div>
        """)
    with col2:
        r.html(f"""
        <div style="background:{COLOR_BLUE_PALE};border:0.5px solid {COLOR_BLUE_BORDER_DARK};border-radius:12px;padding:14px;text-align:center;margin-bottom:12px;">
            <p style="font-size:12px;color:{COLOR_BLUE_DARK};margin:0 0 4px;">OOS del área</p>
            <p style="font-size:26px;font-weight:500;margin:4px 0;color:{oos_color};">{mult_oos:.0f}%</p>
            <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">{resumen['NO_CONT_OOS']} sin contestar de {resumen['OBJ_OOS']}</p>
        </div>
        """)

    # ===== % cobro promedio del equipo (v9.1) =====
    _render_cobro_promedio(resumen)

    # ===== Estado del equipo =====
    _render_estado_equipo(resumen)

    # ===== Ranking de supervisores =====
    _render_ranking_supervisores(am, periodo_id)

    # ===== Atención urgente: supervisores con candado cerrado =====
    _render_alertas_supervisores(am, periodo_id)

    # ===== Incidencias del área (solo visual) =====
    from components import incidencias_bandeja
    incidencias_bandeja.render(periodo_id, area_manager=am, key="band_am")

    # ===== Drill =====
    st.write("")
    if st.button(f"Ver mis {n_sup} supervisores →", key="ver_sups_btn"):
        st.session_state.pantalla = 'lista_supervisores_am'
        st.rerun()


def _render_cobro_promedio(resumen):
    """v9.1: Bono final promedio de supervisores y de promotores del área.
    Incluye a quienes van en 0% por candado cerrado (es el cobro real esperado)."""
    b_sup = resumen.get('BONO_PROM_SUPERVISORES', 0)
    b_promo = resumen.get('BONO_PROM_PROMOTORES', 0)
    # Semáforos: supervisores topados al 70%, promotores al 100%
    sup_color = COLOR_GREEN if b_sup >= 50 else (COLOR_AMBER if b_sup >= 35 else COLOR_RED_DARK)
    promo_color = COLOR_GREEN if b_promo >= 70 else (COLOR_AMBER if b_promo >= 50 else COLOR_RED_DARK)

    col1, col2 = st.columns(2, gap="small")
    with col1:
        r.html(f"""
        <div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};border-radius:12px;padding:14px;text-align:center;margin-bottom:12px;">
            <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">% cobro prom. supervisores</p>
            <p style="font-size:26px;font-weight:500;margin:4px 0;color:{sup_color};">{b_sup:.0f}%</p>
            <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">Bono final · tope 70% · incluye candados en 0</p>
        </div>
        """)
    with col2:
        r.html(f"""
        <div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};border-radius:12px;padding:14px;text-align:center;margin-bottom:12px;">
            <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">% cobro prom. promotores</p>
            <p style="font-size:26px;font-weight:500;margin:4px 0;color:{promo_color};">{b_promo:.0f}%</p>
            <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">Bono final · incluye candados en 0</p>
        </div>
        """)


def _render_estado_equipo(resumen):
    r.html(f"""
    <div style="margin:14px 0;">
        <p style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin:0 0 8px;">Tu equipo este mes</p>
        <div style="display:flex;gap:10px;margin-bottom:10px;">
            <div style="flex:1;background:{COLOR_GREEN_PALE};border-radius:12px;padding:14px;text-align:center;border:0.5px solid {COLOR_GREEN_BORDER};">
                <p style="font-size:28px;font-weight:600;color:{COLOR_GREEN};margin:0;line-height:1;">{resumen['SUP_CANDADO_ABIERTO']}</p>
                <p style="font-size:12px;color:{COLOR_GREEN_TEXT};margin:6px 0 0;">🔓 Supervisores con candado abierto</p>
            </div>
            <div style="flex:1;background:{COLOR_RED_PALE};border-radius:12px;padding:14px;text-align:center;border:0.5px solid {COLOR_RED_BORDER};">
                <p style="font-size:28px;font-weight:600;color:{COLOR_RED_DARK};margin:0;line-height:1;">{resumen['SUP_CANDADO_CERRADO']}</p>
                <p style="font-size:12px;color:{COLOR_RED_DARK};margin:6px 0 0;">🔒 Con candado cerrado</p>
            </div>
        </div>
        <div style="display:flex;gap:10px;">
            <div style="flex:1;background:{COLOR_GREEN_PALE};border-radius:12px;padding:14px;text-align:center;border:0.5px solid {COLOR_GREEN_BORDER};">
                <p style="font-size:28px;font-weight:600;color:{COLOR_GREEN};margin:0;line-height:1;">{resumen['PROMOTORES_COBRAN']}</p>
                <p style="font-size:12px;color:{COLOR_GREEN_TEXT};margin:6px 0 0;">✅ Promotores que cobrarán</p>
            </div>
            <div style="flex:1;background:{COLOR_RED_PALE};border-radius:12px;padding:14px;text-align:center;border:0.5px solid {COLOR_RED_BORDER};">
                <p style="font-size:28px;font-weight:600;color:{COLOR_RED_DARK};margin:0;line-height:1;">{resumen['PROMOTORES_NO_COBRAN']}</p>
                <p style="font-size:12px;color:{COLOR_RED_DARK};margin:6px 0 0;">🔒 No cobrarán</p>
            </div>
        </div>
    </div>
    """)


def _render_ranking_supervisores(am, periodo_id):
    df = get_supervisores_de_am(am, periodo_id)
    if len(df) < 2:
        return
    mejor = adaptar_supervisor(df.nlargest(1, 'bono_final_pct').iloc[0].to_dict())
    peor = adaptar_supervisor(df.nsmallest(1, 'bono_final_pct').iloc[0].to_dict())

    r.html(f"""
    <div style="background:linear-gradient(135deg,{COLOR_PINK_PALE} 0%,{COLOR_BLUE_PALE} 100%);border-radius:12px;padding:14px;margin-bottom:14px;border:0.5px solid {COLOR_BLUE_BORDER};">
        <p style="font-size:13px;font-weight:500;margin:0 0 12px;color:{COLOR_NAVY};">Ranking de supervisores</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div style="background:{COLOR_WHITE};border-radius:10px;padding:12px;border:0.5px solid {COLOR_GREEN_BORDER};">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="font-size:14px;">🏆</span>
                    <p style="font-size:11px;color:{COLOR_GREEN};margin:0;font-weight:500;">Tu mejor</p>
                </div>
                <p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">{mejor.get('EJECUTIVO', mejor['SUPERVISOR'])}</p>
                <p style="font-size:18px;font-weight:500;margin:6px 0 0;color:{COLOR_GREEN};">{mejor['BONO_FINAL_PCT']:.0f}%</p>
            </div>
            <div style="background:{COLOR_WHITE};border-radius:10px;padding:12px;border:0.5px solid {COLOR_RED_BORDER};">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="font-size:14px;">⚠️</span>
                    <p style="font-size:11px;color:{COLOR_RED_DARK};margin:0;font-weight:500;">Tu menor</p>
                </div>
                <p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">{peor.get('EJECUTIVO', peor['SUPERVISOR'])}</p>
                <p style="font-size:18px;font-weight:500;margin:6px 0 0;color:{COLOR_RED_DARK};">{peor['BONO_FINAL_PCT']:.0f}%</p>
            </div>
        </div>
    </div>
    """)


def _render_alertas_supervisores(am, periodo_id):
    df = get_supervisores_de_am(am, periodo_id)
    if len(df) == 0:
        return
    alertas = df[df['candado_abierto'] == False].head(5)
    if len(alertas) == 0:
        return
    items = ""
    for _, s in alertas.iterrows():
        nombre = s.get('ejecutivo') or s['supervisor']
        ef = float(s.get('efectividad_pct') or 0)
        faltantes = int(s.get('visitas_faltantes_95') or 0)
        items += (
            f'<div style="background:{COLOR_WHITE};border-radius:10px;padding:10px 12px;margin-bottom:6px;">'
            f'<p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">{nombre}</p>'
            f'<p style="font-size:11px;color:{COLOR_RED_DARK};margin:2px 0 0;">Candado cerrado · efectividad {ef:.0f}%, faltan {faltantes} visitas</p>'
            f'</div>'
        )
    r.html(
        f'<div style="background:{COLOR_RED_PALE};border:0.5px solid {COLOR_RED_BORDER};border-radius:12px;padding:14px;margin-bottom:12px;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        f'<span style="font-size:18px;">⚠️</span>'
        f'<p style="font-size:13px;font-weight:500;color:{COLOR_RED_DARK};margin:0;">Supervisores en riesgo ({len(alertas)})</p>'
        f'</div>'
        f'{items}'
        f'</div>'
    )
