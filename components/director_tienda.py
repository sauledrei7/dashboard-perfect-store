"""
TABLERO DEL DIRECTOR — Ficha de tienda (v25).

Un buscador sobre todas las tiendas y, de la que se elija, todo su historial en una
pantalla, con el formato del one pager de visita a campo: si fue Perfect Store y qué
pilar le faltó, lo que mide el cliente (exhibiciones, OSA, precios y encuestas) y el
mapa semana a semana de los últimos meses.

No pide datos nuevos: data.get_ficha_tienda() junta, por CURT, las tablas del bono y
las de Exhibiciones, OSA y Precios. El armado vive en ficha_tienda_calc.py; aquí solo
se deciden íconos, colores y acomodo.

Mismos cuidados que director_secciones.py:
- Ningún bloque HTML lleva renglones en blanco (st.markdown lo cortaría ahí).
- Todo texto que viene de la base pasa por _e() antes de meterse al HTML.
"""
import pandas as pd
import streamlit as st

import ficha_tienda_calc as fc
import kpis_cliente_calc as kc
import render as r
from components.director_kpis import MIME_XLSX, _mes, _pie_dato, _semanas, _vacio, _var_pts, _var_rel
from components.director_secciones import _e, tarjeta_titulo
from data import (get_catalogo_tiendas, get_equipo_rutas, get_exh_escenas_tienda, get_ficha_tienda,
                  get_periodos_director)
from director_calc import nombre_corto

CARA = {'ok': '😄', 'cer': '😐', 'mal': '😞', 'nd': '😶'}
ICONO = {'Whisky': '🥃', 'Tequila': '🍸', 'Vodka': '🍹', 'EXH': '📦', 'ps': '🏆', 'unicas': '📦', 'capturas': '📸',
         'osa': '🛒', 'precios': '🏷️', 'enc': '📝', 'sin_exh': '📦', 'nd': '😶', 'ok': '✓'}
NOMBRE_PILAR = {'Whisky': 'Whisky', 'Tequila': 'Tequila', 'Vodka': 'Vodka', 'EXH': 'Exh'}
MAX_RAZONES = 6

