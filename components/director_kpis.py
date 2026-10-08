"""
TABLERO DEL DIRECTOR — Exhibiciones, OSA y Precios (v25).

Lo que el cliente mide de la ejecución en tienda, aparte del bono: cuántas
exhibiciones hay y de qué, si el producto está en el anaquel (OSA) y si el
precio está donde debe. Los datos llegan de data.get_kpis_cliente() y se arman
en kpis_cliente_calc.py; aquí solo se deciden textos, colores y acomodo.

Mismos cuidados que director_secciones.py:
- Ningún bloque HTML lleva renglones en blanco (st.markdown lo cortaría ahí).
- Todo texto que viene de la base pasa por _e() antes de meterse al HTML.
"""
import pandas as pd
import streamlit as st

import kpis_cliente_calc as kc
import render as r
from components.director_secciones import _e, control, tarjeta_titulo
from data import get_exh_escenas_tienda, get_kpis_cliente, get_periodos_con_precios

MIME_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
LIMITE_SKU = 25
LIMITE_TIENDAS = 15

CSS_KPIS = """
<style>
.dg11 { grid-template-columns: repeat(2, minmax(0,1fr)); }
.kv { display: flex; align-items: flex-end; gap: 14px; height: 196px; position: relative; padding-top: 6px; }
.kv-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 4px; height: 100%; }
.kv-col i { display: block; width: 100%; max-width: 64px; border-radius: 8px 8px 3px 3px;
  background: linear-gradient(180deg,#FF6FA8,#4F7BE8); }
.kv-col.kv-off i { background: #DCE4F5; }
.kv-col.kv-cero i { background: #F4BCC3; }
.kv-v { font-size: 12px; font-weight: 500; color: #1F2A5C; font-variant-numeric: tabular-nums;
  position: relative; z-index: 1; background: #fff; padding: 0 4px; border-radius: 4px; }
.kv-col.kv-off .kv-v { color: #9AA6D1; }
.kv-meta { position: absolute; left: 0; right: 0; border-top: 1px dashed #B83D7A; }
.kv-meta span { position: absolute; right: 0; top: -17px; font-size: 10.5px; color: #B83D7A; background: #fff; padding: 0 4px; }
.kv-pie { display: flex; gap: 14px; margin-top: 6px; }
.kv-pie > div { flex: 1; text-align: center; font-size: 11px; color: #6B7BB8; line-height: 1.4; }
.kv-pie b { display: block; font-size: 12px; font-weight: 500; color: #1F2A5C; }
.kv-pie .kv-sel b { color: #B83D7A; }
.kd-up { color: #1E5C36 !important; } .kd-down { color: #B5303F !important; }
.kd-eq { color: #6B7BB8 !important; } .kd-na { color: #9AA6D1 !important; }
table.dtab td.dbarra { min-width: 90px; width: 20%; }
/* Streamlit fuerza 1rem a todo <p> del markdown: estos tamaños van con !important */
p.knota { font-size: 11.5px !important; color: #9AA6D1; margin: 10px 0 0; line-height: 1.5; }
p.ksub { font-size: 12px !important; color: #6B7BB8; margin: 6px 0 4px; font-weight: 500; }
.kbeta { display: flex; gap: 10px; align-items: center; background: #EEF3FE; border: 0.5px solid #C8D6F4;
  border-radius: 10px; padding: 10px 14px; font-size: 13px; color: #2F3F9E; margin-bottom: 14px; }
.kbeta b { font-size: 10.5px; font-weight: 600; letter-spacing: .06em; color: #fff; background: #4055C8;
  border-radius: 999px; padding: 2px 8px; flex: none; }
.kaviso-n { background: #FDF0E8 !important; border-color: #F1D2B8 !important; color: #98580E !important; }
.kaviso-n b { color: #98580E !important; }
.kchips { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 10px; }
.kchips span { background: #F4F7FE; border: 0.5px solid #DCE4F5; border-radius: 999px; padding: 3px 10px; font-size: 12px; color: #1F2A5C; }
.kchips span small { color: #6B7BB8; font-size: 12px; }
p.kgrande { font-size: 30px !important; font-weight: 500; color: #B5303F; line-height: 1; text-align: right; margin: 0; }
p.kgrande small { display: block; font-size: 11.5px; font-weight: 400; color: #6B7BB8; margin-top: 4px; }
/* Un número del encabezado no se parte (en 1024 px, 327,352 frentes salía como 327,35 / 2) */
.dh p.dh-v2 { white-space: nowrap; }
@media (max-width: 1180px) { .dh p.dh-v2 { font-size: 25px; } }
</style>
"""


# ============================================================
# FORMATO
# ============================================================
def _n(x) -> str:
    return '—' if x is None else f'{x:,.0f}'


def _n1(x) -> str:
    return '—' if x is None else f'{x:,.1f}'


def _p(x, d=1) -> str:
    return '—' if x is None else f'{x * 100:.{d}f}%'


def _dinero(x) -> str:
    return '—' if x is None else f'${x:,.0f}'


def _dif(x) -> str:
    if x is None:
        return '—'
    return '0%' if abs(x) < 0.0005 else f"{'+' if x > 0 else '−'}{abs(x) * 100:.1f}%"


def _var_rel(cur, ant, bajar_es_bueno=False):
    """(texto, clase) del cambio relativo contra el periodo anterior."""
    if cur is None or not ant:
        return '—', 'na'
    v = cur / ant - 1
    if abs(v) < 0.005:
        return '=', 'eq'
    bueno = v < 0 if bajar_es_bueno else v > 0
    return f"{'+' if v > 0 else '−'}{abs(v) * 100:.1f}%", 'up' if bueno else 'down'


def _var_pts(cur, ant, bajar_es_bueno=False, neutro=False):
    """(texto, clase) del cambio en puntos de un porcentaje."""
    if cur is None or ant is None:
        return '—', 'na'
    d = (cur - ant) * 100
    if abs(d) < 0.05:
        return '=', 'eq'
    bueno = d < 0 if bajar_es_bueno else d > 0
    return f"{'+' if d > 0 else '−'}{abs(d):.1f} pts", 'eq' if neutro else ('up' if bueno else 'down')


def _dd(par) -> str:
    texto, clase = par
    return f'<span class="dd dd-{"eq" if clase == "na" else clase}">{texto}</span>'


def _mini(par) -> str:
    return f'<span class="dn2 kd-{par[1]}">{par[0]}</span>'


def _chip(par, contra) -> str:
    texto = 'sin periodo anterior' if par[0] == '—' or not contra else f'{par[0]} vs {contra}'
    return f'<span class="dh-chip">{texto}</span>'


def _pill(v, clase) -> str:
    return f'<span class="dp dp-{clase}">{_p(v)}</span>'


def _pill_osa(v) -> str:
    return _pill(v, 'n' if v is None else ('g' if v >= 0.95 else ('y' if v >= 0.85 else 'r')))


def _barra(frac) -> str:
    return f'<div class="dbar"><i style="width:{max(0.0, min(100.0, (frac or 0) * 100)):.1f}%"></i></div>'


def _celda_doble(valor, par) -> str:
    return f'<td class="dnum"><b>{valor}</b>{_mini(par)}</td>'


def _mes(periodo) -> str:
    if not periodo:
        return ''
    return str(periodo.get('mes') or periodo.get('periodo_id') or '').capitalize()


def _semanas(periodo):
    """[(semana, lunes)] del periodo."""
    s_ini, s_fin = int(periodo['semana_inicio']), int(periodo['semana_fin'])
    ini = pd.Timestamp(periodo['fecha_inicio'])
    return [(s, ini + pd.Timedelta(days=7 * (s - s_ini))) for s in range(s_ini, s_fin + 1)]


