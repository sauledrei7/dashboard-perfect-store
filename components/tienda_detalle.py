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
from data import get_detalle_tienda, get_tienda_info, adaptar_detalle, adaptar_tiendas, get_resumen_promotor, adaptar_promotor, get_oos_tienda, get_oos_tienda_semana


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
    canal_raw = info.get('CANAL', info.get('Canal', 'Sin canal'))
    # Mapear a etiqueta amigable
    canal_map = {
        'AUTOSERVICIOS': 'Autoservicio',
        'CASH&CARRY': 'Cash & Carry',
        'CASH & CARRY': 'Cash & Carry',
        'MAYORISTAS': 'Mayorista',
        'DEPARTAMENTALES': 'Departamental',
    }
    canal = canal_map.get(str(canal_raw).upper().strip(), str(canal_raw).title())
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

    # Tomar objetivos de la PRIMERA fila no-incidencia (todas las semanas tienen el mismo obj)
    fila_obj = detalle[detalle.get('Incidencia', 0) != 1]
    if len(fila_obj) == 0:
        fila_obj = detalle
    fila_obj = fila_obj.iloc[0] if len(fila_obj) > 0 else None
    
    # Helper: obtener objetivo desde detalle o info, sin defaults hardcodeados
    def _get_obj(key):
        v = None
        if fila_obj is not None and key in fila_obj.index:
            v = fila_obj.get(key)
            if pd.isna(v): v = None
        if v is None and info:
            v = info.get(key)
            if pd.isna(v): v = None
        return v
    
    obj_w = _get_obj('Objetivo Whisky')
    obj_t = _get_obj('Objetivo Tequila')
    obj_v = _get_obj('Objetivo Vodka')
    obj_e = _get_obj('Objetivo Puntos HS')
    
    # Si vienen en escala 0-1, multiplicar por 100. Si en 0-100, dejar igual.
    if obj_w is not None and obj_w <= 1.5: obj_w *= 100
    if obj_t is not None and obj_t <= 1.5: obj_t *= 100
    if obj_v is not None and obj_v <= 1.5: obj_v *= 100
    
    # Detectar si es bonus (Mayoreo/Departamental)
    canal_actual = info.get('CANAL', info.get('Canal', '')).upper().strip() if info else ''
    es_bonus = canal_actual in ('MAYORISTAS', 'DEPARTAMENTALES')
    canal_label = 'Mayoreo' if canal_actual == 'MAYORISTAS' else ('Departamental' if canal_actual == 'DEPARTAMENTALES' else canal_actual.title())
    
    # Si es Mayoreo o Departamental: SIEMPRE mostrar aviso (con o sin AOP)
    if es_bonus:
        sin_aop = (obj_w is None and obj_t is None and obj_v is None)
        if sin_aop:
            mensaje_extra = "Esta tienda no tiene objetivos SOS asignados."
        else:
            mensaje_extra = "Esta tienda tiene objetivos SOS, pero no cuenta al denominador del bono."
        r.html(f"""
        <div style="background:{COLOR_PINK_PALE};border-radius:12px;padding:14px;margin:14px 0;border:0.5px solid {COLOR_BLUE_BORDER};">
            <p style="font-size:13px;color:{COLOR_NAVY};margin:0;line-height:1.5;">
                ⭐ Esta tienda es de canal <strong>{canal_label}</strong>. {mensaje_extra}
                Si logra ser PS, suma como <strong>BONUS</strong> al numerador del cálculo del bono.
            </p>
        </div>
        """)
    
    # Renderizar KPIs (cada uno se autoexcluye si su objetivo es None)
    if not (obj_w is None and obj_t is None and obj_v is None):
        _render_kpi(detalle, semanas, 'Total Whisky', "SOS Whisky", obj_w, es_pct=True)
        _render_kpi(detalle, semanas, 'Total tequila', "SOS Tequila", obj_t, es_pct=True)
        _render_kpi(detalle, semanas, 'Total vodka', "SOS Vodka", obj_v, es_pct=True)
        _render_kpi(detalle, semanas, 'Puntos Promedio Exhibición', "EXH", obj_e, es_pct=False)
    elif obj_e is not None:
        # Sin SOS pero con EXH: mostrar solo EXH
        _render_kpi(detalle, semanas, 'Puntos Promedio Exhibición', "EXH", obj_e, es_pct=False)

    _render_tabla_exh(detalle, semanas)
    _render_visitas(detalle, semanas, periodo_id)

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
    
    # Si el objetivo es None (tienda sin AOP, ej. Mayorista), no mostramos esta sección
    if objetivo is None or (isinstance(objetivo, float) and pd.isna(objetivo)):
        return
    
    # Asegurar que objetivo es numérico
    try:
        objetivo = float(objetivo)
    except (ValueError, TypeError):
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

    # Si el objetivo es 0, la tienda no tiene meta cargada para esta categoría:
    # mostramos los valores en gris con carita neutra (no podemos juzgar cumplimiento).
    sin_objetivo = (objetivo == 0)

    if sin_objetivo:
        emoji = "😐"
    elif prom >= objetivo:
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
        elif sin_objetivo:
            # Sin objetivo: gris siempre, sin juicio de cumplimiento
            valor_txt = f"{v:.0f}%" if es_pct else f"{v:.0f}"
            cuadros += (
                f'<div style="text-align:center;">'
                f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{int(s)}</p>'
                f'<div style="background:{COLOR_BLUE_BG};border-radius:8px;padding:6px;">'
                f'<p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_TEXT_SECONDARY};">{valor_txt}</p>'
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
    if sin_objetivo:
        obj_txt = "sin objetivo asignado"
    else:
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


def _render_visitas(detalle, semanas, periodo_id):
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
                f'<p style="font-size:10px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Sin dato</p>'
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
                f'<p style="font-size:10px;color:{COLOR_AMBER};margin:2px 0 0;">Incidencia</p>'
                f'</div></div>'
            )
        else:
            cuadros += (
                f'<div style="text-align:center;">'
                f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{int(s)}</p>'
                f'<div style="background:{COLOR_GREEN_PALE};border-radius:8px;padding:6px;">'
                f'<span style="font-size:18px;color:{COLOR_GREEN};">✓</span>'
                f'<p style="font-size:10px;color:{COLOR_GREEN_TEXT};margin:2px 0 0;">Visitada</p>'
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

    # ===== OOS de ESTA tienda (desglose por semana) =====
    # v9.3: se quitó la tarjeta del multiplicador OOS de la ruta (total del mes);
    # en el detalle de tienda solo mostramos el OOS de la tienda por semana.
    _render_oos_tienda(detalle, periodo_id)


def _render_oos_tienda(detalle, periodo_id):
    """v9: OOS de ESTA tienda. Muestra desglose por semana (última captura por
    Store x Product x Semana) + total del periodo. Si no tiene objetivo, no aparece."""
    if 'Store Number' not in detalle.columns or len(detalle) == 0:
        return
    curt = str(detalle.iloc[0]['Store Number'])

    # Total del periodo (tabla oos_tienda)
    d = get_oos_tienda(curt, periodo_id)
    if not d:
        return
    obj_tot = int(d.get('obj_oos', 0) or 0)
    cont_tot = int(d.get('contestadas_oos', 0) or 0)
    no_cont_tot = int(d.get('no_cont_oos', 0) or 0)
    if obj_tot <= 0:
        return
    pct_tot = d.get('pct_contestadas')
    pct_tot = float(pct_tot) if pct_tot is not None else (cont_tot / obj_tot * 100)

    # Desglose por semana (tabla oos_tienda_semana)
    dfs = get_oos_tienda_semana(curt, periodo_id)

    def _col(pct):
        if pct >= 95: return COLOR_GREEN, COLOR_GREEN_PALE, COLOR_GREEN_TEXT
        if pct >= 85: return COLOR_AMBER, COLOR_AMBER_PALE, COLOR_AMBER
        return COLOR_RED_DARK, COLOR_RED_PALE, COLOR_RED_DARK

    titulo = (
        f'<p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:14px 4px 8px;font-weight:500;">'
        f'OOS de esta tienda</p>'
    )
    r.html(titulo)

    # ----- Cuadritos por semana (obj / contestadas) -----
    cuadros = ""
    if len(dfs) > 0:
        semanas_oos = dfs.sort_values('semana')
        n_sem = len(semanas_oos)
        for _, row in semanas_oos.iterrows():
            s = int(row['semana'])
            obj = int(row.get('obj_oos', 0) or 0)
            cont = int(row.get('contestadas_oos', 0) or 0)
            if obj <= 0:
                cuadros += (
                    f'<div style="text-align:center;">'
                    f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{s}</p>'
                    f'<div style="background:{COLOR_BLUE_BG};border-radius:8px;padding:6px;">'
                    f'<p style="font-size:13px;font-weight:500;margin:0;color:{COLOR_TEXT_SECONDARY};">—</p>'
                    f'</div></div>'
                )
                continue
            pct = cont / obj * 100
            color, bg, _t = _col(pct)
            cuadros += (
                f'<div style="text-align:center;">'
                f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{s}</p>'
                f'<div style="background:{bg};border-radius:8px;padding:6px;">'
                f'<p style="font-size:14px;font-weight:500;margin:0;color:{color};">{cont}/{obj}</p>'
                f'<p style="font-size:9px;color:{color};margin:1px 0 0;">{pct:.0f}%</p>'
                f'</div></div>'
            )

    color_t, bg_t, _tt = _col(pct_tot)
    grid = (
        f'<div style="display:grid;grid-template-columns:repeat({len(dfs)}, 1fr);gap:6px;margin-bottom:12px;">{cuadros}</div>'
        if len(dfs) > 0 else
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 10px;">Sin desglose semanal disponible.</p>'
    )

    tarjeta = (
        f'<div style="background:{COLOR_WHITE};border-radius:12px;padding:14px;margin-bottom:10px;'
        f'border:0.5px solid {COLOR_BLUE_BORDER};">'
        f'{grid}'
        f'<div style="border-top:0.5px solid {COLOR_BLUE_BORDER};padding-top:10px;'
        f'display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="display:flex;gap:16px;">'
        f'<div style="text-align:center;">'
        f'<p style="font-size:16px;font-weight:500;color:{COLOR_NAVY};margin:0;">{obj_tot}</p>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Objetivo</p></div>'
        f'<div style="text-align:center;">'
        f'<p style="font-size:16px;font-weight:500;color:{COLOR_GREEN};margin:0;">{cont_tot}</p>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Contestadas</p></div>'
        f'<div style="text-align:center;">'
        f'<p style="font-size:16px;font-weight:500;color:{color_t if no_cont_tot > 0 else COLOR_NAVY};margin:0;">{no_cont_tot}</p>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">No contest.</p></div>'
        f'</div>'
        f'<div style="background:{bg_t};border-radius:10px;padding:6px 14px;">'
        f'<span style="font-size:20px;font-weight:600;color:{color_t};">{pct_tot:.0f}%</span>'
        f'</div>'
        f'</div></div>'
    )
    r.html(tarjeta)


def _render_multiplicador_oos(detalle, periodo_id):
    """Muestra el multiplicador OOS de la ruta del promotor (es del mes completo,
    aplica al bono — el detalle por tienda está en la tarjeta de arriba)."""
    if 'Ruta' not in detalle.columns or len(detalle) == 0:
        return
    ruta = detalle.iloc[0]['Ruta']
    k = adaptar_promotor(get_resumen_promotor(ruta, periodo_id))
    if not k:
        return

    mult = k.get('MULT_OOS_PCT', 100)
    obj = int(k.get('OBJ_OOS', 0) or 0)
    no_cont = int(k.get('NO_CONT_OOS', 0) or 0)

    # Color según el multiplicador
    if mult >= 95:
        color = COLOR_GREEN
        bg = COLOR_GREEN_PALE
    elif mult >= 85:
        color = COLOR_AMBER
        bg = COLOR_AMBER_PALE
    else:
        color = COLOR_RED_DARK
        bg = COLOR_RED_PALE

    titulo = (
        f'<p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:14px 4px 8px;font-weight:500;">'
        f'Multiplicador OOS</p>'
    )
    r.html(titulo)

    tarjeta = (
        f'<div style="background:{COLOR_WHITE};border-radius:12px;padding:14px;margin-bottom:10px;'
        f'border:0.5px solid {COLOR_BLUE_BORDER};">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">'
        f'<div>'
        f'<p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:0;">Multiplicador de tu ruta</p>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Suma TODAS tus tiendas · aplica al bono del mes</p>'
        f'</div>'
        f'<div style="background:{bg};border-radius:10px;padding:8px 16px;">'
        f'<span style="font-size:22px;font-weight:600;color:{color};">{mult:.0f}%</span>'
        f'</div></div>'
        f'<div style="display:flex;gap:8px;border-top:0.5px solid {COLOR_BLUE_BORDER};padding-top:10px;">'
        f'<div style="flex:1;text-align:center;">'
        f'<p style="font-size:16px;font-weight:500;color:{COLOR_NAVY};margin:0;">{obj}</p>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Objetivo</p>'
        f'</div>'
        f'<div style="flex:1;text-align:center;">'
        f'<p style="font-size:16px;font-weight:500;color:{color};margin:0;">{no_cont}</p>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">No contestadas</p>'
        f'</div>'
        f'</div></div>'
    )
    r.html(tarjeta)
