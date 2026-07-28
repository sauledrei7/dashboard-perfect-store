"""
Bandeja de incidencias (v10) — solo VISUAL, sin descarga ni aprobación.
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
    COLOR_GREEN, COLOR_AMBER, COLOR_RED_DARK, COLOR_RED_PALE, COLOR_WHITE,
)
from data import get_incidencias_ambito, firmar_url_foto

TIPO_COLOR = {
    'SOS TEQUILA': COLOR_AMBER, 'SOS WHISKY': COLOR_AMBER, 'SOS VODKA': COLOR_AMBER,
    'EXH': COLOR_BLUE_BORDER, 'OOS': COLOR_RED_DARK,
}


def render(periodo_id: str, area_manager: str = None, supervisor: str = None, key: str = "band"):
    df = get_incidencias_ambito(periodo_id, area_manager=area_manager, supervisor=supervisor)
    n = len(df)

    # Encabezado con contador tipo notificación
    titulo = "Incidencias del área" if area_manager else "Incidencias de tu equipo"
    badge = (f'<span style="background:{COLOR_RED_DARK};color:#fff;font-size:11px;font-weight:500;'
             f'padding:2px 8px;border-radius:10px;margin-left:8px;">{n}</span>') if n > 0 else ""
    r.html(f"""
    <div style="margin:18px 4px 8px;display:flex;align-items:center;">
        <span style="font-size:18px;margin-right:6px;">🔔</span>
        <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};">{titulo}</p>
        {badge}
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
    with st.expander(f"Ver las {n} incidencias", expanded=False):
        # Orden más reciente primero
        if 'created_at' in df.columns:
            df = df.sort_values('created_at', ascending=False)
        for idx, inc in df.iterrows():
            _render_tarjeta(inc, key=f"{key}_{idx}")


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


def _render_tarjeta(inc, key):
    tipo = inc.get('tipo', '')
    color = TIPO_COLOR.get(tipo, COLOR_TEXT_SECONDARY)
    sem = inc.get('semana')
    sem_txt = f"S{int(sem)}" if pd.notna(sem) else "—"
    tienda = inc.get('tienda') or f"CURT {inc.get('curt','')}"
    ruta = inc.get('ruta', '')
    com = (inc.get('comentario') or '').strip()
    fecha = str(inc.get('created_at', ''))[:10]
    fotos = inc.get('fotos') or []

    r.html(f"""
    <div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};
    border-radius:10px;padding:10px 12px;margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="background:{COLOR_PINK_PALE};color:{color};font-size:11px;font-weight:500;
            padding:2px 8px;border-radius:6px;">{tipo}</span>
            <span style="font-size:11px;color:{COLOR_TEXT_SECONDARY};">{sem_txt} · {fecha}</span>
        </div>
        <p style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin:4px 0 0;">{tienda}</p>
        <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">Reportada por {ruta}</p>
        <p style="font-size:12px;color:{COLOR_NAVY};margin:6px 0 0;line-height:1.4;">{com}</p>
    </div>
    """)

    # Ver fotos: botón que firma las URLs on-demand
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
