"""
TABLERO DEL DIRECTOR — las 5 secciones (v20).

Inicio, Áreas, Supervisores, Foco OOS y Uso de ATLAS. Los números llegan ya
calculados desde data.get_tablero_director() (que usa director_calc.py); aquí
solo se deciden colores, textos y acomodo.

Dos cuidados que no se ven:
- Ningún bloque HTML lleva renglones en blanco. st.markdown corta el HTML en
  el primer renglón vacío y lo que sigue sale como texto o como código.
- Todo texto que viene de la base pasa por _e() antes de meterse al HTML.
"""
import html as _html
import streamlit as st
import render as r
from data import get_tablero_director, get_uso_director, get_conteo_incidencias_director

AREA_COLORES = ['#FF6FA8', '#4F7BE8', '#1F2A5C', '#A9B6E6', '#C56FA0', '#2D8A4E']


# ============================================================
# FORMATO
# ============================================================
def _e(x) -> str:
    return _html.escape(str(x)) if x is not None else '—'


def f(v, d=0) -> str:
    return '—' if v is None else f"{v:,.{d}f}"


def pct(v, d=0) -> str:
    return '—' if v is None else f"{v:,.{d}f}%"


# Semáforos: los de PS, OOS y bono son los mismos de la vista del AM.
SEM = {
    'ps': lambda v: 'g' if v >= 80 else ('y' if v >= 60 else 'r'),
    'oos': lambda v: 'g' if v >= 95 else ('y' if v >= 85 else 'r'),
    'captura': lambda v: 'g' if v >= 95 else ('y' if v >= 90 else 'r'),
    'efect': lambda v: 'g' if v >= 95 else 'r',
    'sos': lambda v: 'g' if v >= 85 else ('y' if v >= 75 else 'r'),
    'bono_promo': lambda v: 'g' if v >= 70 else ('y' if v >= 50 else 'r'),
    'bono_sup': lambda v: 'g' if v >= 50 else ('y' if v >= 35 else 'r'),
}


def sem_nr(v, promedio) -> str:
    if v is None or not promedio:
        return 'n'
    return 'r' if v > 2 * promedio else ('y' if v > promedio else 'g')


def pill(v, sem, d=0) -> str:
    clase = 'n' if v is None else sem(v)
    return f'<span class="dp dp-{clase}">{pct(v, d)}</span>'


def pill_nr(v, promedio, d=1) -> str:
    return f'<span class="dp dp-{sem_nr(v, promedio)}">{pct(v, d)}</span>'


def color_txt(v, sem) -> str:
    return 'dc-n' if v is None else f'dc-{sem(v)}'


def _corto(periodo) -> str:
    return periodo['nombre'][:3].lower()


def _delta_partes(cur, prv, prev, menos_es_mejor=False, d=1, pts=True):
    """(clase, texto) de la comparación contra el periodo anterior, o None."""
    if prev is None or cur is None or prv is None:
        return None
    x = cur - prv
    if abs(x) < (0.05 if d else 0.5):
        return 'eq', f'= que {_corto(prev)}'
    bueno = x < 0 if menos_es_mejor else x > 0
    unidad = ' pts' if pts else ''
    return ('up' if bueno else 'down'), f"{'▲' if x > 0 else '▼'} {f(abs(x), d)}{unidad} vs {_corto(prev)}"


def delta(cur, prv, prev, **kw) -> str:
    p = _delta_partes(cur, prv, prev, **kw)
    return f'<span class="dd dd-{p[0]}">{p[1]}</span>' if p else ''


def chip_heroe(cur, prv, prev, **kw) -> str:
    p = _delta_partes(cur, prv, prev, **kw)
    return f'<span class="dh-chip">{p[1]}</span>' if p else ''


def delta_conteo(cur, prv, P, PREV) -> str:
    """Un conteo que crece con las semanas (encuestas sin contestar) no se puede
    comparar entre un periodo de 1 semana y uno de 4: se compara por semana."""
    if PREV is None or prv is None:
        return ''
    if P['semanas'] == PREV['semanas']:
        return delta(cur, prv, PREV, menos_es_mejor=True, d=0, pts=False)
    a, b = cur / max(P['semanas'], 1), prv / max(PREV['semanas'], 1)
    if round(a) == round(b):
        return f'<span class="dd dd-eq">{f(a)} por semana, igual que {_corto(PREV)}</span>'
    clase = 'up' if a < b else 'down'
    return f'<span class="dd dd-{clase}">{"▲" if a > b else "▼"} {f(a)} por semana · {_corto(PREV)}: {f(b)}</span>'


def kpi(tono, etiqueta, valor, clase, sub, comparacion='') -> str:
    return (f'<div class="dk dk-{tono}"><p class="dk-k">{etiqueta}</p>'
            f'<p class="dk-v {clase}">{valor}</p><p class="dk-s">{sub}</p>{comparacion}</div>')


def tarjeta_titulo(titulo, sub='', extra='') -> str:
    # <p> y no <h3>: Streamlit les pone su propio tamaño y un ancla a los h1-h3.
    return f'<div class="dct"><div><p class="dct-h">{titulo}</p><p class="dct-s">{sub}</p></div>{extra}</div>'


def control(etiqueta, opciones, key, actual, fmt=str):
    """Selector de botones que nunca se queda en blanco.

    st.segmented_control deja des-seleccionar tocando la opción activa; aquí eso
    no tiene sentido (siempre hay un periodo, un orden, un área), así que se
    regresa a la opción que estaba.
    """
    def formato(x):
        # Una etiqueta que no se encuentra no debe tumbar la pantalla.
        try:
            texto = fmt(x)
        except Exception:
            texto = None
        return str(x) if texto is None else str(texto)

    if st.session_state.get(key) not in opciones:
        st.session_state[key] = actual if actual in opciones else opciones[0]
    valor = st.segmented_control(etiqueta, opciones, format_func=formato, key=key,
                                 label_visibility='collapsed')
    if valor is None:
        st.rerun()
    return valor


