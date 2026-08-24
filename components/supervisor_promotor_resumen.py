"""
PANTALLA v12 — Resumen de UN promotor visto por su supervisor (o por el AM).

Es la pantalla intermedia entre la lista de promotores y la lista de tiendas.
Muestra, en este orden:
  1. El MISMO resumen que ve el promotor al entrar (se reusa promotor_resumen
     en modo solo_lectura, para no mantener dos layouts en paralelo).
  2. Las RESPUESTAS de OOS: cuántas veces contestó cada motivo y cuántas dejó
     sin contestar (que son las que castigan el multiplicador del bono).
  3. Cuántas incidencias ha levantado en la app, por estado y por tipo.
     Solo conteo — autorizar/rechazar sigue viviendo en la bandeja del supervisor.
  4. Botón para bajar a las tiendas del promotor.

NOTA TÉCNICA: igual que en tienda_detalle.py, los bloques con loop se construyen
concatenando strings de UNA línea y se mandan en un solo r.html().
"""
import streamlit as st
import render as r
import pandas as pd
from styles.theme import (
    COLOR_PINK_PALE, COLOR_PINK_TEXT, COLOR_PINK_BORDER, COLOR_PINK_TEXT_LIGHT,
    COLOR_BLUE_PRIMARY, COLOR_BLUE_DARK, COLOR_BLUE_PALE, COLOR_BLUE_BG,
    COLOR_BLUE_BORDER, COLOR_BLUE_BORDER_DARK, COLOR_NAVY, COLOR_TEXT_SECONDARY,
    COLOR_GREEN, COLOR_GREEN_PALE, COLOR_GREEN_TEXT, COLOR_GREEN_BORDER,
    COLOR_AMBER, COLOR_AMBER_PALE,
    COLOR_RED_DARK, COLOR_RED_PALE, COLOR_RED_BORDER,
    COLOR_GRAY_LIGHT, COLOR_WHITE,
)
from data import (
    get_resumen_promotor, adaptar_promotor, get_periodo_descripcion,
    get_oos_respuestas_ruta, get_oos_ruta_por_semana, get_conteo_incidencias_ruta,
)
from components import promotor_resumen


def render(periodo_id: str, volver_a: str = 'lista_promotores'):
    """Resumen del promotor seleccionado. La ruta viene de session_state."""
    ruta = st.session_state.get('ruta_seleccionada')
    if not ruta:
        st.error("No se seleccionó ningún promotor")
        return

    periodo_desc = get_periodo_descripcion(periodo_id)

    # ===== HEADER =====
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Volver", key="back_resumen_promo"):
            st.session_state.pantalla = st.session_state.get('volver_de_resumen', volver_a)
            st.rerun()
    with col2:
        r.html(f"""
        <div>
            <p style="font-size:17px;font-weight:500;margin:0;color:{COLOR_NAVY};">{ruta}</p>
            <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Así lo ve tu promotor · {periodo_desc}</p>
        </div>
        """)

    st.write("")

    # ===== 1) EL RESUMEN TAL CUAL LO VE EL PROMOTOR =====
    promotor_resumen.render({'identificador': ruta, 'nombre': ruta}, periodo_id, solo_lectura=True)

    # Si no hay KPIs, promotor_resumen ya mostró el vacío; no seguimos.
    kpis = adaptar_promotor(get_resumen_promotor(ruta, periodo_id))
    if kpis is None:
        return

    # ===== 2) RESPUESTAS DE OOS =====
    _render_respuestas_oos(ruta, periodo_id, kpis)

    # ===== 3) INCIDENCIAS LEVANTADAS EN LA APP =====
    _render_incidencias_resumen(ruta, periodo_id)

    # ===== 4) DRILL A TIENDAS =====
    st.write("")
    if st.button(f"Ver tiendas de {ruta} →", key="ver_tiendas_de_promo"):
        st.session_state.pantalla = 'tiendas_de_promotor'
        st.rerun()