def _rango(lunes) -> str:
    return f'{lunes:%d/%m} – {lunes + pd.Timedelta(days=6):%d/%m}'


def _vacio(texto) -> None:
    r.html(f'<div class="dvacio">{texto}</div>')


def _cargar(periodo_id, kpi):
    """Los datos del KPI, o None con un aviso si todavía no se pueden leer."""
    try:
        return get_kpis_cliente(periodo_id, kpi)
    except Exception as e:
        # El detalle va al log; al director no se le enseña un traceback.
        print(f"[DIRECTOR {kpi.upper()}] {periodo_id}: {e}")
        _vacio('Todavía no se pueden leer estos datos. Si esta sección se acaba de instalar, falta correr en '
               'Supabase el SQL de la v25 o subir los CSV de csv_director.')
        return None


def _estructura(datos):
    return kc.estructura(datos['rt'], datos['kp'], datos['ruta_area'])


@st.cache_data(ttl=3600, show_spinner=False)
def _excel(periodo_id: str, kpi: str, cual: str, s: int, leido: str) -> bytes:
    """Las descargas: 'tiendas' de una semana (0 = el mes) o el 'final' del mes con sus semanas.

    leido = cuándo se leyeron los datos. Va en la llave del caché: "Actualizar datos"
    no limpia este caché, pero sí cambia leido, así que el Excel nunca es más viejo
    que lo que se ve en pantalla.
    """
    datos = get_kpis_cliente(periodo_id, kpi)
    est = _estructura(datos)
    semanas = [w for w, _ in _semanas(datos['periodo'])]
    mes = _mes(datos['periodo'])
    periodo = 'mes completo' if s == kc.MES else f'semana {s}'
    if kpi == 'exh':
        df = kc.tabla_exh_tiendas(datos['tienda'], est, semanas)
        titulo = f'Exhibiciones por tienda · {mes} · exhibiciones únicas y capturas de cada semana y del mes'
    elif kpi == 'osa':
        if cual == 'final':
            df = kc.tabla_osa_final(datos['tienda'], est, semanas)
            titulo = f'OSA por tienda · resultado final de {mes} · con la regla del cliente · OSA de cada semana'
        else:
            df = kc.tabla_osa_tiendas(datos['tienda'], est, s)
            titulo = f'OSA por tienda · {mes}, {periodo} · con la regla del cliente · del más bajo al más alto'
    else:
        if cual == 'final':
            df = kc.tabla_precios_final(datos['tienda'], est, semanas)
            titulo = f'Adherencia de precios por tienda · resultado final de {mes} · ±5% del precio estrategia'
        else:
            df = kc.tabla_precios_tiendas(datos['tienda'], est, s)
            titulo = f'Adherencia de precios por tienda · {mes}, {periodo} · ±5% del precio estrategia'
    return kc.excel(df, 'TIENDAS', titulo)


def _descarga(etiqueta, periodo_id, kpi, cual, s, nombre, key, principal=False):
    try:
        datos = _excel(periodo_id, kpi, cual, s, get_kpis_cliente(periodo_id, kpi)['leido'])
    except Exception as e:
        print(f"[DIRECTOR DESCARGA] {kpi} {cual} {s}: {e}")
        st.button(etiqueta, key=key, disabled=True, use_container_width=True)
        return
    st.download_button(etiqueta, data=datos, file_name=nombre, mime=MIME_XLSX, key=key, on_click='ignore',
                       icon=':material/download:', type='primary' if principal else 'secondary',
                       use_container_width=True)


def _barras_semanas(cols, meta=None, tope=None) -> str:
    """Barras verticales: cols = [(valor, texto, apagada)].

    meta = fracción donde va la línea punteada. Los porcentajes se dibujan de 0 a 100%
    (tope=1) para no exagerar diferencias chicas; los conteos, contra el más alto.
    """
    if tope is None:
        tope = 1.0 if meta is not None else max([c[0] for c in cols if c[0] is not None] + [1e-9])
    h = '<div class="kv">'
    if meta is not None:
        h += f'<div class="kv-meta" style="bottom:{meta * 150:.0f}px"><span>{meta * 100:.0f}%</span></div>'
    for valor, texto, apagada in cols:
        alto = max(3, round((valor or 0) / tope * 150))
        h += (f'<div class="kv-col{" kv-off" if apagada else ""}"><span class="kv-v">{texto}</span>'
              f'<i style="height:{alto}px"></i></div>')
    return h + '</div>'


def _pie_semanas(items, elegida=None) -> str:
    return ('<div class="kv-pie">' + ''.join(
        f'<div class="{"kv-sel" if s == elegida else ""}"><b>S{s}</b>{extra}</div>' for s, extra in items) + '</div>')


def _pie_dato(texto) -> None:
    r.html(f'<p class="dact">{texto}</p>')


