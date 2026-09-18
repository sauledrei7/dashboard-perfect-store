"""
Cálculos del tablero del director (v20).

Aquí solo vive pandas: nada de streamlit ni de Supabase. Cada función recibe
las tablas ya leídas y regresa diccionarios listos para pintar. Así el tablero
se puede probar contra los CSV de cualquier corrida sin levantar la app, y los
números se revisan en un solo lugar.

Las reglas son las mismas que ya usan la vista del AM y el reporte de top
ofenders, para que un número nunca diga una cosa aquí y otra allá:

- PS para bono = (PS elegibles + bonus de mayoreo/departamental) / capturadas.
  Es el que ven promotores y supervisores, y el que se paga.
- PS real = tiendas PS / tiendas visitadas de todos los canales, sin la regla
  del bono. Cuenta exactamente las mismas tiendas PS que el de bono; lo único
  que cambia es el total.
- OOS = 1 - sin contestar / encuestas con objetivo.
- SOS y exhibiciones = % de tiendas visitadas que llegan a su objetivo.
- No reconocido = los 3 motivos de TRAX que dicen "reconocido" (TRAX, nueva
  imagen y militraje). Semáforo contra el promedio del equipo: rojo arriba de
  2 veces, amarillo arriba del promedio, y solo entra quien tiene al menos 10
  respuestas (un 1 de 1 no es un 100%).
- Las áreas se agrupan con la estructura del periodo más reciente, para que
  julio y septiembre se puedan comparar aunque el maestro se haya reacomodado.
"""
import numpy as np
import pandas as pd

CANALES_ELEGIBLES = ('AUTOSERVICIOS', 'CASH&CARRY')
CANALES_BONUS = ('MAYORISTAS', 'DEPARTAMENTALES')
MOTIVO_SIN_CONTESTAR = 'SIN CONTESTAR'
INCIDENCIA_NO_RECONOCIDO = 'Producto no reconocido por TRAX.'
MIN_RESPUESTAS_RANKING = 10
SEMANAS_REINCIDENCIA = 9
GRUPOS_MOTIVO = ('nr', 'cat', 'inv', 'otros', 'sc')