def _tabla_vacia(texto) -> None:
    r.html(f'<div class="dvacio">{texto}</div>')


# ============================================================
# 1. INICIO
# ============================================================
def inicio(P, PREV, historial):
    n = P['nacional']
    pv = PREV['nacional'] if PREV else {}
    sup_abiertos = n.get('sups', 0) - n.get('sup_cerrado', 0)
    sup_abiertos_prev = (pv.get('sups', 0) - pv.get('sup_cerrado', 0)) if PREV else None
    brecha = (n['ps'] - n['ps_real']) if n['ps'] is not None and n['ps_real'] is not None else None

    heroe = (
        '<div class="dh">'
        '<div class="dh-ps"><p class="dh-k">Perfect Store nacional</p><div class="dh-dos">'
        f'<div><p class="dh-v">{pct(n["ps_real"])}</p>'
        f'<p class="dh-s"><b>Real</b> · {f(n["ps_real_tiendas"])} PS de {f(n["visitadas"])} visitadas</p>'
        f'{chip_heroe(n["ps_real"], pv.get("ps_real"), PREV)}</div>'
        f'<div><p class="dh-v dh-vb">{pct(n["ps"])}</p>'
        f'<p class="dh-s"><b>Para bono</b> · sobre {f(n["capturadas"])} capturadas</p>'
        f'{chip_heroe(n["ps"], pv.get("ps"), PREV)}</div></div>'
        + (f'<p class="dh-brecha">+{f(brecha, 1)} pts por mayoreo y departamental: sus {n["bonus_ps"]} PS '
           f'suman al bono, pero sus {n["bonus_visitadas"]} visitadas no cuentan en el total.</p>' if brecha else '')
        + '</div>'
        f'<div><p class="dh-k">Cobro promotores</p><p class="dh-v2">{pct(n["bono_promo"])}</p>'
        f'<p class="dh-s">promedio · incluye candados en 0</p>{chip_heroe(n["bono_promo"], pv.get("bono_promo"), PREV)}</div>'
        f'<div><p class="dh-k">Cobro supervisores</p><p class="dh-v2">{pct(n.get("bono_sup"))}</p>'
        f'<p class="dh-s">promedio · tope 70% · 🔓 {sup_abiertos} de {n.get("sups", 0)} abiertos</p>'
        f'{chip_heroe(n.get("bono_sup"), pv.get("bono_sup"), PREV)}</div>'
        f'<div><p class="dh-k">Promotores que cobran</p><p class="dh-v2">{f(n["cobran"])}</p>'
        f'<p class="dh-s">de {f(n["rutas"])} rutas · {n["promo_cerrado"]} con candado cerrado</p>'
        f'{chip_heroe(n["cobran"], pv.get("cobran"), PREV, d=0, pts=False)}</div>'
        '</div>'
    )
    r.html(heroe)

    tarjetas = [
        ('rosa', 'OOS', pct(n['oos'], 1), color_txt(n['oos'], SEM['oos']),
         f'{f(n["no_cont"])} sin contestar de {f(n["obj_oos"])}', delta(n['oos'], pv.get('oos'), PREV)),
        ('azul', 'Captura de tiendas', pct(n['captura'], 1), color_txt(n['captura'], SEM['captura']),
         f'{f(n["capturadas"])} tiendas capturadas', delta(n['captura'], pv.get('captura'), PREV)),
        ('rosa', 'Efectividad de visitas', pct(n['efect'], 1), color_txt(n['efect'], SEM['efect']),
         'el candado se cierra abajo de 95%', delta(n['efect'], pv.get('efect'), PREV)),
        ('azul', 'Visitas con incidencia', pct(n['vis_incid'], 1), 'dc-n',
         'vacaciones, vacantes, incapacidad…', delta(n['vis_incid'], pv.get('vis_incid'), PREV, menos_es_mejor=True)),
        ('azul', 'SOS whisky', pct(n['sos_w']), color_txt(n['sos_w'], SEM['sos']),
         'tiendas en objetivo', delta(n['sos_w'], pv.get('sos_w'), PREV)),
        ('rosa', 'SOS tequila', pct(n['sos_t']), color_txt(n['sos_t'], SEM['sos']),
         'tiendas en objetivo', delta(n['sos_t'], pv.get('sos_t'), PREV)),
        ('azul', 'SOS vodka', pct(n['sos_v']), color_txt(n['sos_v'], SEM['sos']),
         'tiendas en objetivo', delta(n['sos_v'], pv.get('sos_v'), PREV)),
        ('rosa', 'Exhibiciones 4 puntos', pct(n['exh']), color_txt(n['exh'], SEM['sos']),
         'tiendas con sus 4 puntos', delta(n['exh'], pv.get('exh'), PREV)),
    ]
    r.html('<div class="dg dg4">' + ''.join(kpi(*t) for t in tarjetas) + '</div>')

    r.html('<div class="dcard">'
           + tarjeta_titulo('Matriz de áreas', 'PS, OOS, SOS y cobro de cada área · el detalle está en Áreas',
                            '<span class="dt dt-b">estructura de áreas vigente</span>')
           + f'<div class="dtw">{_tabla_areas(P)}</div></div>')

    izq, der = st.columns([1.15, 1], gap="medium")
    with izq:
        with st.container(border=True, key='dircard_tendencia'):
            r.html(tarjeta_titulo('Cómo vienen las áreas', ' → '.join(h['nombre'] for h in historial)))
            metricas = {'ps_real': 'PS real', 'ps': 'PS bono', 'bono_promo': 'Cobro',
                        'captura': 'Captura', 'efect': 'Efectividad'}
            metrica = control('Métrica', list(metricas), 'dir_tendencia', 'ps_real', metricas.get)
            r.html(_svg_tendencia(historial, metrica, P['id']))
    with der:
        r.html('<div class="dcard">'
               + tarjeta_titulo('Ranking de supervisores', f'Por cobro final · los {len(P["supervisores"])} del país')
               + _ranking(P) + '</div>')

    r.html('<p class="dpie"><b>PS real:</b> tiendas PS ÷ tiendas visitadas, de todos los canales. '
           '<b>PS para bono:</b> mayoreo y departamental suman si logran PS, pero no cuentan en el total; '
           'es el que ven promotores y supervisores y el que se paga.<br>'
           'Semáforo · PS (real y bono): verde 80%+, amarillo 60%+ · OOS: verde 95%+, amarillo 85%+ · '
           'Captura: verde 95%+, amarillo 90%+ · Efectividad: rojo abajo de 95% (candado) · '
           'SOS y exhibiciones: verde 85%+, amarillo 75%+ · Cobro promotores: verde 70%+, amarillo 50%+.</p>')