# ============================================================
# EXHIBICIONES
# ============================================================
def exhibiciones(periodos, periodo_id):
    r.html(CSS_KPIS)
    datos = _cargar(periodo_id, 'exh')
    if not datos:
        return
    est = _estructura(datos)
    sem = _semanas(datos['periodo'])
    v = kc.exh_vista(datos['tienda'], datos['corte'], datos['tienda_ant'], datos['corte_ant'], est, [s for s, _ in sem])
    if v is None:
        _vacio('Este periodo todavía no tiene exhibiciones cargadas.')
        return
    contra = _mes(datos['previo']).lower() if datos['previo'] else None
    T = v['tot']
    mes = _mes(datos['periodo'])

    izq, der = st.columns([3.2, 1], vertical_alignment='center')
    with izq:
        r.html('<div class="daviso">ℹ️ <span><b>Todo lo que se capturó en TRAX en el mes.</b> Aquí no se mide si la '
               'tienda cumple: el cumplimiento de exhibiciones del bono sigue en Inicio y en Supervisores.</span></div>')
    with der:
        _descarga('Tiendas, semana a semana', periodo_id, 'exh', 'tiendas', kc.MES,
                  f'Exhibiciones_tiendas_{mes.lower()}.xlsx', f'dirdl_exh_{periodo_id}')

    r.html('<div class="dh">'
           f'<div><p class="dh-k">Exhibiciones únicas</p><p class="dh-v">{_n(T["exh"])}</p>'
           f'<p class="dh-s">{_n1(T["por_tienda"])} por tienda del maestro · {_n(T["tiendas_con"])} tiendas con al menos una</p>'
           f'{_chip(_var_rel(T["exh"], T["exh_ant"]), contra)}</div>'
           f'<div><p class="dh-k">Capturas</p><p class="dh-v2">{_n(T["cap"])}</p>'
           f'<p class="dh-s">{_n1(T["cap"] / T["exh"] if T["exh"] else None)} productos por exhibición</p>'
           f'{_chip(_var_rel(T["cap"], T["cap_ant"]), contra)}</div>'
           f'<div><p class="dh-k">Frentes</p><p class="dh-v2">{_n(T["fre"])}</p>'
           f'<p class="dh-s">{_n1(T["fre"] / T["exh"] if T["exh"] else None)} frentes por exhibición</p>'
           f'{_chip(_var_rel(T["fre"], T["fre_ant"]), contra)}</div>'
           f'<div><p class="dh-k">Alto impacto</p><p class="dh-v2">{_p(T["alto_pct"])}</p>'
           f'<p class="dh-s">{_n(T["alto"])} exhibiciones</p>{_chip(_var_pts(T["alto_pct"], T["alto_pct_ant"]), contra)}</div>'
           '</div>')

    # Categorías y cuántas tuvo cada tienda
    max_c = max([c['cap'] for c in v['categorias']] + [1])
    filas = ''.join(
        f'<tr><td class="di"><span class="dn1">{_e(c["k"])}</span><span class="dn2">{_p(c["exh"] / T["exh"], 0)} de las exhibiciones · '
        f'{_p(c["cap"] / T["cap"], 0)} de las capturas</span></td><td class="dbarra">{_barra(c["cap"] / max_c)}</td>'
        + _celda_doble(_n(c['exh']), _var_rel(c['exh'], c['exh_ant'])) + _celda_doble(_n(c['cap']), _var_rel(c['cap'], c['cap_ant']))
        + f'<td class="dnum">{_n(c["fre"])}</td></tr>' for c in v['categorias'])
    nota_cat = (f'Por categoría las exhibiciones únicas suman {_n(v["suma_categorias"])}, más que las {_n(T["exh"])} del mes: '
                'una exhibición con whisky y tequila cuenta en las dos.'
                + (f' {_n(v["pos"])} capturas de material POS no entran en las categorías.' if v['pos'] else ''))
    tabla_cat = ('<table class="dtab"><tr><th class="di">Categoría</th><th></th><th>Exhibiciones únicas</th><th>Capturas</th>'
                 f'<th>Frentes</th></tr>{filas}</table>')
    dist = v['dist']
    barras = _barras_semanas([(b['n'], _n(b['n']), False) for b in dist])
    barras = barras.replace('<div class="kv-col">', '<div class="kv-col kv-cero">', 1)
    pie = '<div class="kv-pie">' + ''.join(f'<div>{_e(b["k"])}</div>' for b in dist) + '</div>'
    r.html('<div class="dg dg32">'
           '<div class="dcard">' + tarjeta_titulo('Por categoría', 'Exhibiciones únicas = exhibiciones con al menos un producto '
                                                  'de la categoría · capturas = todo lo que se capturó de ella')
           + f'<div class="dtw">{tabla_cat}</div><p class="knota">{nota_cat}</p></div>'
           '<div class="dcard">' + tarjeta_titulo('¿Cuántas exhibiciones tuvo cada tienda?', 'Tiendas del maestro según sus exhibiciones del mes')
           + barras + pie
           + f'<p class="knota">Por tienda del maestro, en promedio: {_n1(T["por_tienda"])} exhibiciones únicas y '
             f'{_n1(T["cap_por_tienda"])} capturas en el mes. {_n(v["sin"]["n"])} tiendas no tuvieron ninguna; '
             f'{_n(v["sin"]["vis"])} de ellas sí se visitaron.</p></div>'
           '</div>')

    # Marcas
    with st.container(border=True, key='dircard_exh_marcas'):
        a, b = st.columns([3, 1.3], vertical_alignment='center')
        with a:
            r.html(tarjeta_titulo('Por marca', 'Exhibiciones únicas = exhibiciones con al menos un producto de la marca · '
                                  'capturas = todo lo que se capturó de ella'))
        with b:
            nivel = control('Nivel', ['marca', 'variante'], 'dir_exh_nivel', 'marca', {'marca': 'Marcas', 'variante': 'Variantes'}.get)
        if nivel == 'marca':
            lista, columna = v['marcas'], 'Marca'
        else:
            lista, columna = v['variantes'][:LIMITE_SKU], 'Variante'
        max_m = max([m['cap'] for m in lista] + [1])

        def fila_marca(m, sub):
            return (f'<tr><td class="di"><span class="dn1">{_e(m["k"])}</span><span class="dn2">{sub}</span></td>'
                    f'<td class="dbarra">{_barra(m["cap"] / max_m)}</td>'
                    + _celda_doble(_n(m['exh']), _var_rel(m['exh'], m['exh_ant']))
                    + _celda_doble(_n(m['cap']), _var_rel(m['cap'], m['cap_ant']))
                    + f'<td class="dnum">{_p(m["cap"] / T["cap"])}</td><td class="dnum">{_n(m["fre"])}</td>'
                    f'<td class="dnum">{_n(m["tiendas"])}</td></tr>')
        cuerpo = ''.join(fila_marca(m, _e(f'{m["cat"]} · {len(m["variantes"])} variantes') if nivel == 'marca'
                                    else _e(m['padre'])) for m in lista)
        total = (f'<tr class="dtot"><td class="di">Total del mes</td><td></td>'
                 + _celda_doble(_n(T['exh']), _var_rel(T['exh'], T['exh_ant']))
                 + _celda_doble(_n(T['cap']), _var_rel(T['cap'], T['cap_ant']))
                 + f'<td class="dnum">100%</td><td class="dnum">{_n(T["fre"])}</td><td class="dnum">{_n(T["tiendas_con"])}</td></tr>')
        r.html(f'<div class="dtw"><table class="dtab"><tr><th class="di">{columna}</th><th></th><th>Exhibiciones únicas</th>'
               f'<th>Capturas</th><th>% capturas</th><th>Frentes</th><th>Tiendas</th></tr>{cuerpo}{total}</table></div>')
        if nivel == 'marca':
            abrir = st.selectbox('Ver las variantes de una marca', [None] + [m['k'] for m in lista],
                                 format_func=lambda x: 'Elige una marca' if x is None else x, key='dir_exh_abrir')
            if abrir:
                m = next(x for x in lista if x['k'] == abrir)
                max_m = max([x['cap'] for x in m['variantes']] + [1])
                r.html('<div class="dtw"><table class="dtab"><tr><th class="di">Variante</th><th></th><th>Exhibiciones únicas</th>'
                       '<th>Capturas</th><th>% capturas</th><th>Frentes</th><th>Tiendas</th></tr>'
                       + ''.join(fila_marca(x, '') for x in m['variantes']) + '</table></div>')
            r.html('<p class="knota">Una exhibición con dos marcas cuenta como exhibición única en las dos; por eso las marcas '
                   'suman más que el total del mes, que no repite ninguna.</p>')
        else:
            r.html(f'<p class="knota">Las {len(lista)} variantes con más capturas, de {len(v["variantes"])}.</p>')

    # Dónde se exhibe y semana a semana
    max_u = max([u['exh'] for u in v['ubicaciones']] + [1])
    filas_u = ''.join(
        f'<tr><td class="di"><span class="dn1">{_e(u["nombre"])}</span><span class="dn2">{_p(u["exh"] / T["exh"])} de las '
        f'exhibiciones</span></td><td class="dbarra">{_barra(u["exh"] / max_u)}</td>'
        + _celda_doble(_n(u['exh']), _var_rel(u['exh'], u['exh_ant'])) + _celda_doble(_n(u['cap']), _var_rel(u['cap'], u['cap_ant']))
        + f'<td><span class="dt {"dt-y" if u["exh"] and u["alto"] / u["exh"] >= 0.2 else "dt-b"}">{_p(u["alto"] / u["exh"] if u["exh"] else None, 0)}</span></td></tr>'
        for u in v['ubicaciones'])
    barras = _barras_semanas([(w['exh'], _n(w['exh']), False) for w in v['semanas']])
    rangos = dict(sem)
    pie = _pie_semanas([(w['s'], f'{_rango(rangos[w["s"]])}<br><b>{_n(w["cap"])}</b>capturas · {_p(w["alto_pct"])} alto impacto')
                        for w in v['semanas']])
    r.html('<div class="dg dg11">'
           '<div class="dcard">' + tarjeta_titulo('Dónde se exhibe', 'Cada exhibición tiene una sola ubicación: aquí las únicas sí suman el total')
           + '<div class="dtw"><table class="dtab"><tr><th class="di">Ubicación</th><th></th><th>Exhibiciones únicas</th>'
           f'<th>Capturas</th><th>Alto impacto</th></tr>{filas_u}</table></div></div>'
           '<div class="dcard">' + tarjeta_titulo('Semana a semana', 'La barra son las exhibiciones únicas; abajo, las capturas y el alto impacto')
           + barras + pie + '</div></div>')

    # Por equipo
    with st.container(border=True, key='dircard_exh_equipo'):
        a, b = st.columns([2.6, 1.6], vertical_alignment='center')
        opciones = {'area': 'Áreas', 'supervisor': 'Supervisores', 'cadena': 'Cadenas'}
        with b:
            grupo = control('Equipo', list(opciones), 'dir_exh_equipo', 'supervisor', opciones.get)
        prom = T['por_tienda'] or 0
        filas = v['equipo'][grupo]
        if grupo == 'cadena':
            filas = sorted(filas, key=lambda x: -x['exh'])[:15]
            nota = f'Las 15 cadenas con más exhibiciones, de {len(v["equipo"]["cadena"])}.'
        else:
            filas = sorted(filas, key=lambda x: (x['por'] if x['por'] is not None else 0))
            nota = 'Primero los de menos exhibiciones por tienda. La comparación es por tienda, para que no la mueva el cambio de tiendas.'
        with a:
            r.html(tarjeta_titulo({'area': 'Por área', 'supervisor': 'Por supervisor', 'cadena': 'Por cadena'}[grupo], nota))

        def clase_por(x):
            if x is None or not prom:
                return 'n'
            return 'g' if x >= prom else ('y' if x >= 0.8 * prom else 'r')
        cuerpo = ''.join(
            f'<tr><td class="di"><span class="dn1">{_e(x["nombre"])}</span><span class="dn2">{_e(x["sub"])}</span></td>'
            f'<td class="dnum">{_n(x["tiendas"])}</td><td class="dnum">{_n(x["sin"])}</td><td class="dnum"><b>{_n(x["exh"])}</b></td>'
            f'<td class="dnum">{_n(x["cap"])}</td><td><span class="dp dp-{clase_por(x["por"])}">{_n1(x["por"])}</span></td>'
            f'<td>{_dd(_var_rel(x["por"], x.get("por_ant")))}</td><td class="dnum">{_n(x["fre"])}</td>'
            f'<td class="dnum">{_p(x["alto_pct"])}</td></tr>' for x in filas)
        nacional = (f'<tr class="dtot"><td class="di">Nacional</td><td class="dnum">{_n(T["maestro"])}</td>'
                    f'<td class="dnum">{_n(v["sin"]["n"])}</td><td class="dnum">{_n(T["exh"])}</td><td class="dnum">{_n(T["cap"])}</td>'
                    f'<td>{_n1(T["por_tienda"])}</td><td></td><td class="dnum">{_n(T["fre"])}</td><td class="dnum">{_p(T["alto_pct"])}</td></tr>')
        r.html('<div class="dtw"><table class="dtab"><tr><th class="di">' + {'area': 'Área', 'supervisor': 'Supervisor', 'cadena': 'Cadena'}[grupo]
               + '</th><th>Tiendas</th><th>Sin exhibición</th><th>Exhibiciones únicas</th><th>Capturas</th><th>Por tienda</th>'
               f'<th>vs {_e(contra or "ant.")}</th><th>Frentes</th><th>Alto impacto</th></tr>{cuerpo}{nacional}</table></div>'
               f'<p class="knota">Por tienda = exhibiciones únicas del mes entre las tiendas. Verde: arriba del promedio nacional '
               f'({_n1(prom)}) · amarillo: hasta 20% abajo · rojo: más abajo.</p>')

    # Tiendas
    izq, der = st.columns([1, 1], gap='medium')
    with izq:
        with st.container(border=True, key='dircard_exh_tiendas'):
            r.html(tarjeta_titulo('Las exhibiciones de una tienda', 'Cada exhibición con su foto en TRAX'))
            mas = v['mas']
            r.html('<div class="dtw"><table class="dtab"><tr><th class="di">Las que más tienen</th><th>Únicas</th><th>Capturas</th></tr>'
                   + ''.join(f'<tr><td class="di"><span class="dn1">{_e(t["tienda"])}</span><span class="dn2">CURT {_e(t["curt"])} · '
                             f'{_e(t["cadena"])} · {_e(t["sup"])}</span></td><td class="dnum"><b>{_n(t["exh"])}</b></td>'
                             f'<td class="dnum">{_n(t["cap"])}</td></tr>' for t in mas) + '</table></div>')
            opciones_t = est.index.tolist()
            elegida = st.selectbox('Busca cualquier tienda', [None] + opciones_t, key=f'dir_exh_tienda_{periodo_id}',
                                   format_func=lambda c: 'Escribe el nombre o el CURT' if c is None
                                   else f'{est.loc[c, "tienda"]} · CURT {c} · {est.loc[c, "cadena"]}')
    with der:
        s_info = v['sin']
        chips = ''.join(f'<span>{_e(x["cadena"])} <small>{_n(x["n"])}</small></span>' for x in s_info['por_cadena'][:6])
        lista_sin = ''.join(f'<tr><td class="di"><span class="dn1">{_e(x["tienda"])}</span><span class="dn2">CURT {_e(x["curt"])} · '
                            f'{_e(x["cadena"])} · {_e(x["sup"])} · {_e(x["ruta"])}</span></td><td><span class="dt dt-y">Visitada</span></td></tr>'
                            for x in s_info['visitadas'])
        r.html('<div class="dcard">' + tarjeta_titulo('Tiendas sin ninguna exhibición', 'Tiendas del maestro sin una sola exhibición en el mes',
                                                      f'<p class="kgrande">{_n(s_info["n"])}<small>{_n(s_info["vis"])} visitadas · '
                                                      f'{_n(s_info["n"] - s_info["vis"])} sin visita</small></p>')
               + f'<div class="kchips">{chips}</div>'
               + (f'<p class="ksub">Sí se visitaron y no traen exhibiciones</p><div class="dtw"><table class="dtab">{lista_sin}</table></div>'
                  if lista_sin else '')
               + '<p class="knota">La lista completa sale en la descarga de tiendas.</p></div>')

    if elegida:
        try:
            escenas = kc.exh_detalle_tienda(get_exh_escenas_tienda(periodo_id, elegida))
        except Exception as e:
            print(f"[DIRECTOR EXH TIENDA] {periodo_id} {elegida}: {e}")
            escenas = None
        t = est.loc[elegida]
        if escenas is None:
            _vacio('No se pudieron leer las exhibiciones de esta tienda. Intenta en unos segundos.')
        elif not escenas:
            _vacio(f'{_e(t["tienda"])} no tuvo exhibiciones en {mes.lower()}.')
        else:
            unicas = len(escenas)
            capt = sum(x['capturas'] for x in escenas)
            frentes = sum(x['frentes'] for x in escenas)
            altas = sum(1 for x in escenas if x['impacto'] == 'Alto')
            filas = ''.join(
                f'<tr><td>{x["fecha"]}</td><td>S{x["semana"]}</td><td class="di">{_e(x["ubicacion"])}</td>'
                f'<td><span class="dt {"dt-y" if x["impacto"] == "Alto" else "dt-b"}">{_e(x["impacto"])}</span></td>'
                f'<td class="di"><span class="dn1">{_e(x["variante"])}</span><span class="dn2">{_e(x["categoria"])}</span></td>'
                f'<td class="di" style="white-space: normal; color: #6B7BB8;">{_e(x["productos"])}</td>'
                f'<td class="dnum">{_n(x["capturas"])}</td><td class="dnum">{_n(x["frentes"])}</td>'
                f'<td><a href="{_e(x["liga"])}" target="_blank" rel="noopener">Ver en TRAX</a></td></tr>' for x in escenas)
            r.html('<div class="dcard">' + tarjeta_titulo(_e(t['tienda']), f'CURT {_e(elegida)} · {_e(t["cadena"])} · {_e(t["area"])} · '
                                                          f'{_e(t["sup"])} · {_e(t["ruta"])}')
                   + '<div class="dmk">'
                   f'<div><span>Exhibiciones únicas</span><b>{_n(unicas)}</b></div><div><span>Capturas</span><b>{_n(capt)}</b></div>'
                   f'<div><span>Frentes</span><b>{_n(frentes)}</b></div><div><span>Alto impacto</span><b>{_n(altas)}</b></div></div>'
                   '<div class="dtw"><table class="dtab"><tr><th>Fecha</th><th>Sem.</th><th class="di">Ubicación</th><th>Impacto</th>'
                   '<th class="di">Producto principal</th><th class="di">Todo lo que trae la exhibición</th><th>Capt.</th><th>Frentes</th>'
                   f'<th>Foto</th></tr>{filas}</table></div>'
                   '<p class="knota">Ver en TRAX abre la escena en TRAX; pide tu sesión de TRAX.</p></div>')

    r.html('<p class="dpie"><b>Cómo se cuenta.</b> Exhibición única = una escena de TRAX, es decir, una exhibición fotografiada '
           'en una visita; si se fotografía en dos visitas, cuenta dos veces. Captura = cada producto reconocido dentro de una '
           f'exhibición. Frentes = facings. {_n(T["sin_respuesta"])} exhibiciones sin respuesta de tipo cuentan como bajo '
           'impacto, igual que en el cálculo del bono. Se cuenta todo el mes, también las semanas con incidencia de TRAX.</p>')
    _pie_dato(f'Datos al cierre de la semana {sem[-1][0]}')


