"""
v25 — La ficha de una tienda: todo su historial en una pantalla.

Solo pandas, igual que director_calc.py y kpis_cliente_calc.py: recibe las filas de
UNA tienda y regresa un diccionario con textos y estados. Los colores, los íconos y el
acomodo se deciden en components/director_tienda.py.

Qué junta:
  - Perfect Store, lo del bono: resumen_tienda (el mes) y detalle_semanal (la semana).
  - Lo que mide el cliente: exh_tienda_semana, osa_tienda_semana y precios_tienda_semana.
  - Las encuestas de agotados que cuentan para el OOS: oos_tienda_semana.

Qué cumple la tienda en el mes lo dice components/cumplimiento.py, con el veredicto del
pipeline; aquí no se vuelve a calcular. La semana no trae veredicto por categoría: su
color es solo una guía contra el objetivo del mes.

Estados: 'ok' cumple · 'cer' cerca (85% o más del objetivo) · 'mal' abajo ·
'nd' sin medición · 'neu' sin semáforo.

Escalas: en la base, el SOS y sus objetivos vienen en 0-100, y así se quedan aquí.
Solo se pasan a 0-1 para preguntarle a cumplimiento.py, que así los espera.
"""
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd

from components import cumplimiento
from kpis_cliente_calc import COLS_PASAN, COLS_RAZON, COLS_SIGUEN, NOMBRE_RAZON, _f

# (nombre, columna del SOS, columna del objetivo, y cómo las llama cumplimiento.py)
CATS = (('Whisky', 'sos_whisky', 'obj_whisky', 'Total Whisky', 'Objetivo Whisky'),
        ('Tequila', 'sos_tequila', 'obj_tequila', 'Total tequila', 'Objetivo Tequila'),
        ('Vodka', 'sos_vodka', 'obj_vodka', 'Total vodka', 'Objetivo Vodka'))
PILARES = ('Whisky', 'Tequila', 'Vodka', 'EXH')
CERCA = 0.85
MESES_EN_MAPA = 3           # el mes elegido y los dos anteriores; si no hay tantos antes, los que siguen
CANAL = {'AUTOSERVICIOS': 'Autoservicio', 'CASH&CARRY': 'Cash & Carry', 'CASH & CARRY': 'Cash & Carry',
         'MAYORISTAS': 'Mayorista', 'DEPARTAMENTALES': 'Departamental'}


# ------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------
def _filas(df) -> list:
    return [] if df is None or len(df) == 0 else df.to_dict('records')


def _si(v) -> bool:
    return str(v).strip().lower() in ('1', '1.0', 'true')


def _txt(v) -> str:
    return ' '.join(str(v).split()) if v is not None and pd.notna(v) else ''


def _ent(v) -> int:
    x = _f(v)
    return 0 if x is None else int(round(x))


def _d(v, dec=2) -> str:
    """Número con decimales fijos, redondeando como Excel: 37.25 a un decimal es 37.3 (el
    formato de Python lo dejaría en 37.2), y la base trae el SOS justo con 2 decimales."""
    if v is None:
        return '—'
    return str(Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP))


def _signo(v, dec=2) -> str:
    v = round(v, dec + 4)             # 45.72 - 55.34 da -9.620000000000005
    return ('+' if v >= 0 else '−') + _d(abs(v), dec)


def _p(v, dec=1) -> str:
    return '—' if v is None else _d(round(v * 100, 8), dec) + '%'


def _n(v) -> str:
    return '—' if v is None else f'{v:,.0f}'


def _g(v) -> str:
    """4.0 -> '4'; 2.5 -> '2.5'."""
    return '—' if v is None else f'{v:g}'


def _lista(a) -> str:
    a = list(a)
    return ''.join(a) if len(a) <= 1 else ', '.join(a[:-1]) + ' y ' + a[-1]


def _meses_txt(n) -> str:
    return f'{n} mes' if n == 1 else f'{n} meses'