# ============================================================
# BLOQUE OOS — cuántas veces contestó cada motivo
# ============================================================
def _meta_motivo(motivo):
    """(emoji, etiqueta corta, es_sin_contestar) para cada motivo de OOS.
    Se hace por substring y no por texto exacto porque la redacción del catálogo
    cambia entre meses (guiones, comillas, espacios)."""
    m = str(motivo).strip().lower()
    if 'sin contestar' in m or 'no contestada' in m:
        return ('⚠️', 'Sin contestar', True)
    # Contestada pero TRAX no guardó el texto: cuenta como contestada (no castiga)
    if 'sin motivo' in m:
        return ('❔', 'Contestada sin motivo', False)
    if 'no hay inventario' in m:
        return ('📦', 'Sin inventario en tienda', False)
    if 'trax' in m:
        return ('👁️', 'En anaquel, no lo vio TRAX', False)
    if 'bodega' in m:
        return ('🏬', 'En bodega, no en anaquel', False)
    if 'fantasma' in m:
        return ('👻', 'Inventario fantasma', False)
    if 'catalogado' in m:
        return ('🏷️', 'SKU no catalogado', False)
    if 'no puede exhibirse' in m:
        return ('🚫', 'No se puede exhibir', False)
    if 'obstruido' in m or 'bloqueado' in m:
        return ('⛔', 'Obstruido en anaquel', False)
    if 'militraje' in m:
        return ('📏', 'Militraje no reconocido', False)
    if 'nueva imagen' in m:
        return ('🖼️', 'Nueva imagen', False)
    return ('•', str(motivo)[:45], False)