# ============================================================
# OSA
# ============================================================
def osa(periodos, periodo_id):
    r.html(CSS_KPIS)
    datos = _cargar(periodo_id, 'osa')
    if not datos:
        return
    est = _estructura(datos)
    sem = _semanas(datos['periodo'])
    semanas = [s for s, _ in sem]
    s_fin_previo = int(datos['previo']['semana_fin']) if datos['previo'] else None
    mes = _mes(datos['periodo'])

    r.html('<div class="daviso">ℹ️ <span><b>OSA con la regla del cliente:</b> los agotados cuya razón es de reconocimiento '
           'o de acomodo pasan a disponible. Todas las capturas del periodo, solo tiendas del maestro.</span></div>')

    with st.container(border=True, key='dircard_osa_filtro'):
        a, b, c = st.columns([2.4, 1, 1], vertical_alignment='center')
        with a:
            s = control('Semana', [kc.MES] + semanas, f'dir_osa_sem_{periodo_id}', kc.MES,
                        lambda w: 'Mes completo' if w == kc.MES else f'S{w}')
        etiqueta = 'mes' if s == kc.MES else f'S{s}'
        with b:
            _descarga('Tiendas del mes' if s == kc.MES else f'Tiendas de la S{s}', periodo_id, 'osa', 'tiendas', s,
                      f'OSA_tiendas_{etiqueta}_{mes.lower()}.xlsx', f'dirdl_osa_{periodo_id}_{s}')
        with c:
            _descarga('Resultado final del mes', periodo_id, 'osa', 'final', kc.MES,
                      f'OSA_resultado_final_{mes.lower()}.xlsx', f'dirdl_osa_final_{periodo_id}', principal=True)

    v = kc.osa_vista(datos['tienda'], datos['corte'], datos['tienda_ant'], datos['corte_ant'], est, semanas, s, s_fin_previo)
    if v is None:
        _vacio('Este periodo todavía no tiene OSA cargado.' if s == kc.MES else f'La semana {s} todavía no tiene OSA cargado.')
        return
    T = v['tot']
    if s == kc.MES:
        contra = _mes(datos['previo']).lower() if datos['previo'] else None
    else:
        contra = f'S{v["s_ant"]}' if v['s_ant'] else None

    r.html('<div class="dh">'
           f'<div><p class="dh-k">{"OSA del mes" if s == kc.MES else f"OSA de la semana {s}"}</p><p class="dh-v">{_p(T["osa"])}</p>'
           f'<p class="dh-s">{_n(T["ag"])} agotados de {_n(T["codigos"])} códigos evaluados · {_n(T["tiendas"])} tiendas</p>'
           f'{_chip(_var_pts(T["osa"], T["osa_ant"]), contra)}</div>'
           f'<div><p class="dh-k">Según TRAX</p><p class="dh-v2">{_p(T["osa_trax"])}</p>'
           f'<p class="dh-s">{_n(T["at"])} agotados antes de la regla</p></div>'
           f'<div><p class="dh-k">Pasan a disponible</p><p class="dh-v2">{_n(T["rc"])}</p>'
           f'<p class="dh-s">{_p(T["rc"] / T["at"] if T["at"] else None, 0)} de los agotados de TRAX</p></div>'
           f'<div><p class="dh-k">Siguen agotados</p><p class="dh-v2">{_n(T["ag"])}</p>'
           f'<p class="dh-s">sobre todo: {_e((T["razon"] or "—").lower())}</p></div>'
           '</div>')

    rangos = dict(sem)
    barras = _barras_semanas([(w['osa'], _p(w['osa']), s != kc.MES and w['s'] != s) for w in v['semanas']], meta=0.95)
    pie = _pie_semanas([(w['s'], _rango(rangos[w['s']])) for w in v['semanas']], elegida=s)
    max_r = max([x['n'] for x in v['razones']] + [1])

    def fila_razon(x):
        return (f'<tr><td class="di">{_e(x["k"])}</td><td class="dbarra">{_barra(x["n"] / max_r)}</td><td class="dnum">{_n(x["n"])}</td>'
                f'<td class="dnum"><b>{_p(x["pct"])}</b></td><td>{_dd(_var_pts(x["pct"], x["pct_ant"], bajar_es_bueno=True, neutro=x["pasa"]))}</td></tr>')
    siguen = ''.join(fila_razon(x) for x in v['razones'] if not x['pasa'])
    pasan = ''.join(fila_razon(x) for x in v['razones'] if x['pasa'])
    r.html('<div class="dg dg11">'
           '<div class="dcard">' + tarjeta_titulo('Semanas del mes', 'La línea punteada es el 95% con el que el archivo 5 KIPIS da el OSA por cumplido')
           + barras + pie + '</div>'
           '<div class="dcard">' + tarjeta_titulo('Por qué se agota', 'Razón que dio el promotor, en % de todos los códigos evaluados')
           + f'<div class="dtw"><table class="dtab"><tr><th class="di">Siguen como agotado</th><th></th><th>Códigos</th><th>%</th>'
             f'<th>vs {_e(contra or "ant.")}</th></tr>{siguen}'
           + f'<tr><th class="di">Pasan a disponible</th><th></th><th></th><th></th><th></th></tr>{pasan}</table></div></div>'
           '</div>')

    # Por producto
    with st.container(border=True, key='dircard_osa_productos'):
        a, b = st.columns([3, 1.5], vertical_alignment='center')
        niveles = {'categoria': 'Categorías', 'marca': 'Marcas', 'sku': 'SKU'}
        with b:
            nivel = control('Producto', list(niveles), 'dir_osa_producto', 'categoria', niveles.get)
        lista = [x for x in v['productos'][nivel] if nivel != 'sku' or x['codigos'] >= 20]
        ver_todos = nivel == 'sku' and len(lista) > LIMITE_SKU and st.session_state.get('dir_osa_sku_todos', False)
        mostrar = lista if (nivel != 'sku' or ver_todos) else lista[:LIMITE_SKU]
        with a:
            r.html(tarjeta_titulo({'categoria': 'OSA por categoría', 'marca': 'OSA por marca', 'sku': 'OSA por SKU'}[nivel],
                                  f'Los {len(mostrar)} SKU con el OSA más bajo, de {len(lista)} con 20 códigos o más'
                                  if nivel == 'sku' and len(mostrar) < len(lista) else 'Del OSA más bajo al más alto'))
        cuerpo = ''.join(
            f'<tr><td class="di"><span class="dn1">{_e(x["k"])}</span><span class="dn2">'
            + (_e(f'{x["marca"]} · {x["categoria"]}') if nivel == 'sku' else
               _e(f'{x["categoria"]} · {x["skus"]} SKU') if nivel == 'marca' else f'{x["skus"]} SKU')
            + f'</span></td><td class="dnum">{_n(x["codigos"])}</td><td class="dnum">{_n(x["at"])}</td>'
              f'<td class="dnum kd-up">{_n(x["rc"])}</td><td class="dnum"><b>{_n(x["ag"])}</b></td><td>{_pill_osa(x["osa"])}</td>'
              f'<td>{_dd(_var_pts(x["osa"], x["osa_ant"]))}</td><td class="di" style="color:#6B7BB8">{_e(x["razon"] or "—")}</td></tr>'
            for x in mostrar)
        r.html(f'<div class="dtw"><table class="dtab"><tr><th class="di">{niveles[nivel][:-1] if nivel != "sku" else "SKU"}</th>'
               '<th>Códigos</th><th>Agotados TRAX</th><th>Pasan</th><th>Siguen agotados</th><th>OSA</th>'
               f'<th>vs {_e(contra or "ant.")}</th><th class="di">Razón principal</th></tr>{cuerpo}</table></div>')
        if nivel == 'sku' and len(lista) > LIMITE_SKU:
            st.toggle(f'Ver los {len(lista)} SKU', key='dir_osa_sku_todos')

    # Por equipo
    _equipo_osa(v, contra, s)

    # Tiendas
    _tiendas_kpi(v['tiendas'], 'osa', periodo_id, s, contra, minimo=30 if s == kc.MES else 10)

    r.html('<p class="dpie"><b>Cómo se cuenta.</b> OSA = 1 − agotados finales / códigos evaluados, con todas las capturas del '
           'periodo. Pasan a disponible: militraje, en anaquel no reconocido por TRAX, obstruido, en tienda sin poder exhibirse, '
           'nueva imagen y en bodega. Siguen agotados: no catalogado, sin inventario, inventario fantasma y sin respuesta del '
           'promotor. Con una semana elegida se compara contra la semana anterior; con el mes completo, contra el mes anterior. '
           'Semáforo: verde 95% o más (lo que el archivo 5 KIPIS da por cumplido) · amarillo 85% a 95% · rojo menos de 85%.</p>')
    _pie_dato(f'Datos al cierre de la semana {semanas[-1]}')