# ------------------------------------------------------------
# El mes y la semana de una tienda
# ------------------------------------------------------------
def _mes_tienda(fila: dict) -> dict:
    """Una fila de resumen_tienda, con números de Python y el veredicto del pipeline."""
    sos = {c[0]: _f(fila.get(c[1])) for c in CATS}
    obj = {c[0]: _f(fila.get(c[2])) for c in CATS}
    medida = _si(fila.get('tienda_visitada'))
    adaptada = {'cumplio_wtv': fila.get('cumplio_wtv'), 'CUMPLIO 4': fila.get('cumplio_4'),
                'Puntos Promedio Exhibición': fila.get('exh_puntos'), 'Objetivo Puntos HS': fila.get('obj_exh'),
                'Cadena': _txt(fila.get('cadena'))}
    for nombre, _, _, col, col_obj in CATS:
        adaptada[col] = None if sos[nombre] is None else sos[nombre] / 100.0
        adaptada[col_obj] = obj[nombre]
    return {
        'ruta': _txt(fila.get('ruta')), 'tienda': _txt(fila.get('tienda')), 'cadena': _txt(fila.get('cadena')),
        'canal': _txt(fila.get('canal')), 'medida': medida, 'ps': medida and _si(fila.get('es_ps')),
        'sos': sos, 'obj': obj, 'pts': _f(fila.get('exh_puntos')), 'obj_exh': _f(fila.get('obj_exh')),
        'cumple': cumplimiento.categorias(adaptada) if medida else {k: False for k in PILARES},
        'nota_exh': cumplimiento.nota_exh(adaptada) if medida else '',
    }


def _semana(d, e, o, p, q) -> dict:
    """Una semana de la tienda: el detalle del bono, exhibiciones, OSA, precios y encuestas."""
    w = {'medida': d is not None, 'inc': False, 'sos': {c[0]: None for c in CATS}, 'pts': None, 'c4': None, 'ai': 0, 'bi': 0,
         'exh': 0, 'cap': 0, 'fre': 0, 'alto': 0,
         'cod': None, 'trax': None, 'pasan': None, 'siguen': None, 'raz': {},
         'pcap': None, 'pok': None, 'parr': None, 'pab': None, 'eobj': None, 'econt': None}
    if d is not None:
        w['inc'] = _si(d.get('incidencia'))
        for c in CATS:
            w['sos'][c[0]] = _f(d.get(c[1]))
        w['pts'] = _f(d.get('exh_puntos'))
        c4 = _f(d.get('cumplio_4'))
        w['c4'] = None if c4 is None else c4 >= 1
        w['ai'] = sum(_ent(v) for k, v in d.items() if str(k).endswith('_ai'))
        w['bi'] = sum(_ent(v) for k, v in d.items() if str(k).endswith('_bi'))
    if e is not None:
        w.update(exh=_ent(e.get('exhibiciones')), cap=_ent(e.get('capturas')), fre=_ent(e.get('frentes')),
                 alto=_ent(e.get('alto_impacto')))
    if o is not None:
        w['raz'] = {c: _ent(o.get(c)) for c in COLS_RAZON}
        w['cod'] = _ent(o.get('codigos'))
        w['pasan'] = sum(w['raz'][c] for c in COLS_PASAN)
        w['siguen'] = sum(w['raz'][c] for c in COLS_SIGUEN)
        w['trax'] = w['pasan'] + w['siguen']
    if p is not None:
        w['pcap'] = _ent(p.get('capturas'))
        w['pok'] = _ent(p.get('en_rango')) + _ent(p.get('sin_esperado'))
        w['parr'] = _ent(p.get('arriba_5_15')) + _ent(p.get('arriba_15'))
        w['pab'] = _ent(p.get('abajo_15')) + _ent(p.get('abajo_5_15'))
    if q is not None:
        w['eobj'], w['econt'] = _ent(q.get('obj_oos')), _ent(q.get('contestadas_oos'))
    return w


def _por_semana(df, sumar=None) -> dict:
    """{(periodo, semana): fila}. Con sumar, las filas repetidas de una semana se acumulan."""
    out = {}
    for f in _filas(df):
        s = _f(f.get('semana'))
        if s is None:
            continue
        k = (str(f.get('periodo_id')), int(s))
        if sumar and k in out:
            for c in sumar:
                out[k][c] = _ent(out[k].get(c)) + _ent(f.get(c))
        else:
            out[k] = dict(f)
    return out


# ------------------------------------------------------------
# Estados
# ------------------------------------------------------------
def estado_ps(m) -> str:
    return 'nd' if not m or not m['medida'] else ('ok' if m['ps'] else 'mal')


def estado_sos(m, cat) -> str:
    if not m or not m['medida'] or m['sos'][cat] is None:
        return 'nd'
    if m['cumple'][cat]:
        return 'ok'
    o = m['obj'][cat]
    return 'cer' if o and o > 0 and m['sos'][cat] >= CERCA * o else 'mal'


def estado_exh(m) -> str:
    if not m or not m['medida']:
        return 'nd'
    if m['cumple']['EXH']:
        return 'ok'
    o = m['obj_exh']
    return 'cer' if o and o > 0 and m['pts'] is not None and m['pts'] >= CERCA * o else 'mal'