def _render_respuestas_oos(ruta, periodo_id, kpis):
    """Desglose de las respuestas de OOS del promotor: cuántas veces contestó
    cada motivo, más las que dejó sin contestar."""
    obj = int(kpis.get('OBJ_OOS', 0) or 0)
    no_cont = int(kpis.get('NO_CONT_OOS', 0) or 0)
    contestadas = max(0, obj - no_cont)
    mult = float(kpis.get('MULT_OOS_PCT', 100) or 100)

    if obj <= 0:
        return

    r.html(f"""
    <div style="margin:20px 4px 8px;display:flex;align-items:center;gap:8px;">
        <span style="font-size:18px;">💬</span>
        <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};">Respuestas de OOS</p>
    </div>
    """)

    # ----- Tarjeta de totales -----
    color_mult = COLOR_GREEN if mult >= 95 else (COLOR_AMBER if mult >= 85 else COLOR_RED_DARK)
    bg_mult = COLOR_GREEN_PALE if mult >= 95 else (COLOR_AMBER_PALE if mult >= 85 else COLOR_RED_PALE)
    r.html(
        f'<div style="background:{COLOR_WHITE};border-radius:12px;padding:14px;margin-bottom:10px;'
        f'border:0.5px solid {COLOR_BLUE_BORDER};">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="display:flex;gap:16px;">'
        f'<div style="text-align:center;">'
        f'<p style="font-size:18px;font-weight:600;color:{COLOR_NAVY};margin:0;">{obj}</p>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Objetivo</p></div>'
        f'<div style="text-align:center;">'
        f'<p style="font-size:18px;font-weight:600;color:{COLOR_GREEN};margin:0;">{contestadas}</p>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Contestadas</p></div>'
        f'<div style="text-align:center;">'
        f'<p style="font-size:18px;font-weight:600;color:{COLOR_RED_DARK if no_cont > 0 else COLOR_NAVY};margin:0;">{no_cont}</p>'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Sin contestar</p></div>'
        f'</div>'
        f'<div style="background:{bg_mult};border-radius:10px;padding:6px 14px;text-align:center;">'
        f'<span style="font-size:20px;font-weight:600;color:{color_mult};">{mult:.0f}%</span>'
        f'<p style="font-size:9px;color:{color_mult};margin:0;">multiplicador</p>'
        f'</div></div></div>'
    )

    # ----- Desglose por semana (de oos_tienda_semana, ya existe) -----
    _render_oos_semanas(ruta, periodo_id)

    # ----- Desglose por MOTIVO (tabla oos_respuestas, v12) -----
    df = get_oos_respuestas_ruta(ruta, periodo_id)
    if len(df) == 0:
        r.html(
            f'<div style="background:{COLOR_BLUE_BG};border-radius:10px;padding:12px 14px;'
            f'margin-bottom:10px;border:0.5px solid {COLOR_BLUE_BORDER};">'
            f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;line-height:1.5;">'
            f'ℹ️ El detalle de <b>qué contestó</b> en cada OOS todavía no está cargado para este periodo. '
            f'Se activa al subir la tabla <code>oos_respuestas</code>.'
            f'</p></div>'
        )
        return

    if 'motivo' not in df.columns or 'veces' not in df.columns:
        return

    # Agregamos las semanas: aquí interesa el total del periodo por motivo
    agg = df.groupby('motivo', as_index=False)['veces'].sum()
    agg['veces'] = pd.to_numeric(agg['veces'], errors='coerce').fillna(0).astype(int)
    agg = agg[agg['veces'] > 0].copy()
    if len(agg) == 0:
        return

    # Separamos "sin contestar" del resto: es la única que pega al bono
    agg['_es_sin'] = agg['motivo'].apply(lambda m: _meta_motivo(m)[2])
    contestadas_df = agg[~agg['_es_sin']].sort_values('veces', ascending=False)
    sin_df = agg[agg['_es_sin']]

    total_resp = int(contestadas_df['veces'].sum())
    max_veces = int(contestadas_df['veces'].max()) if len(contestadas_df) > 0 else 0

    filas = ""
    for _, row in contestadas_df.iterrows():
        emoji, etiqueta, _ = _meta_motivo(row['motivo'])
        veces = int(row['veces'])
        pct = (veces / total_resp * 100) if total_resp > 0 else 0
        ancho = (veces / max_veces * 100) if max_veces > 0 else 0
        filas += (
            f'<div style="padding:10px 0;border-bottom:0.5px solid {COLOR_BLUE_BORDER};">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;">'
            f'<div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;">'
            f'<span style="font-size:16px;">{emoji}</span>'
            f'<span style="font-size:12px;color:{COLOR_NAVY};line-height:1.3;">{etiqueta}</span>'
            f'</div>'
            f'<div style="text-align:right;white-space:nowrap;">'
            f'<span style="font-size:15px;font-weight:600;color:{COLOR_NAVY};">{veces}</span>'
            f'<span style="font-size:10px;color:{COLOR_TEXT_SECONDARY};margin-left:6px;">vec.</span>'
            f'<span style="font-size:10px;color:{COLOR_PINK_TEXT_LIGHT};margin-left:6px;">{pct:.0f}%</span>'
            f'</div></div>'
            f'<div style="background:{COLOR_BLUE_BG};border-radius:4px;height:6px;overflow:hidden;">'
            f'<div style="width:{ancho:.0f}%;height:6px;background:linear-gradient(90deg,{COLOR_BLUE_PRIMARY},{COLOR_PINK_TEXT_LIGHT});border-radius:4px;"></div>'
            f'</div></div>'
        )

    # Fila de "sin contestar" al final, destacada en rojo
    sin_html = ""
    if len(sin_df) > 0:
        n_sin = int(sin_df['veces'].sum())
        if n_sin > 0:
            sin_html = (
                f'<div style="background:{COLOR_RED_PALE};border-radius:10px;padding:10px 12px;margin-top:10px;'
                f'border:0.5px solid {COLOR_RED_BORDER};display:flex;justify-content:space-between;align-items:center;">'
                f'<div style="display:flex;align-items:center;gap:8px;">'
                f'<span style="font-size:16px;">⚠️</span>'
                f'<span style="font-size:12px;color:{COLOR_RED_DARK};">Sin contestar <span style="opacity:0.75;">· castiga el bono</span></span>'
                f'</div>'
                f'<span style="font-size:16px;font-weight:600;color:{COLOR_RED_DARK};">{n_sin}</span>'
                f'</div>'
            )

    r.html(
        f'<div style="background:{COLOR_WHITE};border-radius:12px;padding:6px 14px 14px;margin-bottom:10px;'
        f'border:0.5px solid {COLOR_BLUE_BORDER};">'
        f'<p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:12px 0 4px;">'
        f'Qué contestó en las {total_resp} respuestas del periodo</p>'
        f'{filas}'
        f'{sin_html}'
        f'</div>'
    )


