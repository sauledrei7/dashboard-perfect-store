"""
PANTALLA 1 — Resumen del promotor.
Muestra: bono (con candado), KPIs, cumplimientos por categoría, oportunidades, alertas, visitas.
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
    COLOR_AMBER, COLOR_RED, COLOR_RED_DARK, COLOR_RED_PALE, COLOR_RED_BORDER,
    COLOR_GRAY_LIGHT, COLOR_WHITE,
    color_semaforo, mensaje_segun_bono,
)
from data import (
    get_resumen_promotor, get_tiendas_de_ruta, get_tiendas_cerca_ps,
    adaptar_promotor, adaptar_tiendas, get_periodo_descripcion
)


def render(usuario: dict, periodo_id: str, solo_lectura: bool = False):
    """Renderiza la pantalla del resumen del promotor.

    solo_lectura=True (v12): la misma vista pero embebida en la pantalla del
    supervisor/AM. Omite el saludo "Hola", el botón Salir y el botón de tiendas,
    porque esos los pone la pantalla contenedora. Así el supervisor ve EXACTAMENTE
    lo que ve su promotor, sin mantener dos versiones del mismo layout."""
    ruta = usuario['identificador']
    periodo_desc = get_periodo_descripcion(periodo_id)
    resumen = adaptar_promotor(get_resumen_promotor(ruta, periodo_id))

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

    candado_abierto = bool(resumen['CANDADO_ABIERTO'])
    bono_potencial = resumen['BONO_POTENCIAL_PCT']
    bono_final = resumen['BONO_FINAL_PCT']
    pct_ps = resumen['PCT_PS_RUTA']
    mult_oos = resumen['MULT_OOS_PCT']
    efectividad = resumen['EFECTIVIDAD_PCT']
    visitas_faltantes = int(resumen.get('VISITAS_FALTANTES_95', 0))

    # ===== HEADER =====
    if not solo_lectura:
        col1, col2 = st.columns([4, 1])
        with col1:
            r.html(f"""
            <div>
                <p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:0;">Hola {usuario['nombre']}</p>
                <p style="font-size:18px;font-weight:500;margin:2px 0 0;color:{COLOR_NAVY};">Ruta {ruta}</p>
            </div>
            """)
        with col2:
            if st.button("Salir", key="logout_btn"):
                from auth import cerrar_sesion
                cerrar_sesion()
                st.rerun()

        r.html(f"""
        <div style="background:{COLOR_BLUE_BG};border-radius:10px;padding:10px 12px;margin:14px 0 12px 0;border:0.5px solid {COLOR_BLUE_BORDER};">
            <span style="font-size:13px;color:{COLOR_TEXT_SECONDARY};">📅 Periodo:</span>
            <span style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin-left:6px;">{periodo_desc}</span>
        </div>
        """)

    # ===== HERO DEL BONO =====
    _render_bono_hero(bono_potencial, bono_final, pct_ps, mult_oos, candado_abierto)

    # ===== ALERTA DE CANDADO CERRADO (si aplica) =====
    if not candado_abierto:
        r.html(f"""
        <div style="background:{COLOR_RED_PALE};border-radius:0 0 12px 12px;padding:12px 14px;margin-top:-8px;margin-bottom:14px;border:0.5px solid {COLOR_RED_BORDER};border-top:none;">
            <div style="display:flex;align-items:flex-start;gap:8px;">
                <span style="font-size:20px;">⚠️</span>
                <div>
                    <p style="font-size:12px;font-weight:500;color:{COLOR_RED_DARK};margin:0;">No vas a cobrar bono este mes</p>
                    <p style="font-size:11px;color:{COLOR_RED_DARK};margin:4px 0 0;line-height:1.5;">
                        Tu efectividad va en {efectividad:.0f}%. Necesitas al menos 95% para liberar el bono.
                        Te faltan <strong>{visitas_faltantes} visitas</strong> por hacer.
                    </p>
                </div>
            </div>
        </div>
        """)

    # ===== CANDADO STATUS =====
    _render_candado(candado_abierto, efectividad)

    # ===== KPIs: %PS y Multiplicador OOS =====
    _render_kpis_ps_oos(resumen)

    # ===== CUMPLIMIENTO POR CATEGORÍA =====
    _render_cumplimiento_categorias(resumen)

    # ===== CERCA DE SER PS =====
    _render_cerca_ps(ruta, periodo_id)

    # ===== VISITAS =====
    _render_visitas(resumen)

    # ===== BOTÓN VER TIENDAS =====
    if not solo_lectura:
        st.write("")
        if st.button("Ver mis tiendas →", key="ver_tiendas_btn"):
            st.session_state.pantalla = 'tiendas_promotor'
            st.rerun()


def _render_bono_hero(bono_potencial, bono_final, pct_ps, mult_oos, candado_abierto):
    """Bono grande con gradiente. Atenuado si candado cerrado."""
    valor_mostrar = bono_potencial  # Siempre mostrar potencial
    label = "Tu bono va en" if candado_abierto else "Tu bono potencial"
    msg = mensaje_segun_bono(bono_final if candado_abierto else 0)
    emoji = "😄" if (candado_abierto and bono_final >= 60) else ("😟" if not candado_abierto else "🙂")

    if candado_abierto:
        # Versión normal
        r.html(f"""
        <div style="background:linear-gradient(135deg,{COLOR_PINK_PRIMARY} 0%,{COLOR_PINK_LIGHT} 50%,{COLOR_BLUE_PRIMARY} 100%);border-radius:16px;padding:22px;margin-bottom:14px;text-align:center;color:white;">
            <p style="font-size:14px;opacity:0.95;margin:0 0 6px;">{label}</p>
            <p style="font-size:52px;font-weight:500;margin:0;line-height:1;">{valor_mostrar:.0f}%</p>
            <div style="margin-top:10px;font-size:14px;">{emoji} {msg}</div>
            <div style="border-top:0.5px solid rgba(255,255,255,0.3);margin-top:14px;padding-top:12px;font-size:11px;opacity:0.9;">
                PS {pct_ps:.0f}% × OOS {mult_oos:.0f}%
            </div>
        </div>
        """)
    else:
        # Versión atenuada con overlay
        r.html(f"""
        <div style="background:linear-gradient(135deg,{COLOR_PINK_PRIMARY} 0%,{COLOR_PINK_LIGHT} 50%,{COLOR_BLUE_PRIMARY} 100%);border-radius:16px;padding:22px;margin-bottom:6px;text-align:center;color:white;position:relative;overflow:hidden;">
            <div style="position:absolute;inset:0;background:rgba(255,255,255,0.55);border-radius:16px;"></div>
            <div style="position:relative;z-index:1;opacity:0.55;">
                <p style="font-size:13px;opacity:0.95;margin:0 0 6px;">{label}</p>
                <p style="font-size:52px;font-weight:500;margin:0;line-height:1;">{valor_mostrar:.0f}%</p>
                <p style="font-size:11px;margin:8px 0 0;opacity:0.85;">PS {pct_ps:.0f}% × OOS {mult_oos:.0f}% = {valor_mostrar:.0f}%</p>
            </div>
            <div style="position:relative;z-index:2;margin-top:14px;display:flex;align-items:center;justify-content:center;gap:6px;background:rgba(181,48,63,0.95);padding:8px 14px;border-radius:10px;">
                <span style="font-size:18px;">🔒</span>
                <span style="font-size:13px;font-weight:500;">Bloqueado por candado</span>
            </div>
        </div>
        """)


def _render_candado(abierto, efectividad):
    """Tarjeta del candado abierto/cerrado."""
    if abierto:
        r.html(f"""
        <div style="background:{COLOR_GREEN_PALE};border:0.5px solid {COLOR_GREEN_BORDER};border-radius:12px;padding:14px;margin-bottom:12px;display:flex;align-items:center;gap:12px;">
            <span style="font-size:28px;">🔓</span>
            <div style="flex:1;">
                <p style="font-size:13px;font-weight:500;color:{COLOR_GREEN_TEXT};margin:0;">Candado abierto</p>
                <p style="font-size:12px;color:{COLOR_GREEN};margin:2px 0 0;">Efectividad {efectividad:.0f}% (mínimo 95%)</p>
            </div>
            <span style="font-size:22px;color:{COLOR_GREEN};">✓</span>
        </div>
        """)
    else:
        r.html(f"""
        <div style="background:{COLOR_RED_PALE};border:0.5px solid {COLOR_RED_BORDER};border-radius:12px;padding:14px;margin-bottom:12px;display:flex;align-items:center;gap:12px;">
            <span style="font-size:28px;">🔒</span>
            <div style="flex:1;">
                <p style="font-size:13px;font-weight:500;color:{COLOR_RED_DARK};margin:0;">Candado cerrado</p>
                <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Efectividad {efectividad:.0f}% (mínimo 95%)</p>
            </div>
            <span style="font-size:22px;color:{COLOR_RED_DARK};">✗</span>
        </div>
        """)


def _render_kpis_ps_oos(resumen):
    """Dos tarjetas: %PS y Multiplicador OOS."""
    col1, col2 = st.columns(2, gap="small")
    with col1:
        r.html(f"""
        <div style="background:{COLOR_PINK_PALE};border:0.5px solid {COLOR_PINK_BORDER};border-radius:12px;padding:14px;text-align:center;margin-bottom:12px;">
            <p style="font-size:12px;color:{COLOR_PINK_TEXT};margin:0 0 4px;">% PS de ruta</p>
            <p style="font-size:26px;font-weight:500;margin:4px 0;color:{COLOR_NAVY};">{resumen['PCT_PS_RUTA']:.0f}%</p>
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


