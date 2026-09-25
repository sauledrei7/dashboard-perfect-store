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
import hashlib
import json

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
    get_borrador, guardar_borrador, borrar_borrador, comprimir_foto,
)
from components import galeria

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
    # v15: la tienda no tenía el producto. No es una falla de TRAX sino una
    # condición de la tienda, pero afecta igual al KPI y hay que documentarla.
    'Desabasto.',
    'Otro (habilita explicación obligatoria).',
]
INCIDENCIA_TOUCHPOINT = 'Touchpoint no reflejado.'   # solo Exhibiciones

# Motivos que exigen decir QUÉ producto falló.
# Desabasto NO va aquí a propósito: se levanta cuando la tienda no tenía ningún
# SKU de la categoría, así que pedirle marcar cuáles sería contradictorio.
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
# v14: el catálogo dejó de ser solo las 3 categorías que se miden en SOS.
# Entran Baileys (LICOR), Zacapa y Captain Morgan (RON), Tanqueray (GINEBRA),
# Mezcal Unión (MEZCAL) y los letreros del OOS (MENU).
# Debe coincidir con el CHECK de 03_productos_v14.sql.
CATEGORIAS = ['TEQUILA', 'VODKA', 'WHISKY', 'LICOR', 'RON',
              'GINEBRA', 'MEZCAL', 'MENU', 'POS', 'OTRO']
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
    'Desabasto.': {
        'titulo': 'La tienda no tenía nada de producto',
        'items': [
            'Foto del <b>anaquel vacío</b>, donde se vea que no hay qué exhibir.',
            'Si la tienda te dio su reporte de inventario, adjúntalo también.',
            'En la explicación dinos <b>desde cuándo</b> está así y si ya lo reportaste.',
        ],
        'ojo': 'Esto es para cuando <b>no tenías ni un SKU</b> de la categoría. '
               'Si sí había producto y el problema fue otro, elige el motivo que '
               'corresponda: no es una falla de TRAX, es que no había qué exhibir.',
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
        # v18: si dejó algo a medias, que el botón lo diga. Si no, no hay
        # forma de que sepa que su avance sigue ahí.
        pendiente = bool(_borrador_de(curt, periodo_id))
        etiqueta = ("▸ Seguir con la incidencia que dejaste" if pendiente
                    else "＋ Levantar incidencia")
        if st.button(etiqueta, key=f"btn_abrir_inc_{curt}"):
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


# ============================================================
# BORRADOR (v18)
#
# v17 logró que el promotor volviera identificado, pero el formulario a medio
# llenar seguía viviendo en la memoria del servidor. Si el celular alcanzaba a
# descartar la pestaña —lo típico al salir a Trax por el link— regresaba a un
# formulario en blanco.
#
# Aquí el avance se guarda conforme lo escriben, y se repone al volver.
#
# Las fotos NO van al borrador, a propósito: ver el comentario del SQL. En
# corto, son archivos y guardarlas dejaría basura en Storage cada vez que
# alguien abandona un borrador; y desde v17 tomar fotos ya no saca de la app,
# así que casi nunca hay fotos que perder cuando esto se cae.
# ============================================================
# INTERRUPTOR DE EMERGENCIA.
#
# Ponlo en False y haz Reboot: el borrador se apaga por completo —ni lee ni
# escribe— y el formulario vuelve a comportarse exactamente como antes de v18.
# Todo lo demás (la sesión que no te saca al login, la cámara dentro de la app)
# sigue funcionando.
#
# Está aquí para que, si algo se pone raro en campo, tengas cómo apagar SOLO
# esto en dos minutos, sin revertir el despliegue completo ni tocar la base.
BORRADOR_ACTIVO = True


def _username():
    return (st.session_state.get('usuario') or {}).get('username')


def _borrador_de(curt, periodo_id):
    """Lee el borrador UNA vez por sesión y tienda, y se queda con él.

    Sin este candado cada rerun sería una consulta más, y Streamlit hace un
    rerun cada vez que el promotor toca cualquier cosa del formulario.
    """
    if not BORRADOR_ACTIVO:
        return None

    cache_key = f"inc_borr_cache_{curt}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    datos = None
    username = _username()
    if username:
        fila = get_borrador(username, curt)
        # Un borrador de otro periodo ya no sirve: las semanas no coinciden.
        if fila and fila.get('periodo_id') == periodo_id:
            datos = fila.get('datos') or None

    st.session_state[cache_key] = datos
    return datos


def _olvidar_borrador(curt):
    """Tira el avance, en la base y en la sesión. Al guardar y al cancelar."""
    username = _username()
    if username and BORRADOR_ACTIVO:
        borrar_borrador(username, curt)
    for k in (f"inc_borr_cache_{curt}", f"inc_borr_puesto_{curt}",
              f"inc_borr_firma_{curt}", f"inc_borr_aviso_{curt}"):
        st.session_state.pop(k, None)


def _restaurar_borrador(curt, periodo_id, opciones_kpi, semanas):
    """Repone en pantalla lo que el promotor llevaba escrito.

    Corre una sola vez por formulario abierto y ANTES de que se dibuje ningún
    widget: la única manera de pre-llenar un widget de Streamlit es dejarle el
    valor en session_state antes de crearlo.

    Cada valor se valida contra las opciones de HOY. Uno que ya no exista
    —la tienda pasó a Perfect Store y su KPI ya no está permitido, o la semana
    se salió del periodo— tiraría el widget con excepción, así que se descarta
    en silencio.

    Devuelve True si repuso algo, para poder avisarle al promotor.
    """
    puesto_key = f"inc_borr_puesto_{curt}"
    if st.session_state.get(puesto_key):
        return st.session_state.get(f"inc_borr_aviso_{curt}", False)
    st.session_state[puesto_key] = True

    datos = _borrador_de(curt, periodo_id)
    if not datos:
        return False

    repuesto = False

    kpi = datos.get('kpi')
    if kpi in opciones_kpi:
        st.session_state[f"inc_kpi_{curt}"] = kpi
        repuesto = True

        motivo = datos.get('motivo')
        if motivo in incidencias_de(kpi):
            # La llave del motivo lleva el KPI dentro, así que solo cuadra
            # porque arriba ya se repuso ese mismo KPI.
            st.session_state[f"inc_motivo_{curt}_{kpi}"] = motivo

            productos = datos.get('productos') or []
            if motivo in INCIDENCIAS_DE_PRODUCTO and productos:
                cat = CATEGORIA_POR_KPI.get(kpi)
                try:
                    catalogo = set(get_productos(kpi, cat)['producto'].tolist())
                except Exception:
                    catalogo = set()
                validos = [p for p in productos if p == TODOS or p in catalogo]
                if validos:
                    st.session_state[f"inc_prod_{curt}_{kpi}_{cat or 'all'}"] = validos

    if datos.get('semana') in semanas:
        st.session_state[f"inc_sem_{curt}"] = datos['semana']
        repuesto = True

    for campo, llave in (('comentario', 'inc_com'), ('link_trax', 'inc_trax')):
        valor = (datos.get(campo) or '').strip()
        if valor:
            st.session_state[f"{llave}_{curt}"] = valor
            repuesto = True

    st.session_state[f"inc_borr_aviso_{curt}"] = repuesto
    return repuesto


def _guardar_borrador_si_cambio(curt, periodo_id, valores):
    """Guarda el avance, pero solo cuando de verdad cambió algo.

    La comparación no es un lujo: Streamlit vuelve a correr el script cada vez
    que tocan cualquier campo, y sin ella cada uno de esos reruns sería una
    escritura a Supabase en medio de que están escribiendo.
    """
    if not BORRADOR_ACTIVO:
        return

    limpio = {k: v for k, v in valores.items() if v not in (None, '', [], ())}
    firma = json.dumps(limpio, sort_keys=True, default=str)

    firma_key = f"inc_borr_firma_{curt}"
    if st.session_state.get(firma_key) == firma:
        return
    st.session_state[firma_key] = firma

    if not limpio:
        return   # abrieron el formulario y no han escrito nada todavía

    username = _username()
    if username:
        guardar_borrador(username, curt, periodo_id, limpio)


# ============================================================
# FOTOS (v17)
#
# Antes esto era un st.file_uploader a secas. El problema no era el widget:
# era que en el celular abrir la galería o la cámara SACA del navegador, y
# mientras el promotor está afuera el sistema operativo suspende la pestaña.
# Al volver, se perdía la sesión y el formulario completo.
#
# st.camera_input abre la cámara DENTRO de la página. No sale del navegador,
# así que la pestaña no se suspende y no se pierde nada.
#
# v22: la mayoría usa la galería, y era ahí donde fallaba. st.file_uploader
# pedía archivos por extensión (en Android podía abrir el explorador de
# archivos en vez de la galería), subía la foto original de 3 a 10 MB por datos
# móviles y daba los errores en inglés. Ahora la galería es un componente
# propio (components/galeria.py) que achica la foto en el mismo celular. El
# file_uploader de antes se queda de repuesto dentro de un desplegable.
# ============================================================
MAX_FOTOS = 3


def _agregar_foto(acum, datos) -> bool:
    """Suma una foto al montón si no está repetida y si todavía cabe.

    La huella hace falta porque los widgets devuelven la MISMA foto en cada
    corrida del script mientras no se limpien: sin ella, la foto entraría
    varias veces.

    v22: la foto se comprime al agregarla y no hasta guardar, para que la
    sesión no cargue fotos de 10 MB mientras el promotor llena lo demás.
    """
    if not datos or len(acum) >= MAX_FOTOS:
        return False
    datos = comprimir_foto(datos)
    huella = hashlib.md5(datos).hexdigest()
    if any(h == huella for _n, _d, h in acum):
        return False
    acum.append((f"foto_{len(acum) + 1}.jpg", datos, huella))
    return True


def _selector_fotos(curt):
    """De 1 a 3 fotos. Devuelve la lista de (nombre, bytes, huella).

    Las fotos se acumulan en session_state y no en el widget, porque
    st.camera_input solo se queda con la última: sin acumulador no se podrían
    juntar tres.
    """
    acum_key = f"inc_fotos_acum_{curt}"
    if acum_key not in st.session_state:
        st.session_state[acum_key] = []
    acum = st.session_state[acum_key]

    st.caption(f"Fotos: llevas {len(acum)} de {MAX_FOTOS} (mínimo 1)")
    # Va arriba y no dentro de la galería: si con esa selección se llenaron las
    # 3, la galería ya no se pinta y el aviso se perdería.
    visto_key, aviso_key = f"inc_galeria_visto_{curt}", f"inc_galeria_aviso_{curt}"
    if st.session_state.get(aviso_key):
        st.warning(st.session_state[aviso_key])

    if len(acum) < MAX_FOTOS:
        # v22: la galería va primero, y por lo tanto por default: es la que usa
        # la mayoría y la que saca la foto completa del celular.
        modo = st.radio(
            "Cómo agregar la foto",
            ["🖼️ De galería", "📸 Tomar ahora"],
            key=f"inc_modofoto_{curt}", horizontal=True, label_visibility="collapsed",
        )

        # La llave lleva len(acum) para que el widget se limpie solo después de
        # cada foto: si no, se queda mostrando la anterior y confunde.
        if modo.startswith("📸"):
            st.caption("Se abre aquí mismo, sin salir de la app.")
            tomada = st.camera_input("Tomar foto", label_visibility="collapsed",
                                     key=f"inc_cam_{curt}_{len(acum)}")
            if tomada is not None and _agregar_foto(acum, tomada.getvalue()):
                st.rerun()
        else:
            st.caption("Se preparan en tu celular antes de subirlas, así pesan poco.")
            sel_id, nuevas, aviso = galeria.elegir_fotos(key=f"inc_galeria_{curt}_{len(acum)}",
                                                         max_fotos=MAX_FOTOS - len(acum),
                                                         recibido=st.session_state.get(visto_key))
            # El componente regresa la misma selección en cada corrida del
            # script: el id evita sumarla dos veces antes de que cambie la llave.
            if sel_id and sel_id != st.session_state.get(visto_key):
                st.session_state[visto_key] = sel_id
                st.session_state[aviso_key] = aviso
                for datos in nuevas:
                    _agregar_foto(acum, datos)
                # Siempre se vuelve a correr: si entró alguna, para dejar el
                # botón limpio; si no (eran repetidas), para que el componente
                # reciba la confirmación, deje de reenviar y suelte las fotos.
                st.rerun()
            with st.expander("¿No se abre tu galería? Prueba aquí"):
                st.caption("Es el cargador de antes. Si la foto no aparece a la primera, "
                           "vuelve a elegirla.")
                subidas = st.file_uploader(
                    "Fotos", type=['jpg', 'jpeg', 'png'], accept_multiple_files=True,
                    label_visibility="collapsed", key=f"inc_fotos_{curt}_{len(acum)}",
                )
                agregadas = [_agregar_foto(acum, f.getvalue()) for f in (subidas or [])]
                if any(agregadas):
                    st.rerun()
    else:
        st.caption("Ya tienes las 3. Quita una si quieres cambiarla.")

    if acum:
        cols = st.columns(MAX_FOTOS)
        for i, (_nombre, datos, _h) in enumerate(list(acum)):
            with cols[i]:
                st.image(datos, use_container_width=True)
                if st.button("Quitar", key=f"inc_quitafoto_{curt}_{i}"):
                    acum.pop(i)
                    st.session_state.pop(aviso_key, None)
                    st.rerun()

    return acum


def _limpiar_fotos(curt):
    """Vacía el montón de fotos. Se llama al cancelar y al guardar, para que la
    siguiente incidencia de esta tienda no arranque con las fotos de la pasada."""
    st.session_state.pop(f"inc_fotos_acum_{curt}", None)
    st.session_state.pop(f"inc_galeria_aviso_{curt}", None)


def _render_formulario(curt, periodo_id, info, ruta, abierto_key, permitidos=None):
    # Estas dos suben aquí porque el borrador se repone ANTES de dibujar nada,
    # y para validar lo que trae necesita saber qué opciones hay hoy.
    opciones_kpi = permitidos or list(KPIS)
    semanas = _semanas_del_periodo(curt, periodo_id)

    try:
        recuperado = _restaurar_borrador(curt, periodo_id, opciones_kpi, semanas)
    except Exception as e:
        # Reponer el avance es un extra. Si algo sale mal el formulario tiene
        # que abrir en blanco, nunca dejar de abrir.
        print(f"[BORRADOR RESTAURAR] {e}")
        recuperado = False

    r.html(f"""
    <div style="background:{COLOR_PINK_PALE};border:0.5px solid {COLOR_PINK_BORDER};
    border-radius:12px;padding:4px 14px 14px;margin:6px 0 10px;">
        <p style="font-size:13px;font-weight:500;color:{COLOR_NAVY};margin:12px 0 2px;">Nueva incidencia</p>
        <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0 0 4px;">
            Todos los campos y al menos 1 foto son obligatorios</p>
    </div>
    """)

    if recuperado:
        r.html(
            f'<div style="background:{COLOR_GREEN_PALE};border:0.5px solid {COLOR_GREEN_BORDER};'
            f'border-radius:10px;padding:10px 12px;margin:0 0 10px;">'
            f'<p style="font-size:12px;color:{COLOR_GREEN_TEXT};margin:0;line-height:1.45;">'
            f'✓ <b>Recuperamos lo que llevabas.</b> Revísalo por si algo cambió. '
            f'Las fotos sí hay que volver a tomarlas.</p></div>'
        )

    _render_guia_general()

    # ---------- 1. KPI afectado ----------
    # En tiendas Perfect Store la lista viene recortada a OOS: no tiene caso
    # mostrar un dropdown de una sola opción, se informa y ya.
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

    # ---------- 3. Productos (solo motivos de producto) ----------
    # v14: ya NO se pregunta la categoría. Cada KPI trae su propio universo
    # (OOS 91, Exhibiciones 113, SOS los de su categoría) y el buscador del
    # multiselect resuelve mejor que obligar a drilear por categoría en celular.
    # Para SOS la categoría sale del KPI; para OOS y Exhibiciones se deduce
    # de lo que el promotor marque.
    categoria = None
    productos_sel = None
    if motivo in INCIDENCIAS_DE_PRODUCTO:
        cat_del_kpi = CATEGORIA_POR_KPI.get(kpi)
        if cat_del_kpi:
            r.html(
                f'<p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:0 0 6px;">'
                f'Categoría: <b style="color:{COLOR_NAVY};">{cat_del_kpi.title()}</b> '
                f'<span style="color:{COLOR_PINK_TEXT};">(por el KPI que elegiste)</span></p>'
            )
        productos_sel, categoria = _selector_productos(curt, kpi, cat_del_kpi)

    # ---------- 4. Semana ----------
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
    fotos = _selector_fotos(curt)
    n_fotos = len(fotos)

    # v18: se guarda el avance aquí, ya con todos los campos leídos, y antes de
    # los botones: así queda a salvo aunque el celular corte la conexión en el
    # siguiente paso.
    _guardar_borrador_si_cambio(curt, periodo_id, {
        'kpi': kpi, 'motivo': motivo, 'categoria': categoria,
        'productos': productos_sel, 'semana': semana,
        'comentario': comentario, 'link_trax': link_trax,
    })

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Cancelar", key=f"inc_cancel_{curt}"):
            st.session_state[abierto_key] = False
            _limpiar_fotos(curt)
            _olvidar_borrador(curt)
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
    # La categoría ya no se valida: o la impone el KPI, o se deduce de lo
    # elegido, y puede quedar en NULL si el promotor marca de varias.
    if motivo in INCIDENCIAS_DE_PRODUCTO and not productos_sel:
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

    with st.spinner("Subiendo fotos y guardando..."):
        try:
            paths = []
            for _nombre, datos, _huella in fotos[:MAX_FOTOS]:
                paths.append(subir_foto_incidencia(datos, ruta, str(curt)))
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
    _limpiar_fotos(curt)
    _olvidar_borrador(curt)
    st.success("Incidencia guardada ✓")
    st.rerun()


def _selector_productos(curt, kpi, categoria=None):
    """Selección MÚLTIPLE de SKUs del universo que le toca a este KPI,
    con opción TODOS. Devuelve (seleccion, categoria_resultante).

    La categoría se deduce de lo marcado cuando el KPI no la impone:
    si todo lo elegido es de la misma, se guarda esa; si es mezcla, va NULL
    (los productos ya quedan guardados uno por uno de todos modos)."""
    df = get_productos(kpi, categoria)
    if len(df) == 0:
        st.warning("No pudimos cargar el catálogo de productos. "
                   "Escribe en la explicación cuál fue el producto afectado.")
        return None, categoria

    skus = df['producto'].tolist()
    etiqueta_todos = ("▸ TODOS los de %s" % categoria.title()) if categoria else "▸ TODOS los productos"

    sel = st.multiselect(
        f"¿Qué producto(s)? · {len(skus)} disponibles",
        [TODOS] + skus,
        format_func=lambda p: etiqueta_todos if p == TODOS else p,
        key=f"inc_prod_{curt}_{kpi}_{categoria or 'all'}",
        placeholder="Escribe para buscar…",
        help="Puedes marcar varios. Si falló todo el anaquel, usa TODOS.",
    )

    if TODOS in sel:
        if len(sel) > 1:
            st.caption("Marcaste TODOS: se ignoran los productos sueltos.")
        return [TODOS], categoria
    if not sel:
        return None, categoria

    if categoria:
        return sel, categoria
    # Sin categoría impuesta: se deduce de lo elegido
    cats = set(df[df['producto'].isin(sel)]['categoria'].dropna())
    return sel, (cats.pop() if len(cats) == 1 else None)


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