def _render_oos_semanas(ruta, periodo_id):
    """Cuadritos S27/S28… con contestadas/objetivo de TODA la ruta."""
    dfs = get_oos_ruta_por_semana(ruta, periodo_id)
    if len(dfs) == 0:
        return

    cuadros = ""
    for _, row in dfs.iterrows():
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
        if pct >= 95:
            color, bg = COLOR_GREEN, COLOR_GREEN_PALE
        elif pct >= 85:
            color, bg = COLOR_AMBER, COLOR_AMBER_PALE
        else:
            color, bg = COLOR_RED_DARK, COLOR_RED_PALE
        cuadros += (
            f'<div style="text-align:center;">'
            f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">S{s}</p>'
            f'<div style="background:{bg};border-radius:8px;padding:6px;">'
            f'<p style="font-size:14px;font-weight:500;margin:0;color:{color};">{cont}/{obj}</p>'
            f'<p style="font-size:9px;color:{color};margin:1px 0 0;">{pct:.0f}%</p>'
            f'</div></div>'
        )

    r.html(
        f'<div style="background:{COLOR_WHITE};border-radius:12px;padding:14px;margin-bottom:10px;'
        f'border:0.5px solid {COLOR_BLUE_BORDER};">'
        f'<p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:0 0 10px;">Contestadas por semana</p>'
        f'<div style="display:grid;grid-template-columns:repeat({len(dfs)}, 1fr);gap:6px;">{cuadros}</div>'
        f'</div>'
    )


# ============================================================
# BLOQUE INCIDENCIAS — solo conteo
# ============================================================
def _render_incidencias_resumen(ruta, periodo_id):
    """Cuántas incidencias levantó el promotor en la app, por estado y por tipo.
    Solo lectura: autorizar/rechazar vive en la bandeja del resumen del supervisor."""
    c = get_conteo_incidencias_ruta(ruta, periodo_id)
    total = c.get('TOTAL', 0)

    r.html(f"""
    <div style="margin:20px 4px 8px;display:flex;align-items:center;gap:8px;">
        <span style="font-size:18px;">⚠️</span>
        <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};">Incidencias que ha levantado</p>
    </div>
    """)

    if total == 0:
        r.html(
            f'<div style="background:{COLOR_BLUE_BG};border-radius:10px;padding:14px;text-align:center;'
            f'border:0.5px solid {COLOR_BLUE_BORDER};margin-bottom:8px;">'
            f'<p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:0;">'
            f'No ha levantado incidencias este periodo.</p></div>'
        )
        return

    pend = c.get('PENDIENTES', 0)
    aut = c.get('AUTORIZADAS', 0)
    no_aut = c.get('NO_AUTORIZADAS', 0)

    # Chips por tipo
    chips = ""
    for tipo, n in sorted(c.get('POR_TIPO', {}).items(), key=lambda x: -x[1]):
        chips += (
            f'<span style="background:{COLOR_PINK_PALE};color:{COLOR_PINK_TEXT};font-size:11px;'
            f'padding:3px 10px;border-radius:8px;border:0.5px solid {COLOR_PINK_BORDER};">'
            f'{tipo} · <b>{n}</b></span>'
        )
    chips_html = (
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:12px;'
        f'padding-top:12px;border-top:0.5px solid {COLOR_BLUE_BORDER};">{chips}</div>'
    ) if chips else ""

    r.html(
        f'<div style="background:{COLOR_WHITE};border-radius:12px;padding:14px;margin-bottom:10px;'
        f'border:0.5px solid {COLOR_BLUE_BORDER};">'
        f'<div style="display:flex;align-items:center;gap:14px;">'
        f'<div style="text-align:center;min-width:64px;">'
        f'<p style="font-size:30px;font-weight:600;color:{COLOR_NAVY};margin:0;line-height:1;">{total}</p>'
        f'<p style="font-size:10px;color:{COLOR_TEXT_SECONDARY};margin:4px 0 0;">en total</p>'
        f'</div>'
        f'<div style="flex:1;display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;">'
        f'<div style="text-align:center;background:{COLOR_AMBER_PALE};border-radius:8px;padding:8px 4px;">'
        f'<p style="font-size:16px;font-weight:600;margin:0;color:{COLOR_AMBER};">{pend}</p>'
        f'<p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">⏳ Pend.</p></div>'
        f'<div style="text-align:center;background:{COLOR_GREEN_PALE};border-radius:8px;padding:8px 4px;">'
        f'<p style="font-size:16px;font-weight:600;margin:0;color:{COLOR_GREEN};">{aut}</p>'
        f'<p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">✓ Autoriz.</p></div>'
        f'<div style="text-align:center;background:{COLOR_RED_PALE};border-radius:8px;padding:8px 4px;">'
        f'<p style="font-size:16px;font-weight:600;margin:0;color:{COLOR_RED_DARK};">{no_aut}</p>'
        f'<p style="font-size:9px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">✕ Rechaz.</p></div>'
        f'</div></div>'
        f'{chips_html}'
        f'</div>'
    )