def _equipo_osa(v, contra, s):
    with st.container(border=True, key='dircard_osa_equipo'):
        a, b = st.columns([2.4, 2], vertical_alignment='center')
        opciones = {'area': 'Áreas', 'supervisor': 'Supervisores', 'ruta': 'Promotores', 'cadena': 'Cadenas'}
        with b:
            grupo = control('Equipo', list(opciones), 'dir_osa_equipo', 'supervisor', opciones.get)
        filas = v['equipo'][grupo]
        # Una cadena de una sola tienda no dice nada de la cadena
        minimo = 500 if s == kc.MES else 120
        if grupo == 'cadena':
            filas = [x for x in filas if x['codigos'] >= minimo]
        limite = {'area': 99, 'supervisor': 99, 'ruta': 30, 'cadena': 20}[grupo]
        todos = len(filas) > limite and st.session_state.get(f'dir_osa_eq_todos_{grupo}', False)
        mostrar = filas if todos else filas[:limite]
        titulo = {'area': 'OSA por área', 'supervisor': 'OSA por supervisor', 'ruta': 'OSA por promotor', 'cadena': 'OSA por cadena'}[grupo]
        sub = (f'Los {len(mostrar)} de OSA más bajo, de {len(filas)}.' if len(mostrar) < len(filas) else 'Del OSA más bajo al más alto.')
        if grupo == 'cadena':
            sub += f' Solo cadenas con {minimo} códigos o más.'
        with a:
            r.html(tarjeta_titulo(titulo, sub))
        cuerpo = ''.join(
            f'<tr><td class="di"><span class="dn1">{_e(x["nombre"])}</span><span class="dn2">{_e(x["sub"])}</span></td>'
            f'<td class="dnum">{_n(x["tiendas"])}</td><td class="dnum">{_n(x["codigos"])}</td><td class="dnum">{_n(x["ag"])}</td>'
            f'<td class="dbarra">{_barra(x["osa"])}</td><td>{_pill_osa(x["osa"])}</td><td>{_dd(_var_pts(x["osa"], x.get("osa_ant")))}</td>'
            f'<td class="di" style="color:#6B7BB8">{_e(x["razon"] or "—")}</td></tr>' for x in mostrar)
        T = v['tot']
        nacional = (f'<tr class="dtot"><td class="di">Nacional</td><td class="dnum">{_n(T["tiendas"])}</td><td class="dnum">{_n(T["codigos"])}</td>'
                    f'<td class="dnum">{_n(T["ag"])}</td><td></td><td>{_p(T["osa"])}</td><td>{_dd(_var_pts(T["osa"], T["osa_ant"]))}</td>'
                    f'<td class="di" style="color:#6B7BB8">{_e(T["razon"] or "—")}</td></tr>')
        r.html('<div class="dtw"><table class="dtab"><tr><th class="di">'
               + {'area': 'Área', 'supervisor': 'Supervisor', 'ruta': 'Promotor', 'cadena': 'Cadena'}[grupo]
               + f'</th><th>Tiendas</th><th>Códigos</th><th>Agotados</th><th></th><th>OSA</th><th>vs {_e(contra or "ant.")}</th>'
               f'<th class="di">Razón principal</th></tr>{cuerpo}{nacional}</table></div>')
        if len(filas) > limite:
            st.toggle(f'Ver los {len(filas)}', key=f'dir_osa_eq_todos_{grupo}')


