"""
TABLERO DEL DIRECTOR (v20) — el marco: menú lateral, encabezado y periodo.

Es la única pantalla de ATLAS pensada para computadora. El resto de la app
sigue siendo de celular y no se entera de nada de esto: el CSS ancho se mete
solo cuando se pinta esta pantalla, y vive únicamente en la sesión del
director. Si un promotor entra al mismo tiempo, su app se ve como siempre.

Las secciones están en director_secciones.py.
"""
import streamlit as st
import render as r
from auth import cerrar_sesion, set_periodo_actual
import pandas as pd
from data import get_periodos_director, get_tablero_director, get_resumen_director, limpiar_cache_director
from components import director_secciones as sec

SECCIONES = [
    ('inicio', 'Inicio', 'Tablero maestro', ':material/home:'),
    ('areas', 'Áreas', 'Áreas', ':material/map:'),
    ('supervisores', 'Supervisores', 'Supervisores', ':material/groups:'),
    ('foco', 'Foco OOS', 'Foco OOS', ':material/track_changes:'),
    ('uso', 'Uso de ATLAS', 'Uso de ATLAS', ':material/smartphone:'),
]
PERIODOS_EN_TENDENCIA = 6

CSS_DIRECTOR = """
<style>
[data-testid="stMainBlockContainer"], .main .block-container, .stMainBlockContainer {
  max-width: 1400px !important; padding: 1.6rem 2.4rem 3rem !important; }
[data-testid="stAppViewContainer"] { background: #FAFBFF; }
/* menú lateral */
[class*="st-key-dirnav_"] button { background: transparent !important; color: #6B7BB8 !important; border: 0 !important;
  box-shadow: none !important; justify-content: flex-start !important; padding: 9px 12px !important;
  font-weight: 400 !important; border-radius: 10px !important; }
[class*="st-key-dirnav_"] button:hover { background: #F4F7FE !important; transform: none !important; }
[class*="st-key-dirnav_"] button > div { justify-content: flex-start !important; }
.st-key-dirnav_ACTIVO button { background: #FDF0F7 !important; color: #B83D7A !important; font-weight: 500 !important;
  box-shadow: inset 0 0 0 0.5px #F8D3E5 !important; }
/* botones secundarios (ver área, abrir supervisor, volver) */
[class*="st-key-dirlink_"] button, .st-key-dir_volver_tablero button { background: #fff !important; color: #B83D7A !important;
  border: 0.5px solid #F8D3E5 !important; padding: 7px 12px !important; font-size: 13px !important; box-shadow: none !important; }
[class*="st-key-dirlink_"] button:hover, .st-key-dir_volver_tablero button:hover { background: #FDF0F7 !important; transform: none !important; }
[class*="st-key-dirlink_"] button:disabled { color: #9AA6D1 !important; border-color: #DCE4F5 !important; background: #F4F7FE !important; }
/* selectores de botones (periodo, métrica, orden, vista) */
[data-testid="stBaseButton-segmented_control"] { background: #fff !important; color: #6B7BB8 !important;
  border-color: #DCE4F5 !important; font-size: 13px !important; }
[data-testid="stBaseButton-segmented_controlActive"] { background: #FDF0F7 !important; color: #B83D7A !important;
  border-color: #F8D3E5 !important; font-weight: 500 !important; font-size: 13px !important; }
.st-key-dir_periodo [data-testid="stButtonGroup"] { display: flex; justify-content: flex-end; }
/* tarjetas con widgets adentro: el borde lo pinta el contenedor de afuera */
[data-testid="stVerticalBlockBorderWrapper"]:has(> [class*="st-key-dircard_"]) { background: #fff;
  border-radius: 14px !important; border-color: #DCE4F5 !important; padding: 18px 20px !important; }
/* Streamlit le quita 1rem abajo a cada markdown; los bloques grandes lo recuperan */
.dh, .dg, .dcard, .daviso, .dac { margin-bottom: 14px !important; }
/* textos sueltos: Streamlit fuerza 1rem a todo <p> del markdown */
p.dnavt, p.dact, p.dlbl, p.dsub-der, p.dnota, p.dpie { font-size: 12px !important; }
p.dpie, p.dnota { font-size: 11.5px !important; }
/* marca y usuario */
.dmarca { display: flex; align-items: center; gap: 12px; padding: 4px 6px 18px; }
.dmarca .dlogo { width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center;
  background: linear-gradient(135deg,#FF6FA8 0%,#FF8DBD 50%,#4F7BE8 100%); }
.dmarca b { font-size: 19px; font-weight: 500; letter-spacing: .14em; display: block; color: #1F2A5C; }
.dmarca small { font-size: 11px; color: #C56FA0; }
.dyo { display: flex; align-items: center; gap: 10px; background: #F4F7FE; border: 0.5px solid #DCE4F5; border-radius: 12px;
  padding: 10px 12px; margin-bottom: 14px; }
.dyo .dav { width: 34px; height: 34px; border-radius: 50%; color: #fff; display: grid; place-items: center; font-size: 12px;
  font-weight: 500; flex: none; background: linear-gradient(135deg,#FF6FA8 0%,#4F7BE8 100%); }
.dyo p { margin: 0; font-size: 13px; font-weight: 500; color: #1F2A5C; }
.dyo span { font-size: 11px; color: #6B7BB8; }
.dnavt { font-size: 11px; color: #9AA6D1; letter-spacing: .08em; margin: 0 0 4px 10px; }
.dact { font-size: 11px; color: #9AA6D1; text-align: center; margin-top: 6px; }
/* encabezado */
.dtop .dhola { font-size: 13px; color: #6B7BB8; margin: 0; }
.dtop .dtit { font-size: 25px; font-weight: 500; color: #1F2A5C; margin: 2px 0 0; line-height: 1.2; }
.dtop .dsubt { font-size: 12px; color: #C56FA0; margin: 3px 0 0; }
.dlbl { font-size: 12px; color: #6B7BB8; margin: 0 0 -6px; }
.daviso { display: flex; gap: 10px; align-items: center; background: #F4F7FE; border: 0.5px solid #DCE4F5; border-radius: 10px;
  padding: 9px 14px; font-size: 13px; color: #6B7BB8; }
.daviso b { color: #1F2A5C; font-weight: 500; }
/* bloques */
.dg { display: grid; gap: 14px; }
.dg4 { grid-template-columns: repeat(4, minmax(0,1fr)); }
.dg32 { grid-template-columns: minmax(0,3fr) minmax(0,2fr); }
.dg21 { grid-template-columns: minmax(0,2fr) minmax(0,1fr); }
.dcard { background: #fff; border: 0.5px solid #DCE4F5; border-radius: 14px; padding: 18px 20px; }
.dct { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.dct .dct-h { font-size: 15px; font-weight: 500; color: #1F2A5C; margin: 0; }
.dct .dct-grande { font-size: 19px; }
.dct .dct-s { font-size: 12px; color: #6B7BB8; margin: 1px 0 0; }
.dsub-der { font-size: 12px; color: #6B7BB8; text-align: right; margin: 10px 0 0; }
/* héroe */
.dh { background: linear-gradient(135deg,#FF6FA8 0%,#FF8DBD 50%,#4F7BE8 100%); border-radius: 16px; color: #fff;
  display: grid; grid-template-columns: 2.2fr repeat(3,1fr); overflow: hidden; }
.dh > div { padding: 22px; }
.dh > div + div { border-left: 0.5px solid rgba(255,255,255,.3); }
.dh p { color: #fff; margin: 0; }
.dh .dh-k { font-size: 13px; opacity: .95; }
.dh .dh-dos { display: flex; align-items: flex-start; gap: 26px; }
.dh .dh-dos > div + div { padding-left: 26px; border-left: 0.5px solid rgba(255,255,255,.35); }
.dh .dh-v { font-size: 54px; font-weight: 500; line-height: 1; margin: 8px 0; }
.dh .dh-vb { font-size: 38px; margin-top: 16px; }
.dh .dh-v2 { font-size: 30px; font-weight: 500; line-height: 1; margin: 10px 0 8px; }
.dh .dh-s { font-size: 12px; opacity: .92; }
.dh .dh-s b { font-weight: 500; }
.dh .dh-brecha { margin-top: 14px; font-size: 12px; border-top: 0.5px solid rgba(255,255,255,.3); padding-top: 10px; }
.dh-chip { display: inline-block; margin-top: 10px; background: rgba(255,255,255,.2); border: 0.5px solid rgba(255,255,255,.45);
  border-radius: 999px; padding: 3px 10px; font-size: 12px; }
/* tarjetas KPI */
.dk { border-radius: 12px; padding: 14px 16px; }
.dk p { margin: 0; }
.dk-rosa { background: #FDF0F7; border: 0.5px solid #F8D3E5; }
.dk-azul { background: #EEF3FE; border: 0.5px solid #C8D6F4; }
.dk .dk-k { font-size: 12px; color: #6B7BB8; }
.dk-rosa .dk-k { color: #B83D7A; }
.dk .dk-v { font-size: 28px; font-weight: 500; margin: 6px 0 4px; line-height: 1.05; }
.dk .dk-v small { font-size: 14px; color: #6B7BB8; font-weight: 400; }
.dk .dk-s { font-size: 11px; color: #6B7BB8; }
.dk-rosa .dk-s { color: #C56FA0; }
.dd { display: inline-block; font-size: 11px; font-weight: 500; border-radius: 999px; padding: 1px 8px; margin-top: 8px; }
.dd-up { background: #E8F5EC; color: #1E5C36; }
.dd-down { background: #FCE8EB; color: #B5303F; }
.dd-eq { background: #fff; color: #6B7BB8; box-shadow: inset 0 0 0 0.5px #DCE4F5; }
.dc-g { color: #2D8A4E !important; } .dc-y { color: #C98319 !important; } .dc-r { color: #B5303F !important; } .dc-n { color: #1F2A5C !important; }
/* semáforo */
.dp { display: inline-block; min-width: 52px; text-align: center; border-radius: 7px; padding: 4px 8px; font-size: 12.5px; font-weight: 500; }
.dp-mini { min-width: 40px; padding: 4px 5px; }
.dp-g { background: #E8F5EC; color: #1E5C36; } .dp-y { background: #FDF0E8; color: #98580E; }
.dp-r { background: #FCE8EB; color: #B5303F; } .dp-n { background: #F4F7FE; color: #1F2A5C; }
.dt { display: inline-block; font-size: 11px; border-radius: 999px; padding: 2px 9px; font-weight: 500; white-space: nowrap; }
.dt-g { background: #E8F5EC; color: #1E5C36; } .dt-r { background: #FCE8EB; color: #B5303F; }
.dt-y { background: #FDF0E8; color: #98580E; } .dt-b { background: #EEF3FE; color: #4055C8; }
/* tablas */
.dtw { overflow-x: auto; }
table.dtab { width: 100%; border-collapse: collapse; font-size: 13px; border: 0 !important; margin: 0; display: table; }
table.dtab th { font-size: 11px; font-weight: 500; color: #9AA6D1; text-align: center; padding: 0 6px 10px; white-space: nowrap;
  border: 0 !important; background: transparent !important; }
table.dtab td { padding: 8px 6px; border: 0 !important; border-top: 0.5px solid #EDF0F8 !important; text-align: center;
  white-space: nowrap; color: #1F2A5C; background: transparent !important; }
table.dtab tr { background: transparent !important; }
table.dtab .di { text-align: left; }
table.dtab tr.dtot td { background: #F4F7FE !important; font-weight: 500; border-top: 0.5px solid #DCE4F5 !important; }
table.dtab .dn1 { font-weight: 500; }
table.dtab .dn2 { display: block; font-size: 11px; color: #6B7BB8; margin-top: 1px; font-weight: 400; }
table.dtab .dnum { font-variant-numeric: tabular-nums; }
table.dtab b { font-weight: 500; }
.drk-n { color: #9AA6D1 !important; font-size: 12px; width: 26px; }
/* ranking */
.drk { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.drk-col { border-radius: 10px; padding: 12px; background: #fff; }
.drk-b { border: 0.5px solid #BBDFC4; } .drk-m { border: 0.5px solid #F4BCC3; }
.drk-h { font-size: 12px; font-weight: 500; margin: 0 0 6px; }
.drk-it { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 7px 0;
  border-top: 0.5px solid #EDF0F8; font-size: 13px; color: #1F2A5C; }
.drk-col .drk-h + .drk-it { border-top: 0; }
.drk-it small { display: block; font-size: 11px; color: #6B7BB8; }
/* áreas */
.dac { border-radius: 14px; padding: 16px 18px; background: #fff; border: 0.5px solid #DCE4F5; margin-bottom: 4px; }
.dac p { margin: 0; }
.dac .dac-nm { font-size: 15px; font-weight: 500; color: #1F2A5C; }
.dac .dac-mt { font-size: 11px; color: #6B7BB8; }
.dac .dac-big { font-size: 40px; font-weight: 500; line-height: 1; margin: 14px 0 2px; }
.dac .dac-lb { font-size: 12px; color: #6B7BB8; }
.dac .dac-mini { display: flex; justify-content: space-between; margin-top: 14px; padding-top: 10px; border-top: 0.5px solid #EDF0F8;
  font-size: 12px; color: #6B7BB8; }
.dac .dac-mini b { display: block; font-size: 14px; font-weight: 500; color: #1F2A5C; }
.dac-sel { background: linear-gradient(135deg,#FF6FA8 0%,#FF8DBD 50%,#4F7BE8 100%); border-color: transparent; }
.dac-sel .dac-nm, .dac-sel .dac-big, .dac-sel .dac-mini b { color: #fff !important; }
.dac-sel .dac-mt, .dac-sel .dac-lb, .dac-sel .dac-mini { color: rgba(255,255,255,.92); }
.dac-sel .dac-mini { border-top-color: rgba(255,255,255,.3); }
.dmk { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 10px; margin-bottom: 18px; }
.dmk > div { background: #F4F7FE; border: 0.5px solid #DCE4F5; border-radius: 10px; padding: 10px 12px; }
.dmk > div:nth-child(odd) { background: #FDF0F7; border-color: #F8D3E5; }
.dmk span { font-size: 11px; color: #6B7BB8; }
.dmk b { display: block; font-size: 20px; font-weight: 500; margin-top: 3px; }
/* foco */
.dbar { height: 8px; border-radius: 999px; background: #EDF0F8; overflow: hidden; }
.dbar i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg,#FF6FA8,#4F7BE8); }
.dsrow { display: grid; grid-template-columns: 118px minmax(0,1fr) 52px; gap: 10px; align-items: center; padding: 7px 0;
  font-size: 13px; color: #1F2A5C; }
.dsrow small { display: block; font-size: 11px; color: #6B7BB8; }
.dleg { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11.5px; color: #6B7BB8; margin-top: 10px; }
.dleg i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.dsin { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 9px 0;
  border-top: 0.5px solid #EDF0F8; font-size: 13px; color: #1F2A5C; }
.dsin .dn1 { font-weight: 500; } .dsin .dn2 { display: block; font-size: 11px; color: #6B7BB8; }
.dnota { font-size: 11.5px; color: #6B7BB8; margin: 12px 0 0; }
.dpie { font-size: 11.5px; color: #9AA6D1; line-height: 1.6; margin: 4px 0 0; }
.dpie b { font-weight: 500; color: #6B7BB8; }
.dvacio { background: #F4F7FE; border: 0.5px solid #DCE4F5; border-radius: 10px; padding: 14px; text-align: center;
  font-size: 13px; color: #6B7BB8; }
</style>
"""


