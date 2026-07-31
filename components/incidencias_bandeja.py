"""
Bandeja de incidencias (v11) — el supervisor AUTORIZA/RECHAZA; AM y director solo ven.
La ven el supervisor (incidencias de sus promotores) y el AM (de toda su área).
Muestra las incidencias levantadas como una lista tipo notificaciones,
con opción de ver las fotos (URL firmada temporal).
"""
import streamlit as st
import render as r
import pandas as pd
from styles.theme import (
    COLOR_PINK_PALE, COLOR_PINK_TEXT, COLOR_PINK_BORDER, COLOR_BLUE_PALE,
    COLOR_BLUE_BG, COLOR_BLUE_BORDER, COLOR_NAVY, COLOR_TEXT_SECONDARY,
    COLOR_GREEN, COLOR_GREEN_PALE, COLOR_AMBER, COLOR_AMBER_PALE, COLOR_BLUE_DARK,
    COLOR_RED_DARK, COLOR_RED_PALE, COLOR_WHITE,
)
from data import get_incidencias_ambito, firmar_url_foto

TIPO_COLOR = {
    'SOS TEQUILA': COLOR_AMBER, 'SOS WHISKY': COLOR_AMBER, 'SOS VODKA': COLOR_AMBER,
    'EXH': COLOR_BLUE_BORDER, 'OOS': COLOR_RED_DARK,
}


def render(periodo_id: str, area_manager: str = None, supervisor: str = None,
           key: str = "band", puede_resolver: bool = None):
    df = get_incidencias_ambito(periodo_id, area_manager=area_manager, supervisor=supervisor)
    n = len(df)
    # Por defecto: solo el supervisor autoriza/rechaza; AM y director solo ven.
    if puede_resolver is None:
        puede_resolver = bool(supervisor) and not area_manager

    # Encabezado con contador tipo notificación
    titulo = "Incidencias del área" if area_manager else "Incidencias de tu equipo"
    n_pend = int((df['estado'].fillna('PENDIENTE') == 'PENDIENTE').sum()) if n > 0 and 'estado' in df.columns else 0
    badge = (f'<span style="background:{COLOR_RED_DARK};color:#fff;font-size:11px;font-weight:500;'
             f'padding:2px 8px;border-radius:10px;margin-left:8px;">{n}</span>') if n > 0 else ""
    pend_badge = (f'<span style="background:{COLOR_AMBER_PALE};color:{COLOR_AMBER};font-size:11px;font-weight:500;'
                  f'padding:2px 8px;border-radius:10px;margin-left:6px;">⏳ {n_pend} pend.</span>') if n_pend > 0 else ""
    r.html(f"""
    <div style="margin:18px 4px 8px;display:flex;align-items:center;">
        <span style="font-size:18px;margin-right:6px;">🔔</span>
        <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};">{titulo}</p>
        {badge}{pend_badge}
    </div>
    """)

    if n == 0:
        r.html(f"""
        <div style="background:{COLOR_BLUE_BG};border-radius:10px;padding:14px;text-align:center;
        border:0.5px solid {COLOR_BLUE_BORDER};margin-bottom:8px;">
            <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:0;">
                Sin incidencias reportadas este periodo.
            </p>
        </div>
        """)
        return

    # Mini-resumen por tipo
    _render_resumen_tipos(df)

    # Lista (colapsada dentro de un expander para no saturar el resumen)
    _exp_abierto = puede_resolver and n_pend > 0
    with st.expander(f"Ver las {n} incidencias", expanded=_exp_abierto):
        # Orden más reciente primero
        if 'created_at' in df.columns:
            df = df.sort_values('created_at', ascending=False)
        for idx, inc in df.iterrows():
            _render_tarjeta(inc, key=f"{key}_{idx}", puede_resolver=puede_resolver)


def _render_resumen_tipos(df):
    conteo = df['tipo'].value_counts().to_dict()
    chips = ""
    for tipo, c in conteo.items():
        color = TIPO_COLOR.get(tipo, COLOR_TEXT_SECONDARY)
        chips += (
            f'<div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};'
            f'border-radius:8px;padding:6px 10px;text-align:center;min-width:70px;">'
            f'<p style="font-size:18px;font-weight:600;margin:0;color:{color};">{c}</p>'
            f'<p style="font-size:10px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{tipo}</p>'
            f'</div>'
        )
    r.html(
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">{chips}</div>'
    )