def _render_cumplimiento_categorias(resumen):
    """4 círculos con SOS Whisky/Tequila/Vodka y EXH."""
    sos_w = resumen['SOS_WHISKY_PROM']
    sos_t = resumen['SOS_TEQUILA_PROM']
    sos_v = resumen['SOS_VODKA_PROM']
    exh_ratio = float(resumen['EXH_4_PROM'])  # 0 a 1: % tiendas que cumplieron EXH 4
    exh_pct = exh_ratio * 100  # convertir a %

    # Objetivos: 35% whisky, 30% tequila, 25% vodka, 80% EXH (% tiendas que cumplen)
    color_w = _color_categoria(sos_w, 35)
    color_t = _color_categoria(sos_t, 30)
    color_v = _color_categoria(sos_v, 25)
    color_e = _color_categoria(exh_pct, 80)

    r.html(f"""
    <div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};border-radius:12px;padding:14px;margin-bottom:12px;">
        <p style="font-size:13px;font-weight:500;margin:0 0 12px;color:{COLOR_NAVY};">Cumplimiento por categoría</p>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;">
            <div style="text-align:center;">
                <div style="width:44px;height:44px;border-radius:50%;background:{color_w};margin:0 auto 6px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;">🥃</div>
                <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">Whisky</p>
                <p style="font-size:13px;font-weight:500;margin:2px 0 0;color:{COLOR_NAVY};">{sos_w:.0f}%</p>
            </div>
            <div style="text-align:center;">
                <div style="width:44px;height:44px;border-radius:50%;background:{color_t};margin:0 auto 6px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;">🍸</div>
                <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">Tequila</p>
                <p style="font-size:13px;font-weight:500;margin:2px 0 0;color:{COLOR_NAVY};">{sos_t:.0f}%</p>
            </div>
            <div style="text-align:center;">
                <div style="width:44px;height:44px;border-radius:50%;background:{color_v};margin:0 auto 6px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;">🍹</div>
                <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">Vodka</p>
                <p style="font-size:13px;font-weight:500;margin:2px 0 0;color:{COLOR_NAVY};">{sos_v:.0f}%</p>
            </div>
            <div style="text-align:center;">
                <div style="width:44px;height:44px;border-radius:50%;background:{color_e};margin:0 auto 6px;display:flex;align-items:center;justify-content:center;color:white;font-size:22px;">📦</div>
                <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">EXH</p>
                <p style="font-size:13px;font-weight:500;margin:2px 0 0;color:{COLOR_NAVY};">{exh_pct:.0f}%</p>
            </div>
        </div>
    </div>
    """)