def render(usuario: dict, periodo_id: str):
    seccion = st.session_state.get('dir_seccion', 'inicio')
    if seccion not in {s[0] for s in SECCIONES}:
        seccion = 'inicio'
    r.html(CSS_DIRECTOR.replace('dirnav_ACTIVO', f'dirnav_{seccion}'))

    try:
        periodos = get_periodos_director()
    except Exception as e:
        print(f"[DIRECTOR PERIODOS] {e}")
        st.error("No pudimos cargar los periodos en este momento. Intenta recargar la página.")
        return
    if len(periodos) == 0:
        st.warning("No hay datos cargados todavía.")
        return

    ids = periodos['periodo_id'].tolist()
    if periodo_id not in ids:
        periodo_id = ids[-1]
        set_periodo_actual(periodo_id)

    nav, cuerpo = st.columns([1, 4.6], gap="large")
    with nav:
        _menu(usuario, seccion)
    with cuerpo:
        periodo_id = _encabezado(periodos, periodo_id, seccion)
        _contenido(periodos, periodo_id, seccion)


def _menu(usuario, seccion):
    r.html('<div class="dmarca"><div class="dlogo"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
           'stroke="#fff" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="9.2" cy="19.6" r="1.35"/>'
           '<circle cx="17.6" cy="19.6" r="1.35"/><path d="M2.6 3.6h2.5l2.3 10.9a1.7 1.7 0 0 0 1.7 1.3h8.3a1.7 1.7 0 0 0 1.6-1.3'
           'l1.5-6.6H6.1"/></svg></div><div><b>ATLAS</b><small>Perfect Store</small></div></div>'
           f'<div class="dyo"><div class="dav">DO</div><div><p>{sec._e(usuario.get("nombre") or "Director")}</p>'
           '<span>Operación nacional</span></div></div><p class="dnavt">TABLERO</p>')
    for sid, etiqueta, _, icono in SECCIONES:
        if st.button(etiqueta, key=f"dirnav_{sid}", icon=icono, use_container_width=True):
            st.session_state['dir_seccion'] = sid
            st.rerun()
    st.write("")
    # v20.1: el tablero guarda los datos 1 hora. Este botón los relee al
    # momento, por ejemplo justo después de subir una corrida.
    if st.button("Actualizar datos", key="dirlink_actualizar", icon=":material/refresh:", use_container_width=True):
        limpiar_cache_director()
        st.rerun()
    if st.button("Salir", key="dir_salir", use_container_width=True):
        cerrar_sesion()
        st.rerun()