def _sos_triple(x) -> str:
    return ' '.join(f'<span class="dp dp-{"n" if x.get(k) is None else SEM["sos"](x[k])} dp-mini">{pct(x.get(k))}</span>'
                    for k in ('sos_w', 'sos_t', 'sos_v'))


def _tabla_areas(P) -> str:
    def fila(nombre, sub, a, clase=''):
        return (f'<tr class="{clase}"><td class="di"><span class="dn1">{_e(nombre)}</span><span class="dn2">{sub}</span></td>'
                f'<td>{pill(a["ps_real"], SEM["ps"])}</td><td>{pill(a["ps"], SEM["ps"])}</td>'
                f'<td>{pill(a["oos"], SEM["oos"], 1)}</td><td>{pill(a["captura"], SEM["captura"])}</td>'
                f'<td>{pill(a["efect"], SEM["efect"], 1)}</td><td>{_sos_triple(a)}</td>'
                f'<td>{pill(a["exh"], SEM["sos"])}</td><td>{pill(a["bono_promo"], SEM["bono_promo"])}</td>'
                f'<td class="dnum">{a["cobran"]}<span class="dn2">de {a["rutas"]}</span></td></tr>')
    h = ('<table class="dtab"><tr><th class="di">Área</th><th>PS real</th><th>PS bono</th><th>OOS</th>'
         '<th>Captura</th><th>Efect.</th><th>SOS W · T · V</th><th>Exh</th><th>Cobro</th><th>Cobran</th></tr>')
    for nombre, a in P['areas'].items():
        h += fila(nombre, f'{a.get("sups", 0)} sups · {a["rutas"]} rutas', a)
    n = P['nacional']
    h += fila('Nacional', f'{n.get("sups", 0)} sups · {n["rutas"]} rutas', n, 'dtot')
    return h + '</table>'


def _ranking(P) -> str:
    ss = sorted([s for s in P['supervisores'] if s.get('bono') is not None], key=lambda s: -s['bono'])
    if not ss:
        return '<div class="dvacio">Sin supervisores en este periodo.</div>'

    def it(s):
        candado = '' if s['candado'] else ' · 🔒'
        return (f'<div class="drk-it"><div>{_e(s["sup"])}<small>{_e(s["area"])} · PS real {pct(s.get("ps_real"))} · '
                f'bono {pct(s["ps"])}{candado}</small></div>{pill(s["bono"], SEM["bono_sup"])}</div>')
    return ('<div class="drk">'
            f'<div class="drk-col drk-b"><p class="drk-h dc-g">🏆 Mejores</p>{"".join(it(s) for s in ss[:4])}</div>'
            f'<div class="drk-col drk-m"><p class="drk-h dc-r">⚠️ Menores</p>{"".join(it(s) for s in ss[::-1][:4])}</div>'
            '</div>')