CSS_FICHA = """
<style>
/* Los 4 estados: cumple, cerca, abajo y sin medición; neu = sin semáforo */
.ft-ok { background: #E8F5EC; color: #1E5C36; } .ft-cer { background: #FDF0E8; color: #98580E; }
.ft-mal { background: #FCE8EB; color: #B5303F; } .ft-nd { background: #F4F7FE; color: #9AA6D1; }
.ft-neu { background: #fff; color: #1F2A5C; box-shadow: inset 0 0 0 0.5px #DCE4F5; }
.ft-f-ok { background: #2D8A4E; } .ft-f-cer { background: #E8A53D; } .ft-f-mal { background: #D94557; } .ft-f-nd { background: #9AA6D1; }
.ft-t-ok { color: #1E5C36; } .ft-t-cer { color: #98580E; } .ft-t-mal { color: #B5303F; } .ft-t-nd { color: #6B7BB8; }
/* encabezado, como el del one pager */
.ft-hero { position: relative; overflow: hidden; border-radius: 18px; color: #fff; display: grid;
  grid-template-columns: minmax(0,1fr) 330px; gap: 22px; align-items: center; padding: 22px 22px 22px 28px;
  background: linear-gradient(135deg,#FF6FA8 0%,#FF8DBD 42%,#4F7BE8 100%); margin-bottom: 14px; }
.ft-hero .ft-etq { font-size: 11.5px; font-weight: 600; letter-spacing: .14em; }
.ft-hero .ft-nom { font-size: 34px; font-weight: 600; line-height: 1.08; margin: 6px 0; }
.ft-hero .ft-nom.ft-largo { font-size: 28px; }
.ft-hero .ft-meta { font-size: 14px; }
.ft-hero .ft-eq { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.ft-hero .ft-eq span { background: rgba(255,255,255,.18); border: 0.5px solid rgba(255,255,255,.5); border-radius: 9px;
  padding: 3px 10px; font-size: 12.5px; white-space: nowrap; }
.ft-hero .ft-eq b { font-weight: 600; }
.ft-hero .ft-hist { display: inline-block; margin-top: 12px; background: rgba(31,42,92,.18); border-radius: 9px;
  padding: 6px 12px; font-size: 13.5px; }
.ft-estado { background: #fff; color: #1F2A5C; border-radius: 15px; padding: 14px 16px 16px; box-shadow: 0 12px 28px rgba(31,42,92,.2); }
.ft-estado .ft-per { font-size: 11px; font-weight: 600; letter-spacing: .08em; color: #6B7BB8; }
.ft-estado .ft-ps { display: flex; align-items: center; gap: 12px; margin: 8px 0 12px; }
.ft-estado .ft-cara { font-size: 46px; line-height: 1; }
.ft-estado .ft-ps b { display: block; font-size: 29px; font-weight: 600; line-height: 1; }
.ft-estado .ft-ps small { display: block; font-size: 12.5px; color: #6B7BB8; margin-top: 3px; }
.ft-pils { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 6px; }
.ft-pil { display: flex; flex-direction: column; align-items: center; border-radius: 10px; padding: 5px 0 4px;
  font-size: 20px; line-height: 1.15; }
.ft-pil small { font-size: 11px; font-weight: 600; }
.ft-pil.ft-nd small { color: #6B7BB8; }
/* títulos de bloque */
.ft-tit { display: flex; align-items: baseline; gap: 10px; margin: 4px 0 10px; }
.ft-tit b { font-size: 16px; font-weight: 600; color: #1F2A5C; }
.ft-tit span { font-size: 12.5px; color: #6B7BB8; }
.ft-g4 { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; margin-bottom: 14px; }
.ft-g32 { display: grid; grid-template-columns: minmax(0,1.5fr) minmax(0,1fr); gap: 12px; align-items: start; margin-bottom: 14px; }
/* tarjetas de Perfect Store */
.ft-kpi { background: #fff; border: 0.5px solid #DCE4F5; border-radius: 14px; padding: 14px 16px; display: flex; flex-direction: column; }
.ft-kpi .ft-top { display: flex; align-items: center; gap: 10px; }
.ft-kpi .ft-circ { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 19px; flex: none; }
.ft-kpi .ft-nm { font-size: 15px; font-weight: 600; line-height: 1.15; color: #1F2A5C; min-width: 0; }
.ft-kpi .ft-nm small { display: block; font-size: 11.5px; font-weight: 400; color: #6B7BB8; }
.ft-kpi .ft-car { margin-left: auto; font-size: 24px; line-height: 1; }
.ft-kpi .ft-lin { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin: 12px 0 6px; flex-wrap: wrap; }
.ft-kpi .ft-big { font-size: 30px; font-weight: 600; line-height: 1; letter-spacing: -.01em; white-space: nowrap; color: #1F2A5C; }
.ft-kpi .ft-big small { font-size: 15px; font-weight: 400; color: #6B7BB8; margin-left: 2px; letter-spacing: 0; }
.ft-kpi .ft-big.ft-sin { color: #9AA6D1; }
.ft-gap { font-size: 12px; font-weight: 600; padding: 3px 8px; border-radius: 7px; white-space: nowrap; }
.ft-kpi .ft-obj { font-size: 12px; color: #6B7BB8; }
.ft-barra { position: relative; height: 7px; border-radius: 99px; background: #EEF3FE; margin-top: 9px; }
.ft-barra i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 99px; }
.ft-barra em { position: absolute; top: -3px; bottom: -3px; left: 66.67%; width: 2px; margin-left: -1px; background: #1F2A5C;
  border-radius: 2px; }
.ft-kpi .ft-pk { font-size: 11.5px; color: #6B7BB8; margin-top: 8px; line-height: 1.35; }
/* tarjetas de lo que mide el cliente */
.ft-cli { background: #fff; border: 0.5px solid #DCE4F5; border-radius: 14px; padding: 14px 16px; display: flex; flex-direction: column;
  gap: 5px; align-items: flex-start; }
.ft-cli .ft-ck { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; font-size: 13.5px;
  font-weight: 500; color: #1F2A5C; }
.ft-cli .ft-cv { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
.ft-cli .ft-cv b { font-size: 28px; font-weight: 600; line-height: 1.05; font-variant-numeric: tabular-nums; color: #1F2A5C; }
.ft-cli .ft-cv span { font-size: 13px; color: #6B7BB8; margin-right: 8px; }
.ft-cli .ft-cs { font-size: 12px; color: #6B7BB8; line-height: 1.4; }
.ft-cli .dd { margin-top: 2px; }
.ft-tag { display: inline-block; font-size: 11px; border-radius: 999px; padding: 2px 9px; font-weight: 500; white-space: nowrap; }
.ft-beta { background: #4055C8; color: #fff; letter-spacing: .06em; }
/* qué revisar y por qué se agota */
.ft-agenda { background: linear-gradient(135deg,#FDF0F7 0%,#EEF3FE 100%); border: 0.5px solid #F8D3E5; border-radius: 14px;
  padding: 14px 18px 8px; color: #1F2A5C; }
.ft-agenda .ft-at { font-size: 16px; font-weight: 600; }
.ft-agenda .ft-as { font-size: 12px; color: #6B7BB8; margin: 2px 0 6px; }
.ft-item { padding: 7px 0; border-top: 0.5px solid rgba(200,214,244,.9); font-size: 13.5px; line-height: 1.4; }
.ft-item b { font-weight: 600; }
.ft-item small { color: #6B7BB8; font-size: 12.5px; }
.ft-razones { background: #fff; border: 0.5px solid #DCE4F5; border-radius: 14px; padding: 14px 18px; color: #1F2A5C; }
.ft-razones .ft-at { font-size: 16px; font-weight: 600; }
.ft-razones .ft-as { font-size: 12px; color: #6B7BB8; margin: 2px 0 8px; }
.ft-raz { display: grid; grid-template-columns: minmax(0,1fr) 34px 128px; gap: 8px; align-items: center; font-size: 13px;
  padding: 5px 0; border-top: 0.5px solid #EDF0F8; }
.ft-raz b { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
.ft-raz .ft-der { text-align: right; }
/* el mapa semana a semana */
.ft-mapa { min-width: 880px; display: flex; flex-direction: column; gap: 3px; }
.ft-fila { display: grid; gap: 3px; }
.ft-grp { text-align: center; font-size: 11.5px; font-weight: 600; letter-spacing: .1em; padding: 5px 0; border-radius: 9px;
  background: #F4F7FE; color: #6B7BB8; }
.ft-grp.ft-sel { background: linear-gradient(135deg,#FF6FA8,#4F7BE8); color: #fff; }
.ft-col { display: flex; flex-direction: column; align-items: center; line-height: 1.2; color: #6B7BB8; font-size: 10.5px; padding: 2px 0; }
.ft-col b { font-size: 13.5px; font-weight: 600; }
.ft-col.ft-m { color: #1F2A5C; }
.ft-col.ft-m.ft-sel { color: #B83D7A; }
.ft-lbl { display: flex; flex-direction: column; justify-content: center; min-width: 0; font-size: 13.5px; font-weight: 600;
  line-height: 1.2; color: #1F2A5C; }
.ft-lbl small { font-size: 11px; font-weight: 400; color: #6B7BB8; line-height: 1.25; }
.ft-c { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px; min-height: 42px;
  border-radius: 9px; font-size: 14px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.1; text-align: center; }
.ft-c small { font-size: 10.5px; font-weight: 500; }
.ft-c.ft-inc { font-size: 12px; font-weight: 500; }
.ft-c.ft-cps { flex-direction: row; gap: 10px; font-size: 15px; }
.ft-c.ft-m.ft-ok { box-shadow: inset 0 0 0 0.5px #BBDFC4; } .ft-c.ft-m.ft-cer { box-shadow: inset 0 0 0 0.5px #F3D2AE; }
.ft-c.ft-m.ft-mal { box-shadow: inset 0 0 0 0.5px #F4BCC3; } .ft-c.ft-m.ft-nd { box-shadow: inset 0 0 0 0.5px #DCE4F5; }
.ft-c.ft-m.ft-sel { box-shadow: inset 0 0 0 1.6px #FF6FA8; }
.ft-sep { font-size: 11px; font-weight: 600; letter-spacing: .1em; color: #C56FA0; border-bottom: 1px solid #F8D3E5;
  padding: 8px 0 3px; margin-bottom: 1px; }
.ft-ley { display: flex; align-items: center; gap: 5px; font-size: 12px; color: #6B7BB8; flex-wrap: wrap; }
.ft-ley i { width: 11px; height: 11px; border-radius: 3px; display: inline-block; margin-left: 8px; }
.ft-ley i.ft-ok { border: 0.5px solid #BBDFC4; } .ft-ley i.ft-cer { border: 0.5px solid #F3D2AE; }
.ft-ley i.ft-mal { border: 0.5px solid #F4BCC3; } .ft-ley i.ft-nd { border: 0.5px solid #DCE4F5; }
.ft-nota { font-size: 11.5px; color: #9AA6D1; line-height: 1.5; margin-top: 8px; }
.ft-sin { background: #F4F7FE; border: 0.5px solid #DCE4F5; border-radius: 14px; padding: 26px 20px; text-align: center; color: #6B7BB8; }
.ft-sin b { display: block; font-size: 16px; font-weight: 600; color: #1F2A5C; margin-bottom: 4px; }
.ft-sin span { font-size: 13px; }
/* En una pantalla angosta (1024 px) el nombre y los números grandes bajan un poco para no salirse */
@media (max-width: 1180px) {
  .ft-hero { grid-template-columns: minmax(0,1fr) 290px; gap: 16px; padding: 18px 18px 18px 22px; }
  .ft-hero .ft-nom, .ft-hero .ft-nom.ft-largo { font-size: 24px; }
  .ft-kpi { padding: 12px; }
  .ft-kpi .ft-top { gap: 7px; }
  .ft-kpi .ft-circ { width: 30px; height: 30px; font-size: 16px; }
  .ft-kpi .ft-nm { font-size: 13.5px; }
  .ft-kpi .ft-nm small { font-size: 10.5px; }
  .ft-kpi .ft-car { font-size: 20px; }
  .ft-kpi .ft-big { font-size: 25px; }
  .ft-cli .ft-cv b { font-size: 24px; }
}
</style>
"""