def _tiendas_kpi(filas, kpi, periodo_id, s, contra, minimo):
    """Tabla de tiendas con buscador (OSA o precios), de la peor a la mejor."""
    with st.container(border=True, key=f'dircard_{kpi}_tiendas'):
        a, b = st.columns([2, 1.6], vertical_alignment='center')
        with b:
            q = st.text_input('Buscar tienda', key=f'dir_{kpi}_buscar', placeholder='Tienda, CURT, cadena, supervisor o promotor',
                              label_visibility='collapsed')
        campo = 'codigos' if kpi == 'osa' else 'capturas'
        lista = [x for x in filas if x[campo] >= minimo]
        if q:
            texto = q.strip().lower()
            lista = [x for x in lista if texto in f'{x["curt"]} {x["tienda"]} {x["cadena"]} {x["sup"]} {x["ruta"]}'.lower()]
        ver = st.session_state.get(f'dir_{kpi}_tiendas_todas', False)
        mostrar = lista[:200] if ver else lista[:LIMITE_TIENDAS]
        unidad = 'códigos evaluados' if kpi == 'osa' else 'capturas'
        with a:
            r.html(tarjeta_titulo('Tiendas', f'{"Del OSA más bajo al más alto" if kpi == "osa" else "De menor a mayor adherencia"}, '
                                             f'con {minimo} {unidad} o más · {_n(len(lista))} tiendas'))
        if not lista:
            _vacio('Ninguna tienda coincide con la búsqueda.')
            return
        if kpi == 'osa':
            cuerpo = ''.join(
                f'<tr><td class="di"><span class="dn1">{_e(x["tienda"])}</span><span class="dn2">CURT {_e(x["curt"])} · {_e(x["cadena"])} · '
                f'{_e(x["sup"])} · {_e(x["ruta"])}</span></td><td class="dnum">{_n(x["codigos"])}</td><td class="dnum">{_n(x["ag"])}</td>'
                f'<td>{_pill_osa(x["osa"])}</td><td>{_dd(_var_pts(x["osa"], x["osa_ant"]))}</td>'
                f'<td class="di" style="color:#6B7BB8">{_e(x["razon"] or "—")}</td></tr>' for x in mostrar)
            encabezado = (f'<tr><th class="di">Tienda</th><th>Códigos</th><th>Agotados</th><th>OSA</th><th>vs {_e(contra or "ant.")}</th>'
                          '<th class="di">Razón principal</th></tr>')
        else:
            cuerpo = ''.join(
                f'<tr><td class="di"><span class="dn1">{_e(x["tienda"])}</span><span class="dn2">CURT {_e(x["curt"])} · {_e(x["cadena"])} · '
                f'{_e(x["sup"])} · {_e(x["ruta"])}</span></td><td class="dnum">{_n(x["capturas"])}</td>'
                f'<td class="dnum"><b>{_p(x["adh"])}</b></td><td class="dnum kd-down">{_p(x["arriba"])}</td>'
                f'<td class="dnum" style="color:#4055C8">{_p(x["abajo"])}</td><td>{_dd(_var_pts(x["adh"], x["adh_ant"]))}</td></tr>'
                for x in mostrar)
            encabezado = (f'<tr><th class="di">Tienda</th><th>Capturas</th><th>Adherencia</th><th>Arriba +5%</th><th>Abajo −5%</th>'
                          f'<th>vs {_e(contra or "ant.")}</th></tr>')
        r.html(f'<div class="dtw"><table class="dtab">{encabezado}{cuerpo}</table></div>')
        if len(lista) > LIMITE_TIENDAS:
            st.toggle(f'Ver {min(len(lista), 200)} tiendas (todas salen en la descarga)', key=f'dir_{kpi}_tiendas_todas')