def _nombre_periodo(periodos, pid):
    filas = periodos[periodos['periodo_id'] == pid]
    if len(filas) == 0:
        return str(pid)
    fila = filas.iloc[0]
    # El año sale de la fecha y no de la columna 'anio', que viene adelantada un año.
    try:
        anio = str(fila['fecha_fin'])[:4]
    except Exception:
        anio = ''
    return f"{str(fila.get('mes') or pid).capitalize()} {anio}".strip()


def _encabezado(periodos, periodo_id, seccion):
    titulo = next(s[2] for s in SECCIONES if s[0] == seccion)
    izq, der = st.columns([2.2, 2])
    ids = periodos['periodo_id'].tolist()[-PERIODOS_EN_TENDENCIA:]
    if periodo_id not in ids:
        ids = ids + [periodo_id]
    with der:
        r.html('<p class="dlbl" style="text-align:right">📅 Periodo</p>')
        elegido = sec.control('Periodo', ids, 'dir_periodo', periodo_id,
                              lambda pid: _nombre_periodo(periodos, pid).split(' ')[0])
        if elegido != periodo_id:
            set_periodo_actual(elegido)
            periodo_id = elegido
    fila = periodos[periodos['periodo_id'] == periodo_id].iloc[0]
    s_ini, s_fin = int(fila['semana_inicio']), int(fila['semana_fin'])
    semanas = f"semana {s_ini}" if s_ini == s_fin else f"semanas {s_ini}–{s_fin}"
    with izq:
        r.html(f'<div class="dtop"><p class="dhola">Hola, {sec._e((st.session_state.get("usuario") or {}).get("nombre") or "Director")}</p>'
               f'<p class="dtit">{titulo}</p><p class="dsubt">{_nombre_periodo(periodos, periodo_id)} · {semanas}</p></div>')
    return periodo_id