def estado_osa(v) -> str:
    return 'nd' if v is None else ('ok' if v >= 0.95 else ('cer' if v >= 0.85 else 'mal'))


def _estado_enc(cont, obj, por_semana=False) -> str:
    if not obj:
        return 'nd'
    if cont >= obj:
        return 'ok'
    if por_semana:
        return 'mal' if cont == 0 else 'cer'
    return 'cer' if cont / obj >= CERCA else 'mal'


# ------------------------------------------------------------
# La ficha
# ------------------------------------------------------------
def ventana(orden, sel) -> list:
    """Los meses que salen en el mapa: el elegido y los anteriores y, si es de los primeros,
    los que le siguen. Así cambiar de mes no cambia lo que se ve, solo cuál va al frente."""
    inicio = max(0, list(orden).index(sel) - MESES_EN_MAPA + 1)
    return list(orden)[inicio: inicio + MESES_EN_MAPA]


def _armar(curt, periodos, sel, rt, ds, oos, exh, osa, pre):
    """Lo que comparten la pantalla y el Excel: los meses de la tienda y las semanas del mapa."""
    filas_rt = {str(f.get('periodo_id')): f for f in _filas(rt)}
    orden = [p['pid'] for p in periodos]
    if sel not in orden:
        return None
    info = {p['pid']: p for p in periodos}
    meses = {pid: _mes_tienda(filas_rt[pid]) for pid in orden if pid in filas_rt}
    if not meses:
        return None
    meses_mapa = ventana(orden, sel)
    d_i, e_i, o_i, p_i = _por_semana(ds), _por_semana(exh), _por_semana(osa), _por_semana(pre)
    q_i = _por_semana(oos, sumar=('obj_oos', 'contestadas_oos'))
    semanas = {pid: {s: _semana(d_i.get((pid, s)), e_i.get((pid, s)), o_i.get((pid, s)), p_i.get((pid, s)), q_i.get((pid, s)))
                     for s, _ in info[pid]['semanas']}
               for pid in meses_mapa if pid in meses}
    return {'curt': str(curt), 'orden': orden, 'info': info, 'meses': meses, 'ventana': meses_mapa, 'semanas': semanas, 'sel': sel}


def _tot(a, pid, campo):
    """Suma de un dato en las semanas de un mes; None si ninguna semana lo trae."""
    vals = [w[campo] for w in a['semanas'].get(pid, {}).values() if w[campo] is not None]
    return sum(vals) if vals else None


def _razones_mes(a, pid) -> dict:
    out = {c: 0 for c in COLS_RAZON}
    for w in a['semanas'].get(pid, {}).values():
        for c, n in w['raz'].items():
            out[c] += n
    return out


def _historia(a) -> str:
    meses, info = a['meses'], a['info']
    medidos = [pid for pid in a['orden'] if pid in meses and meses[pid]['medida']]
    en_ps = [pid for pid in medidos if meses[pid]['ps']]
    if not medidos:
        return 'Sin medición en lo que lleva en ATLAS'
    if not en_ps:
        return 'Sin Perfect Store en ' + ('su único mes medido' if len(medidos) == 1 else f'los {len(medidos)} meses')
    hoy = meses[medidos[-1]]['ps']
    racha = 0
    for pid in reversed(medidos):
        if meses[pid]['ps'] != hoy:
            break
        racha += 1
    txt = f'Perfect Store en {len(en_ps)} de {_meses_txt(len(medidos))}'
    if not hoy:
        return txt + ' · el último fue ' + info[en_ps[-1]]['nombre'].lower()
    if racha < len(medidos):
        return txt + (f' · lleva {racha} seguidos' if racha > 1 else ' · lo recuperó en ' + info[medidos[-1]]['nombre'].lower())
    return txt


