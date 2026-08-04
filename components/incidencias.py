"""
Módulo de incidencias (v10).
Formulario embebido en el detalle de tienda, SOLO para promotores.
- 1 tipo por incidencia (SOS Tequila/Whisky/Vodka, EXH, OOS)
- Semana del periodo activo
- Comentario libre
- 1 a 3 fotos OBLIGATORIAS (comprimidas y subidas a Storage privado)
El promotor puede levantar N incidencias por tienda.
"""
import streamlit as st
import render as r
import pandas as pd
from styles.theme import (
    COLOR_PINK_PALE, COLOR_PINK_TEXT, COLOR_PINK_BORDER, COLOR_BLUE_PALE,
    COLOR_BLUE_BG, COLOR_BLUE_BORDER, COLOR_BLUE_DARK, COLOR_NAVY, COLOR_TEXT_SECONDARY,
    COLOR_GREEN, COLOR_GREEN_PALE, COLOR_GREEN_TEXT, COLOR_GREEN_BORDER,
    COLOR_AMBER, COLOR_AMBER_PALE, COLOR_RED_DARK, COLOR_RED_PALE,
    COLOR_RED_BORDER, COLOR_WHITE,
)
from data import (
    guardar_incidencia, subir_foto_incidencia, get_incidencias_de_tienda,
    get_detalle_tienda, adaptar_detalle,
)

TIPOS = ['SOS TEQUILA', 'SOS WHISKY', 'SOS VODKA', 'EXH', 'OOS']


def render_seccion(curt, periodo_id, info):
    """Sección de incidencias dentro del detalle de tienda.
    Solo se muestra a promotores (el router lo controla, pero revalidamos aquí)."""
    usuario = st.session_state.get('usuario', {})
    if usuario.get('tipo') != 'promotor':
        # Supervisor/AM: solo ven las incidencias ya reportadas, sin poder crear
        _render_lista_incidencias(curt, periodo_id, solo_lectura=True)
        return

    ruta = usuario.get('identificador')

    # Título de sección
    r.html(f"""
    <div style="margin:18px 4px 8px;display:flex;align-items:center;gap:8px;">
        <span style="font-size:18px;">⚠️</span>
        <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};">Incidencias de la tienda</p>
    </div>
    """)

    # Lista de incidencias ya levantadas en esta tienda
    _render_lista_incidencias(curt, periodo_id, solo_lectura=False)

    # Botón para abrir/cerrar el formulario
    abierto_key = f"form_inc_abierto_{curt}"
    if abierto_key not in st.session_state:
        st.session_state[abierto_key] = False

    if not st.session_state[abierto_key]:
        if st.button("＋ Levantar incidencia", key=f"btn_abrir_inc_{curt}"):
            st.session_state[abierto_key] = True
            st.rerun()
        return

    # ===== FORMULARIO =====
    _render_formulario(curt, periodo_id, info, ruta, abierto_key)


def _semanas_del_periodo(curt, periodo_id):
    """Semanas disponibles del periodo (desde el detalle semanal de la tienda)."""
    det = adaptar_detalle(get_detalle_tienda(curt, periodo_id))
    if len(det) > 0 and 'Semana' in det.columns:
        return sorted(int(s) for s in det['Semana'].dropna().unique())
    return []


def _render_formulario(curt, periodo_id, info, ruta, abierto_key):
    r.html(f"""
    <div style="background:{COLOR_PINK_PALE};border:0.5px solid {COLOR_PINK_BORDER};
    border-radius:12px;padding:4px 14px 14px;margin:6px 0 10px;">
        <p style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin:12px 0 2px;">Nueva incidencia</p>
        <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">Todos los campos y al menos 1 foto son obligatorios</p>
    </div>
    """)

    tipo = st.selectbox("Tipo de incidencia", TIPOS, key=f"inc_tipo_{curt}")

    semanas = _semanas_del_periodo(curt, periodo_id)
    if semanas:
        semana = st.selectbox("Semana afectada", semanas,
                              format_func=lambda s: f"Semana {s}", key=f"inc_sem_{curt}")
    else:
        semana = None
        st.caption("Sin semanas cargadas para este periodo.")

    comentario = st.text_area("Breve explicación", key=f"inc_com_{curt}",
                              placeholder="Describe brevemente qué pasó...", max_chars=500)

    link_trax = st.text_input("Link visita Trax *", key=f"inc_trax_{curt}",
                              placeholder="https://...")

    st.caption("Sube de 1 a 3 fotos (obligatorio)")
    fotos = st.file_uploader(
        "Fotos", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True,
        key=f"inc_fotos_{curt}", label_visibility="collapsed",
    )

    # Validaciones en vivo
    n_fotos = len(fotos) if fotos else 0
    if n_fotos > 3:
        st.warning("Máximo 3 fotos. Se tomarán las primeras 3.")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Cancelar", key=f"inc_cancel_{curt}"):
            st.session_state[abierto_key] = False
            st.rerun()
    with col2:
        guardar = st.button("Guardar incidencia", key=f"inc_guardar_{curt}", type="primary")

    if guardar:
        # Validar
        faltan = []
        if not tipo:
            faltan.append("tipo")
        if semana is None:
            faltan.append("semana")
        if not (comentario or "").strip():
            faltan.append("explicación")
        if not (link_trax or "").strip():
            faltan.append("link de Trax")
        if n_fotos < 1:
            faltan.append("al menos 1 foto")
        if faltan:
            st.error("Falta: " + ", ".join(faltan) + ".")
            return

        fotos_usar = fotos[:3]
        with st.spinner("Subiendo fotos y guardando..."):
            try:
                paths = []
                for f in fotos_usar:
                    p = subir_foto_incidencia(f.getvalue(), ruta, str(curt))
                    paths.append(p)
                guardar_incidencia(
                    curt=curt, ruta=ruta, periodo_id=periodo_id, tipo=tipo,
                    semana=semana, comentario=comentario.strip(), fotos_paths=paths,
                    reportada_por=st.session_state['usuario'].get('username', ruta),
                    tienda=info.get('Tienda') if info else None,
                    cadena=info.get('Cadena') if info else None,
                    canal=info.get('CANAL', info.get('Canal')) if info else None,
                    link_trax=(link_trax or '').strip() or None,
                )
            except Exception as e:
                print(f"[GUARDAR_INCIDENCIA ERROR] {e}")
                st.error("No pudimos guardar la incidencia. Intenta de nuevo.")
                return

        # limpiar caché de la lista y cerrar form
        get_incidencias_de_tienda.clear()
        st.session_state[abierto_key] = False
        st.success("Incidencia guardada ✓")
        st.rerun()