def _render_tarjeta(inc, key, puede_resolver=False):
    tipo = inc.get('tipo', '')
    color = TIPO_COLOR.get(tipo, COLOR_TEXT_SECONDARY)
    sem = inc.get('semana')
    sem_txt = f"S{int(sem)}" if pd.notna(sem) else "—"
    tienda = inc.get('tienda') or f"CURT {inc.get('curt','')}"
    ruta = inc.get('ruta', '')
    com = (inc.get('comentario') or '').strip()
    fecha = str(inc.get('created_at', ''))[:10]
    fotos = inc.get('fotos') or []
    estado = inc.get('estado', 'PENDIENTE') or 'PENDIENTE'
    link_trax = (inc.get('link_trax') or '').strip()
    inc_id = inc.get('id')

    # Badge de estado
    if estado == 'AUTORIZADA':
        est_bg, est_color, est_txt = COLOR_GREEN_PALE, COLOR_GREEN, '✓ Autorizada'
    elif estado == 'NO_AUTORIZADA':
        est_bg, est_color, est_txt = COLOR_RED_PALE, COLOR_RED_DARK, '✕ No autorizada'
    else:
        est_bg, est_color, est_txt = COLOR_AMBER_PALE, COLOR_AMBER, '⏳ Pendiente'

    trax_html = (
        f'<a href="{link_trax}" target="_blank" style="font-size:11px;color:{COLOR_BLUE_DARK};'
        f'text-decoration:none;">🔗 Ver visita Trax</a>' if link_trax else ''
    )

    r.html(f"""
    <div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};
    border-radius:10px;padding:10px 12px;margin-bottom:4px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="background:{COLOR_PINK_PALE};color:{color};font-size:11px;font-weight:500;
            padding:2px 8px;border-radius:6px;">{tipo}</span>
            <span style="background:{est_bg};color:{est_color};font-size:11px;font-weight:500;
            padding:2px 8px;border-radius:6px;">{est_txt}</span>
        </div>
        <p style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin:4px 0 0;">{tienda}</p>
        <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{sem_txt} · {fecha} · Reportada por {ruta}</p>
        <p style="font-size:12px;color:{COLOR_NAVY};margin:6px 0 0;line-height:1.4;">{com}</p>
        <div style="margin-top:4px;">{trax_html}</div>
    </div>
    """)

    # Ver fotos
    if len(fotos) > 0:
        ver_key = f"ver_fotos_{key}"
        if st.session_state.get(ver_key):
            for i, p in enumerate(fotos[:3]):
                url = firmar_url_foto(p, 3600)
                if url:
                    st.image(url, caption=f"Foto {i+1}", use_container_width=True)
            if st.button("Ocultar fotos", key=f"hide_{key}"):
                st.session_state[ver_key] = False
                st.rerun()
        else:
            if st.button(f"📷 Ver {len(fotos)} foto(s)", key=f"show_{key}"):
                st.session_state[ver_key] = True
                st.rerun()

    # ===== Botones de aprobación (solo supervisor y solo si está PENDIENTE) =====
    if puede_resolver and estado == 'PENDIENTE' and inc_id is not None:
        _render_acciones_resolver(inc_id, key)


def _render_acciones_resolver(inc_id, key):
    from data import resolver_incidencia, get_incidencias_ambito
    rechazar_key = f"rechazando_{key}"

    if st.session_state.get(rechazar_key):
        # Modo rechazo: pedir motivo
        motivo = st.text_input("Motivo del rechazo *", key=f"motivo_{key}",
                               placeholder="Ej. la foto no corresponde a la tienda")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirmar rechazo", key=f"conf_rech_{key}", type="primary"):
                if not (motivo or '').strip():
                    st.error("Escribe el motivo del rechazo.")
                else:
                    usuario = st.session_state.get('usuario', {})
                    resolver_incidencia(inc_id, autorizar=False,
                                        resuelta_por=usuario.get('username', usuario.get('identificador', '')),
                                        motivo_rechazo=motivo.strip())
                    get_incidencias_ambito.clear() if hasattr(get_incidencias_ambito, 'clear') else None
                    st.session_state[rechazar_key] = False
                    st.rerun()
        with c2:
            if st.button("Cancelar", key=f"canc_rech_{key}"):
                st.session_state[rechazar_key] = False
                st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✓ Autorizar", key=f"aut_{key}", type="primary"):
                usuario = st.session_state.get('usuario', {})
                resolver_incidencia(inc_id, autorizar=True,
                                    resuelta_por=usuario.get('username', usuario.get('identificador', '')))
                get_incidencias_ambito.clear() if hasattr(get_incidencias_ambito, 'clear') else None
                st.rerun()
        with c2:
            if st.button("✕ Rechazar", key=f"rech_{key}"):
                st.session_state[rechazar_key] = True
                st.rerun()