# ============================================================
# FORMATO
# ============================================================
def _n(x) -> str:
    return '—' if x is None else f'{x:,.0f}'


def _lista_periodos(periodos) -> list:
    """Los periodos como los pide ficha_tienda_calc: del más viejo al más nuevo, con sus semanas."""
    out = []
    for p in periodos.to_dict('records'):
        nombre = _mes(p)
        out.append({'pid': p['periodo_id'], 'nombre': nombre, 'corto': nombre[:3].lower(), 'semanas': _semanas(p)})
    return out


def _texto(v) -> str:
    return str(v).strip() if v is not None and pd.notna(v) else ''


def _chip(par, previo) -> str:
    """El cambio contra el mes anterior, o por qué no se puede comparar."""
    texto, clase = par
    if texto == '—':
        return f'<span class="dd dd-eq">{"sin dato de " + _e(previo) if previo else "sin mes anterior"}</span>'
    return f'<span class="dd dd-{clase}">{texto} vs {_e(previo)}</span>'


# ============================================================
# LAS PIEZAS
# ============================================================
def _hero(f, equipo) -> str:
    e = f['estado']
    sup, area = equipo.get(f['ruta'], (None, None))
    chips = [('Promotor', f['ruta']), ('Supervisor', nombre_corto(sup) if _texto(sup) else ''), ('Área', _texto(area))]
    eq = ''.join(f'<span>{k} <b>{_e(v)}</b></span>' for k, v in chips if v)
    pilares = ''.join(
        f'<div class="ft-pil ft-{"nd" if e == "nd" else ("ok" if p["ok"] else "mal")}">{ICONO[p["k"]]}'
        f'<small>{"" if e == "nd" else ("✓ " if p["ok"] else "✕ ")}{NOMBRE_PILAR[p["k"]]}</small></div>' for p in f['pilares'])
    return ('<div class="ft-hero"><div>'
            f'<div class="ft-etq">FICHA DE TIENDA · CURT {_e(f["curt"])}</div>'
            f'<div class="ft-nom{" ft-largo" if len(f["tienda"]) > 25 else ""}">{_e(f["tienda"])}</div>'
            f'<div class="ft-meta">{_e(" · ".join(x for x in (f["cadena"], f["canal"]) if x))}</div>'
            f'<div class="ft-eq">{eq}</div>'
            f'<div class="ft-hist">🏆 {_e(f["historia"])}</div></div>'
            '<div class="ft-estado">'
            f'<div class="ft-per">📅 {_e(f["mes"].upper())} · S{f["semanas"][0]}–S{f["semanas"][-1]}</div>'
            f'<div class="ft-ps"><span class="ft-cara">{CARA[e]}</span><div><b class="ft-t-{e}">{f["ps"]}</b>'
            f'<small>{_e(f["ps_sub"])}</small></div></div>'
            f'<div class="ft-pils">{pilares}</div></div></div>')