# ============================================================
# PRECIOS
# ============================================================
def precios(periodos, periodo_id):
    r.html(CSS_KPIS)
    try:
        con_precios = get_periodos_con_precios()
    except Exception as e:
        print(f"[DIRECTOR PRECIOS] periodos: {e}")
        _vacio('Todavía no se pueden leer los precios. Si esta sección se acaba de instalar, falta correr en Supabase '
               'el SQL de la v25 o subir los CSV de csv_director.')
        return
    ids = periodos['periodo_id'].tolist()
    if not con_precios:
        _vacio('Todavía no hay reportes de precios cargados.')
        return
    # Un mes sin reporte de precios muestra el último que sí tiene (beta)
    pos = ids.index(periodo_id) if periodo_id in ids else len(ids) - 1
    anteriores = [p for p in ids[:pos + 1] if p in con_precios]
    pid = periodo_id if periodo_id in con_precios else (anteriores[-1] if anteriores else con_precios[-1])
    datos = _cargar(pid, 'precios')
    if not datos:
        return
    mes = _mes(datos['periodo'])
    if pid != periodo_id:
        pedido = periodos[periodos['periodo_id'] == periodo_id]
        nombre_pedido = _mes(pedido.iloc[0].to_dict()) if len(pedido) else periodo_id
        r.html(f'<div class="kbeta"><b>BETA</b><span>{_e(nombre_pedido)} todavía no tiene reporte de precios. Mientras llega, '
               f'aquí ves {_e(mes.lower())} (semanas {int(datos["periodo"]["semana_inicio"])}–{int(datos["periodo"]["semana_fin"])}), '
               'el último que hay.</span></div>')
    r.html('<div class="daviso kaviso-n">⚠️ <span><b>Adherencia = precio capturado dentro de ±5% del precio estrategia.</b> '
           'El precio estrategia parece ser uno solo para todo el país; por eso Soriana y los mayoristas salen tan arriba. '
           'Hasta que el cliente lo confirme, aquí no hay semáforo de cumplimiento.</span></div>')

    est = _estructura(datos)
    sem = _semanas(datos['periodo'])
    semanas = [s for s, _ in sem]
    s_fin_previo = int(datos['previo']['semana_fin']) if datos['previo'] else None
    with st.container(border=True, key='dircard_pre_filtro'):
        a, b, c = st.columns([2.4, 1, 1], vertical_alignment='center')
        with a:
            s = control('Semana', [kc.MES] + semanas, f'dir_pre_sem_{pid}', kc.MES,
                        lambda w: 'Mes completo' if w == kc.MES else f'S{w}')
        etiqueta = 'mes' if s == kc.MES else f'S{s}'
        with b:
            _descarga('Tiendas del mes' if s == kc.MES else f'Tiendas de la S{s}', pid, 'precios', 'tiendas', s,
                      f'Precios_tiendas_{etiqueta}_{mes.lower()}.xlsx', f'dirdl_pre_{pid}_{s}')
        with c:
            _descarga('Resultado final del mes', pid, 'precios', 'final', kc.MES,
                      f'Precios_resultado_final_{mes.lower()}.xlsx', f'dirdl_pre_final_{pid}', principal=True)

    v = kc.precios_vista(datos['tienda'], datos['corte'], datos['tienda_ant'], datos['corte_ant'], est, semanas, s, s_fin_previo)
    if v is None:
        _vacio('Este periodo no tiene precios en esa semana.')
        return
    T = v['tot']
    if s == kc.MES:
        contra = _mes(datos['previo']).lower() if datos['previo'] and T['adh_ant'] is not None else None
    else:
        contra = f'S{v["s_ant"]}' if v['s_ant'] and T['adh_ant'] is not None else None

    r.html('<div class="dh">'
           f'<div><p class="dh-k">{"Adherencia del mes" if s == kc.MES else f"Adherencia de la semana {s}"}</p>'
           f'<p class="dh-v">{_p(T["adh"])}</p>'
           f'<p class="dh-s">{_n(T["ok"])} de {_n(T["capturas"])} capturas dentro de ±5% · {_n(T["tiendas"])} tiendas</p>'
           f'{_chip(_var_pts(T["adh"], T["adh_ant"]), contra)}</div>'
           f'<div><p class="dh-k">Más de 5% arriba</p><p class="dh-v2">{_p(T["arriba_pct"])}</p><p class="dh-s">{_n(T["arriba"])} capturas</p></div>'
           f'<div><p class="dh-k">Más de 5% abajo</p><p class="dh-v2">{_p(T["abajo_pct"])}</p><p class="dh-s">{_n(T["abajo"])} capturas</p></div>'
           f'<div><p class="dh-k">Diferencia típica</p><p class="dh-v2">{_dif(T["dif"])}</p><p class="dh-s">mediana de capturado contra esperado</p></div>'
           '</div>')

    rangos = dict(sem)
    barras = _barras_semanas([(w['adh'], _p(w['adh']), s != kc.MES and w['s'] != s) for w in v['semanas']], tope=1.0)
    pie = _pie_semanas([(w['s'], _rango(rangos[w['s']])) for w in v['semanas']], elegida=s)
    colores = {'abajo_15': '#4055C8', 'abajo_5_15': '#8FA6E8', 'en_rango': '#7CC495', 'arriba_5_15': '#F4A3AE',
               'arriba_15': '#E0566A', 'sin_esperado': '#C8D0E8'}
    max_t = max([x['n'] for x in v['tramos']] + [1])
    negrita = ' style="font-weight:500"'
    tramos = ''.join(
        f'<tr><td class="di"{negrita if x["campo"] == "en_rango" else ""}>{_e(x["k"])}</td>'
        f'<td class="dbarra"><div class="dbar"><i style="width:{x["n"] / max_t * 100:.1f}%;background:{colores[x["campo"]]}"></i></div></td>'
        f'<td class="dnum">{_n(x["n"])}</td><td class="dnum"><b>{_p(x["pct"])}</b></td></tr>' for x in v['tramos'])
    r.html('<div class="dg dg11">'
           '<div class="dcard">' + tarjeta_titulo('Semanas del mes', 'Adherencia de cada semana') + barras + pie + '</div>'
           '<div class="dcard">' + tarjeta_titulo('¿Qué tan lejos del precio estrategia?', 'Capturas del periodo según su diferencia contra el precio esperado')
           + f'<div class="dtw"><table class="dtab">{tramos}</table></div></div>'
           '</div>')

    with st.container(border=True, key='dircard_pre_productos'):
        a, b = st.columns([3, 1.5], vertical_alignment='center')
        niveles = {'categoria': 'Categorías', 'marca': 'Marcas', 'sku': 'SKU'}
        with b:
            nivel = control('Producto', list(niveles), 'dir_pre_producto', 'sku', niveles.get)
        with a:
            r.html(tarjeta_titulo({'categoria': 'Adherencia por categoría', 'marca': 'Adherencia por marca', 'sku': 'Adherencia por SKU'}[nivel],
                                  'De la menor adherencia a la mayor · diferencia típica = mediana de capturado contra esperado'))
        es_sku = nivel == 'sku'
        cuerpo = ''.join(
            f'<tr><td class="di"><span class="dn1">{_e(x["k"])}</span><span class="dn2">'
            + (_e(f'{x["marca"]} · {x["categoria"]}') if es_sku else f'{x["skus"]} SKU')
            + f'</span></td><td class="dnum">{_n(x["capturas"])}</td><td class="dbarra">{_barra(x["adh"])}</td>'
              f'<td class="dnum"><b>{_p(x["adh"])}</b></td><td class="dnum kd-down">{_p(x["arriba"])}</td>'
              f'<td class="dnum" style="color:#4055C8">{_p(x["abajo"])}</td>'
            + (f'<td class="dnum">{_dinero(x["precio_estrategia"])}</td><td class="dnum">{_dinero(x["precio_tipico"])}</td>' if es_sku else '')
            + f'<td class="dnum">{_dif(x["dif"])}</td><td>{_dd(_var_pts(x["adh"], x["adh_ant"]))}</td></tr>'
            for x in v['productos'][nivel])
        r.html(f'<div class="dtw"><table class="dtab"><tr><th class="di">{"SKU" if es_sku else niveles[nivel][:-1]}</th><th>Capturas</th><th></th>'
               '<th>Adherencia</th><th>Arriba +5%</th><th>Abajo −5%</th>'
               + ('<th>Precio estrategia</th><th>Precio típico</th>' if es_sku else '')
               + f'<th>Diferencia típica</th><th>vs {_e(contra or "ant.")}</th></tr>{cuerpo}</table></div>')

    with st.container(border=True, key='dircard_pre_equipo'):
        a, b = st.columns([2.4, 2], vertical_alignment='center')
        opciones = {'cadena': 'Cadenas', 'area': 'Áreas', 'supervisor': 'Supervisores', 'ruta': 'Promotores'}
        with b:
            grupo = control('Equipo', list(opciones), 'dir_pre_equipo', 'cadena', opciones.get)
        minimo = {'cadena': 300 if s == kc.MES else 80, 'ruta': 50 if s == kc.MES else 15}.get(grupo, 1)
        filas = [x for x in v['equipo'][grupo] if x['capturas'] >= minimo]
        limite = {'area': 99, 'supervisor': 99, 'ruta': 30, 'cadena': 20}[grupo]
        todos = len(filas) > limite and st.session_state.get(f'dir_pre_eq_todos_{grupo}', False)
        mostrar = filas if todos else filas[:limite]
        sub = (f'Los {len(mostrar)} de menor adherencia, de {len(filas)}.' if len(mostrar) < len(filas) else 'De menor a mayor adherencia.')
        if minimo > 1:
            sub += f' Solo {opciones[grupo].lower()} con {minimo} capturas o más.'
        with a:
            r.html(tarjeta_titulo({'cadena': 'Adherencia por cadena', 'area': 'Adherencia por área', 'supervisor': 'Adherencia por supervisor',
                                   'ruta': 'Adherencia por promotor'}[grupo], sub))
        cuerpo = ''.join(
            f'<tr><td class="di"><span class="dn1">{_e(x["nombre"])}</span><span class="dn2">{_e(x["sub"])}</span></td>'
            f'<td class="dnum">{_n(x["tiendas"])}</td><td class="dnum">{_n(x["capturas"])}</td><td class="dbarra">{_barra(x["adh"])}</td>'
            f'<td class="dnum"><b>{_p(x["adh"])}</b></td><td class="dnum kd-down">{_p(x["arriba"])}</td>'
            f'<td class="dnum" style="color:#4055C8">{_p(x["abajo"])}</td><td class="dnum">{_dif(x["dif"])}</td>'
            f'<td>{_dd(_var_pts(x["adh"], x.get("adh_ant")))}</td></tr>' for x in mostrar)
        nacional = (f'<tr class="dtot"><td class="di">Nacional</td><td class="dnum">{_n(T["tiendas"])}</td><td class="dnum">{_n(T["capturas"])}</td>'
                    f'<td></td><td class="dnum">{_p(T["adh"])}</td><td class="dnum">{_p(T["arriba_pct"])}</td><td class="dnum">{_p(T["abajo_pct"])}</td>'
                    f'<td class="dnum">{_dif(T["dif"])}</td><td>{_dd(_var_pts(T["adh"], T["adh_ant"]))}</td></tr>')
        r.html('<div class="dtw"><table class="dtab"><tr><th class="di">'
               + {'cadena': 'Cadena', 'area': 'Área', 'supervisor': 'Supervisor', 'ruta': 'Promotor'}[grupo]
               + f'</th><th>Tiendas</th><th>Capturas</th><th></th><th>Adherencia</th><th>Arriba +5%</th><th>Abajo −5%</th>'
               f'<th>Diferencia típica</th><th>vs {_e(contra or "ant.")}</th></tr>{cuerpo}{nacional}</table></div>')
        if len(filas) > limite:
            st.toggle(f'Ver los {len(filas)}', key=f'dir_pre_eq_todos_{grupo}')

    _tiendas_kpi(v['tiendas'], 'precios', pid, s, contra, minimo=30 if s == kc.MES else 10)

    r.html('<p class="dpie"><b>Cómo se cuenta.</b> Adherencia = capturas dentro de ±5% del precio estrategia, más las que no '
           'traen precio esperado, entre todas las capturas del periodo (sin quitar repetidas). Arriba y abajo = fuera de ese '
           'rango. Diferencia típica = la mediana de precio capturado contra esperado. Con una semana elegida se compara contra '
           'la semana anterior; con el mes completo, contra el mes anterior, si tiene reporte de precios.</p>')
    _pie_dato(f'Reporte de precios de {mes.lower()} · semanas {semanas[0]}–{semanas[-1]}')