def _kpis(a, M) -> list:
    """Las 4 tarjetas de Perfect Store del mes elegido."""
    out = []
    for nombre, *_ in CATS:
        e = estado_sos(M, nombre)
        k = {'k': nombre, 'estado': e, 'sub': 'Share of shelf', 'valor': '—', 'uni': '', 'gap': '', 'obj': 'Sin medición este mes',
             'cubre': None, 'nota': ''}
        if e != 'nd':
            s, o = M['sos'][nombre], M['obj'][nombre]
            hay = o is not None and o > 0
            k.update(valor=_d(s), uni='%', gap=_signo(s - o) + ' pts' if hay else 'sin objetivo',
                     obj=f'Objetivo {_d(o)}%' if hay else 'Sin objetivo cargado: así no puede cumplir',
                     cubre=s / o if hay else 0.0,
                     nota=f'Va en el {_d(s / o * 100, 1)}% de su objetivo' if hay else '')
        out.append(k)
    e = estado_exh(M)
    k = {'k': 'EXH', 'estado': e, 'sub': 'Puntos por semana', 'valor': '—', 'uni': '', 'gap': '', 'obj': 'Sin medición este mes',
         'cubre': None, 'nota': ''}
    if e != 'nd' and M['pts'] is not None:
        pts, o = M['pts'], M['obj_exh']
        hay = o is not None and o > 0
        cumple = M['cumple']['EXH']
        k.update(valor=_d(pts), uni='/sem',
                 gap=_signo(pts - o) if hay else ('✓ cumple' if cumple else '✕'),
                 obj=f'Objetivo {_g(o)}/sem' if hay else 'Sin objetivo: siempre cumple',
                 cubre=pts / o if hay else (1.5 if cumple else 0.0), sin_marca=not hay,
                 nota=f'Alto impacto {_n(_tot(a, a["sel"], "ai") or 0)} · bajo {_n(_tot(a, a["sel"], "bi") or 0)}',
                 nota2=M['nota_exh'])
    elif e != 'nd':
        k['estado'] = 'nd'
    out.append(k)
    return out


def _cliente(a, M) -> dict:
    """Las 4 tarjetas de lo que mide el cliente, con el mes anterior al lado."""
    sel, orden, info = a['sel'], a['orden'], a['info']
    pos = orden.index(sel)
    prev = orden[pos - 1] if pos > 0 and orden[pos - 1] in a['semanas'] else None
    tot = lambda campo: _tot(a, sel, campo) if M else None                 # noqa: E731
    ant = lambda campo: _tot(a, prev, campo) if prev else None             # noqa: E731

    cod, ag = tot('cod'), tot('siguen')
    osa = 1 - ag / cod if cod else None
    cod_a = ant('cod')
    osa_a = 1 - ant('siguen') / cod_a if cod_a else None

    # Precios: si el mes no trae reporte, el último mes anterior del mapa que sí lo tenga
    antes = [pid for pid in a['ventana'] if orden.index(pid) < pos]
    mes_pre = sel if tot('pcap') else next((pid for pid in reversed(antes) if _tot(a, pid, 'pcap')), None)
    pcap = _tot(a, mes_pre, 'pcap') if mes_pre else None

    eobj, econt = tot('eobj'), tot('econt') or 0
    faltan = [s for s, w in a['semanas'].get(sel, {}).items() if w['eobj'] and w['econt'] < w['eobj']] if M else []
    return {
        'previo': info[prev]['nombre'].lower() if prev else None,
        'exh': {'exh': tot('exh'), 'cap': tot('cap'), 'fre': tot('fre'), 'alto': tot('alto'),
                'exh_ant': ant('exh'), 'cap_ant': ant('cap')},
        'osa': {'osa': osa, 'estado': estado_osa(osa), 'cod': cod, 'siguen': ag, 'pasan': tot('pasan'), 'trax': tot('trax'),
                'osa_ant': osa_a},
        'precios': {'adh': _tot(a, mes_pre, 'pok') / pcap if pcap else None, 'cap': pcap,
                    'ok': _tot(a, mes_pre, 'pok') if pcap else None, 'arriba': _tot(a, mes_pre, 'parr') if pcap else None,
                    'abajo': _tot(a, mes_pre, 'pab') if pcap else None,
                    'mes': info[mes_pre]['nombre'].lower() if mes_pre else None, 'prestado': bool(pcap) and mes_pre != sel},
        'enc': {'obj': eobj, 'cont': econt if eobj else None, 'estado': _estado_enc(econt, eobj), 'faltan': faltan},
    }


