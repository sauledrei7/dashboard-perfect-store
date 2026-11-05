"""
Bandeja de incidencias (v11). La ven el supervisor (las de su equipo) y el AM
(las de toda su área), como una lista tipo notificaciones, con sus fotos.

Quién autoriza o rechaza:
  - hasta septiembre, el supervisor, lo que levantaban sus promotores;
  - v28: el GR (el area manager), y solo las de su área. Desde octubre las
    levanta el supervisor y nacen pendientes; quien levanta ya no valida. Las
    que los promotores dejaron pendientes antes del cambio también las valida
    el GR. El supervisor y el director solo ven.
"""
import streamlit as st
import render as r
import pandas as pd
import validacion_calc as vc
from styles.theme import (
    COLOR_PINK_PALE, COLOR_PINK_TEXT, COLOR_PINK_BORDER, COLOR_BLUE_PALE,
    COLOR_BLUE_BG, COLOR_BLUE_BORDER, COLOR_NAVY, COLOR_TEXT_SECONDARY,
    COLOR_GREEN, COLOR_GREEN_PALE, COLOR_AMBER, COLOR_AMBER_PALE, COLOR_BLUE_DARK,
    COLOR_RED_DARK, COLOR_RED_PALE, COLOR_WHITE,
)
from data import get_incidencias_ambito, firmar_url_foto
from components.incidencias import etiqueta_motivo

TIPO_COLOR = {
    'SOS TEQUILA': COLOR_AMBER, 'SOS WHISKY': COLOR_AMBER, 'SOS VODKA': COLOR_AMBER,
    # v13: 'EXH' se renombró a 'EXHIBICIONES'. Se deja el viejo por las incidencias
    # levantadas antes de la migración.
    'EXHIBICIONES': COLOR_BLUE_DARK, 'EXH': COLOR_BLUE_DARK, 'OOS': COLOR_RED_DARK,
}