def _render_lista_incidencias(curt, periodo_id, solo_lectura):
    df = get_incidencias_de_tienda(curt, periodo_id)
    if len(df) == 0:
        if solo_lectura:
            return
        r.html(f"""
        <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:4px 4px 10px;">
            Aún no hay incidencias reportadas en esta tienda.
        </p>
        """)
        return

    # Colores por tipo
    tipo_color = {
        'SOS TEQUILA': COLOR_AMBER, 'SOS WHISKY': COLOR_AMBER, 'SOS VODKA': COLOR_AMBER,
        'EXH': COLOR_BLUE_BORDER, 'OOS': COLOR_RED_DARK,
    }

    if solo_lectura:
        r.html(f"""
        <div style="margin:18px 4px 8px;display:flex;align-items:center;gap:8px;">
            <span style="font-size:18px;">⚠️</span>
            <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};">Incidencias reportadas ({len(df)})</p>
        </div>
        """)

    items = ""
    for _, inc in df.iterrows():
        tipo = inc.get('tipo', '')
        color = tipo_color.get(tipo, COLOR_TEXT_SECONDARY)
        sem = inc.get('semana')
        sem_txt = f"S{int(sem)}" if pd.notna(sem) else "—"
        com = (inc.get('comentario') or '').strip()
        n_fotos = len(inc.get('fotos') or [])
        fecha = str(inc.get('created_at', ''))[:10]
        estado = inc.get('estado', 'PENDIENTE') or 'PENDIENTE'
        link_trax = (inc.get('link_trax') or '').strip()
        motivo_rechazo = (inc.get('motivo_rechazo') or '').strip()

        # Badge de estado
        if estado == 'AUTORIZADA':
            est_bg, est_color, est_txt = COLOR_GREEN_PALE, COLOR_GREEN_TEXT, '✓ Autorizada'
        elif estado == 'NO_AUTORIZADA':
            est_bg, est_color, est_txt = COLOR_RED_PALE, COLOR_RED_DARK, '✕ No autorizada'
        else:
            est_bg, est_color, est_txt = COLOR_AMBER_PALE, COLOR_AMBER, '⏳ Pendiente'

        trax_html = (
            f'<a href="{link_trax}" target="_blank" style="font-size:11px;color:{COLOR_BLUE_DARK};text-decoration:none;">🔗 Ver visita Trax</a>'
            if link_trax else ''
        )
        rechazo_html = (
            f'<p style="font-size:11px;color:{COLOR_RED_DARK};margin:4px 0 0;">Motivo: {motivo_rechazo}</p>'
            if (estado == 'NO_AUTORIZADA' and motivo_rechazo) else ''
        )

        items += (
            f'<div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};'
            f'border-radius:10px;padding:10px 12px;margin-bottom:6px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
            f'<span style="background:{COLOR_PINK_PALE};color:{color};font-size:11px;font-weight:500;'
            f'padding:2px 8px;border-radius:6px;">{tipo}</span>'
            f'<span style="background:{est_bg};color:{est_color};font-size:11px;font-weight:500;'
            f'padding:2px 8px;border-radius:6px;">{est_txt}</span>'
            f'</div>'
            f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{sem_txt} · {fecha}</p>'
            f'<p style="font-size:12px;color:{COLOR_NAVY};margin:4px 0 0;line-height:1.4;">{com}</p>'
            f'{rechazo_html}'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">'
            f'<span style="font-size:10px;color:{COLOR_TEXT_SECONDARY};">📷 {n_fotos} foto(s)</span>'
            f'{trax_html}'
            f'</div>'
            f'</div>'
        )
    r.html(f'<div style="margin-bottom:8px;">{items}</div>')