def _agenda(a, M, cli) -> dict:
    """Qué revisar, como la agenda del one pager: lo que le falta para ser PS y las semanas flojas."""
    sel, orden, meses, info = a['sel'], a['orden'], a['meses'], a['info']
    mes = info[sel]['nombre'].lower()
    e = estado_ps(M)
    titulo = {'ok': 'Es PS · para que siga así', 'mal': 'Para ser PS le falta', 'nd': 'Sin medición en el mes'}[e]
    items = []
    if M is None:
        items.append({'tipo': 'nd', 'a': 'Sin datos', 'b': f': la tienda no estaba en el maestro de {mes}.', 'c': ''})
        return {'estado': e, 'titulo': titulo, 'sub': f'Con los números de {mes}', 'items': items}
    if e == 'nd':
        items.append({'tipo': 'nd', 'a': 'Medición', 'b': f': la tienda no se visitó en {mes}.', 'c': ' · ¿se está capturando?'})
        return {'estado': e, 'titulo': titulo, 'sub': f'Con los números de {mes}', 'items': items}

    hasta_hoy = [pid for pid in orden[:orden.index(sel) + 1] if pid in meses and meses[pid]['medida']]

    def racha(pilar) -> str:
        """Cuántos meses medidos lleva sin cumplir ese pilar, contando hacia atrás desde el elegido."""
        n = 0
        for pid in reversed(hasta_hoy):
            if meses[pid]['cumple'][pilar]:
                break
            n += 1
        if len(hasta_hoy) <= 1:
            return 'es su primer mes medido'
        if n == len(hasta_hoy):
            return f'0 de {n} meses medidos'
        return f'{n} meses seguidos sin cumplir' if n >= 2 else 'se cayó este mes'

    faltan = sorted((c[0] for c in CATS if not M['cumple'][c[0]]),
                    key=lambda k: M['sos'][k] / M['obj'][k] if M['obj'][k] and M['sos'][k] is not None else 0)
    unico = ' · es lo único que le falta' if len(faltan) + (0 if M['cumple']['EXH'] else 1) == 1 else ''
    for k in faltan:
        s, o = M['sos'][k], M['obj'][k]
        h = 'en 0% este mes · ¿hay producto en anaquel?' if s == 0 else racha(k)
        items.append({'tipo': k, 'a': k, 'c': f' · {h}{unico}',
                      'b': f': faltan {_d(o - s)} pts ({_d(s)}% → {_d(o)}%)' if o and o > 0 and s is not None
                      else ': no tiene objetivo cargado'})
    if not M['cumple']['EXH']:
        items.append({'tipo': 'EXH', 'a': 'Exhibiciones', 'c': f' · {racha("EXH")}{unico}',
                      'b': f': {_d(M["pts"])} por semana' + (f', objetivo {_g(M["obj_exh"])}' if M['obj_exh'] else '')})
    if e == 'ok':
        # En un empate gana el orden de siempre: whisky, tequila, vodka
        justos = sorted(((M['sos'][c[0]] / M['obj'][c[0]], c[0]) for c in CATS if M['obj'][c[0]] and M['sos'][c[0]] is not None),
                        key=lambda x: x[0])
        if justos:
            r, k = justos[0]
            items.append({'tipo': k, 'a': k, 'b': f': el SOS más justo, {_d(M["sos"][k])}% ({_d(r * 100, 1)}% de su objetivo)',
                          'c': f' · que no baje de {_d(M["obj"][k])}%'})
    sem = a['semanas'].get(sel, {})
    bajas = [(s, w) for s, w in sem.items() if w['cod'] and 1 - w['siguen'] / w['cod'] < 0.85]
    if bajas:
        items.append({'tipo': 'osa', 'a': 'OSA', 'c': '',
                      'b': ': ' + _lista(f'S{s} en {_p(1 - w["siguen"] / w["cod"], 0)} ({w["siguen"]} agotados)' for s, w in bajas)})
    if cli['enc']['faltan']:
        items.append({'tipo': 'enc', 'a': 'Encuestas OOS', 'c': ' · cuentan para el multiplicador OOS del promotor',
                      'b': ': ' + _lista(f'S{s} con {sem[s]["econt"]} de {sem[s]["eobj"]}' for s in cli['enc']['faltan'])})
    sin_exh = [s for s, w in sem.items() if w['medida'] and not w['inc'] and w['exh'] == 0]
    if sin_exh and (cli['exh']['exh'] or 0) > 0:
        items.append({'tipo': 'sin_exh', 'a': 'Semanas sin exhibiciones', 'b': ': ' + _lista(f'S{s}' for s in sin_exh), 'c': ''})
    if not items:
        items.append({'tipo': 'ok', 'a': 'Sin pendientes', 'b': f' en {mes}.', 'c': ''})
    return {'estado': e, 'titulo': titulo, 'sub': f'Con los números de {mes} · lo que hay que revisar', 'items': items[:6]}


def _celda(t, e, s='', mes=False, sel=False, span=1) -> dict:
    return {'t': t, 's': s, 'e': e, 'mes': mes, 'sel': sel, 'span': span}