def _svg_tendencia(historial, metrica, actual_id) -> str:
    W, H, L, R, T, B = 640, 270, 38, 92, 14, 30
    if len(historial) < 2:
        return '<div class="dvacio">Hace falta más de un periodo para ver la tendencia.</div>'
    areas = sorted({a for h in historial for a in h['areas']})
    series = [(a, [h['areas'].get(a, {}).get(metrica) for h in historial]) for a in areas]
    series.append(('Nacional', [h['nacional'].get(metrica) for h in historial]))
    valores = [v for _, vs in series for v in vs if v is not None]
    if not valores:
        return '<div class="dvacio">Sin datos para esta métrica.</div>'
    paso = 10 if max(valores) - min(valores) > 30 else 5
    lo = int(min(valores) // paso * paso)
    hi = int(-(-max(valores) // paso) * paso)
    if hi - lo < 2 * paso:
        hi = lo + 2 * paso

    def x(i):
        return L + i * (W - L - R) / (len(historial) - 1)

    def y(v):
        return T + (hi - v) * (H - T - B) / (hi - lo)

    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block">']
    for g in range(lo, hi + 1, paso):
        s.append(f'<line x1="{L}" x2="{W - R}" y1="{y(g):.1f}" y2="{y(g):.1f}" stroke="#EDF0F8"/>'
                 f'<text x="{L - 8}" y="{y(g) + 4:.1f}" font-size="11" fill="#9AA6D1" text-anchor="end">{g}</text>')
    for i, h in enumerate(historial):
        es = h['id'] == actual_id
        etiqueta = h['nombre'] + (f' ({h["semanas"]} sem)' if i == len(historial) - 1 and i > 0
                                  and h['semanas'] < historial[i - 1]['semanas'] else '')
        s.append(f'<text x="{x(i):.1f}" y="{H - 8}" font-size="12" fill="{"#B83D7A" if es else "#6B7BB8"}" '
                 f'font-weight="{500 if es else 400}" text-anchor="middle">{_e(etiqueta)}</text>')
    etiquetas = []
    for k, (nombre, vs) in enumerate(series):
        nacional = nombre == 'Nacional'
        color = '#6B7BB8' if nacional else AREA_COLORES[k % len(AREA_COLORES)]
        puntos = [(x(i), y(v)) for i, v in enumerate(vs) if v is not None]
        if not puntos:
            continue
        # Sin comillas anidadas ni diagonales dentro de los f-strings: eso solo
        # lo acepta Python 3.12+, y Streamlit Cloud elige la versión solo.
        guiones = 'stroke-dasharray="4 4" ' if nacional else ''
        coords = ' '.join('%.1f,%.1f' % (a, b) for a, b in puntos)
        grosor = 1.5 if nacional else 2.4
        s.append(f'<polyline fill="none" stroke="{color}" stroke-width="{grosor}" {guiones}'
                 f'stroke-linecap="round" stroke-linejoin="round" points="{coords}"/>')
        if not nacional:
            for i, v in enumerate(vs):
                if v is not None:
                    radio = 4.5 if historial[i]['id'] == actual_id else 3
                    s.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="{radio}" fill="#fff" stroke="{color}" stroke-width="2"/>')
        ultimo = next((v for v in reversed(vs) if v is not None), None)
        etiquetas.append([nombre, color, puntos[-1][1], ultimo])
    etiquetas.sort(key=lambda e: e[2])
    for i in range(1, len(etiquetas)):
        if etiquetas[i][2] - etiquetas[i - 1][2] < 14:
            etiquetas[i][2] = etiquetas[i - 1][2] + 14
    for nombre, color, yy, v in etiquetas:
        texto_color = '#7F8FCB' if color == '#A9B6E6' else color
        s.append(f'<text x="{W - R + 10}" y="{yy + 4:.1f}" font-size="11.5" fill="{texto_color}" font-weight="500">'
                 f'{_e(nombre.replace("GR_", ""))} {f(v)}</text>')
    s.append('</svg>')
    return ''.join(s)


# ============================================================
# 2. ÁREAS
# ============================================================
def areas(P, PREV):
    nombres = list(P['areas'])
    if not nombres:
        _tabla_vacia('No hay áreas en este periodo.')
        return
    if st.session_state.get('dir_area') not in nombres:
        st.session_state['dir_area'] = nombres[0]
    sel = st.session_state['dir_area']

    columnas = st.columns(len(nombres), gap="small")
    for col, nombre in zip(columnas, nombres):
        a = P['areas'][nombre]
        with col:
            r.html(f'<div class="dac{" dac-sel" if nombre == sel else ""}"><p class="dac-nm">{_e(nombre)}</p>'
                   f'<p class="dac-mt">{a.get("sups", 0)} supervisores · {a["rutas"]} rutas · {f(a["tiendas"])} tiendas</p>'
                   f'<p class="dac-big {color_txt(a["ps_real"], SEM["ps"])}">{pct(a["ps_real"])}</p>'
                   f'<p class="dac-lb">Perfect Store real · para bono {pct(a["ps"])}</p>'
                   f'<div class="dac-mini"><div>Cobro<b>{pct(a["bono_promo"])}</b></div><div>OOS<b>{pct(a["oos"], 1)}</b></div>'
                   f'<div>Captura<b>{pct(a["captura"])}</b></div><div>Efect.<b>{pct(a["efect"], 1)}</b></div></div></div>')
            # El área elegida también lleva botón (apagado) para que las 4
            # tarjetas queden del mismo alto.
            if st.button("Viendo esta área" if nombre == sel else f"Ver {nombre}", key=f"dirlink_area_{nombre}",
                         use_container_width=True, disabled=nombre == sel):
                st.session_state['dir_area'] = nombre
                st.rerun()

    a = P['areas'][sel]
    ap = PREV['areas'].get(sel, {}) if PREV else {}
    sups = sorted([s for s in P['supervisores'] if s['area'] == sel], key=lambda s: (s['bono'] is None, s['bono'] or 0))

    with st.container(border=True, key='dircard_area'):
        izq, der = st.columns([3, 1.1])
        with izq:
            r.html(f'<div class="dct"><div><p class="dct-h dct-grande">{_e(sel)}</p>'
                   f'<p class="dct-s">{a.get("sups", 0)} supervisores · {a["rutas"]} rutas · {f(a["tiendas"])} tiendas · '
                   f'{a["cobran"]} promotores cobran</p></div></div>')
        with der:
            if st.button("Ver como Area Manager →", key="dir_entrar_am", use_container_width=True):
                _abrir_vista_am(sel, 'resumen_am')
        franja = [
            ('PS real', pct(a['ps_real']), color_txt(a['ps_real'], SEM['ps']), delta(a['ps_real'], ap.get('ps_real'), PREV)),
            ('PS para bono', pct(a['ps']), color_txt(a['ps'], SEM['ps']), delta(a['ps'], ap.get('ps'), PREV)),
            ('OOS', pct(a['oos'], 1), color_txt(a['oos'], SEM['oos']), delta(a['oos'], ap.get('oos'), PREV)),
            ('Captura', pct(a['captura'], 1), color_txt(a['captura'], SEM['captura']), delta(a['captura'], ap.get('captura'), PREV)),
            ('Efectividad', pct(a['efect'], 1), color_txt(a['efect'], SEM['efect']), delta(a['efect'], ap.get('efect'), PREV)),
            ('Exhibiciones', pct(a['exh']), color_txt(a['exh'], SEM['sos']), delta(a['exh'], ap.get('exh'), PREV)),
            ('Cobro promotores', pct(a['bono_promo']), color_txt(a['bono_promo'], SEM['bono_promo']),
             delta(a['bono_promo'], ap.get('bono_promo'), PREV)),
            ('No reconocido', pct(a['nr'], 1), f'dc-{sem_nr(a["nr"], P["prom_nr"])}',
             delta(a['nr'], ap.get('nr'), PREV, menos_es_mejor=True)),
        ]
        r.html('<div class="dmk">' + ''.join(f'<div><span>{k}</span><b class="{c}">{v}</b>{d}</div>'
                                              for k, v, c, d in franja) + '</div>')
        r.html(tarjeta_titulo('Sus supervisores', 'Ordenados por cobro, del menor al mayor')
               + f'<div class="dtw">{tabla_supervisores(sups, P, con_area=False)}</div>')
        _abrir_supervisor(sups, 'area')


def celda_sin_contestar(s) -> str:
    """v21: cuántas encuestas de OOS dejó sin contestar todo su equipo. Lleva el
    color de su OOS, que es de donde sale el %; el cero siempre va en verde."""
    nc, obj = s.get('no_cont'), s.get('obj_oos')
    if nc is None:
        return '<span class="dp dp-n">—</span>'
    clase = 'g' if nc == 0 else ('n' if s.get('oos') is None else SEM['oos'](s['oos']))
    titulo = f' title="{f(nc)} de {f(obj)} encuestas con objetivo"' if obj else ''
    return f'<span class="dp dp-{clase}"{titulo}>{f(nc)}</span>'


def tabla_supervisores(lista, P, con_area=True) -> str:
    h = ('<table class="dtab"><tr><th class="drk-n"></th><th class="di">Supervisor</th><th>Rutas</th><th>PS real</th>'
         '<th>PS bono</th><th>OOS</th><th>Captura</th><th>Efect.</th><th>SOS W · T · V</th><th>Exh</th>'
         '<th>No recon.</th><th>Sin contestar</th><th>Candado</th><th>Cobro</th></tr>')
    for i, s in enumerate(lista, 1):
        candado = ('<span class="dt dt-g">🔓 Abierto</span>' if s['candado']
                   else f'<span class="dt dt-r">🔒 Faltan {s["faltan"]}</span>')
        sub = (f'{_e(s["area"])} · ' if con_area else '') + f'{s.get("cobran", 0)} de {s.get("rutas", 0)} promotores cobran'
        # v21: el renglón de abajo puede partirse en dos. Con la columna de sin
        # contestar, la tabla ya no cabía en una laptop y el cobro se escondía.
        h += (f'<tr><td class="drk-n">{i}</td><td class="di"><span class="dn1">{_e(s["sup"])}</span>'
              f'<span class="dn2" style="white-space:normal;">{sub}</span></td>'
              f'<td class="dnum">{s.get("rutas", 0)}</td><td>{pill(s.get("ps_real"), SEM["ps"])}</td>'
              f'<td>{pill(s["ps"], SEM["ps"])}</td><td>{pill(s["oos"], SEM["oos"], 1)}</td>'
              f'<td>{pill(s.get("captura"), SEM["captura"])}</td><td>{pill(s["efect"], SEM["efect"], 1)}</td>'
              f'<td>{_sos_triple(s)}</td><td>{pill(s.get("exh"), SEM["sos"])}</td>'
              f'<td>{pill_nr(s.get("nr"), P["prom_nr"])}</td><td>{celda_sin_contestar(s)}</td><td>{candado}</td>'
              f'<td>{pill(s["bono"], SEM["bono_sup"])}</td></tr>')
    return h + '</table>'


def _abrir_vista_am(area, pantalla, **extra):
    """Deja al director dentro de las pantallas del AM, parado en un área.
    app.py las pinta igual que para el AM, con un botón para volver."""
    st.session_state['director_area'] = area
    for k, v in extra.items():
        st.session_state[k] = v
    st.session_state.pantalla = pantalla
    st.rerun()


def _valor_orden(s, campo) -> str:
    v = s.get(campo)
    if campo == 'no_cont':
        return f(v)
    return pct(v, 1 if campo in ('oos', 'efect', 'nr') else 0)


def _abrir_supervisor(lista, contexto, campo='bono'):
    """v21: el desplegable va de mayor a menor en la medida con la que se ordena
    la tabla, y la enseña en cada renglón. La tabla, en cambio, pone primero a
    los que más atención necesitan."""
    if not lista:
        return
    nombre = next((n for n, c, _ in ORDENES.values() if c == campo), campo)
    ordenados = sorted(lista, key=lambda s: (s.get(campo) is None, -(s.get(campo) or 0)))
    izq, der = st.columns([3, 1.2])
    with izq:
        etiquetas = {s['supervisor']: f"{s['sup']} · {s['area']} · {nombre} {_valor_orden(s, campo)}"
                     for s in ordenados}
        elegido = st.selectbox("Abrir supervisor", list(etiquetas),
                               format_func=lambda sid: etiquetas.get(sid, str(sid)),
                               key=f"dir_abrir_sup_{contexto}", label_visibility='collapsed')
    with der:
        if st.button("Ver sus promotores →", key=f"dirlink_sup_{contexto}", use_container_width=True):
            s = next(x for x in lista if x['supervisor'] == elegido)
            _abrir_vista_am(s['area'], 'promotores_de_supervisor_am',
                            supervisor_seleccionado=s['supervisor'],
                            supervisor_seleccionado_nombre=s['sup'])


# ============================================================
# 3. SUPERVISORES
# ============================================================
ORDENES = {
    'bono': ('Cobro', 'bono', 1), 'ps_real': ('PS real', 'ps_real', 1), 'ps': ('PS bono', 'ps', 1),
    'efect': ('Efectividad', 'efect', 1), 'captura': ('Captura', 'captura', 1), 'oos': ('OOS', 'oos', 1),
    'nr': ('No reconocido', 'nr', -1), 'sc': ('Sin contestar', 'no_cont', -1),
}


def supervisores(P, PREV):
    with st.container(border=True, key='dircard_sups'):
        filtro_col, orden_col = st.columns([1, 1.9])
        with filtro_col:
            r.html('<p class="dlbl">Área</p>')
            area = control('Área', ['Todas'] + list(P['areas']), 'dir_sup_area', 'Todas')
        with orden_col:
            r.html('<p class="dlbl">Ordenar por (primero los que más atención necesitan)</p>')
            orden = control('Ordenar', list(ORDENES), 'dir_sup_orden', 'bono', lambda k: ORDENES[k][0])
        _, campo, direccion = ORDENES[orden]
        lista = [s for s in P['supervisores'] if area == 'Todas' or s['area'] == area]
        # Sin dato va al final, sin importar el orden.
        lista.sort(key=lambda s: (s.get(campo) is None, direccion * (s.get(campo) or 0)))
        cerrados = sum(1 for s in lista if not s['candado'])
        donde = 'del país' if area == 'Todas' else f'de {_e(area)}'
        aviso = (f'<span class="dc-r">{cerrados} con candado cerrado</span>' if cerrados
                 else 'todos con candado abierto')
        r.html(tarjeta_titulo(f'Los {len(lista)} supervisores {donde}', aviso)
               + f'<div class="dtw">{tabla_supervisores(lista, P)}</div>')
        _abrir_supervisor(lista, 'lista', campo)


# ============================================================
# 4. FOCO OOS
# ============================================================
def foco(P, PREV):
    # v20.1: el tablero se guarda 1 hora, pero las incidencias cambian todo el
    # día; se leen aparte (2 minutos) y se pegan aquí.
    conteo = get_conteo_incidencias_director(P['id'])
    P = dict(P, promotores=[dict(x, inc_nr=int(conteo['nr'].get(x['ruta'], 0)),
                                 inc_oos=int(conteo['oos'].get(x['ruta'], 0)))
                            for x in P['promotores']])
    n = P['nacional']
    pv = PREV['nacional'] if PREV else {}
    r.html('<div class="dg dg4">'
           + kpi('rosa', 'Contestan "no reconocido"', pct(n['nr'], 1), 'dc-n', 'de todas las respuestas OOS',
                 delta(n['nr'], pv.get('nr'), PREV, menos_es_mejor=True))
           + kpi('azul', 'Encuestas sin contestar', f(n['no_cont']), 'dc-r' if n['no_cont'] else 'dc-g',
                 f'en {P["rutas_sc"]} rutas · de {f(n["obj_oos"])}', delta_conteo(n['no_cont'], pv.get('no_cont'), P, PREV))
           + kpi('rosa', 'Promotores en rojo', f(P['rojos_nr']), 'dc-r', 'más de 2× el promedio de no reconocido',
                 delta(P['rojos_nr'], PREV['rojos_nr'] if PREV else None, PREV, menos_es_mejor=True, d=0, pts=False))
           + kpi('azul', 'Contestan "no catalogado"', pct(n['cat'], 1), 'dc-y' if (n['cat'] or 0) > 30 else 'dc-n',
                 'hay que vigilarlo: es la otra salida fácil', delta(n['cat'], pv.get('cat'), PREV, menos_es_mejor=True))
           + '</div>')

    top_sups = sorted([s for s in P['supervisores'] if s.get('nr') is not None], key=lambda s: -s['nr'])[:7]
    filas_sup = ''.join(
        f'<div class="dsrow"><div>{_e(s["sup"])}<small>{_e(s["area"])}</small></div>'
        f'<div class="dbar"><i style="width:{min(100, (s["nr"] or 0) / 50 * 100):.0f}%"></i></div>'
        f'{pill_nr(s["nr"], P["prom_nr"], 0)}</div>' for s in top_sups)
    r.html('<div class="dg dg32">'
           '<div class="dcard">' + tarjeta_titulo('Qué contestan, semana a semana',
                                                  'Mezcla de motivos de las encuestas OOS · semanas TRAX')
           + _svg_motivos(P) +
           '<div class="dleg"><span><i style="background:#FF6FA8"></i>No reconocido</span>'
           '<span><i style="background:#4F7BE8"></i>No catalogado</span><span><i style="background:#C8D6F4"></i>Sin inventario</span>'
           '<span><i style="background:#E4E8F4"></i>Otros motivos</span><span><i style="background:#B5303F"></i>Sin contestar</span></div></div>'
           '<div class="dcard">' + tarjeta_titulo('Supervisores', '% de "no reconocido" de todo su equipo')
           + (filas_sup or '<div class="dvacio">Sin respuestas OOS en este periodo.</div>')
           + '<p class="dnota">Si varios del mismo equipo salen en rojo, el tema es del supervisor.</p></div>'
           '</div>')

    with st.container(border=True, key='dircard_foco'):
        vistas = {'nr': 'No reconocido por TRAX', 'sc': 'No contestan'}
        izq, der = st.columns([1.3, 2])
        with izq:
            vista = control('Vista', list(vistas), 'dir_foco', 'nr', vistas.get)
        with der:
            sub = (f'Promedio del equipo: {pct(P["prom_nr"], 1)} · mínimo 10 respuestas para entrar'
                   if vista == 'nr' else 'Encuestas OOS que el promotor dejó en blanco')
            r.html(f'<p class="dsub-der">{sub}</p>')
        if vista == 'nr':
            lista = sorted([x for x in P['promotores'] if x['semaforo'] in ('ROJO', 'AMARILLO')],
                           key=lambda x: -(x['pct_nr'] or 0))[:15]
            r.html(f'<div class="dtw">{_tabla_nr(lista)}</div>' if lista else
                   '<div class="dvacio">Nadie arriba del promedio en este periodo.</div>')
        else:
            lista = sorted([x for x in P['promotores'] if x['no_cont'] > 0],
                           key=lambda x: (-x['no_cont'], x['oos'] or 0))[:15]
            r.html(f'<div class="dtw">{_tabla_sc(lista)}</div>' if lista else
                   '<div class="dvacio">Nadie dejó encuestas sin contestar en este periodo.</div>')
        _abrir_promotor(lista, vista)


def _tabla_nr(lista) -> str:
    h = ('<table class="dtab"><tr><th class="drk-n"></th><th class="di">Promotor</th><th>Respuestas</th>'
         '<th>No reconocido</th><th>%</th><th>× el promedio</th><th>TRAX · imagen · ml</th>'
         '<th>Semanas arriba del promedio</th><th>Incidencias "no reconocido" en ATLAS</th></tr>')
    for i, x in enumerate(lista, 1):
        tono_sem = 'r' if x['nr_arriba'] >= 6 else ('y' if x['nr_arriba'] >= 3 else 'b')
        # 0 incidencias con un rojo es justo el caso que hay que mirar.
        tono_inc = 'r' if (x['inc_nr'] == 0 and x['semaforo'] == 'ROJO') else 'b'
        h += (f'<tr><td class="drk-n">{i}</td><td class="di"><span class="dn1">{_e(x["ruta"])}</span>'
              f'<span class="dn2">{_e(x["sup"])} · {_e(x["area"])}</span></td>'
              f'<td class="dnum">{x["resp"]}</td><td class="dnum"><b>{x["nr"]}</b></td>'
              f'<td><span class="dp dp-{"r" if x["semaforo"] == "ROJO" else "y"}">{pct(x["pct_nr"])}</span></td>'
              f'<td class="dnum">{f(x["veces"], 1)}×</td><td class="dnum">{x["trax"]} · {x["imagen"]} · {x["ml"]}</td>'
              f'<td><span class="dt dt-{tono_sem}">{x["nr_arriba"]} de {x["nr_eval"]}</span></td>'
              f'<td><span class="dt dt-{tono_inc}">{x["inc_nr"]}</span></td></tr>')
    return h + ('</table><p class="dnota">Semanas arriba del promedio: de las últimas 9 semanas con respuestas. '
                'Incidencias: cuántas veces respaldó un "no reconocido" con incidencia y foto en ATLAS este periodo.</p>')


def _tabla_sc(lista) -> str:
    h = ('<table class="dtab"><tr><th class="drk-n"></th><th class="di">Promotor</th><th>Encuestas</th>'
         '<th>Sin contestar</th><th>OOS del promotor</th><th>Semanas con encuestas en blanco</th>'
         '<th>Supervisor</th><th>Incidencias OOS en ATLAS</th></tr>')
    for i, x in enumerate(lista, 1):
        tono = 'r' if x['sc_semanas'] >= 3 else ('y' if x['sc_semanas'] >= 2 else 'b')
        reincide = ' · reincide' if x['sc_semanas'] >= 3 else ''
        h += (f'<tr><td class="drk-n">{i}</td><td class="di"><span class="dn1">{_e(x["ruta"])}</span>'
              f'<span class="dn2">{_e(x["area"])}</span></td>'
              f'<td class="dnum">{f(x["obj_oos"])}</td><td class="dnum"><b class="dc-r">{x["no_cont"]}</b></td>'
              f'<td>{pill(x["oos"], SEM["oos"], 1)}</td>'
              f'<td><span class="dt dt-{tono}">{x["sc_semanas"]} de {x["nr_eval"]}{reincide}</span></td>'
              f'<td>{_e(x["sup"])}</td><td><span class="dt dt-b">{x["inc_oos"]}</span></td></tr>')
    return h + ('</table><p class="dnota">El OOS del promotor es el que ya castiga su bono: 1 − sin contestar ÷ encuestas. '
                'Cuenta la última captura de cada producto en cada tienda por semana. '
                'No entran las tiendas fuera del maestro (nadie las visita).</p>')


def _abrir_promotor(lista, contexto):
    if not lista:
        return
    izq, der = st.columns([3, 1.2])
    with izq:
        etiquetas = {x['ruta']: f"{x['ruta']} · {x['sup']} · {x['area']}" for x in lista}
        elegido = st.selectbox("Abrir promotor", list(etiquetas),
                               format_func=lambda ruta: etiquetas.get(ruta, str(ruta)),
                               key=f"dir_abrir_promo_{contexto}", label_visibility='collapsed')
    with der:
        if st.button("Ver resumen del promotor →", key=f"dirlink_promo_{contexto}", use_container_width=True):
            x = next(p for p in lista if p['ruta'] == elegido)
            _abrir_vista_am(x['area'], 'resumen_de_promotor',
                            ruta_seleccionada=x['ruta'],
                            volver_de_resumen='director',
                            volver_de_tiendas='resumen_de_promotor')


def _svg_motivos(P) -> str:
    semanas = P.get('semanal') or []
    if not semanas:
        return '<div class="dvacio">Sin respuestas OOS todavía.</div>'
    W, H, L, R, T, B = 640, 290, 34, 8, 30, 28
    bw = (W - L - R) / len(semanas)
    s = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block">']
    dentro = [i for i, w in enumerate(semanas) if P['s_ini'] <= w['semana'] <= P['s_fin']]
    if dentro:
        x1, x2 = L + dentro[0] * bw + 2, L + (dentro[-1] + 1) * bw - 2
        s.append(f'<rect x="{x1:.1f}" y="4" width="{x2 - x1:.1f}" height="{H - 4}" rx="10" fill="#FDF0F7"/>')
    for g in (0, 25, 50, 75, 100):
        yy = T + (100 - g) * (H - T - B) / 100
        s.append(f'<text x="{L - 8}" y="{yy + 4:.1f}" font-size="11" fill="#9AA6D1" text-anchor="end">{g}%</text>')
    for i, w in enumerate(semanas):
        total = sum(w[k] for k in ('nr', 'cat', 'inv', 'otros', 'sc')) or 1
        x0, ancho = L + i * bw + bw * 0.2, bw * 0.6
        en_periodo = P['s_ini'] <= w['semana'] <= P['s_fin']
        yy = H - B
        for k, color in (('sc', '#B5303F'), ('otros', '#E4E8F4'), ('inv', '#C8D6F4'), ('cat', '#4F7BE8'), ('nr', '#FF6FA8')):
            alto = w[k] / total * (H - T - B)
            yy -= alto
            s.append(f'<rect x="{x0:.1f}" y="{yy:.1f}" width="{ancho:.1f}" height="{max(0, alto - 1.2):.1f}" fill="{color}"/>')
        s.append(f'<text x="{x0 + ancho / 2:.1f}" y="{T - 10}" font-size="11.5" fill="#B83D7A" font-weight="500" '
                 f'text-anchor="middle">{f(w["nr"] / total * 100)}%</text>')
        s.append(f'<text x="{x0 + ancho / 2:.1f}" y="{H - 9}" font-size="11.5" fill="{"#B83D7A" if en_periodo else "#6B7BB8"}" '
                 f'font-weight="{500 if en_periodo else 400}" text-anchor="middle">S{w["semana"]}</text>')
    s.append('</svg>')
    return ''.join(s)


# ============================================================
# 5. USO DE ATLAS
# ============================================================
def uso(P, PREV):
    with st.spinner("Revisando accesos e incidencias…"):
        U = get_uso_director(P['id'])
    if U is None:
        _tabla_vacia('No pudimos leer los accesos en este momento. Intenta recargar en unos segundos.')
        return

    inc = U['incidencias']
    cortos = {'promotor': 'promotores', 'supervisor': 'supervisores', 'am': 'AM'}
    roles = ' · '.join(f"{cortos[t]} {v['entraron']}/{v['total']}" for t, v in U['roles'].items())
    r.html('<div class="dg dg4">'
           + kpi('rosa', 'Entraron a ATLAS', f'{f(U["entraron"])} <small>de {f(U["total"])}</small>',
                 'dc-n', f'últimos 7 días · {roles}')
           + kpi('azul', 'Promotores que no han entrado', f(len(U['sin_entrar'])),
                 'dc-r' if U['sin_entrar'] else 'dc-g', 'en los últimos 7 días')
           + kpi('rosa', 'Incidencias levantadas', f(inc['total']), 'dc-n',
                 f'en {P["nombre"].lower()} · {inc["autorizadas"]} autorizadas · {inc["rechazadas"]} rechazadas')
           + kpi('azul', 'Pendientes de autorizar', f(inc['pendientes']),
                 'dc-r' if inc['pendientes_viejas'] else 'dc-n', f'{inc["pendientes_viejas"]} con más de 3 días esperando')
           + '</div>')

    def fila_sup(s):
        tono = 'r' if s['pendientes_viejas'] else ('y' if s['pendientes'] else 'b')
        viejas = f' · {s["pendientes_viejas"]} con +3 días' if s['pendientes_viejas'] else ''
        return (f'<tr><td class="di"><span class="dn1">{_e(s["sup"])}</span><span class="dn2">{_e(s["area"])}</span></td>'
                f'<td class="dnum">{s["levantadas"]}</td><td class="dnum">{s["autorizadas"]}</td>'
                f'<td class="dnum">{s["rechazadas"]}</td>'
                f'<td><span class="dt dt-{tono}">{s["pendientes"]}{viejas}</span></td>'
                f'<td class="dnum">{f(s["dias_resolver"], 1)}</td></tr>')
    filas = ''.join(fila_sup(s) for s in U['por_supervisor'])
    tabla_sups = ('<table class="dtab"><tr><th class="di">Supervisor</th><th>Levantadas</th><th>Autorizadas</th>'
                  '<th>Rechazadas</th><th>Pendientes</th><th>Días en resolver</th></tr>' + filas + '</table>')

    def cuando(x):
        return 'sin entrar en 35 días o más' if x['dias'] is None else f'última vez hace {x["dias"]} días'
    lista = ''.join(
        f'<div class="dsin"><div><span class="dn1">{_e(x["ruta"])}</span>'
        f'<span class="dn2">{_e(x["sup"])} · {_e(x["area"])}</span></div><span class="dt dt-{"r" if x["dias"] is None else "y"}">'
        f'{cuando(x)}</span></div>' for x in U['sin_entrar'][:20])
    resto = len(U['sin_entrar']) - 20
    r.html('<div class="dg dg21">'
           '<div class="dcard">' + tarjeta_titulo('Incidencias por supervisor', 'Quién autoriza a tiempo y quién las deja esperando')
           + f'<div class="dtw">{tabla_sups}</div></div>'
           '<div class="dcard">' + tarjeta_titulo('Promotores sin entrar', 'Más de 7 días sin abrir ATLAS')
           + (lista or '<div class="dvacio">Todos los promotores entraron esta semana.</div>')
           + (f'<p class="dnota">Y {resto} más.</p>' if resto > 0 else '')
           + '</div></div>')