def _kpi(k) -> str:
    e = k['estado']
    nombre = 'Exhibiciones' if k['k'] == 'EXH' else k['k']
    cab = (f'<div class="ft-top"><span class="ft-circ ft-f-{e}">{ICONO[k["k"]]}</span>'
           f'<div class="ft-nm">{nombre}<small>{k["sub"]}</small></div><span class="ft-car">{CARA[e]}</span></div>')
    if e == 'nd':
        return (f'<div class="ft-kpi">{cab}<div class="ft-lin"><span class="ft-big ft-sin">—</span></div>'
                f'<div class="ft-obj">{k["obj"]}</div></div>')
    ancho = max(0.0, min(k['cubre'] or 0.0, 1.5)) / 1.5 * 100
    notas = ' · '.join(x for x in (k['nota'], k.get('nota2', '')) if x)
    return (f'<div class="ft-kpi">{cab}'
            f'<div class="ft-lin"><span class="ft-big">{k["valor"]}<small>{k["uni"]}</small></span>'
            f'<span class="ft-gap ft-{e}">{k["gap"]}</span></div>'
            f'<div class="ft-obj">{_e(k["obj"])}</div>'
            f'<div class="ft-barra"><i class="ft-f-{e}" style="width:{ancho:.1f}%"></i>{"" if k.get("sin_marca") else "<em></em>"}</div>'
            f'<div class="ft-pk">{_e(notas)}</div></div>')