def _mapa(a) -> dict:
    """Todas las semanas de los meses del mapa y cada mes completo, renglón por renglón."""
    meses, info, sel = a['meses'], a['info'], a['sel']
    cols = []                          # (periodo, semana) o (periodo, None) para el mes completo
    grupos = []
    for pid in a['ventana']:
        sem = info[pid]['semanas']
        grupos.append({'titulo': f'{info[pid]["nombre"].upper()} · S{sem[0][0]}–S{sem[-1][0]}', 'sel': pid == sel, 'span': len(sem) + 1})
        cols += [(pid, s) for s, _ in sem] + [(pid, None)]
    encabezados = [{'t': 'Mes' if s is None else f'S{s}', 'mes': s is None, 'sel': pid == sel,
                    's': info[pid]['corto'] if s is None else f'{dict(info[pid]["semanas"])[s]:%d/%m}'}
                   for pid, s in cols]

    def fila(tipo, lbl, sub, por_semana, por_mes) -> dict:
        celdas = []
        for pid, s in cols:
            m = meses.get(pid)
            c = None
            if m is not None:
                c = por_mes(pid, m) if s is None else por_semana(a['semanas'][pid][s], m)
            if c is None:
                c = _celda('—', 'nd')
            c['mes'], c['sel'] = s is None, pid == sel
            celdas.append(c)
        return {'tipo': tipo, 'lbl': lbl, 'sub': sub, 'celdas': celdas}

    medidos = [pid for pid in a['orden'] if pid in meses and meses[pid]['medida']]
    en_ps = [pid for pid in medidos if meses[pid]['ps']]
    celdas_ps = []
    for pid in a['ventana']:
        m = meses.get(pid)
        e = estado_ps(m)
        falt = ''
        if e == 'mal':
            f = [k.lower() if k != 'EXH' else 'exhibiciones' for k in PILARES if not m['cumple'][k]]
            falt = ('faltó ' if len(f) == 1 else 'faltaron ') + _lista(f) if f else ''
        celdas_ps.append(_celda('No estaba en el maestro' if m is None else {'ok': 'PS', 'mal': 'No PS', 'nd': 'Sin datos'}[e],
                                e, falt, mes=True, sel=pid == sel, span=len(info[pid]['semanas']) + 1))
    filas = [{'tipo': 'titulo', 'lbl': 'PERFECT STORE · LO QUE CUENTA PARA EL BONO'},
             {'tipo': 'ps', 'lbl': 'Perfect Store', 'celdas': celdas_ps,
              'sub': f'{len(en_ps)} de {_meses_txt(len(medidos))}' if medidos else 'sin medición'}]

    ref = meses.get(sel) or meses[[pid for pid in a['orden'] if pid in meses][-1]]
    for nombre, *_ in CATS:
        def semana_sos(w, m, k=nombre):
            if not m['medida'] or not w['medida']:
                return None
            if w['inc']:
                return _celda('inc.', 'nd')
            s, o = w['sos'][k], m['obj'][k]
            if s is None:
                return None
            hay = o is not None and o > 0
            return _celda(_d(s, 1), 'ok' if hay and s >= o + cumplimiento.EMPATE else ('cer' if hay and s >= CERCA * o else 'mal'))

        def mes_sos(pid, m, k=nombre):
            e = estado_sos(m, k)
            if e == 'nd':
                return None
            o = m['obj'][k]
            return _celda(_d(m['sos'][k]), e, _signo(m['sos'][k] - o) if o and o > 0 else 'sin obj.')

        filas.append(fila(nombre, nombre, f'SOS % · objetivo {_d(ref["obj"][nombre])}', semana_sos, mes_sos))

    def semana_pts(w, m):
        if not m['medida'] or not w['medida']:
            return None
        if w['inc']:
            return _celda('inc.', 'nd')
        if w['pts'] is None:
            return None
        o = m['obj_exh']
        e = 'ok' if w['c4'] else ('cer' if o and o > 0 and w['pts'] >= CERCA * o else 'mal')
        return _celda(_g(round(w['pts'], 1)), e, '✓' if w['c4'] else '✕')

    def mes_pts(pid, m):
        e = estado_exh(m)
        if e == 'nd' or m['pts'] is None:
            return None
        return _celda(_d(m['pts']), e, '✓ cumple' if m['cumple']['EXH'] else '✕')

    filas.append(fila('EXH', 'Exhibiciones', 'puntos por semana' + (f' · objetivo {_g(ref["obj_exh"])}' if ref['obj_exh'] else ' · sin objetivo'),
                      semana_pts, mes_pts))
    filas.append({'tipo': 'titulo', 'lbl': 'LO QUE MIDE EL CLIENTE'})

    def conteo(tipo, lbl, sub, campo):
        return fila(tipo, lbl, sub,
                    lambda w, m: _celda(_n(w[campo]), 'neu') if w[campo] > 0 else _celda('0', 'nd'),
                    lambda pid, m: _celda(_n(_tot(a, pid, campo) or 0), 'neu' if (_tot(a, pid, campo) or 0) > 0 else 'nd'))

    filas.append(conteo('unicas', 'Exhibiciones únicas', 'escenas de TRAX', 'exh'))
    filas.append(conteo('capturas', 'Capturas', 'todo lo que se capturó', 'cap'))

    def semana_osa(w, m):
        if not w['cod']:
            return None
        v = 1 - w['siguen'] / w['cod']
        return _celda(_p(v, 0), estado_osa(v), f'{w["siguen"]} agot.' if w['siguen'] else '')

    def mes_osa(pid, m):
        cod = _tot(a, pid, 'cod')
        if not cod:
            return None
        ag = _tot(a, pid, 'siguen') or 0
        return _celda(_p(1 - ag / cod), estado_osa(1 - ag / cod), f'{ag} agot.')

    filas.append(fila('osa', 'OSA', 'disponibilidad · regla del cliente', semana_osa, mes_osa))

    def semana_pre(w, m):
        return _celda(_p(w['pok'] / w['pcap'], 0), 'neu', f'{w["pok"]} de {w["pcap"]}') if w['pcap'] else None

    def mes_pre(pid, m):
        cap = _tot(a, pid, 'pcap')
        if not cap:
            return None
        ok = _tot(a, pid, 'pok') or 0
        return _celda(_p(ok / cap), 'neu', f'{ok} de {cap}')

    filas.append(fila('precios', 'Precios', 'adherencia ±5% · beta', semana_pre, mes_pre))

    def semana_enc(w, m):
        return _celda(f'{w["econt"]}/{w["eobj"]}', _estado_enc(w['econt'], w['eobj'], por_semana=True)) if w['eobj'] else None

    def mes_enc(pid, m):
        obj = _tot(a, pid, 'eobj')
        if not obj:
            return None
        cont = _tot(a, pid, 'econt') or 0
        return _celda(f'{cont}/{obj}', _estado_enc(cont, obj), _p(cont / obj, 0))

    filas.append(fila('enc', 'Encuestas OOS', 'contestadas / con objetivo', semana_enc, mes_enc))
    return {'grupos': grupos, 'cols': encabezados, 'filas': filas, 'n_cols': len(cols)}


