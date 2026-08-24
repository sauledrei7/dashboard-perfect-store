"""
Módulo de incidencias — v13.
Formulario embebido en el detalle de tienda, SOLO para promotores.

Cambios v13 (antes: 1 solo dropdown de tipo):
  1. KPI AFECTADO (5) → SOS Tequila/Whisky/Vodka, Exhibiciones, OOS.
  2. INCIDENCIA (8 motivos + "Touchpoint no reflejado" exclusivo de Exhibiciones).
  3. Si el motivo es de producto (no reconocido / mal reconocido):
     se piden CATEGORÍA y PRODUCTOS (selección múltiple, o TODOS).
     La categoría se pre-llena sola cuando el KPI ya la implica (SOS WHISKY → WHISKY).
  4. GUÍA DE EVIDENCIA que cambia según el motivo elegido, escrita para campo.

Se mantiene: semana, explicación obligatoria, link de Trax, 1 a 3 fotos.
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
    get_detalle_tienda, adaptar_detalle, get_productos, get_oos_tienda,
)

# ============================================================
# CATÁLOGOS  (deben coincidir con los CHECK de 02_incidencias_v13.sql)
# ============================================================
KPIS = ['SOS TEQUILA', 'SOS WHISKY', 'SOS VODKA', 'EXHIBICIONES', 'OOS']

INCIDENCIAS_BASE = [
    'Información no reflejada.',
    'Producto no reconocido por TRAX.',
    'Producto reconocido incorrectamente.',
    'Problema de imagen / stitching.',
    'Objetivo o Target incorrecto.',
    'Objetivo no visible.',
    'Problema de sincronización.',
    'Otro (habilita explicación obligatoria).',
]
INCIDENCIA_TOUCHPOINT = 'Touchpoint no reflejado.'   # solo Exhibiciones

# Motivos que exigen decir QUÉ producto falló
INCIDENCIAS_DE_PRODUCTO = (
    'Producto no reconocido por TRAX.',
    'Producto reconocido incorrectamente.',
)

# KPIs que ya traen la categoría implícita (no se le pregunta al promotor)
CATEGORIA_POR_KPI = {
    'SOS TEQUILA': 'TEQUILA',
    'SOS WHISKY': 'WHISKY',
    'SOS VODKA': 'VODKA',
}
CATEGORIAS = ['TEQUILA', 'VODKA', 'WHISKY']
TODOS = 'TODOS'

# Los selectores arrancan SIN nada elegido. Si se dejan con la primera opción
# puesta, el promotor puede guardar sin haberla mirado: el caso feo es la
# semana, que se iría a la primera del periodo y mandaría al supervisor a
# revisar una semana donde no pasó nada.
ELIGE = '— Elige una —'

# El catálogo se guarda con su texto oficial, pero hay que mostrarlo limpio:
# "(habilita explicación obligatoria)" es una nota de diseño del formulario,
# no algo que el promotor o el supervisor deban leer.
ETIQUETA_CORTA = {
    'Otro (habilita explicación obligatoria).': 'Otro',
}


def etiqueta_motivo(motivo):
    """Texto del motivo listo para pantalla. Lo usan el formulario, la lista
    de la tienda y la bandeja del supervisor, para que digan todos lo mismo."""
    if not motivo:
        return ''
    m = str(motivo).strip()
    return ETIQUETA_CORTA.get(m, m.rstrip('.'))


def incidencias_de(kpi):
    """Motivos disponibles según el KPI. 'Touchpoint no reflejado' solo aplica
    a Exhibiciones (así viene en la especificación)."""
    lista = list(INCIDENCIAS_BASE)
    if kpi == 'EXHIBICIONES':
        lista.insert(-1, INCIDENCIA_TOUCHPOINT)   # antes de "Otro"
    return lista


# ============================================================
# QUÉ PUEDE LEVANTAR SEGÚN EL RESULTADO DE LA TIENDA  (v13.1)
# ============================================================
def kpis_permitidos(info, curt, periodo_id):
    """Decide qué KPIs puede reportar el promotor en ESTA tienda.

    Regla:
      · Tienda NO Perfect Store  -> puede levantar de cualquier tipo.
      · Tienda Perfect Store     -> el punto ya se ganó, así que SOS y
        EXHIBICIONES no tienen nada que disputar. Solo se abre el formulario
        si le quedaron encuestas de OOS SIN CONTESTAR, porque esas todavía
        le bajan el multiplicador del bono.
      · Tienda PS que contestó todo su OOS (o que no traía objetivo)
        -> no hay nada que reportar, se cierra el formulario.

    Devuelve (lista_de_kpis, motivo). Lista vacía = bloqueada.
    """
    es_ps = (info.get('PS FINAL') == 1) if info else False
    if not es_ps:
        return list(KPIS), None

    d = get_oos_tienda(str(curt), periodo_id) or {}
    obj = int(d.get('obj_oos', 0) or 0)
    no_cont = int(d.get('no_cont_oos', 0) or 0)

    if no_cont > 0:
        return ['OOS'], ('ps_solo_oos', no_cont)
    if obj > 0:
        return [], ('ps_oos_completo', obj)
    return [], ('ps_sin_oos', 0)


def _render_aviso_ps(motivo):
    """Explica al promotor por qué esta tienda tiene el formulario limitado.
    Se redacta en positivo: la tienda salió bien, no es un castigo."""
    clave, n = motivo

    if clave == 'ps_solo_oos':
        titulo = 'Esta tienda salió Perfect Store 🎉'
        cuerpo = (f'Como ya la ganaste, no hay nada que reclamar de SOS ni de Exhibiciones. '
                  f'Pero te quedaron <b>{n} encuesta(s) de OOS sin contestar</b>, y eso sí te '
                  f'baja el multiplicador. Por eso aquí solo puedes levantar incidencias de OOS.')
    elif clave == 'ps_oos_completo':
        titulo = 'Esta tienda ya está completa ✅'
        cuerpo = (f'Salió Perfect Store y contestaste tus <b>{n} encuestas de OOS</b>. '
                  f'No hay nada que reportar: tu bono por esta tienda ya está al 100%.')
    else:
        titulo = 'Esta tienda ya está completa ✅'
        cuerpo = ('Salió Perfect Store y no traía objetivo de OOS, así que no hay '
                  'nada que reportar. Tu bono por esta tienda ya está al 100%.')

    r.html(
        f'<div style="background:{COLOR_GREEN_PALE};border:0.5px solid {COLOR_GREEN_BORDER};'
        f'border-radius:12px;padding:12px 14px;margin:6px 0 10px;">'
        f'<p style="font-size:13px;font-weight:600;color:{COLOR_GREEN_TEXT};margin:0 0 4px;">{titulo}</p>'
        f'<p style="font-size:12px;color:{COLOR_NAVY};margin:0;line-height:1.5;">{cuerpo}</p>'
        f'</div>'
    )


# ============================================================
# GUÍA DE EVIDENCIA — versión para campo
# ============================================================
GUIA = {
    INCIDENCIA_TOUCHPOINT: {
        'titulo': 'Faltan touchpoints en el reporte',
        'items': [
            'Pega el link de la <b>visita completa</b>.',
            'Foto donde se vean los touchpoints que <b>sí hiciste</b>.',
            'Foto del <b>reporte</b>, donde se vea cuáles te contó TRAX.',
            'En la explicación dinos <b>cuáles faltan y cuántos son</b>.',
        ],
        'ojo': 'Tenemos que poder comparar tu visita contra el reporte y sacar la diferencia. '
               'Si solo mandas una de las dos, no se puede.',
    },
    'Problema de imagen / stitching.': {
        'titulo': 'La imagen se pegó mal',
        'items': [
            'Sube <b>la imagen ya pegada</b> (la que arma TRAX), no otra.',
            'Que se alcance a ver si la botella quedó <b>cortada, encimada o fuera de cuadro</b>.',
        ],
        'ojo': 'Un screenshot general de touchpoints NO sirve aquí. Necesitamos ver el pegado.',
    },
    'Producto no reconocido por TRAX.': {
        'titulo': 'TRAX no vio el producto',
        'items': [
            'Sube la <b>imagen de detección</b>, esa donde salen los puntos o marcas.',
            'Que se vea el producto <b>completo y sin nada encima</b>.',
            'En la explicación dinos si de plano <b>no lo detectó</b> o si la foto no alcanzaba.',
        ],
        'ojo': 'Marca abajo cuál o cuáles productos fueron. Si fue todo el anaquel, usa TODOS.',
    },
    'Producto reconocido incorrectamente.': {
        'titulo': 'TRAX lo confundió con otro',
        'items': [
            'Sube la <b>imagen de detección</b> con los puntos de reconocimiento.',
            'En la explicación dinos <b>por cuál producto lo confundió</b>.',
        ],
        'ojo': 'Marca abajo el producto que TÚ pusiste en el anaquel, no por el que lo confundió.',
    },
    'Otro (habilita explicación obligatoria).': {
        'titulo': 'Algo que no está en la lista',
        'items': [
            'Primero <b>revisa la lista de arriba</b>: casi siempre hay una opción que sí aplica.',
            'Si de plano no encaja, explica <b>qué esperabas ver y qué viste</b>.',
            'Sube la foto donde <b>se note el problema</b>.',
        ],
        'ojo': 'Aquí no tenemos de dónde agarrarnos: si la explicación queda corta, '
               'tu supervisor no va a poder autorizarla. Escríbela completa.',
    },
}

GUIA_DEFAULT = {
    'titulo': 'Qué necesitamos ver',
    'items': [
        'Foto donde se vea <b>claramente</b> el problema.',
        'El link de la visita en Trax.',
        'Una explicación corta de qué pasó.',
    ],
    'ojo': '',
}


def _render_guia_general():
    """Guía fija: se abre sola la primera vez y se puede colapsar."""
    with st.expander("📋 Antes de levantar tu incidencia — léelo tantito", expanded=False):
        r.html(f"""
        <div style="font-size:12px;color:{COLOR_NAVY};line-height:1.6;">
            <p style="margin:0 0 10px;font-weight:500;">1. Revisa tu foto antes de mandarla</p>
            <p style="margin:0 0 10px;color:{COLOR_TEXT_SECONDARY};">
                Si la foto no deja ver el problema, la incidencia se va a rechazar.
                Antes de subirla pregúntate:
            </p>
            <div style="background:{COLOR_BLUE_BG};border-radius:10px;padding:10px 12px;margin-bottom:12px;">
                <p style="margin:0;color:{COLOR_NAVY};">
                    ✔️ ¿Se ve nítida? (que no salga borrosa)<br>
                    ✔️ ¿Sale el producto completo? (que no quede cortado)<br>
                    ✔️ ¿Hay algo tapándolo?<br>
                    ✔️ ¿Está bien encuadrado?
                </p>
            </div>
            <p style="margin:0 0 6px;font-weight:500;">2. Confirma que sí era un error de TRAX</p>
            <p style="margin:0 0 12px;color:{COLOR_TEXT_SECONDARY};">
                A veces el touchpoint no aparece porque <b>así debía ser</b> según la regla
                (hay categorías y productos que no cuentan). Si no estás seguro de que ese
                producto debía contar, pregúntale a tu supervisor antes de levantarla.
            </p>
            <p style="margin:0 0 6px;font-weight:500;">3. Una incidencia por problema</p>
            <p style="margin:0;color:{COLOR_TEXT_SECONDARY};">
                Si en la misma tienda fallaron cosas distintas, levanta una por cada una.
                Si fue el mismo problema con varios productos, puedes marcarlos todos juntos.
            </p>
        </div>
        """)


def _render_guia_motivo(motivo):
    """Tarjeta que cambia según el motivo elegido: qué evidencia se necesita."""
    g = GUIA.get(motivo, GUIA_DEFAULT)
    items = "".join(
        f'<li style="margin-bottom:5px;">{it}</li>' for it in g['items']
    )
    ojo = (
        f'<div style="background:{COLOR_AMBER_PALE};border-radius:8px;padding:8px 10px;margin-top:10px;">'
        f'<p style="font-size:11px;color:{COLOR_NAVY};margin:0;line-height:1.5;">⚠️ {g["ojo"]}</p>'
        f'</div>'
    ) if g['ojo'] else ''

    r.html(
        f'<div style="background:{COLOR_BLUE_PALE};border:0.5px solid {COLOR_BLUE_BORDER};'
        f'border-radius:12px;padding:12px 14px;margin:4px 0 14px;">'
        f'<p style="font-size:12px;font-weight:600;color:{COLOR_BLUE_DARK};margin:0 0 8px;">'
        f'📎 {g["titulo"]} — esto necesitamos:</p>'
        f'<ul style="font-size:12px;color:{COLOR_NAVY};margin:0;padding-left:18px;line-height:1.5;">'
        f'{items}</ul>'
        f'{ojo}'
        f'</div>'
    )


# ============================================================
# SECCIÓN PRINCIPAL
# ============================================================
def render_seccion(curt, periodo_id, info):
    """Sección de incidencias dentro del detalle de tienda.
    Solo se muestra a promotores (el router lo controla, pero revalidamos aquí)."""
    usuario = st.session_state.get('usuario', {})
    if usuario.get('tipo') != 'promotor':
        # Supervisor/AM: solo ven las incidencias ya reportadas, sin poder crear
        _render_lista_incidencias(curt, periodo_id, solo_lectura=True)
        return

    ruta = usuario.get('identificador')

    r.html(f"""
    <div style="margin:18px 4px 8px;display:flex;align-items:center;gap:8px;">
        <span style="font-size:18px;">⚠️</span>
        <p style="font-size:14px;font-weight:500;margin:0;color:{COLOR_NAVY};">Incidencias de la tienda</p>
    </div>
    """)

    _render_lista_incidencias(curt, periodo_id, solo_lectura=False)

    # v13.1: si la tienda ya es PS, se limita (o se cierra) el formulario
    permitidos, bloqueo = kpis_permitidos(info, curt, periodo_id)
    if bloqueo:
        _render_aviso_ps(bloqueo)
    if not permitidos:
        return   # nada que reportar: ni siquiera mostramos el botón

    abierto_key = f"form_inc_abierto_{curt}"
    if abierto_key not in st.session_state:
        st.session_state[abierto_key] = False

    if not st.session_state[abierto_key]:
        if st.button("＋ Levantar incidencia", key=f"btn_abrir_inc_{curt}"):
            st.session_state[abierto_key] = True
            st.rerun()
        return

    _render_formulario(curt, periodo_id, info, ruta, abierto_key, permitidos)


def _semanas_del_periodo(curt, periodo_id):
    """Semanas disponibles del periodo (desde el detalle semanal de la tienda)."""
    det = adaptar_detalle(get_detalle_tienda(curt, periodo_id))
    if len(det) > 0 and 'Semana' in det.columns:
        return sorted(int(s) for s in det['Semana'].dropna().unique())
    return []


def _render_formulario(curt, periodo_id, info, ruta, abierto_key, permitidos=None):
    r.html(f"""
    <div style="background:{COLOR_PINK_PALE};border:0.5px solid {COLOR_PINK_BORDER};
    border-radius:12px;padding:4px 14px 14px;margin:6px 0 10px;">
        <p style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin:12px 0 2px;">Nueva incidencia</p>
        <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">
            Todos los campos y al menos 1 foto son obligatorios</p>
    </div>
    """)

    _render_guia_general()

    # ---------- 1. KPI afectado ----------
    # En tiendas Perfect Store la lista viene recortada a OOS: no tiene caso
    # mostrar un dropdown de una sola opción, se informa y ya.
    opciones_kpi = permitidos or list(KPIS)
    if len(opciones_kpi) == 1:
        kpi = opciones_kpi[0]
        r.html(
            f'<p style="font-size:13px;color:{COLOR_TEXT_SECONDARY};margin:10px 0 4px;">'
            f'KPI afectado: <b style="color:{COLOR_NAVY};">{kpi}</b></p>'
        )
    else:
        kpi = st.selectbox("¿Qué KPI se afectó?", opciones_kpi,
                           index=None, placeholder=ELIGE, key=f"inc_kpi_{curt}")

    # ---------- 2. Motivo ----------
    # El motivo depende del KPI, así que no se muestra hasta que hay KPI.
    motivo = None
    if kpi:
        motivo = st.selectbox(
            "¿Qué pasó?", incidencias_de(kpi),
            index=None, placeholder=ELIGE,
            format_func=etiqueta_motivo,
            key=f"inc_motivo_{curt}_{kpi}",   # la key incluye el KPI para resetear la lista al cambiarlo
        )

    # ---------- Guía que cambia según el motivo ----------
    if motivo:
        _render_guia_motivo(motivo)

    # ---------- 3. Categoría y productos (solo motivos de producto) ----------
    categoria = None
    productos_sel = None
    if motivo in INCIDENCIAS_DE_PRODUCTO:
        categoria = CATEGORIA_POR_KPI.get(kpi)
        if categoria:
            # El KPI ya dice la categoría: se informa, no se pregunta.
            r.html(
                f'<p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:0 0 6px;">'
                f'Categoría: <b style="color:{COLOR_NAVY};">{categoria.title()}</b> '
                f'<span style="color:{COLOR_PINK_TEXT};">(por el KPI que elegiste)</span></p>'
            )
        else:
            # Exhibiciones y OOS no traen categoría implícita
            categoria = st.selectbox(
                "Categoría del producto", CATEGORIAS,
                index=None, placeholder=ELIGE,
                format_func=lambda c: c.title(), key=f"inc_cat_{curt}",
            )
        if categoria:
            productos_sel = _selector_productos(curt, categoria)

    # ---------- 4. Semana ----------
    semanas = _semanas_del_periodo(curt, periodo_id)
    if semanas:
        semana = st.selectbox("Semana afectada", semanas,
                              index=None, placeholder=ELIGE,
                              format_func=lambda s: f"Semana {s}", key=f"inc_sem_{curt}")
    else:
        semana = None
        st.caption("Sin semanas cargadas para este periodo.")

    # ---------- 5. Explicación ----------
    # OJO: motivo puede ser None mientras el promotor no elija nada.
    ayuda_com = ("Obligatorio. Como elegiste \"Otro\", cuéntanos con detalle qué pasó."
                 if (motivo or '').startswith('Otro') else "Obligatorio. Cuéntanos en corto qué pasó.")
    comentario = st.text_area("Breve explicación", key=f"inc_com_{curt}",
                              placeholder="Describe brevemente qué pasó...",
                              help=ayuda_com, max_chars=500)

    # ---------- 6. Link Trax ----------
    link_trax = st.text_input("Link visita Trax *", key=f"inc_trax_{curt}",
                              placeholder="https://...")

    # ---------- 7. Fotos ----------
    st.caption("Sube de 1 a 3 fotos (obligatorio)")
    fotos = st.file_uploader(
        "Fotos", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True,
        key=f"inc_fotos_{curt}", label_visibility="collapsed",
    )
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

    if not guardar:
        return

    # ---------- Validación ----------
    # Se revalida la regla de Perfect Store al guardar, no solo al pintar:
    # el estado de la sesión pudo cambiar entre que abrió el formulario y envió.
    # (kpi puede venir en None si todavía no eligió: eso lo atrapa 'faltan')
    if kpi and kpi not in opciones_kpi:
        st.error("Esta tienda es Perfect Store: aquí solo se pueden levantar incidencias de OOS.")
        return

    faltan = []
    if not kpi:
        faltan.append("el KPI afectado")
    if not motivo:
        faltan.append("qué pasó")
    if motivo in INCIDENCIAS_DE_PRODUCTO:
        if not categoria:
            faltan.append("la categoría")
        elif not productos_sel:
            faltan.append("al menos 1 producto")
    if semana is None:
        faltan.append("la semana")
    if not (comentario or "").strip():
        faltan.append("la explicación")
    if not (link_trax or "").strip():
        faltan.append("el link de Trax")
    if n_fotos < 1:
        faltan.append("al menos 1 foto")
    if faltan:
        st.error("Te falta " + ", ".join(faltan) + ".")
        return

    fotos_usar = fotos[:3]
    with st.spinner("Subiendo fotos y guardando..."):
        try:
            paths = []
            for f in fotos_usar:
                paths.append(subir_foto_incidencia(f.getvalue(), ruta, str(curt)))
            guardar_incidencia(
                curt=curt, ruta=ruta, periodo_id=periodo_id, tipo=kpi,
                semana=semana, comentario=comentario.strip(), fotos_paths=paths,
                reportada_por=st.session_state['usuario'].get('username', ruta),
                tienda=info.get('Tienda') if info else None,
                cadena=info.get('Cadena') if info else None,
                canal=info.get('CANAL', info.get('Canal')) if info else None,
                link_trax=(link_trax or '').strip() or None,
                incidencia=motivo, categoria=categoria, productos=productos_sel,
            )
        except Exception as e:
            print(f"[GUARDAR_INCIDENCIA ERROR] {e}")
            st.error("No pudimos guardar la incidencia. Intenta de nuevo.")
            return

    get_incidencias_de_tienda.clear()
    st.session_state[abierto_key] = False
    st.success("Incidencia guardada ✓")
    st.rerun()


def _selector_productos(curt, categoria):
    """Selección MÚLTIPLE de SKUs de la categoría, con opción TODOS.
    Devuelve ['TODOS'] o la lista de productos elegidos."""
    df = get_productos(categoria)
    if len(df) == 0:
        st.warning("No pudimos cargar el catálogo de productos. "
                   "Escribe en la explicación cuál fue el producto afectado.")
        return None

    skus = df['producto'].tolist()
    opciones = [TODOS] + skus

    sel = st.multiselect(
        f"¿Qué producto(s)? · {len(skus)} de {categoria.title()}",
        opciones,
        format_func=lambda p: "▸ TODOS los de la categoría" if p == TODOS else p,
        key=f"inc_prod_{curt}_{categoria}",
        help="Puedes marcar varios. Si falló todo el anaquel, usa TODOS.",
    )

    if TODOS in sel:
        if len(sel) > 1:
            st.caption("Marcaste TODOS: se ignoran los productos sueltos.")
        return [TODOS]
    return sel or None


# ============================================================
# LISTA DE INCIDENCIAS YA LEVANTADAS
# ============================================================
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

    tipo_color = {
        'SOS TEQUILA': COLOR_AMBER, 'SOS WHISKY': COLOR_AMBER, 'SOS VODKA': COLOR_AMBER,
        'EXHIBICIONES': COLOR_BLUE_DARK, 'EXH': COLOR_BLUE_DARK, 'OOS': COLOR_RED_DARK,
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
        _com = inc.get('comentario')
        com = str(_com).strip() if pd.notna(_com) else ''
        n_fotos = len(inc.get('fotos') or [])
        fecha = str(inc.get('created_at', ''))[:10]
        estado = inc.get('estado', 'PENDIENTE') or 'PENDIENTE'
        _lt = inc.get('link_trax')
        link_trax = str(_lt).strip() if pd.notna(_lt) else ''
        _mr = inc.get('motivo_rechazo')
        motivo_rechazo = str(_mr).strip() if pd.notna(_mr) else ''

        # v13: motivo específico y productos afectados (NULL en las viejas)
        _mo = inc.get('incidencia')
        motivo = str(_mo).strip() if pd.notna(_mo) else ''
        prods = inc.get('productos') or []
        if isinstance(prods, str):
            prods = [prods]

        if estado == 'AUTORIZADA':
            est_bg, est_color, est_txt = COLOR_GREEN_PALE, COLOR_GREEN_TEXT, '✓ Autorizada'
        elif estado == 'NO_AUTORIZADA':
            est_bg, est_color, est_txt = COLOR_RED_PALE, COLOR_RED_DARK, '✕ No autorizada'
        else:
            est_bg, est_color, est_txt = COLOR_AMBER_PALE, COLOR_AMBER, '⏳ Pendiente'

        motivo_html = (
            f'<p style="font-size:12px;color:{COLOR_BLUE_DARK};margin:4px 0 0;font-weight:500;">'
            f'{etiqueta_motivo(motivo)}</p>'
        ) if motivo else ''

        prods_html = ''
        if len(prods) > 0:
            if TODOS in prods:
                etiqueta = 'Todos los de la categoría'
            elif len(prods) <= 2:
                etiqueta = ' · '.join(str(p)[:34] for p in prods)
            else:
                etiqueta = f'{str(prods[0])[:28]} y {len(prods) - 1} más'
            prods_html = (
                f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:3px 0 0;">'
                f'🍾 {etiqueta}</p>'
            )

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
            f'{motivo_html}'
            f'{prods_html}'
            f'<p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:4px 0 0;">{sem_txt} · {fecha}</p>'
            f'<p style="font-size:12px;color:{COLOR_NAVY};margin:4px 0 0;line-height:1.4;">{com}</p>'
            f'{rechazo_html}'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;">'
            f'<span style="font-size:10px;color:{COLOR_TEXT_SECONDARY};">📷 {n_fotos} foto(s)</span>'
            f'{trax_html}'
            f'</div>'
            f'</div>'
        )
    r.html(f'<div style="margin-bottom:8px;">{items}</div>')