def _tarjeta_cliente(titulo, tag, valores, sub, chip='') -> str:
    cifras = ''.join(f'<b{clase}>{v}</b><span>{_e(u)}</span>' for v, u, clase in valores)
    return (f'<div class="ft-cli"><div class="ft-ck"><span>{titulo}</span>{tag}</div>'
            f'<div class="ft-cv">{cifras}</div><div class="ft-cs">{_e(sub)}</div>{chip}</div>')


def _cliente(f) -> str:
    c = f['cliente']
    previo = c['previo']
    x = c['exh']
    exh = _tarjeta_cliente(
        'Exhibiciones', '', [(_n(x['exh']), 'únicas', ''), (_n(x['cap']), 'capturas', '')],
        'Sin datos del mes' if not f['en_maestro'] else
        f'{_n(x["fre"])} frentes · {_n(x["alto"])} de alto impacto'
        + (f' · en {previo}: {_n(x["exh_ant"])} y {_n(x["cap_ant"])}' if x['exh_ant'] is not None else ''),
        _chip(_var_rel(x['exh'], x['exh_ant']), previo))

    o = c['osa']
    hay = o['osa'] is not None
    como_va = {'ok': 'en meta', 'cer': 'cerca', 'mal': 'abajo'}.get(o['estado'], '')
    osa = _tarjeta_cliente(
        'OSA', f'<span class="ft-tag ft-{o["estado"]}">{como_va}</span>' if hay else '',
        [(fc._p(o['osa']), '', f' class="ft-t-{o["estado"]}"' if hay else ' class="ft-t-nd"')],
        f'{_n(o["siguen"])} agotados de {_n(o["cod"])} códigos · {_n(o["pasan"])} pasan a disponible' if hay
        else 'Sin encuesta de anaquel en el mes',
        _chip(_var_pts(o['osa'], o['osa_ant']), previo))

    p = c['precios']
    hay = p['adh'] is not None
    precios = _tarjeta_cliente(
        'Precios', '<span class="ft-tag ft-beta">BETA</span>',
        [(fc._p(p['adh']), 'de ' + p['mes'] if p['prestado'] else '', '' if hay else ' class="ft-t-nd"')],
        f'{_n(p["ok"])} de {_n(p["cap"])} capturas a ±5% del precio estrategia · {_n(p["arriba"])} arriba · {_n(p["abajo"])} abajo'
        if hay else 'Sin capturas de precio',
        '<span class="dd dd-eq">último reporte de precios</span>' if p['prestado'] else '')

    q = c['enc']
    hay = bool(q['obj'])
    enc = _tarjeta_cliente(
        'Encuestas OOS', f'<span class="ft-tag ft-{q["estado"]}">{fc._p(q["cont"] / q["obj"], 0)}</span>' if hay else '',
        [(_n(q['cont']) if hay else '—', f'de {_n(q["obj"])} contestadas' if hay else '', '' if hay else ' class="ft-t-nd"')],
        ('Faltaron en ' + fc._lista(f'S{s}' for s in q['faltan']) if q['faltan'] else 'Todas contestadas') if hay
        else 'Sin encuestas con objetivo en el mes')
    return f'<div class="ft-g4">{exh}{osa}{precios}{enc}</div>'