def ficha(curt, periodos, sel, rt, ds=None, oos=None, exh=None, osa=None, pre=None):
    """Todo lo que pinta la ficha de una tienda.

    periodos: todos, del más viejo al más nuevo: [{'pid', 'nombre', 'corto', 'semanas': [(semana, lunes)]}].
    sel: el periodo elegido. rt … pre: las filas de la tienda en cada tabla, de cualquier periodo.
    Regresa None si la tienda no aparece en ningún periodo.
    """
    a = _armar(curt, periodos, sel, rt, ds, oos, exh, osa, pre)
    if a is None:
        return None
    meses, info = a['meses'], a['info']
    M = meses.get(sel)
    ref = M or meses[[pid for pid in a['orden'] if pid in meses][-1]]
    e = estado_ps(M)
    n_pil = sum(1 for k in PILARES if M and M['cumple'][k])
    mes = info[sel]['nombre']
    cli = _cliente(a, M)
    razones = _razones_mes(a, sel) if M else {}
    return {
        'curt': a['curt'], 'tienda': ref['tienda'], 'cadena': ref['cadena'], 'ruta': ref['ruta'],
        'canal': CANAL.get(ref['canal'].upper(), ref['canal']),
        'mes': mes, 'semanas': [s for s, _ in info[sel]['semanas']],
        'en_maestro': M is not None, 'estado': e, 'historia': _historia(a),
        'ps': {'ok': 'Es PS', 'mal': 'No PS', 'nd': 'Sin datos'}[e],
        'ps_sub': f'No estaba en el maestro de {mes.lower()}' if M is None
        else {'ok': 'Cumple los 4 pilares', 'mal': f'Cumple {n_pil} de 4 pilares', 'nd': 'La tienda no se visitó en el mes'}[e],
        'pilares': [{'k': k, 'ok': bool(M and M['cumple'][k])} for k in PILARES],
        'kpis': _kpis(a, M),
        'cliente': cli,
        'agenda': _agenda(a, M, cli),
        'razones': sorted(({'k': NOMBRE_RAZON[c], 'n': n, 'sigue': c in COLS_SIGUEN} for c, n in razones.items() if n > 0),
                          key=lambda x: -x['n']),
        'mapa': _mapa(a),
    }