def _color_categoria(valor, objetivo):
    """Verde si valor >= objetivo, ámbar si está cerca, rojo si lejos."""
    pct = valor / objetivo if objetivo > 0 else 0
    if pct >= 1.0:
        return COLOR_GREEN
    elif pct >= 0.80:
        return COLOR_AMBER
    else:
        return COLOR_RED


def _render_cerca_ps(ruta, periodo_id):
    """Top 3 tiendas que están cerca de ser PS."""
    tiendas_cerca = adaptar_tiendas(get_tiendas_cerca_ps(ruta, periodo_id, top_n=3))
    if len(tiendas_cerca) == 0:
        return

    items_html = ""
    for _, t in tiendas_cerca.iterrows():
        nombre = str(t.get('Tienda', 'Tienda'))[:30]
        falta = "Cerca de ser PS"
        puntos_exh = t.get('Puntos Promedio Exhibición', 0) or 0
        if pd.notna(puntos_exh) and puntos_exh < 4:
            falta = f"Falta EXH (va en {puntos_exh:.0f}/4)"
        elif pd.notna(t.get('Total Whisky')) and t['Total Whisky'] < 0.35:
            falta = "Falta Whisky"

        items_html += (
            f'<div style="background:{COLOR_PINK_PALE};border-radius:10px;padding:10px 12px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">'
            f'<div style="flex:1;min-width:0;">'
            f'<p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">{nombre}</p>'
            f'<p style="font-size:11px;color:{COLOR_PINK_TEXT};margin:2px 0 0;">{falta}</p>'
            f'</div>'
            f'<span style="font-size:16px;color:{COLOR_PINK_TEXT_LIGHT};">›</span>'
            f'</div>'
        )

    bloque = (
        f'<div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};border-radius:12px;padding:14px;margin-bottom:12px;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
        f'<span style="font-size:18px;">🎯</span>'
        f'<p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">Cerca de ser PS</p>'
        f'</div>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 12px;">Estas tiendas las puedes recuperar fácil</p>'
        f'{items_html}'
        f'</div>'
    )
    r.html(bloque)