def render(periodo_id: str, area_manager: str = None, supervisor: str = None,
           key: str = "band", puede_resolver: bool = None):
    df = get_incidencias_ambito(periodo_id, area_manager=area_manager, supervisor=supervisor)
    n = len(df)
    # v28: por defecto solo el GR valida, y solo en su área.
    if puede_resolver is None:
        puede_resolver = puede_validar(area_manager)

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
    if puede_resolver:
        nota = "Tú las validas: autoriza o rechaza las que estén pendientes."
    elif supervisor and not area_manager:
        nota = "Las levantas tú desde cada tienda, cuando el mes está abierto; las valida tu GR."
    else:
        nota = ""
    if nota:
        r.html(f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:-4px 4px 8px;">{nota}</p>')
    aviso = st.session_state.pop('_bandeja_aviso', None)
    if aviso:
        st.info(aviso)

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
        # v26: la llave va por el id de la incidencia y no por su posición: si llega
        # una nueva mientras el supervisor escribe un rechazo, la lista se recorre
        # y con la posición el "rechazando" brincaba a otra tarjeta.
        for idx, inc in df.iterrows():
            ident = inc.get('id')
            _render_tarjeta(inc, key=f"{key}_{ident if pd.notna(ident) else idx}", puede_resolver=puede_resolver)


def puede_validar(area_manager) -> bool:
    """v28: valida (autoriza o rechaza) solo el GR, y solo las de su área.

    Se pregunta al usuario de la sesión y no al que recibe la pantalla: el
    director entra a las pantallas del AM con un usuario prestado de tipo 'am',
    pero su sesión dice 'admin', así que ahí solo ve.
    """
    u = st.session_state.get('usuario') or {}
    return (bool(area_manager) and u.get('tipo') == 'am'
            and str(u.get('identificador') or '').strip() == str(area_manager).strip())


def _render_resumen_tipos(df):
    conteo = df['tipo'].value_counts().to_dict()
    chips = ""
    for tipo, c in conteo.items():
        color = TIPO_COLOR.get(tipo, COLOR_TEXT_SECONDARY)
        chips += (
            f'<div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};'
            f'border-radius:8px;padding:6px 10px;text-align:center;min-width:70px;">'
            f'<p style="font-size:18px;font-weight:600;margin:0;color:{color};">{c}</p>'
            f'<p style="font-size:10px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{r.texto(tipo)}</p>'
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
    _com = inc.get('comentario')
    com = str(_com).strip() if pd.notna(_com) else ''
    fecha = str(inc.get('created_at', ''))[:10]
    fotos = inc.get('fotos') or []
    estado = inc.get('estado', 'PENDIENTE') or 'PENDIENTE'
    _lt = inc.get('link_trax')
    link_trax = str(_lt).strip() if pd.notna(_lt) else ''
    inc_id = inc.get('id')

    # v13: motivo especifico y productos afectados (NULL en las anteriores a v13)
    _mo = inc.get('incidencia')
    motivo = str(_mo).strip() if pd.notna(_mo) else ''
    _ca = inc.get('categoria')
    categoria = str(_ca).strip() if pd.notna(_ca) else ''
    prods = inc.get('productos') or []
    if isinstance(prods, str):
        prods = [prods]

    # Badge de estado
    if estado == 'AUTORIZADA':
        est_bg, est_color, est_txt = COLOR_GREEN_PALE, COLOR_GREEN, '✓ Autorizada'
    elif estado == 'NO_AUTORIZADA':
        est_bg, est_color, est_txt = COLOR_RED_PALE, COLOR_RED_DARK, '✕ No autorizada'
    else:
        est_bg, est_color, est_txt = COLOR_AMBER_PALE, COLOR_AMBER, '⏳ Pendiente'

    # v27: si la levantó el supervisor, se dice quién; si no, la ruta del promotor.
    if vc.levanto_supervisor(inc):
        origen = f"Ruta {r.texto(ruta)} · la levantó {r.texto(inc.get('reportada_por'))}"
    else:
        origen = f"Reportada por {r.texto(ruta)}"
    # v28: y quién la validó, y por qué la rechazó, para que el supervisor lo vea.
    resolvio = vc.texto(inc.get('resuelta_por'))
    if resolvio and estado in ('AUTORIZADA', 'NO_AUTORIZADA'):
        origen += f" · la {'autorizó' if estado == 'AUTORIZADA' else 'rechazó'} {r.texto(resolvio)}"
    motivo_rechazo = vc.texto(inc.get('motivo_rechazo'))
    rechazo_html = (
        f'<p style="font-size:11px;color:{COLOR_RED_DARK};margin:4px 0 0;">Motivo del rechazo: {r.texto(motivo_rechazo)}</p>'
        if estado == 'NO_AUTORIZADA' and motivo_rechazo else ''
    )

    # v26: lo que escribió el promotor (comentario, link) y lo que viene de la base
    # pasa por r.texto() / r.url() antes de entrar al HTML. Ver render.py.
    link_trax = r.url(link_trax)
    trax_html = (
        f'<a href="{link_trax}" target="_blank" rel="noopener noreferrer" style="font-size:11px;'
        f'color:{COLOR_BLUE_DARK};text-decoration:none;">🔗 Ver visita Trax</a>' if link_trax else ''
    )

    # Motivo especifico: es lo primero que necesita leer quien autoriza
    motivo_html = (
        f'<p style="font-size:12px;font-weight:500;color:{COLOR_BLUE_DARK};margin:4px 0 0;">'
        f'{r.texto(etiqueta_motivo(motivo))}</p>'
    ) if motivo else ''

    prods_html = ''
    if len(prods) > 0:
        if 'TODOS' in prods:
            etiqueta = 'Todos los de %s' % (categoria.title() if categoria else 'la categoría')
        elif len(prods) <= 2:
            etiqueta = ' · '.join(str(p)[:36] for p in prods)
        else:
            etiqueta = '%s y %d más' % (str(prods[0])[:30], len(prods) - 1)
        prods_html = (
            f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:3px 0 0;">🍾 {r.texto(etiqueta)}</p>'
        )

    # OJO: esta tarjeta se arma concatenando strings de UNA línea, NO con un
    # triple-quote multilínea. Si {motivo_html} o {prods_html} van en su propio
    # renglón y llegan vacíos (incidencias anteriores a v13), dedent deja
    # renglones en blanco y Markdown convierte lo que sigue en bloque de código.
    # Es la misma trampa que documenta tienda_detalle.py.
    r.html(
        f'<div style="background:{COLOR_WHITE};border:0.5px solid {COLOR_BLUE_BORDER};'
        f'border-radius:10px;padding:10px 12px;margin-bottom:4px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        f'<span style="background:{COLOR_PINK_PALE};color:{color};font-size:11px;font-weight:500;'
        f'padding:2px 8px;border-radius:6px;">{r.texto(tipo)}</span>'
        f'<span style="background:{est_bg};color:{est_color};font-size:11px;font-weight:500;'
        f'padding:2px 8px;border-radius:6px;">{est_txt}</span>'
        f'</div>'
        f'<p style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin:4px 0 0;">{r.texto(tienda)}</p>'
        f'{motivo_html}'
        f'{prods_html}'
        f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:4px 0 0;">'
        f'{sem_txt} · {r.texto(fecha)} · {origen}</p>'
        f'<p style="font-size:12px;color:{COLOR_NAVY};margin:6px 0 0;line-height:1.4;">{r.texto(com)}</p>'
        f'{rechazo_html}'
        f'<div style="margin-top:4px;">{trax_html}</div>'
        f'</div>'
    )

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


def _resolver(inc_id, autorizar, motivo=None) -> bool:
    """Guarda lo que decidió el GR. Si Supabase falla, avisa en vez de tirar la
    pantalla (antes el error salía como traceback)."""
    from data import resolver_incidencia, get_incidencias_de_tienda
    usuario = st.session_state.get('usuario', {})
    if usuario.get('tipo') != 'am':
        # Los botones solo se pintan para el GR; esto es por si acaso.
        st.error("Solo el GR puede validar incidencias.")
        return False
    try:
        cambio = resolver_incidencia(inc_id, autorizar=autorizar,
                                     resuelta_por=usuario.get('username', usuario.get('identificador', '')),
                                     motivo_rechazo=(motivo or '')[:300] or None)
    except Exception as e:
        print(f"[BANDEJA RESOLVER ERROR] {inc_id}: {e}")
        st.error("No se pudo guardar. Revisa tu conexión e intenta otra vez.")
        return False
    if not cambio:
        # v28: ya no estaba pendiente (la validaron en otra pestaña). No se pisa.
        st.session_state['_bandeja_aviso'] = "Esa incidencia ya estaba validada; la lista ya muestra cómo quedó."
    try:
        get_incidencias_de_tienda.clear()
    except Exception:
        pass
    return True


def _render_acciones_resolver(inc_id, key):
    rechazar_key = f"rechazando_{key}"

    if st.session_state.get(rechazar_key):
        # Modo rechazo: pedir motivo
        motivo = st.text_input("Motivo del rechazo *", key=f"motivo_{key}", max_chars=300,
                               placeholder="Ej. la foto no corresponde a la tienda")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirmar rechazo", key=f"conf_rech_{key}", type="primary"):
                if not (motivo or '').strip():
                    st.error("Escribe el motivo del rechazo.")
                elif _resolver(inc_id, autorizar=False, motivo=motivo.strip()):
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
                if _resolver(inc_id, autorizar=True):
                    st.rerun()
        with c2:
            if st.button("✕ Rechazar", key=f"rech_{key}"):
                st.session_state[rechazar_key] = True
                st.rerun()