def _agenda(f) -> str:
    a = f['agenda']
    icono = {'ok': '🏆', 'mal': '🎯', 'nd': '😶'}[a['estado']]
    items = ''.join(f'<div class="ft-item"><b>{ICONO.get(x["tipo"], "")} {_e(x["a"])}</b>{_e(x["b"])}<small>{_e(x["c"])}</small></div>'
                    for x in a['items'])
    return (f'<div class="ft-agenda"><div class="ft-at">{icono} {a["titulo"]}</div>'
            f'<div class="ft-as">{_e(a["sub"])}</div>{items}</div>')


def _razones(f) -> str:
    o = f['cliente']['osa']
    sub = (f'{_n(o["trax"])} agotados según TRAX; {_n(o["siguen"])} siguen agotados' if o['osa'] is not None
           else 'sin encuesta de anaquel')
    filas = ''.join(
        f'<div class="ft-raz"><span>{_e(x["k"])}</span><b>{_n(x["n"])}</b><span class="ft-der">'
        f'<span class="ft-tag ft-{"mal" if x["sigue"] else "ok"}">{"sigue agotado" if x["sigue"] else "pasa a disponible"}</span>'
        '</span></div>' for x in f['razones'][:MAX_RAZONES])
    if not filas:
        filas = ('<div class="ft-raz" style="display:block;color:#6B7BB8">'
                 + ('Ningún código agotado en el mes.' if o['osa'] is not None
                    else f'La tienda no trae encuesta de anaquel en {_e(f["mes"].lower())}.') + '</div>')
    return (f'<div class="ft-razones"><div class="ft-at">Por qué se agota</div>'
            f'<div class="ft-as">{_e(f["mes"])} · {sub}</div>{filas}</div>')


def _mapa(f) -> str:
    m = f['mapa']
    # Las columnas de mes van un poco más anchas que las de semana
    columnas = '160px ' + ' '.join('minmax(0,1.3fr)' if c['mes'] else 'minmax(0,1fr)' for c in m['cols'])
    abre = f'<div class="ft-fila" style="grid-template-columns:{columnas}">'
    grupos = ''.join(f'<span class="ft-grp{" ft-sel" if g["sel"] else ""}" style="grid-column:span {g["span"]}">{_e(g["titulo"])}</span>'
                     for g in m['grupos'])
    cols = ''.join(f'<span class="ft-col{" ft-m" if c["mes"] else ""}{" ft-sel" if c["sel"] else ""}"><b>{c["t"]}</b>{c["s"]}</span>'
                   for c in m['cols'])
    h = f'{abre}<span></span>{grupos}</div>{abre}<span></span>{cols}</div>'
    for fila in m['filas']:
        if fila['tipo'] == 'titulo':
            h += f'<div class="ft-sep">{fila["lbl"]}</div>'
            continue
        celdas = ''
        for c in fila['celdas']:
            clases = f'ft-c ft-{c["e"]}' + (' ft-m' if c['mes'] else '') + (' ft-sel' if c['sel'] else '')
            if fila['tipo'] == 'ps':
                celdas += (f'<span class="{clases} ft-cps" style="grid-column:span {c["span"]}">'
                           f'<span>{CARA[c["e"]]} {_e(c["t"])}</span><small>{_e(c["s"])}</small></span>')
            else:
                celdas += f'<span class="{clases}{" ft-inc" if c["t"] == "inc." else ""}"><span>{c["t"]}</span><small>{c["s"]}</small></span>'
        h += (f'{abre}<span class="ft-lbl">{ICONO.get(fila["tipo"], "")} {fila["lbl"]}<small>{_e(fila["sub"])}</small></span>'
              f'{celdas}</div>')
    primero, ultimo = m['grupos'][0]['titulo'].split(' · ')[0].lower(), m['grupos'][-1]['titulo'].split(' · ')[0].lower()
    leyenda = ('<div class="ft-ley"><i class="ft-ok"></i>cumple<i class="ft-cer"></i>cerca<i class="ft-mal"></i>abajo'
               '<i class="ft-nd"></i>sin medición</div>')
    return ('<div class="dcard">'
            + tarjeta_titulo('📈 Cómo le ha ido, semana a semana',
                             f'De {primero} a {ultimo} · el mes elegido va marcado en rosa · cámbialo arriba, en Periodo', leyenda)
            + f'<div class="dtw"><div class="ft-mapa">{h}</div></div>'
            '<div class="ft-nota">inc. = semana con incidencia de TRAX: no cuenta para el promedio del mes. El SOS de cada semana '
            'se compara contra el objetivo del mes: cerca = 85% o más. OSA: verde desde 95%, amarillo desde 85%. '
            'Precios va sin semáforo mientras el cliente confirma el precio estrategia.</div></div>')