def _contenido(periodos, periodo_id, seccion):
    ids = periodos['periodo_id'].tolist()
    pos = ids.index(periodo_id)
    try:
        with st.spinner("Armando el tablero…"):
            P = get_tablero_director(periodo_id)
            PREV = get_tablero_director(ids[pos - 1]) if pos > 0 else None
            historial = []
            if seccion == 'inicio':
                # Para la gráfica de tendencia basta el resumen de país y
                # áreas; el tablero completo solo se arma del mes que se ve
                # y del anterior (que ya se necesita para las comparaciones).
                for pid in ids[-PERIODOS_EN_TENDENCIA:]:
                    if pid == periodo_id:
                        h = P
                    elif PREV and pid == PREV['id']:
                        h = PREV
                    else:
                        h = get_resumen_director(pid)
                    if h:
                        historial.append(h)
    except Exception as e:
        # El detalle va al log; al director no se le enseña un traceback.
        print(f"[DIRECTOR TABLERO] {periodo_id}: {e}")
        st.error("No pudimos armar el tablero en este momento. Intenta recargar la página en unos segundos.")
        return

    if P is None:
        st.info("Este periodo todavía no tiene datos cargados.")
        return

    if PREV and P['semanas'] < PREV['semanas'] and seccion != 'uso':
        r.html(f'<div class="daviso">📅 <span><b>{P["nombre"]} lleva {P["semanas"]} semana{"s" if P["semanas"] > 1 else ""}; '
               f'{PREV["nombre"].lower()} tuvo {PREV["semanas"]}.</b> Las comparaciones son contra {PREV["nombre"].lower()} '
               'completo: tómalas como tendencia, no como cierre.</span></div>')

    {'inicio': lambda: sec.inicio(P, PREV, historial),
     'areas': lambda: sec.areas(P, PREV),
     'supervisores': lambda: sec.supervisores(P, PREV),
     'foco': lambda: sec.foco(P, PREV),
     'uso': lambda: sec.uso(P, PREV)}[seccion]()
    r.html(f'<p class="dact">Datos al cierre de la semana {P["s_fin"]}{_antiguedad(P)}</p>')


def _antiguedad(P):
    """' · leídos hace 12 min', para saber si vale la pena tocar Actualizar."""
    try:
        minutos = int((pd.Timestamp.now(tz='UTC') - pd.Timestamp(P['leido'])).total_seconds() // 60)
    except Exception:
        return ''
    if minutos < 1:
        return ' · leídos hace un momento'
    return f" · leídos hace {minutos} min" if minutos < 60 else f" · leídos hace {minutos // 60} h"