# ------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------
def _n(x, dec=1):
    """Número redondeado, o None si no hay dato. None se pinta como '—'."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    if np.isnan(x) or np.isinf(x):
        return None
    return round(x, dec)


def _pct(parte, total):
    return parte / total * 100 if total else np.nan


def _col(df, nombre, defecto=0):
    """Columna numérica sin nulos. Supabase manda None donde el CSV traía vacío."""
    if nombre not in df.columns:
        return pd.Series(defecto, index=df.index, dtype=float)
    return pd.to_numeric(df[nombre], errors='coerce').fillna(defecto)


def _es(df, nombre):
    """Columna booleana donde None cuenta como False."""
    if nombre not in df.columns:
        return pd.Series(False, index=df.index)
    return df[nombre].eq(True)


def nombre_corto(correo) -> str:
    """supervisor22@smiledg.mx -> supervisor22"""
    return str(correo).split('@')[0] if correo else '—'


def grupo_motivo(motivo) -> str:
    m = str(motivo).lower()
    if 'reconocido' in m:
        return 'nr'
    if m == MOTIVO_SIN_CONTESTAR.lower():
        return 'sc'
    if 'catalogado' in m:
        return 'cat'
    if 'no hay inventario' in m:
        return 'inv'
    return 'otros'


def sub_motivo_nr(motivo) -> str:
    """De cuál de los 3 'no reconocido' se trata."""
    m = str(motivo)
    if 'TRAX' in m:
        return 'trax'
    if 'nueva imagen' in m:
        return 'imagen'
    if 'militraje' in m or '“ml”' in m:
        return 'ml'
    return 'trax'


# ------------------------------------------------------------
# Estructura de áreas
# ------------------------------------------------------------
def mapa_areas(kp_reciente: pd.DataFrame):
    """(ruta -> área, supervisor -> área) con el maestro más reciente."""
    if len(kp_reciente) == 0:
        return {}, {}
    ruta_area = kp_reciente.set_index('ruta')['area_manager'].to_dict()
    sup_area = (kp_reciente.dropna(subset=['supervisor'])
                .groupby('supervisor')['area_manager']
                .agg(lambda s: s.mode().iloc[0] if len(s.mode()) else None).to_dict())
    return ruta_area, sup_area


def preparar_respuestas(orr: pd.DataFrame, ruta_area: dict, orden_periodos=None) -> pd.DataFrame:
    """oos_respuestas con su grupo de motivo, su área y la posición de su periodo.

    orden_periodos: los periodo_id del más viejo al más nuevo. La semana TRAX
    vuelve a 1 cada año; con la posición del periodo las semanas se ordenan
    bien aunque la ventana cruce de diciembre a enero.
    """
    if len(orr) == 0:
        return pd.DataFrame(columns=['ruta', 'periodo_id', 'semana', 'motivo', 'veces', 'g', 'sub', 'area', 'pos'])
    o = orr.copy()
    o['veces'] = _col(o, 'veces').astype(int)
    o['semana'] = _col(o, 'semana').astype(int)
    o['g'] = o['motivo'].map(grupo_motivo)
    o['sub'] = np.where(o['g'] == 'nr', o['motivo'].map(sub_motivo_nr), '')
    o['area'] = o['ruta'].map(ruta_area)
    if orden_periodos:
        o['pos'] = o['periodo_id'].map({pid: i for i, pid in enumerate(orden_periodos)}).fillna(-1).astype(int)
    else:
        # Sin orden explícito: dentro de un mismo año, el periodo con semanas más bajas va primero.
        rango = o.groupby('periodo_id')['semana'].min().rank(method='dense').astype(int)
        o['pos'] = o['periodo_id'].map(rango)
    return o


def ventana_semanas(orr: pd.DataFrame, periodo_id: str, s_fin: int, n: int = SEMANAS_REINCIDENCIA) -> pd.DataFrame:
    """Las respuestas de las últimas n semanas que terminan en s_fin del periodo."""
    if len(orr) == 0:
        return orr
    actual = orr.loc[orr['periodo_id'] == periodo_id, 'pos']
    if len(actual) == 0:
        return orr.iloc[0:0]
    pos = int(actual.iloc[0])
    llaves = orr[['pos', 'semana']].drop_duplicates()
    llaves = llaves[(llaves['pos'] < pos) | ((llaves['pos'] == pos) & (llaves['semana'] <= s_fin))]
    llaves = llaves.sort_values(['pos', 'semana']).tail(n)
    return orr.merge(llaves, on=['pos', 'semana'], how='inner')


# ------------------------------------------------------------
# Indicadores de un grupo de rutas
# ------------------------------------------------------------
def indicadores(kp: pd.DataFrame, rt: pd.DataFrame, orr: pd.DataFrame, ks: pd.DataFrame = None) -> dict:
    """Todos los indicadores de un conjunto de rutas (el país, un área o un
    supervisor). kp = kpis_promotor, rt = resumen_tienda, orr = respuestas OOS
    ya preparadas, ks = kpis_supervisor (opcional)."""
    if len(kp) == 0:
        return None

    cap = _col(kp, 'tiendas_capturadas').sum()
    ps = _col(kp, 'ps_elegibles').sum() + _col(kp, 'ps_bonus_mayo_depto').sum()
    obj, nc = _col(kp, 'obj_oos').sum(), _col(kp, 'no_cont_oos').sum()
    prog = _col(kp, 'visitas_programadas').sum()

    visitada = _es(rt, 'tienda_visitada')
    es_ps = _es(rt, 'es_ps') & visitada
    bonus = rt['canal'].isin(CANALES_BONUS) if 'canal' in rt.columns else pd.Series(False, index=rt.index)
    vis = rt[visitada]

    def en_objetivo(real, objetivo):
        con_obj = vis[_col(vis, objetivo, np.nan) > 0]
        if len(con_obj) == 0:
            return np.nan
        return (_col(con_obj, real, 0) >= _col(con_obj, objetivo)).mean() * 100

    respuestas = orr['veces'].sum() if len(orr) else 0

    out = {
        'rutas': int(len(kp)),
        'tiendas': int(_col(kp, 'tiendas_totales').sum()),
        'capturadas': int(cap),
        'ps_tiendas': int(ps),
        'ps': _n(min(_pct(ps, cap), 100.0) if cap else np.nan),
        'ps_real': _n(_pct(es_ps.sum(), visitada.sum())),
        'visitadas': int(visitada.sum()),
        'ps_real_tiendas': int(es_ps.sum()),
        'bonus_visitadas': int((bonus & visitada).sum()),
        'bonus_ps': int((bonus & es_ps).sum()),
        'oos': _n(max(0.0, (1 - nc / obj) * 100) if obj else 100.0),
        'obj_oos': int(obj),
        'no_cont': int(nc),
        'captura': _n(_pct(cap, _col(kp, 'tiendas_elegibles').sum())),
        'efect': _n(_pct(_col(kp, 'visitas_realizadas').sum(), prog)),
        'vis_incid': _n(_pct(_col(kp, 'visitas_incidencia').sum(), prog)),
        'sos_w': _n(en_objetivo('sos_whisky', 'obj_whisky')),
        'sos_t': _n(en_objetivo('sos_tequila', 'obj_tequila')),
        'sos_v': _n(en_objetivo('sos_vodka', 'obj_vodka')),
        'exh': _n(_col(vis, 'cumplio_4').mean() * 100 if len(vis) else np.nan),
        'bono_promo': _n(_col(kp, 'bono_final_pct').mean()),
        'cobran': int((_es(kp, 'candado_abierto') & (_col(kp, 'pct_ps_ruta') >= 1)).sum()),
        'promo_cerrado': int((~_es(kp, 'candado_abierto')).sum()),
        'sin_captura': int((_col(kp, 'tiendas_capturadas') == 0).sum()),
        'nr': _n(_pct(orr.loc[orr['g'] == 'nr', 'veces'].sum(), respuestas)) if respuestas else None,
        'cat': _n(_pct(orr.loc[orr['g'] == 'cat', 'veces'].sum(), respuestas)) if respuestas else None,
        'respuestas': int(respuestas),
    }
    if ks is not None and len(ks):
        out['sups'] = int(len(ks))
        out['bono_sup'] = _n(_col(ks, 'bono_final_pct').mean())
        out['sup_cerrado'] = int((~_es(ks, 'candado_abierto')).sum())
    return out


def indicadores_supervisores(kp: pd.DataFrame, rt: pd.DataFrame, orr: pd.DataFrame) -> dict:
    """Lo mismo que indicadores() para cada supervisor, pero de un jalón.

    v20.1: llamar indicadores() 30 veces (una por supervisor, filtrando las
    tablas cada vez) era lo más lento del tablero. Aquí se agrupa una sola vez.
    Solo trae lo que se pinta de un supervisor; las reglas son idénticas a las
    de indicadores(), y la prueba lo compara contra ella campo por campo.
    orr ya debe traer la columna 'supervisor'.
    """
    if len(kp) == 0:
        return {}
    k = kp.assign(_cap=_col(kp, 'tiendas_capturadas'), _eleg=_col(kp, 'tiendas_elegibles'),
                  _cobra=(_es(kp, 'candado_abierto') & (_col(kp, 'pct_ps_ruta') >= 1)).astype(int))
    g = k.groupby('supervisor')
    base = pd.DataFrame({'rutas': g.size(), 'cap': g['_cap'].sum(), 'eleg': g['_eleg'].sum(),
                         'cobran': g['_cobra'].sum()})

    t = rt.assign(supervisor=rt['ruta'].map(kp.set_index('ruta')['supervisor']))
    visitada = _es(t, 'tienda_visitada')
    t = t.assign(_vis=visitada.astype(int), _ps=(_es(t, 'es_ps') & visitada).astype(int))
    visitadas = t.groupby('supervisor')['_vis'].sum()
    ps_reales = t.groupby('supervisor')['_ps'].sum()
    vis = t[visitada]

    def en_objetivo(real, objetivo):
        con_obj = _col(vis, objetivo, np.nan) > 0
        cumple = (_col(vis, real, 0) >= _col(vis, objetivo)).astype(float)
        return cumple[con_obj].groupby(vis.loc[con_obj, 'supervisor']).mean() * 100

    sos = {c: en_objetivo(real, obj) for c, real, obj in [('sos_w', 'sos_whisky', 'obj_whisky'),
                                                          ('sos_t', 'sos_tequila', 'obj_tequila'),
                                                          ('sos_v', 'sos_vodka', 'obj_vodka')]}
    exh = _col(vis, 'cumplio_4').groupby(vis['supervisor']).mean() * 100
    if len(orr):
        respuestas = orr.groupby('supervisor')['veces'].sum()
        no_rec = orr[orr['g'] == 'nr'].groupby('supervisor')['veces'].sum()
    else:
        respuestas = no_rec = pd.Series(dtype=float)

    out = {}
    for sup, b in base.iterrows():
        resp = respuestas.get(sup, 0)
        out[sup] = {
            'rutas': int(b['rutas']),
            'capturadas': int(b['cap']),
            'captura': _n(_pct(b['cap'], b['eleg'])),
            'cobran': int(b['cobran']),
            'ps_real': _n(_pct(ps_reales.get(sup, 0), visitadas.get(sup, 0))),
            'sos_w': _n(sos['sos_w'].get(sup, np.nan)),
            'sos_t': _n(sos['sos_t'].get(sup, np.nan)),
            'sos_v': _n(sos['sos_v'].get(sup, np.nan)),
            'exh': _n(exh.get(sup, np.nan)),
            'nr': _n(_pct(no_rec.get(sup, 0), resp)) if resp else None,
        }
    return out


# ------------------------------------------------------------
# Un periodo completo
# ------------------------------------------------------------
def tablero_periodo(periodo: dict, kp, ks, rt, orr_todas, ruta_area, sup_area,
                    incidencias: pd.DataFrame = None) -> dict:
    """Todo lo que el tablero necesita de UN periodo.

    periodo: fila de la tabla periodos (periodo_id, mes, semana_inicio, ...).
    orr_todas: respuestas OOS de TODOS los periodos, ya preparadas. Se usan las
    del periodo para los porcentajes y las de las últimas semanas para medir
    reincidencia.
    """
    pid = periodo['periodo_id']
    s_ini, s_fin = int(periodo['semana_inicio']), int(periodo['semana_fin'])

    kp = kp.copy()
    rt = rt.copy()
    ks = ks.copy()
    kp['area'] = kp['ruta'].map(ruta_area).fillna(kp.get('area_manager'))
    rt['area'] = rt['ruta'].map(ruta_area)
    ks['area'] = ks['supervisor'].map(sup_area).fillna(ks.get('area_manager'))
    orr = orr_todas[orr_todas['periodo_id'] == pid]

    areas = sorted(a for a in kp['area'].dropna().unique())
    P = {
        'id': pid,
        'nombre': str(periodo.get('mes') or pid).capitalize(),
        'anio': periodo.get('anio'),
        's_ini': s_ini, 's_fin': s_fin,
        'semanas': s_fin - s_ini + 1,
        'nacional': indicadores(kp, rt, orr, ks),
        'areas': {},
        'supervisores': [],
    }
    for a in areas:
        P['areas'][a] = indicadores(kp[kp['area'] == a], rt[rt['area'] == a],
                                    orr[orr['area'] == a], ks[ks['area'] == a])

    sup_de_ruta = kp.set_index('ruta')['supervisor'].to_dict()
    orr_sup = orr.assign(supervisor=orr['ruta'].map(sup_de_ruta))
    calculados = indicadores_supervisores(kp, rt, orr_sup)
    for _, s in ks.iterrows():
        k = dict(calculados.get(s['supervisor'], {}))
        # Los números "oficiales" del supervisor salen de su propia fila,
        # que es de donde sale su bono.
        k.update({
            'supervisor': s['supervisor'],
            # Se nombra por el correo y no por 'ejecutivo': esa columna del
            # maestro traía códigos (SUPERVISOR_16) hasta agosto y correos desde
            # septiembre, y el mismo supervisor saldría con dos nombres.
            'sup': nombre_corto(s['supervisor']),
            'area': s['area'],
            'ps': _n(s.get('pct_ps')),
            'oos': _n(s.get('mult_oos_pct')),
            'efect': _n(s.get('efectividad_pct')),
            'candado': bool(s.get('candado_abierto')) if s.get('candado_abierto') is not None else False,
            'bono': _n(s.get('bono_final_pct')),
            'faltan': int(_n(s.get('visitas_faltantes_95'), 0) or 0),
        })
        # 'rutas' se queda con las de kpis_promotor y no con rutas_a_cargo: una
        # ruta con tiendas repartidas entre dos supervisores cuenta en los dos
        # en rutas_a_cargo, y la tarjeta diría "7 de 10 cobran" con 11 rutas.
        P['supervisores'].append(k)

    ventana = ventana_semanas(orr_todas, pid, s_fin)
    P['promotores'], P['prom_nr'] = foco_promotores(kp, orr, ventana, incidencias)
    P['semanal'] = mezcla_semanal(ventana)
    P['rojos_nr'] = sum(1 for x in P['promotores'] if x['semaforo'] == 'ROJO')
    P['rutas_sc'] = sum(1 for x in P['promotores'] if x['no_cont'] > 0)
    return P


def resumen_ligero(periodo: dict, kp, rt, ruta_area) -> dict:
    """Solo el país y las áreas, para la gráfica de tendencia de Inicio.

    Es lo que se calcula de los meses que no se están viendo: sin los 30
    supervisores ni los 278 promotores, que son la parte cara del tablero.
    """
    s_ini, s_fin = int(periodo['semana_inicio']), int(periodo['semana_fin'])
    kp = kp.copy()
    rt = rt.copy()
    kp['area'] = kp['ruta'].map(ruta_area).fillna(kp.get('area_manager'))
    rt['area'] = rt['ruta'].map(ruta_area)
    vacio = preparar_respuestas(pd.DataFrame(), ruta_area)
    areas = sorted(a for a in kp['area'].dropna().unique())
    return {
        'id': periodo['periodo_id'],
        'nombre': str(periodo.get('mes') or periodo['periodo_id']).capitalize(),
        's_ini': s_ini, 's_fin': s_fin, 'semanas': s_fin - s_ini + 1,
        'nacional': indicadores(kp, rt, vacio),
        'areas': {a: indicadores(kp[kp['area'] == a], rt[rt['area'] == a], vacio) for a in areas},
    }


def foco_promotores(kp, orr, ventana, incidencias=None):
    """Una fila por promotor para las dos tablas del Foco OOS.
    Regresa (lista, promedio de no reconocido del equipo)."""
    if len(kp) == 0:
        return [], None

    # --- mezcla de respuestas del periodo ---
    if len(orr):
        pr = orr.pivot_table(index='ruta', columns='g', values='veces', aggfunc='sum', fill_value=0)
        subs = orr[orr['g'] == 'nr'].pivot_table(index='ruta', columns='sub', values='veces',
                                                 aggfunc='sum', fill_value=0)
    else:
        pr, subs = pd.DataFrame(), pd.DataFrame()
    for g in GRUPOS_MOTIVO:
        if g not in pr.columns:
            pr[g] = 0
    pr['tot'] = pr[list(GRUPOS_MOTIVO)].sum(axis=1) if len(pr) else 0
    prom_nr = _pct(pr['nr'].sum(), pr['tot'].sum()) if len(pr) and pr['tot'].sum() else np.nan

    # --- reincidencia en las últimas semanas ---
    sem_arriba, sem_eval, sem_sc = {}, {}, {}
    if len(ventana):
        w = ventana.pivot_table(index=['ruta', 'pos', 'semana'], columns='g', values='veces',
                                aggfunc='sum', fill_value=0)
        for g in GRUPOS_MOTIVO:
            if g not in w.columns:
                w[g] = 0
        w['tot'] = w[list(GRUPOS_MOTIVO)].sum(axis=1)
        llave = pd.MultiIndex.from_arrays([w.index.get_level_values('pos'), w.index.get_level_values('semana')])
        prom_sem = (w['nr'].groupby(level=['pos', 'semana']).sum() /
                    w['tot'].groupby(level=['pos', 'semana']).sum())
        w['arriba'] = (w['nr'] / w['tot'].replace(0, np.nan)).values > prom_sem.reindex(llave).values
        sem_arriba = w['arriba'].groupby(level='ruta').sum().astype(int).to_dict()
        sem_eval = w['arriba'].groupby(level='ruta').size().astype(int).to_dict()
        sem_sc = (w['sc'] > 0).groupby(level='ruta').sum().astype(int).to_dict()

    # --- incidencias levantadas en ATLAS ---
    inc_nr, inc_oos = {}, {}
    if incidencias is not None and len(incidencias):
        inc_nr = incidencias[incidencias['incidencia'] == INCIDENCIA_NO_RECONOCIDO].groupby('ruta').size().to_dict()
        inc_oos = incidencias[incidencias['tipo'] == 'OOS'].groupby('ruta').size().to_dict()

    filas = []
    for _, b in kp.iterrows():
        ruta = b['ruta']
        x = pr.loc[ruta] if ruta in pr.index else None
        tot = int(x['tot']) if x is not None else 0
        nr = int(x['nr']) if x is not None else 0
        pct_nr = _pct(nr, tot) if tot else np.nan
        veces = pct_nr / prom_nr if (tot and prom_nr and not np.isnan(prom_nr)) else np.nan
        if tot < MIN_RESPUESTAS_RANKING or np.isnan(veces):
            semaforo = 'POCAS'
        else:
            semaforo = 'ROJO' if veces > 2 else ('AMARILLO' if veces > 1 else 'VERDE')
        s = subs.loc[ruta] if ruta in subs.index else {}
        filas.append({
            'ruta': ruta,
            'sup': nombre_corto(b.get('supervisor')),
            'supervisor': b.get('supervisor'),
            'area': b.get('area'),
            'resp': tot,
            'nr': nr,
            'pct_nr': _n(pct_nr),
            'veces': _n(veces, 2),
            'trax': int(s.get('trax', 0)) if len(s) else 0,
            'imagen': int(s.get('imagen', 0)) if len(s) else 0,
            'ml': int(s.get('ml', 0)) if len(s) else 0,
            'semaforo': semaforo,
            'nr_arriba': int(sem_arriba.get(ruta, 0)),
            'nr_eval': int(sem_eval.get(ruta, 0)),
            'obj_oos': int(_n(b.get('obj_oos'), 0) or 0),
            'no_cont': int(_n(b.get('no_cont_oos'), 0) or 0),
            'oos': _n(b.get('mult_oos_pct')),
            'sc_semanas': int(sem_sc.get(ruta, 0)),
            'inc_nr': int(inc_nr.get(ruta, 0)),
            'inc_oos': int(inc_oos.get(ruta, 0)),
        })
    return filas, _n(prom_nr)


def mezcla_semanal(ventana: pd.DataFrame):
    """Qué se contestó cada semana de la ventana, por grupo de motivo."""
    if len(ventana) == 0:
        return []
    w = ventana.pivot_table(index=['pos', 'semana'], columns='g', values='veces', aggfunc='sum', fill_value=0)
    filas = []
    for (_, semana), x in w.sort_index().iterrows():
        fila = {'semana': int(semana)}
        fila.update({g: int(x.get(g, 0)) for g in GRUPOS_MOTIVO})
        filas.append(fila)
    return filas


# ------------------------------------------------------------
# Uso de ATLAS
# ------------------------------------------------------------
def uso_atlas(usuarios: pd.DataFrame, accesos: pd.DataFrame, incidencias: pd.DataFrame,
              kp: pd.DataFrame, ruta_area: dict, ahora: pd.Timestamp = None,
              dias_activo: int = 7, dias_pendiente: int = 3) -> dict:
    """Quién entra a la app y cómo se atienden las incidencias.

    usuarios: username, tipo, identificador, activo (NUNCA el hash).
    accesos: username, resultado, entro_at.
    incidencias: ruta, estado, created_at, resuelta_en del periodo.
    kp: kpis_promotor del periodo, para saber de quién es cada ruta.
    """
    ahora = ahora if ahora is not None else pd.Timestamp.now(tz='UTC')
    out = {'roles': {}, 'sin_entrar': [], 'incidencias': {}, 'por_supervisor': []}

    # --- accesos ---
    u = usuarios.copy() if len(usuarios) else pd.DataFrame(columns=['username', 'tipo', 'identificador', 'activo'])
    u = u[_es(u, 'activo') | u['activo'].isna()] if 'activo' in u.columns else u
    u = u[u['tipo'].isin(['promotor', 'supervisor', 'am'])]

    ultimo = pd.Series(dtype='datetime64[ns, UTC]')
    if len(accesos):
        a = accesos[accesos['resultado'].isin(['OK', 'COOKIE'])].copy()
        a['entro_at'] = pd.to_datetime(a['entro_at'], utc=True, errors='coerce')
        ultimo = a.dropna(subset=['entro_at']).groupby('username')['entro_at'].max()
    limite = ahora - pd.Timedelta(days=dias_activo)
    activos = set(ultimo[ultimo >= limite].index)

    for tipo, etiqueta in [('promotor', 'Promotores'), ('supervisor', 'Supervisores'), ('am', 'Area Managers')]:
        del_tipo = u[u['tipo'] == tipo]
        out['roles'][tipo] = {'etiqueta': etiqueta, 'total': int(len(del_tipo)),
                              'entraron': int(del_tipo['username'].isin(activos).sum())}
    out['total'] = int(len(u))
    out['entraron'] = int(u['username'].isin(activos).sum())

    sup_de_ruta = kp.set_index('ruta')['supervisor'].to_dict() if len(kp) else {}
    promos = u[(u['tipo'] == 'promotor') & ~u['username'].isin(activos)]
    for _, p in promos.iterrows():
        ruta = str(p.get('identificador') or '').upper()
        visto = ultimo.get(p['username'])
        filas_dias = int((ahora - visto).days) if visto is not None and not pd.isna(visto) else None
        out['sin_entrar'].append({
            'ruta': ruta,
            'sup': nombre_corto(sup_de_ruta.get(ruta)),
            'area': ruta_area.get(ruta),
            'dias': filas_dias,
        })
    # Primero los que nunca han entrado, luego los que llevan más días fuera.
    out['sin_entrar'].sort(key=lambda x: (x['dias'] is not None, -(x['dias'] or 0), x['ruta']))

    # --- incidencias ---
    inc = incidencias.copy() if incidencias is not None and len(incidencias) else pd.DataFrame(
        columns=['ruta', 'estado', 'created_at', 'resuelta_en'])
    inc['estado'] = inc['estado'].fillna('PENDIENTE')
    inc['created_at'] = pd.to_datetime(inc['created_at'], utc=True, errors='coerce')
    inc['resuelta_en'] = pd.to_datetime(inc['resuelta_en'], utc=True, errors='coerce')
    inc['supervisor'] = inc['ruta'].map(sup_de_ruta)
    pend = inc['estado'] == 'PENDIENTE'
    viejas = pend & (inc['created_at'] < ahora - pd.Timedelta(days=dias_pendiente))
    out['incidencias'] = {
        'total': int(len(inc)),
        'autorizadas': int((inc['estado'] == 'AUTORIZADA').sum()),
        'rechazadas': int((inc['estado'] == 'NO_AUTORIZADA').sum()),
        'pendientes': int(pend.sum()),
        'pendientes_viejas': int(viejas.sum()),
    }

    sups = kp[['supervisor']].dropna().drop_duplicates('supervisor') if len(kp) else pd.DataFrame(columns=['supervisor'])
    for _, s in sups.iterrows():
        d = inc[inc['supervisor'] == s['supervisor']]
        resueltas = d.dropna(subset=['resuelta_en'])
        dias = ((resueltas['resuelta_en'] - resueltas['created_at']).dt.total_seconds() / 86400).mean() if len(resueltas) else np.nan
        pendientes = d['estado'] == 'PENDIENTE'
        out['por_supervisor'].append({
            'supervisor': s['supervisor'],
            'sup': nombre_corto(s['supervisor']),
            'area': ruta_area.get(kp.loc[kp['supervisor'] == s['supervisor'], 'ruta'].iloc[0]) if len(kp) else None,
            'levantadas': int(len(d)),
            'autorizadas': int((d['estado'] == 'AUTORIZADA').sum()),
            'rechazadas': int((d['estado'] == 'NO_AUTORIZADA').sum()),
            'pendientes': int(pendientes.sum()),
            'pendientes_viejas': int((pendientes & (d['created_at'] < ahora - pd.Timedelta(days=dias_pendiente))).sum()),
            'dias_resolver': _n(dias),
        })
    # Primero quien tiene más incidencias esperando.
    out['por_supervisor'].sort(key=lambda x: (-x['pendientes_viejas'], -x['pendientes'], -x['levantadas']))
    return out