def tabla_ficha(curt, periodos, sel, rt, ds=None, oos=None, exh=None, osa=None, pre=None, equipo=None) -> pd.DataFrame:
    """La descarga: un renglón por semana y uno por mes completo, de los meses del mapa.

    equipo = {periodo: (supervisor, área)}, para ponerlo junto al promotor.
    """
    a = _armar(curt, periodos, sel, rt, ds, oos, exh, osa, pre)
    if a is None:
        return pd.DataFrame()
    filas = []
    si_no = lambda v: '' if v is None else ('Sí' if v else 'No')        # noqa: E731
    pct = lambda n, d: round(n / d, 4) if d else None                   # noqa: E731
    for pid in a['ventana']:
        m = a['meses'].get(pid)
        if m is None:
            continue
        sup, area = (equipo or {}).get(pid, ('', ''))
        base = {'CURT': a['curt'], 'Tienda': m['tienda'], 'Cadena': m['cadena'], 'Mes': a['info'][pid]['nombre']}
        quien = {'Promotor': m['ruta'], 'Supervisor': sup, 'Área': area}
        objetivos = {f'Objetivo {c[0].lower()} %': m['obj'][c[0]] for c in CATS}
        for s, w in a['semanas'][pid].items():
            fila = dict(base, Semana=f'S{s}', **quien)
            fila.update({'Perfect Store': '', 'Incidencia de TRAX': si_no(w['inc']) if w['medida'] else ''})
            for c in CATS:
                fila[f'SOS {c[0].lower()} %'] = w['sos'][c[0]]
                fila[f'Objetivo {c[0].lower()} %'] = objetivos[f'Objetivo {c[0].lower()} %']
            fila.update({
                'Exhibiciones (puntos)': w['pts'], 'Objetivo de exhibiciones': m['obj_exh'], 'Cumple exhibiciones': si_no(w['c4']),
                'Exhibiciones únicas': w['exh'], 'Capturas': w['cap'], 'Frentes': w['fre'], 'Alto impacto': w['alto'],
                'Códigos OSA': w['cod'], 'Agotados según TRAX': w['trax'], 'Pasan a disponible': w['pasan'],
                'Siguen agotados': w['siguen'], '% OSA': pct((w['cod'] or 0) - (w['siguen'] or 0), w['cod']),
                'Capturas de precio': w['pcap'], 'Precios en rango': w['pok'], '% adherencia de precios': pct(w['pok'], w['pcap']),
                'Encuestas OOS con objetivo': w['eobj'], 'Encuestas contestadas': w['econt'],
            })
            filas.append(fila)
        tot = lambda campo: _tot(a, pid, campo)                          # noqa: E731
        fila = dict(base, Semana='Mes completo', **quien)
        fila.update({'Perfect Store': si_no(m['ps']) if m['medida'] else 'Sin datos', 'Incidencia de TRAX': ''})
        for c in CATS:
            fila[f'SOS {c[0].lower()} %'] = m['sos'][c[0]]
            fila[f'Objetivo {c[0].lower()} %'] = objetivos[f'Objetivo {c[0].lower()} %']
        fila.update({
            'Exhibiciones (puntos)': m['pts'], 'Objetivo de exhibiciones': m['obj_exh'],
            'Cumple exhibiciones': si_no(m['cumple']['EXH']) if m['medida'] else '',
            'Exhibiciones únicas': tot('exh'), 'Capturas': tot('cap'), 'Frentes': tot('fre'), 'Alto impacto': tot('alto'),
            'Códigos OSA': tot('cod'), 'Agotados según TRAX': tot('trax'), 'Pasan a disponible': tot('pasan'),
            'Siguen agotados': tot('siguen'), '% OSA': pct((tot('cod') or 0) - (tot('siguen') or 0), tot('cod')),
            'Capturas de precio': tot('pcap'), 'Precios en rango': tot('pok'), '% adherencia de precios': pct(tot('pok'), tot('pcap')),
            'Encuestas OOS con objetivo': tot('eobj'), 'Encuestas contestadas': tot('econt'),
        })
        filas.append(fila)
    return pd.DataFrame(filas)