def _escenas(f, periodo_id) -> str:
    try:
        escenas = kc.exh_detalle_tienda(get_exh_escenas_tienda(periodo_id, f['curt']))
    except Exception as e:
        print(f"[DIRECTOR FICHA ESCENAS] {periodo_id} {f['curt']}: {e}")
        escenas = None
    x = f['cliente']['exh']
    mes = f['mes'].lower()
    titulo = tarjeta_titulo(f'📦 Sus exhibiciones de {mes}',
                            f'{_n(x["exh"])} exhibiciones únicas · {_n(x["cap"])} capturas · cada una con su foto en TRAX'
                            if f['en_maestro'] else 'Sin datos del mes')
    if escenas is None:
        return f'<div class="dcard">{titulo}<div class="dvacio">No se pudieron leer las exhibiciones. Intenta en unos segundos.</div></div>'
    if not escenas:
        return f'<div class="dcard">{titulo}<div class="dvacio">La tienda no tuvo exhibiciones en {mes}.</div></div>'
    filas = ''.join(
        f'<tr><td>{s["fecha"]}</td><td>S{s["semana"]}</td><td class="di">{_e(s["ubicacion"])}</td>'
        f'<td><span class="dt {"dt-y" if s["impacto"] == "Alto" else "dt-b"}">{_e(s["impacto"])}</span></td>'
        f'<td class="di"><span class="dn1">{_e(s["variante"])}</span><span class="dn2">{_e(s["categoria"])}</span></td>'
        f'<td class="di" style="white-space: normal; color: #6B7BB8;">{_e(s["productos"])}</td>'
        f'<td class="dnum">{_n(s["capturas"])}</td><td class="dnum">{_n(s["frentes"])}</td>'
        f'<td><a href="{_e(s["liga"])}" target="_blank" rel="noopener">Ver en TRAX</a></td></tr>' for s in escenas)
    return (f'<div class="dcard">{titulo}'
            '<div class="dtw"><table class="dtab"><tr><th>Fecha</th><th>Sem.</th><th class="di">Ubicación</th><th>Impacto</th>'
            '<th class="di">Producto principal</th><th class="di">Todo lo que trae la exhibición</th><th>Capt.</th><th>Frentes</th>'
            f'<th>Foto</th></tr>{filas}</table></div>'
            '<div class="ft-nota">Ver en TRAX abre la escena; pide tu sesión de TRAX.</div></div>')


# ============================================================
# LA DESCARGA
# ============================================================
def _equipo(pid) -> dict:
    """{ruta: (supervisor, área)} del periodo; vacío si no se pudo leer (la ficha sale sin esos dos datos)."""
    try:
        return get_equipo_rutas(pid)
    except Exception as e:
        print(f"[DIRECTOR FICHA EQUIPO] {pid}: {e}")
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def _excel(curt: str, periodo_id: str, leido: str) -> bytes:
    """La ficha en Excel: una fila por semana y una por mes completo.

    leido = cuándo se leyeron los datos. Va en la llave del caché para que el Excel
    nunca sea más viejo que lo que se ve en pantalla (igual que en director_kpis).
    """
    datos = get_ficha_tienda(curt)
    lista = _lista_periodos(get_periodos_director())
    equipo = {}
    rutas = {str(x.get('periodo_id')): _texto(x.get('ruta')) for x in datos['rt'].to_dict('records')} if len(datos['rt']) else {}
    for pid in fc.ventana([p['pid'] for p in lista], periodo_id):
        sup, area = _equipo(pid).get(rutas.get(pid, ''), (None, None))
        equipo[pid] = (nombre_corto(sup) if _texto(sup) else '', _texto(area))
    tabla = fc.tabla_ficha(curt, lista, periodo_id, datos['rt'], datos['ds'], datos['oos'], datos['exh'], datos['osa'],
                           datos['pre'], equipo=equipo)
    tienda = tabla['Tienda'].iloc[-1] if len(tabla) else curt
    return kc.excel(tabla, 'FICHA', f'Ficha de tienda · {tienda} · CURT {curt} · cada semana y cada mes completo')