def _render_visitas(resumen):
    """Barrita de progreso de visitas (hechas, incidencia, faltan)."""
    prog = int(resumen['VISITAS_PROGRAMADAS'])
    norm = int(resumen['VISITAS_NORMALES'])
    inc = int(resumen['VISITAS_INCIDENCIA'])
    falta = max(0, prog - norm - inc)
    total_real = norm + inc

    # Calcular widths proporcionales
    if prog == 0:
        return

    # Crear las barritas individuales
    barras_html = ""
    barras_html += f'<div style="flex:{norm};height:22px;background:{COLOR_GREEN};border-radius:3px;"></div>' if norm > 0 else ""
    barras_html += f'<div style="flex:{inc};height:22px;background:{COLOR_AMBER};border-radius:3px;"></div>' if inc > 0 else ""
    barras_html += f'<div style="flex:{falta};height:22px;background:{COLOR_GRAY_LIGHT};border-radius:3px;"></div>' if falta > 0 else ""

    r.html(f"""
    <div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};border-radius:12px;padding:14px;margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_NAVY};">Mis visitas</p>
            <span style="font-size:13px;color:{COLOR_TEXT_SECONDARY};">{total_real} de {prog}</span>
        </div>
        <div style="display:flex;gap:2px;">
            {barras_html}
        </div>
        <div style="display:flex;gap:12px;margin-top:10px;font-size:11px;color:{COLOR_TEXT_SECONDARY};flex-wrap:wrap;">
            <span><span style="display:inline-block;width:8px;height:8px;background:{COLOR_GREEN};border-radius:2px;margin-right:3px;"></span>Hechas {norm}</span>
            <span><span style="display:inline-block;width:8px;height:8px;background:{COLOR_AMBER};border-radius:2px;margin-right:3px;"></span>Incidencia {inc}</span>
            <span><span style="display:inline-block;width:8px;height:8px;background:{COLOR_GRAY_LIGHT};border-radius:2px;margin-right:3px;"></span>Faltan {falta}</span>
        </div>
    </div>
    """)
