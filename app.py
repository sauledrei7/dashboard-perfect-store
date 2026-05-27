"""
Dashboard Perfect Store — App principal.
v7: Conectado a Supabase, con selector de periodo histórico.
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import render as r
from styles.theme import (
    CSS_GLOBAL, COLOR_PINK_PRIMARY, COLOR_BLUE_PRIMARY, COLOR_NAVY,
    COLOR_TEXT_SECONDARY, COLOR_BLUE_BORDER, COLOR_PINK_PALE, COLOR_BLUE_PALE,
    COLOR_GREEN, COLOR_GREEN_PALE, COLOR_AMBER, COLOR_RED_DARK, COLOR_RED_PALE,
    COLOR_RED_BORDER, COLOR_WHITE, COLOR_BLUE_BG,
)
from auth import (
    autenticar, esta_autenticado, get_usuario_actual, cerrar_sesion,
    get_periodo_actual, set_periodo_actual,
)
from components import promotor_resumen, promotor_tiendas, tienda_detalle
from components import supervisor_resumen, supervisor_promotores
from data import listar_periodos, get_periodo_default, get_tiendas_de_ruta, adaptar_tiendas, get_resumen_promotor, adaptar_promotor


# ============================================================
# CONFIG STREAMLIT
# ============================================================
st.set_page_config(
    page_title="Perfect Store",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed",
)
st.markdown(CSS_GLOBAL, unsafe_allow_html=True)


# ============================================================
# LOGIN
# ============================================================
def pantalla_login():
    r.html(f"""
    <div style="text-align:center;padding:40px 0 30px;">
        <div style="font-size:48px;margin-bottom:8px;">🛒</div>
        <h1 style="margin:0;color:{COLOR_NAVY};font-size:28px;font-weight:500;">Perfect Store</h1>
        <p style="color:{COLOR_TEXT_SECONDARY};font-size:14px;margin:8px 0 0;">Inicia sesión para ver tu bono</p>
    </div>
    """)

    r.html(f"""
    <div style="background:linear-gradient(135deg,{COLOR_PINK_PALE} 0%,{COLOR_BLUE_PALE} 100%);border-radius:14px;padding:20px;margin-bottom:20px;border:0.5px solid {COLOR_BLUE_BORDER};">
        <p style="font-size:13px;color:{COLOR_NAVY};margin:0 0 4px;font-weight:500;">¿Cómo iniciar sesión?</p>
        <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:0;line-height:1.5;">
            Si eres promotor, usa tu código (ej. <code>PROMOTOR_43</code>).<br>
            Si eres supervisor, usa tu usuario (ej. <code>supervisor20</code>).
        </p>
    </div>
    """)

    usuario = st.text_input("Usuario", placeholder="PROMOTOR_43 o supervisor20", key="login_user")
    password = st.text_input("Contraseña", type="password", placeholder="Tu contraseña", key="login_pass")

    if st.button("Iniciar sesión", key="btn_login"):
        if not usuario or not password:
            st.warning("Llena ambos campos para continuar.")
            return

        with st.spinner("Validando..."):
            resultado = autenticar(usuario, password)

        if resultado is None:
            st.error("Usuario o contraseña incorrectos.")
        elif resultado.get('expirada'):
            st.error("Tu contraseña ha expirado. Contacta al administrador.")
        else:
            st.session_state.autenticado = True
            st.session_state.usuario = resultado
            # Cargar periodo por default (más reciente)
            try:
                set_periodo_actual(get_periodo_default())
            except Exception:
                pass
            # Pantalla inicial según tipo
            if resultado['tipo'] == 'promotor':
                st.session_state.pantalla = 'resumen_promotor'
            else:
                st.session_state.pantalla = 'resumen_supervisor'
            st.rerun()


# ============================================================
# SELECTOR DE PERIODO (arriba del dashboard)
# ============================================================
def selector_periodo():
    """Muestra el dropdown de periodos disponibles."""
    try:
        df_periodos = listar_periodos()
        if len(df_periodos) == 0:
            st.warning("No hay datos cargados todavía.")
            return

        opciones = df_periodos['periodo_id'].tolist()
        # Fallback: si la descripción está vacía, construirla
        descripciones = {}
        for _, row in df_periodos.iterrows():
            pid = row['periodo_id']
            desc = row.get('descripcion') if 'descripcion' in row else None
            if not desc or str(desc).strip() == '' or str(desc).strip() == 'nan':
                mes = row.get('mes', '')
                anio = row.get('anio', '')
                desc = f"{mes} {anio}" if mes else pid
            descripciones[pid] = desc

        actual = get_periodo_actual() or opciones[0]
        idx_actual = opciones.index(actual) if actual in opciones else 0

        seleccionado = st.selectbox(
            "📅 Periodo",
            options=opciones,
            format_func=lambda x: descripciones.get(x, x),
            index=idx_actual,
            key="selector_periodo",
        )
        if seleccionado != actual:
            set_periodo_actual(seleccionado)
            # Scroll al inicio al cambiar periodo
            _scroll_top()
            st.rerun()
    except Exception as e:
        # El detalle técnico va a los logs del servidor, no a la pantalla del usuario.
        print(f"[PERIODOS ERROR] {e}")
        st.error("No pudimos cargar los periodos en este momento. Intenta recargar la página.")


def _scroll_top():
    """Función desactivada: antes hacía scroll automático al cambiar de pantalla
    usando st.components.v1.html, pero esa API se deprecó (2026-06-01).
    Se dejó vacía para no romper las llamadas existentes en el código.
    Si en el futuro quieres reactivar el scroll, esta es la única función a tocar."""
    pass


# ============================================================
# ROUTER
# ============================================================
def main():
    if not esta_autenticado():
        pantalla_login()
        return

    usuario = get_usuario_actual()
    pantalla = st.session_state.get('pantalla', 'resumen_promotor')
    periodo_id = get_periodo_actual()

    # Detectar cambio de pantalla y hacer scroll al inicio
    pantalla_anterior = st.session_state.get('_pantalla_anterior')
    if pantalla_anterior != pantalla:
        _scroll_top()
        st.session_state['_pantalla_anterior'] = pantalla

    # Mostrar selector de periodo en pantallas principales
    if pantalla in ('resumen_promotor', 'resumen_supervisor'):
        selector_periodo()

    # FLUJO PROMOTOR
    if usuario['tipo'] == 'promotor':
        if pantalla == 'resumen_promotor':
            promotor_resumen.render(usuario, periodo_id)
        elif pantalla == 'tiendas_promotor':
            promotor_tiendas.render(usuario, periodo_id)
        elif pantalla == 'detalle_tienda':
            st.session_state.volver_a = 'tiendas_promotor'
            tienda_detalle.render(periodo_id)
        else:
            promotor_resumen.render(usuario, periodo_id)

    # FLUJO SUPERVISOR
    elif usuario['tipo'] == 'supervisor':
        if pantalla == 'resumen_supervisor':
            supervisor_resumen.render(usuario, periodo_id)
        elif pantalla == 'lista_promotores':
            supervisor_promotores.render(usuario, periodo_id)
        elif pantalla == 'tiendas_de_promotor':
            _render_tiendas_promotor_para_supervisor(usuario, periodo_id)
        elif pantalla == 'detalle_tienda':
            st.session_state.volver_a = 'tiendas_de_promotor'
            tienda_detalle.render(periodo_id)
        else:
            supervisor_resumen.render(usuario, periodo_id)

    else:
        st.error("Tipo de usuario no reconocido.")
        cerrar_sesion()
        st.rerun()


def _render_tiendas_promotor_para_supervisor(usuario, periodo_id):
    """Cuando un supervisor ve las tiendas de uno de sus promotores."""
    from components.promotor_tiendas import _render_tarjeta_tienda

    ruta_sel = st.session_state.get('ruta_seleccionada')
    if not ruta_sel:
        st.error("No se seleccionó ningún promotor")
        return

    tiendas = adaptar_tiendas(get_tiendas_de_ruta(ruta_sel, periodo_id))

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("← Volver", key="back_to_lista_promo"):
            st.session_state.pantalla = 'lista_promotores'
            st.rerun()
    with col2:
        r.html(f"""
        <div>
            <p style="font-size:17px;font-weight:500;margin:0;color:{COLOR_NAVY};">{ruta_sel}</p>
            <p style="font-size:12px;color:{COLOR_TEXT_SECONDARY};margin:2px 0 0;">{len(tiendas)} tiendas</p>
        </div>
        """)

    st.write("")

    # Tarjeta de resumen del bono del promotor (con bono potencial si candado cerrado)
    kpis = adaptar_promotor(get_resumen_promotor(ruta_sel, periodo_id))
    if kpis:
        _render_bono_promotor_para_supervisor(kpis)

    for _, t in tiendas.iterrows():
        _render_tarjeta_tienda(t)


def _render_bono_promotor_para_supervisor(k):
    """Tarjeta de contexto del bono que ve el supervisor al abrir un promotor.
    Cuando el candado está cerrado, muestra el bono POTENCIAL y qué falta."""
    candado = bool(k['CANDADO_ABIERTO'])
    bono_final = k['BONO_FINAL_PCT']
    bono_potencial = k.get('BONO_POTENCIAL_PCT', bono_final)
    pct_ps = k['PCT_PS_RUTA']
    efectividad = k.get('EFECTIVIDAD_PCT', 0)
    faltan = int(k.get('VISITAS_FALTANTES_95', 0) or 0)

    if candado:
        valor = bono_final
        etiqueta = "Bono actual"
        color = COLOR_GREEN if bono_final >= 80 else (COLOR_AMBER if bono_final >= 50 else COLOR_RED_DARK)
        fondo = COLOR_GREEN_PALE if bono_final >= 80 else COLOR_BLUE_BG
        borde = COLOR_BLUE_BORDER
        nota = ""
    else:
        valor = bono_potencial
        etiqueta = "Bono potencial 🔒"
        color = COLOR_RED_DARK
        fondo = COLOR_RED_PALE
        borde = COLOR_RED_BORDER
        falta_txt = (f"Le faltan <b>{faltan}</b> visitas para llegar al 95% y desbloquearlo."
                     if faltan > 0 else "Necesita llegar al 95% de efectividad para desbloquearlo.")
        nota = (f'<p style="font-size:11px;color:{COLOR_RED_DARK};margin:8px 0 0;line-height:1.4;">'
                f'⚠️ Candado cerrado · efectividad {efectividad:.0f}%. {falta_txt}</p>')

    ps_color = COLOR_GREEN if pct_ps >= 80 else (COLOR_AMBER if pct_ps >= 60 else COLOR_RED_DARK)

    r.html(f"""
    <div style="background:{fondo};border-radius:12px;padding:14px 16px;margin-bottom:14px;border:0.5px solid {borde};">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
                <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">{etiqueta}</p>
                <p style="font-size:28px;font-weight:600;margin:2px 0 0;color:{color};">{valor:.0f}%</p>
            </div>
            <div style="text-align:right;">
                <p style="font-size:11px;color:{COLOR_TEXT_SECONDARY};margin:0;">% Perfect Store</p>
                <p style="font-size:20px;font-weight:500;margin:2px 0 0;color:{ps_color};">{pct_ps:.0f}%</p>
            </div>
        </div>
        {nota}
    </div>
    """)


if __name__ == "__main__":
    main()