def _descarga(curt, periodo_id, leido, mes) -> None:
    try:
        datos = _excel(curt, periodo_id, leido)
    except Exception as e:
        print(f"[DIRECTOR FICHA DESCARGA] {curt}: {e}")
        st.button('Descargar la ficha', key='dirdl_ficha_no', disabled=True, use_container_width=True)
        return
    st.download_button('Descargar la ficha', data=datos, file_name=f'Ficha_{curt}_{mes.lower()}.xlsx', mime=MIME_XLSX,
                       key=f'dirdl_ficha_{curt}_{periodo_id}', on_click='ignore', icon=':material/download:',
                       type='primary', use_container_width=True)


# ============================================================
# LA SECCIÓN
# ============================================================
def ficha(periodos, periodo_id):
    r.html(CSS_FICHA)
    try:
        catalogo = get_catalogo_tiendas()
    except Exception as e:
        # El detalle va al log; al director no se le enseña un traceback.
        print(f"[DIRECTOR FICHA] catálogo: {e}")
        _vacio('No se pudo leer la lista de tiendas en este momento. Intenta en unos segundos.')
        return
    if len(catalogo) == 0:
        _vacio('Todavía no hay tiendas cargadas.')
        return
    catalogo = catalogo.assign(tienda=catalogo['tienda'].map(_texto), cadena=catalogo['cadena'].map(_texto)).sort_values('tienda')
    etiquetas = {c: f'{t} · CURT {c} · {cad}' for c, t, cad in zip(catalogo['curt'], catalogo['tienda'], catalogo['cadena'])}
    if st.session_state.get('dir_ficha_tienda') not in etiquetas:
        st.session_state['dir_ficha_tienda'] = None

    datos = None
    with st.container(border=True, key='dircard_ficha_buscar'):
        a, b = st.columns([3.6, 1], vertical_alignment='bottom')
        with a:
            curt = st.selectbox(f'Busca una tienda · {len(etiquetas):,} en ATLAS', [None] + list(etiquetas), key='dir_ficha_tienda',
                                format_func=lambda c: 'Escribe el nombre, el CURT o la cadena' if c is None else etiquetas[c])
        if curt:
            try:
                datos = get_ficha_tienda(curt)
            except Exception as e:
                print(f"[DIRECTOR FICHA] {curt}: {e}")
        with b:
            if curt and datos is not None:
                _descarga(curt, periodo_id, datos['leido'], _mes(periodos[periodos['periodo_id'] == periodo_id].iloc[0].to_dict()))

    if not curt:
        r.html('<div class="ft-sin"><b>Busca una tienda</b><span>Escribe arriba su nombre, su CURT o su cadena. Sale todo su historial: '
               'si fue Perfect Store, exhibiciones, OSA, precios y encuestas, semana a semana.</span></div>')
        return
    if datos is None:
        _vacio('Todavía no se puede leer el historial de la tienda. Si esta sección se acaba de instalar, falta correr en '
               'Supabase el SQL de la v25 o subir los CSV de csv_director.')
        return

    f = fc.ficha(curt, _lista_periodos(periodos), periodo_id, datos['rt'], datos['ds'], datos['oos'], datos['exh'],
                 datos['osa'], datos['pre'])
    if f is None:
        _vacio('No hay datos de esta tienda.')
        return

    mes = f['mes']
    r.html(_hero(f, _equipo(periodo_id)))
    r.html(f'<div class="ft-tit"><b>Perfect Store</b><span>{_e(mes)} · lo que cuenta para el bono</span></div>'
           f'<div class="ft-g4">{"".join(_kpi(k) for k in f["kpis"])}</div>')
    r.html(f'<div class="ft-tit"><b>Lo que mide el cliente</b><span>{_e(mes)} · exhibiciones, anaquel, precios y encuestas</span></div>'
           + _cliente(f))
    r.html(f'<div class="ft-g32">{_agenda(f)}{_razones(f)}</div>')
    r.html(_mapa(f))
    r.html(_escenas(f, periodo_id))
    r.html('<p class="dpie"><b>Cómo se lee.</b> Arriba va el mes elegido; el mapa trae ese mes y los de junto. Perfect Store, '
           'SOS y exhibiciones en puntos son los del bono, con el mismo veredicto que ve el promotor. Exhibiciones únicas, '
           'capturas, OSA y precios son los de las secciones de este tablero.</p>')
    _pie_dato(f'Datos al cierre de la semana {f["semanas"][-1]}')
