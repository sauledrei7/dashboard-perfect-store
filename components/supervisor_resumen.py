"""
PANTALLA 1 — Resumen del supervisor.
Similar al promotor pero con tope del 70%, agregado de N promotores,
y bloques "Promotores cerca del 80%" + "Ranking" + "Atención urgente".
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
    COLOR_RED, COLOR_RED_DARK, COLOR_RED_PALE, COLOR_RED_BORDER, COLOR_WHITE,
)
from data import (
    get_resumen_supervisor, get_promotores_de_supervisor,
    get_promotores_cerca_80, get_mejor_y_peor_promotor,
    adaptar_supervisor, adaptar_promotor, get_periodo_descripcion,
)


def render(usuario: dict, periodo_id: str):
    """Resumen del supervisor."""
    supervisor = usuario['identificador']
    periodo_desc = get_periodo_descripcion(periodo_id)
    resumen = adaptar_supervisor(get_resumen_supervisor(supervisor, periodo_id))
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

    candado = bool(resumen['CANDADO_ABIERTO'])
    bono_potencial = resumen['BONO_POTENCIAL_PCT']
    bono_final = resumen['BONO_FINAL_PCT']
    pct_ps = resumen['PCT_PS']
    mult_oos = resumen['MULT_OOS_PCT']
    efectividad = resumen['EFECTIVIDAD_PCT']
    faltantes = int(resumen.get('VISITAS_FALTANTES_95', 0))
    rutas_a_cargo = int(resumen['RUTAS_A_CARGO'])
    total_tiendas = int(resumen['TIENDAS_TOTALES'])

    # ===== HEADER =====
    col1, col2 = st.columns([4, 1])
    with col1:
        r.html(f"""
        <div>
            <p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:0;">Hola {usuario['nombre']}</p>
            <p style="font-size:17px;font-weight:500;margin:2px 0 0;color:{COLOR_NAVY};">Supervisor</p>
            <p style="font-size:11px;color:{COLOR_PINK_TEXT_LIGHT};margin:2px 0 0;">{rutas_a_cargo} promotores · {total_tiendas} tiendas</p>
        </div>
        """)
    with col2:
        if st.button("Salir", key="logout_sup_btn"):
            from auth import cerrar_sesion
            cerrar_sesion()
            st.rerun()

    r.html(f"""
    <div style="background:{COLOR_BLUE_BG};border-radius:10px;padding:10px 12px;margin:14px 0 12px 0;border:0.5px solid {COLOR_BLUE_BORDER};">
        <span style="font-size:13px;color:{COLOR_TEXT_SECONDARY};">📅 Periodo:</span>
        <span style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin-left:6px;">{periodo_desc}</span>
    </div>
    """)

    # ===== HERO DEL BONO con leyenda 70% =====
    _render_bono_supervisor_hero(bono_potencial, bono_final, pct_ps, mult_oos, candado)

    # ===== Leyenda del tope 70% =====
    r.html(f"""
    <div style="background:{COLOR_PINK_PALE};border-radius:0 0 12px 12px;padding:8px 14px;margin-top:-8px;margin-bottom:14px;text-align:center;border:0.5px solid {COLOR_PINK_BORDER};border-top:none;">
        <p style="font-size:11px;color:{COLOR_PINK_TEXT};margin:0;">ℹ️ Solo el 70% del PS es medible como supervisor</p>
    </div>
    """)

    # ===== ALERTA candado cerrado =====
    if not candado:
        r.html(f"""
        <div style="background:{COLOR_RED_PALE};border-radius:12px;padding:12px 14px;margin-bottom:14px;border:0.5px solid {COLOR_RED_BORDER};">
            <div style="display:flex;align-items:flex-start;gap:8px;">
                <span style="font-size:20px;">⚠️</span>
                <div>
                    <p style="font-size:12px;font-weight:500;color:{COLOR_RED_DARK};margin:0;">No vas a cobrar bono este mes</p>
                    <p style="font-size:11px;color:{COLOR_RED_DARK};margin:4px 0 0;line-height:1.5;">
                        Tu efectividad va en {efectividad:.0f}%. Necesitas al menos 95% para liberar el bono.
                        Te faltan <strong>{faltantes} visitas</strong>.
                    </p>
                </div>
            </div>
        </div>
        """)

    # ===== CANDADO =====
    _render_candado_supervisor(candado, efectividad)

    # ===== KPIs %PS + OOS =====
    _render_kpis_supervisor(resumen)

    # ===== Cuántos promotores cobran / no cobran =====
    _render_cobran_no_cobran(supervisor, periodo_id)

    # ===== Promotores cerca del 80% =====
    _render_cerca_80(supervisor, periodo_id)

    # ===== Atención urgente =====
    _render_alertas(supervisor, periodo_id)

    # ===== Ranking equipo =====
    _render_ranking(supervisor, periodo_id)

    # ===== Botón =====
    st.write("")
    if st.button(f"Ver mis {rutas_a_cargo} promotores →", key="ver_promos_btn"):
        st.session_state.pantalla = 'lista_promotores'
        st.rerun()


def _render_bono_supervisor_hero(bono_potencial, bono_final, pct_ps, mult_oos, candado):
    """Bono con efecto bloqueado si candado cerrado."""
    if candado:
        emoji = "😄" if bono_final >= 60 else ("🙂" if bono_final >= 40 else "😐")
        msg = "¡Vas bien!" if bono_final >= 50 else "Puedes mejorar"
        r.html(f"""
        <div style="background:linear-gradient(135deg,{COLOR_PINK_PRIMARY} 0%,{COLOR_PINK_LIGHT} 50%,{COLOR_BLUE_PRIMARY} 100%);border-radius:16px;padding:22px;margin-bottom:6px;text-align:center;color:white;">
            <p style="font-size:14px;opacity:0.95;margin:0 0 6px;">Tu bono va en</p>
            <p style="font-size:52px;font-weight:500;margin:0;line-height:1;">{bono_final:.0f}%</p>
            <div style="margin-top:10px;font-size:14px;">{emoji} {msg}</div>
            <div style="border-top:0.5px solid rgba(255,255,255,0.3);margin-top:14px;padding-top:12px;font-size:11px;opacity:0.9;">
                PS {pct_ps:.0f}% × OOS {mult_oos:.0f}% × Tope 70% = {bono_final:.0f}%
            </div>
        </div>
        """)
    else:
        r.html(f"""
        <div style="background:linear-gradient(135deg,{COLOR_PINK_PRIMARY} 0%,{COLOR_PINK_LIGHT} 50%,{COLOR_BLUE_PRIMARY} 100%);border-radius:16px;padding:22px;margin-bottom:6px;text-align:center;color:white;position:relative;overflow:hidden;">
            <div style="position:absolute;inset:0;background:rgba(255,255,255,0.55);border-radius:16px;"></div>
            <div style="position:relative;z-index:1;opacity:0.55;">
                <p style="font-size:13px;opacity:0.95;margin:0 0 6px;">Tu bono potencial</p>
                <p style="font-size:52px;font-weight:500;margin:0;line-height:1;">{bono_potencial:.0f}%</p>
                <p style="font-size:11px;margin:8px 0 0;opacity:0.85;">PS {pct_ps:.0f}% × OOS {mult_oos:.0f}% × Tope 70%</p>
            </div>
            <div style="position:relative;z-index:2;margin-top:14px;display:flex;align-items:center;justify-content:center;gap:6px;background:rgba(181,48,63,0.95);padding:8px 14px;border-radius:10px;">
                <span style="font-size:18px;">🔒</span>
                <span style="font-size:13px;font-weight:500;">Bloqueado por candado</span>
            </div>
        </div>
        """)


def _render_candado_supervisor(abierto, ef):
    if abierto:
        r.html(f"""
        <div style="background:{COLOR_GREEN_PALE};border:0.5px solid {COLOR_GREEN_BORDER};border-radius:12px;padding:14px;margin-bottom:10px;display:flex;align-items:center;gap:12px;">
            <span style="font-size:28px;">🔓</span>
            <div style="flex:1;">
                <p style="font-size:13px;font-weight:500;color:{COLOR_GREEN_TEXT};margin:0;">Candado abierto</p>
                <p style="font-size:12px;color:{COLOR_GREEN};margin:2px 0 0;">Efectividad {ef:.0f}% (mínimo 95%)</p>
            </div>
            <span style="font-size:22px;color:{COLOR_GREEN};">✓</span>
        </div>
        """)
    else:
        r.html(f"""
        <div style="background:{COLOR_RED_PALE};border:0.5px solid {COLOR_RED_BORDER};border-radius:12px;padding:14px;margin-bottom:10px;display:flex;align-items:center;gap:12px;">
            <span style="font-size:28px;">🔒</span>
            <div style="flex:1;">
                <p style="font-size:13px;font-weight:500;color:{COLOR_RED_DARK};margin:0;">Candado cerrado</p>
                <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Efectividad {ef:.0f}% (mínimo 95%)</p>
            </div>
            <span style="font-size:22px;color:{COLOR_RED_DARK};">✗</span>
        </div>
        """)


def _render_kpis_supervisor(resumen):
    col1, col2 = st.columns(2, gap="small")
    with col1:
        r.html(f"""
        <div style="background:{COLOR_PINK_PALE};border:0.5px solid {COLOR_PINK_BORDER};border-radius:12px;padding:14px;text-align:center;margin-bottom:12px;">
            <p style="font-size:12px;color:{COLOR_PINK_TEXT};margin:0 0 4px;">% PS general</p>
            <p style="font-size:26px;font-weight:500;margin:4px 0;color:{COLOR_NAVY};">{resumen['PCT_PS']:.0f}%</p>
            <p style="font-size:11px;color:{COLOR_PINK_TEXT_LIGHT};margin:0;">{int(resumen['PS_ELEGIBLES'] + resumen['PS_BONUS_MAYO_DEPTO'])} de {int(resumen['TIENDAS_CAPTURADAS'])} capturadas</p>
        </div>
        """)
    with col2:
        r.html(f"""
        <div style="background:{COLOR_BLUE_PALE};border:0.5px solid {COLOR_BLUE_BORDER_DARK};border-radius:12px;padding:14px;text-align:center;margin-bottom:12px;">
            <p style="font-size:12px;color:{COLOR_BLUE_DARK};margin:0 0 4px;">Multiplicador OOS</p>
            <p style="font-size:26px;font-weight:500;margin:4px 0;color:{COLOR_GREEN};">{resumen['MULT_OOS_PCT']:.0f}%</p>
            <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">{int(resumen['NO_CONT_OOS'])} sin contestar de {int(resumen['OBJ_OOS'])}</p>
        </div>
        """)


def _render_cobran_no_cobran(supervisor, periodo_id):
    """Indicador: cuántos promotores cobrarán bono (candado abierto) y cuántos no."""
    df = get_promotores_de_supervisor(supervisor, periodo_id)
    if len(df) == 0:
        return

    total = len(df)
    # Cobra = candado abierto Y al menos 1% de PS.
    # No cobra = candado cerrado, O candado abierto pero 0% de PS.
    cobran = int(((df['candado_abierto'] == True) & (df['pct_ps_ruta'] >= 1)).sum())
    no_cobran = total - cobran

    r.html(f"""
    <div style="margin:14px 0;">
        <p style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin:0 0 8px;">Tu equipo este mes</p>
        <div style="display:flex;gap:10px;">
            <div style="flex:1;background:{COLOR_GREEN_PALE};border-radius:12px;padding:14px;text-align:center;border:0.5px solid {COLOR_GREEN_BORDER};">
                <p style="font-size:28px;font-weight:600;color:{COLOR_GREEN};margin:0;line-height:1;">{cobran}</p>
                <p style="font-size:12px;color:{COLOR_GREEN_TEXT};margin:6px 0 0;">✅ Cobrarán bono</p>
            </div>
            <div style="flex:1;background:{COLOR_RED_PALE};border-radius:12px;padding:14px;text-align:center;border:0.5px solid {COLOR_RED_BORDER};">
                <p style="font-size:28px;font-weight:600;color:{COLOR_RED_DARK};margin:0;line-height:1;">{no_cobran}</p>
                <p style="font-size:12px;color:{COLOR_RED_DARK};margin:6px 0 0;">🔒 No cobrarán</p>
            </div>
        </div>
        <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:8px 0 0;text-align:center;">
            De {total} promotores · cobra quien cierra con candado abierto (≥95% visitas) y al menos 1% de PS
        </p>
    </div>
    """)


def _render_cerca_80(supervisor, periodo_id):
    cerca_raw = get_promotores_cerca_80(supervisor, periodo_id, top_n=3)
    cerca = pd.DataFrame([adaptar_promotor(r) for _, r in cerca_raw.iterrows()]) if len(cerca_raw)>0 else cerca_raw
    if len(cerca) == 0:
        return
    items = ""
    for _, p in cerca.iterrows():
        ruta_corta = p['RUTA']
        pct_ps = p['PCT_PS_RUTA']
        falta = max(1, int(p['TIENDAS_CAPTURADAS'] * 0.80) - int(p['PS_ELEGIBLES'] + p['PS_BONUS_MAYO_DEPTO']))
        items += (
            f'<div style="background:{COLOR_PINK_PALE};border-radius:10px;padding:10px 12px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">'
            f'<div style="flex:1;min-width:0;">'
            f'<p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">{ruta_corta}</p>'
            f'<p style="font-size:11px;color:{COLOR_PINK_TEXT};margin:2px 0 0;">Va en {pct_ps:.0f}% PS · le faltan {falta} tienda(s)</p>'
            f'</div>'
            f'<span style="background:{COLOR_WHITE};color:{COLOR_PINK_TEXT};font-size:14px;font-weight:500;padding:4px 10px;border-radius:8px;border:0.5px solid {COLOR_PINK_BORDER};">{pct_ps:.0f}%</span>'
            f'</div>'
        )
    bloque = (
        f'<div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};border-radius:12px;padding:14px;margin-bottom:12px;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
        f'<span style="font-size:18px;">🎯</span>'
        f'<p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">Promotores cerca del 80%</p>'
        f'</div>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 12px;">Estos con un empujón llegan al 100% del pago</p>'
        f'{items}'
        f'</div>'
    )
    r.html(bloque)


def _render_alertas(supervisor, periodo_id):
    df_raw = get_promotores_de_supervisor(supervisor, periodo_id)
    if len(df_raw)==0:
        return
    alertas_raw = df_raw[df_raw['candado_abierto']==False].head(5)
    if len(alertas_raw)==0:
        return
    alertas = pd.DataFrame([adaptar_promotor(r) for _, r in alertas_raw.iterrows()])
    if len(alertas) == 0:
        return
    items = ""
    for _, p in alertas.iterrows():
        ruta = p['RUTA']
        ef = p['EFECTIVIDAD_PCT']
        faltantes = int(p.get('VISITAS_FALTANTES_95', 0))
        items += (
            f'<div style="background:{COLOR_WHITE};border-radius:10px;padding:10px 12px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">'
            f'<div style="flex:1;min-width:0;">'
            f'<p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">{ruta}</p>'
            f'<p style="font-size:11px;color:{COLOR_RED_DARK};margin:2px 0 0;">Candado cerrado · efectividad {ef:.0f}%, faltan {faltantes} visitas</p>'
            f'</div>'
            f'<span style="font-size:16px;color:{COLOR_PINK_TEXT_LIGHT};">›</span>'
            f'</div>'
        )
    bloque = (
        f'<div style="background:{COLOR_RED_PALE};border:0.5px solid {COLOR_RED_BORDER};border-radius:12px;padding:14px;margin-bottom:12px;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
        f'<span style="font-size:18px;">⚠️</span>'
        f'<p style="font-size:13px;font-weight:500;color:{COLOR_RED_DARK};margin:0;">Atención urgente ({len(alertas)})</p>'
        f'</div>'
        f'{items}'
        f'</div>'
    )
    r.html(bloque)


def _render_ranking(supervisor, periodo_id):
    mejor_raw, peor_raw = get_mejor_y_peor_promotor(supervisor, periodo_id)
    mejor = adaptar_promotor(mejor_raw)
    peor = adaptar_promotor(peor_raw)
    if mejor is None or peor is None:
        return
    r.html(f"""
    <div style="background:linear-gradient(135deg,{COLOR_PINK_PALE} 0%,{COLOR_BLUE_PALE} 100%);border-radius:12px;padding:14px;margin-bottom:14px;border:0.5px solid {COLOR_BLUE_BORDER};">
        <p style="font-size:13px;font-weight:500;margin:0 0 12px;color:{COLOR_NAVY};">Ranking de tu equipo</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div style="background:{COLOR_WHITE};border-radius:10px;padding:12px;border:0.5px solid {COLOR_GREEN_BORDER};">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="font-size:14px;">🏆</span>
                    <p style="font-size:11px;color:{COLOR_GREEN};margin:0;font-weight:500;">Tu mejor</p>
                </div>
                <p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">{mejor['RUTA']}</p>
                <p style="font-size:18px;font-weight:500;margin:6px 0 0;color:{COLOR_GREEN};">{mejor['BONO_FINAL_PCT']:.0f}%</p>
            </div>
            <div style="background:{COLOR_WHITE};border-radius:10px;padding:12px;border:0.5px solid {COLOR_RED_BORDER};">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
                    <span style="font-size:14px;">⚠️</span>
                    <p style="font-size:11px;color:{COLOR_RED_DARK};margin:0;font-weight:500;">Tu menor</p>
                </div>
                <p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">{peor['RUTA']}</p>
                <p style="font-size:18px;font-weight:500;margin:6px 0 0;color:{COLOR_RED_DARK};">{peor['BONO_FINAL_PCT']:.0f}%</p>
            </div>
        </div>
    </div>
    """)
