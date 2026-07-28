"""
Módulo de datos — Lee de Supabase (PostgreSQL).

Reemplaza al data.py anterior que leía de Excel local.
Mantiene el MISMO API público para que los componentes no cambien.

Funciones cacheadas con @st.cache_data para minimizar queries.
"""
import streamlit as st
import pandas as pd
from supabase import create_client, Client


# ============================================================
# CLIENTE SUPABASE (singleton)
# ============================================================
@st.cache_resource
def _get_client() -> Client:
    """Crea el cliente Supabase una sola vez por sesión."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)


# ============================================================
# CACHÉ DE PERIODOS
# ============================================================
@st.cache_data(ttl=600)
def listar_periodos() -> pd.DataFrame:
    """Lista todos los periodos disponibles (para el selector)."""
    sb = _get_client()
    r = sb.rpc('listar_periodos', {}).execute()
    return pd.DataFrame(r.data)


def get_periodo_default() -> str:
    """Periodo más reciente (default al cargar)."""
    df = listar_periodos()
    if len(df) == 0:
        return None
    return df.iloc[0]['periodo_id']  # listar_periodos ordena DESC


# ============================================================
# DATOS DEL PROMOTOR
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_resumen_promotor(ruta: str, periodo_id: str) -> dict:
    """KPIs del promotor en un periodo específico."""
    sb = _get_client()
    r = sb.table('kpis_promotor').select('*').eq('ruta', ruta).eq('periodo_id', periodo_id).execute()
    if not r.data:
        return None
    return r.data[0]


@st.cache_data(ttl=300, show_spinner=False)
def get_tiendas_de_ruta(ruta: str, periodo_id: str) -> pd.DataFrame:
    """Tiendas del promotor en un periodo."""
    sb = _get_client()
    r = sb.table('resumen_tienda').select('*').eq('ruta', ruta).eq('periodo_id', periodo_id).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_tiendas_cerca_ps(ruta: str, periodo_id: str, top_n: int = 3) -> pd.DataFrame:
    """Tiendas capturadas que NO son PS aún (oportunidades)."""
    df = get_tiendas_de_ruta(ruta, periodo_id)
    if len(df) == 0:
        return df
    candidatas = df[(df['tienda_visitada'] == True) & (df['es_ps'] == False)]
    return candidatas.head(top_n)


# ============================================================
# DATOS DEL SUPERVISOR
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_resumen_supervisor(supervisor: str, periodo_id: str) -> dict:
    """KPIs del supervisor en un periodo."""
    sb = _get_client()
    r = sb.table('kpis_supervisor').select('*').eq('supervisor', supervisor).eq('periodo_id', periodo_id).execute()
    if not r.data:
        return None
    return r.data[0]


@st.cache_data(ttl=300, show_spinner=False)
def get_promotores_de_supervisor(supervisor: str, periodo_id: str) -> pd.DataFrame:
    """Promotores asignados a un supervisor en un periodo."""
    sb = _get_client()
    r = sb.table('kpis_promotor').select('*').eq('supervisor', supervisor).eq('periodo_id', periodo_id).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()


def get_promotores_cerca_80(supervisor: str, periodo_id: str, top_n: int = 3) -> pd.DataFrame:
    """Promotores del supervisor con %PS entre 60 y 80."""
    df = get_promotores_de_supervisor(supervisor, periodo_id)
    if len(df) == 0:
        return df
    cerca = df[(df['pct_ps_ruta'] >= 60) & (df['pct_ps_ruta'] < 80) & (df['candado_abierto'] == True)]
    return cerca.nlargest(top_n, 'pct_ps_ruta')


def get_mejor_y_peor_promotor(supervisor: str, periodo_id: str):
    """Retorna (mejor, peor) por bono_final_pct."""
    df = get_promotores_de_supervisor(supervisor, periodo_id)
    if len(df) == 0:
        return None, None
    mejor = df.nlargest(1, 'bono_final_pct').iloc[0].to_dict()
    peor = df.nsmallest(1, 'bono_final_pct').iloc[0].to_dict()
    return mejor, peor


# ============================================================
# DETALLE DE TIENDA
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_detalle_tienda(curt: str, periodo_id: str) -> pd.DataFrame:
    """Detalle semanal de una tienda en un periodo."""
    sb = _get_client()
    r = sb.table('detalle_semanal').select('*').eq('curt', str(curt)).eq('periodo_id', periodo_id).order('semana').execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_tienda_info(curt: str, periodo_id: str) -> dict:
    """Info de la tienda (1 fila de resumen_tienda)."""
    sb = _get_client()
    r = sb.table('resumen_tienda').select('*').eq('curt', str(curt)).eq('periodo_id', periodo_id).execute()
    if not r.data:
        return None
    return r.data[0]


# ============================================================
# ADAPTADORES — Convertir nombres viejos del Excel a snake_case del Supabase
# ============================================================
# Los componentes esperan claves como 'CANDADO_ABIERTO', 'BONO_FINAL_PCT', etc.
# Pero Supabase guarda 'candado_abierto', 'bono_final_pct'. Mapeo aquí:

MAPEO_PROMOTOR = {
    'CANDADO_ABIERTO': 'candado_abierto',
    'BONO_POTENCIAL_PCT': 'bono_potencial_pct',
    'BONO_FINAL_PCT': 'bono_final_pct',
    'PCT_PS_RUTA': 'pct_ps_ruta',
    'MULT_OOS_PCT': 'mult_oos_pct',
    'EFECTIVIDAD_PCT': 'efectividad_pct',
    'VISITAS_FALTANTES_95': 'visitas_faltantes_95',
    'TIENDAS_CAPTURADAS': 'tiendas_capturadas',
    'TIENDAS_TOTALES': 'tiendas_totales',
    'TIENDAS_ELEGIBLES': 'tiendas_elegibles',
    'PS_ELEGIBLES': 'ps_elegibles',
    'PS_BONUS_MAYO_DEPTO': 'ps_bonus_mayo_depto',
    'OBJ_OOS': 'obj_oos',
    'NO_CONT_OOS': 'no_cont_oos',
    'VISITAS_PROGRAMADAS': 'visitas_programadas',
    'VISITAS_NORMALES': 'visitas_normales',
    'VISITAS_INCIDENCIA': 'visitas_incidencia',
    'SOS_WHISKY_PROM': 'sos_whisky_prom',
    'SOS_TEQUILA_PROM': 'sos_tequila_prom',
    'SOS_VODKA_PROM': 'sos_vodka_prom',
    'EXH_4_PROM': 'exh_4_prom',
    'RUTA': 'ruta',
    'AREA_MANAGER': 'area_manager',
    'EJECUTIVO': 'ejecutivo',
    'SUPERVISOR': 'supervisor',
    'PCT_PAGO': 'pct_pago',
}

MAPEO_SUPERVISOR = dict(MAPEO_PROMOTOR)  # mismo mapping
MAPEO_SUPERVISOR.update({
    'PCT_PS': 'pct_ps',
    'RUTAS_A_CARGO': 'rutas_a_cargo',
    'TIENDAS_MAYO_DEPTO': 'tiendas_mayo_depto',
    'TOPE_PCT': 'tope_pct',
    'BONO_CRUDO_PCT': 'bono_crudo_pct',
})


def adaptar_promotor(row: dict) -> dict:
    """Crea un dict con ambas versiones de claves (snake_case + MAYÚSCULA) para compat."""
    if row is None:
        return None
    out = dict(row)
    for vieja, nueva in MAPEO_PROMOTOR.items():
        if nueva in row:
            out[vieja] = row[nueva]
    return out


def adaptar_supervisor(row: dict) -> dict:
    if row is None:
        return None
    out = dict(row)
    for vieja, nueva in MAPEO_SUPERVISOR.items():
        if nueva in row:
            out[vieja] = row[nueva]
    return out


def adaptar_tiendas(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra columnas snake_case a estilo Excel (TItleCase) para compatibilidad."""
    if len(df) == 0:
        return df
    df = df.rename(columns={
        'curt': 'Store Number',
        'ruta': 'Ruta',
        'tienda': 'Tienda',
        'canal': 'CANAL',
        'cadena': 'Cadena',
        'sos_whisky': 'Total Whisky',
        'sos_tequila': 'Total tequila',
        'sos_vodka': 'Total vodka',
        'exh_puntos': 'Puntos Promedio Exhibición',
        'tienda_visitada': 'Tienda Visitada',
        'es_ps': 'PS FINAL',
        'cumplio_4': 'CUMPLIO 4',
        'obj_whisky': 'Objetivo Whisky',
        'obj_tequila': 'Objetivo Tequila',
        'obj_vodka': 'Objetivo Vodka',
        'obj_exh': 'Objetivo Puntos HS',
    })
    # Las columnas que esperan los componentes
    if 'Tienda Visitada' in df.columns:
        df['Tienda Visitada'] = df['Tienda Visitada'].astype(int)
    if 'PS FINAL' in df.columns:
        df['PS FINAL'] = df['PS FINAL'].astype(int)
    # SOS vienen en escala 0-100 desde Supabase, los componentes esperan 0-1
    for c in ['Total Whisky', 'Total tequila', 'Total vodka']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce') / 100.0
    return df


def adaptar_detalle(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra columnas del detalle semanal."""
    if len(df) == 0:
        return df
    df = df.rename(columns={
        'curt': 'Store Number',
        'ruta': 'Ruta',
        'tienda': 'Tienda',
        'cadena': 'Cadena',
        'canal': 'CANAL',
        'semana': 'Semana',
        'incidencia': 'Incidencia',
        'sos_whisky': 'Total Whisky',
        'sos_tequila': 'Total tequila',
        'sos_vodka': 'Total vodka',
        'exh_puntos': 'Puntos Promedio Exhibición',
        'exh_w_ai': 'EXH AI W',
        'exh_w_bi': 'EXH BI W',
        'exh_t_ai': 'EXH AI T',
        'exh_t_bi': 'EXH BI T',
        'exh_v_ai': 'EXH AI V',
        'exh_v_bi': 'EXH BI V',
        'cumplio_2': 'CUMPLIO 2',
        'cumplio_4': 'CUMPLIO 4',
        'obj_whisky': 'Objetivo Whisky',
        'obj_tequila': 'Objetivo Tequila',
        'obj_vodka': 'Objetivo Vodka',
        'obj_exh': 'Objetivo Puntos HS',
    })
    if 'Incidencia' in df.columns:
        df['Incidencia'] = df['Incidencia'].astype(int)
    for c in ['Total Whisky', 'Total tequila', 'Total vodka']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce') / 100.0
    return df


@st.cache_data(ttl=300)
def get_periodo_descripcion(periodo_id: str) -> str:
    """Devuelve la descripción del periodo (ej. 'Mayo 2026 (semanas 18-19)')."""
    if not periodo_id:
        return ""
    sb = _get_client()
    r = sb.table('periodos').select('descripcion, mes, semana_inicio, semana_fin').eq('periodo_id', periodo_id).limit(1).execute()
    if not r.data:
        return periodo_id
    row = r.data[0]
    return row.get('descripcion') or f"{row.get('mes','')} (S{row.get('semana_inicio','')} - S{row.get('semana_fin','')})"


def get_periodo_corto(periodo_id: str) -> str:
    """Devuelve solo el mes (ej. 'Mayo')."""
    if not periodo_id:
        return ""
    sb = _get_client()
    r = sb.table('periodos').select('mes').eq('periodo_id', periodo_id).limit(1).execute()
    if not r.data:
        return periodo_id
    return r.data[0].get('mes', '')


# ============================================================
# OOS POR TIENDA  (v9 — tabla oos_tienda)
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_oos_tienda(curt: str, periodo_id: str) -> dict:
    """OOS de UNA tienda en el periodo (obj, contestadas, no contestadas).
    Devuelve None si la tienda no tiene objetivo OOS o la tabla no existe."""
    try:
        sb = _get_client()
        r = sb.table('oos_tienda').select('*').eq('curt', str(curt)).eq('periodo_id', periodo_id).limit(1).execute()
        if not r.data:
            return None
        return r.data[0]
    except Exception as e:
        print(f"[OOS_TIENDA ERROR] {e}")
        return None


# ============================================================
# DATOS DEL AREA MANAGER  (v9)
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_supervisores_de_am(area_manager: str, periodo_id: str) -> pd.DataFrame:
    """Supervisores del AM en un periodo (desde kpis_supervisor)."""
    sb = _get_client()
    r = sb.table('kpis_supervisor').select('*').eq('area_manager', area_manager).eq('periodo_id', periodo_id).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_promotores_de_am(area_manager: str, periodo_id: str) -> pd.DataFrame:
    """Todos los promotores del AM en un periodo (desde kpis_promotor)."""
    sb = _get_client()
    r = sb.table('kpis_promotor').select('*').eq('area_manager', area_manager).eq('periodo_id', periodo_id).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()


def get_resumen_am(area_manager: str, periodo_id: str) -> dict:
    """KPIs agregados del área, calculados desde los promotores del AM.
    Misma lógica que el bono: %PS = (PS elegibles + bonus) / capturadas;
    OOS = 1 - (no_cont / obj) agregado."""
    df_p = get_promotores_de_am(area_manager, periodo_id)
    df_s = get_supervisores_de_am(area_manager, periodo_id)
    if len(df_p) == 0:
        return None

    capturadas = int(df_p['tiendas_capturadas'].fillna(0).sum())
    ps_total = int(df_p['ps_elegibles'].fillna(0).sum() + df_p['ps_bonus_mayo_depto'].fillna(0).sum())
    pct_ps = min(ps_total / capturadas * 100, 100.0) if capturadas > 0 else 0.0

    obj_oos = int(df_p['obj_oos'].fillna(0).sum())
    no_cont = int(df_p['no_cont_oos'].fillna(0).sum())
    mult_oos = max(0.0, (1 - no_cont / obj_oos) * 100) if obj_oos > 0 else 100.0

    promotores_cobran = int(((df_p['candado_abierto'] == True) & (df_p['pct_ps_ruta'] >= 1)).sum())
    sup_abiertos = int((df_s['candado_abierto'] == True).sum()) if len(df_s) > 0 else 0

    # v9.1: % promedio de cobro (bono final) — incluye los que van en 0 por candado
    bono_prom_promo = float(pd.to_numeric(df_p['bono_final_pct'], errors='coerce').fillna(0).mean())
    bono_prom_sup = float(pd.to_numeric(df_s['bono_final_pct'], errors='coerce').fillna(0).mean()) if len(df_s) > 0 else 0.0

    return {
        'AREA_MANAGER': area_manager,
        'N_SUPERVISORES': len(df_s),
        'N_PROMOTORES': len(df_p),
        'TIENDAS_TOTALES': int(df_p['tiendas_totales'].fillna(0).sum()),
        'TIENDAS_ELEGIBLES': int(df_p['tiendas_elegibles'].fillna(0).sum()),
        'TIENDAS_CAPTURADAS': capturadas,
        'PS_TOTAL': ps_total,
        'PCT_PS': round(pct_ps, 2),
        'OBJ_OOS': obj_oos,
        'NO_CONT_OOS': no_cont,
        'MULT_OOS_PCT': round(mult_oos, 2),
        'BONO_PROM_SUPERVISORES': round(bono_prom_sup, 2),
        'BONO_PROM_PROMOTORES': round(bono_prom_promo, 2),
        'PROMOTORES_COBRAN': promotores_cobran,
        'PROMOTORES_NO_COBRAN': len(df_p) - promotores_cobran,
        'SUP_CANDADO_ABIERTO': sup_abiertos,
        'SUP_CANDADO_CERRADO': len(df_s) - sup_abiertos,
    }


@st.cache_data(ttl=300, show_spinner=False)
def get_oos_tienda_semana(curt: str, periodo_id: str) -> pd.DataFrame:
    """v9.2: OOS de UNA tienda desglosado por semana (obj, contestadas, no cont).
    DataFrame vacío si no hay datos o la tabla no existe."""
    try:
        sb = _get_client()
        r = sb.table('oos_tienda_semana').select('*').eq('curt', str(curt)).eq('periodo_id', periodo_id).order('semana').execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except Exception as e:
        print(f"[OOS_TIENDA_SEMANA ERROR] {e}")
        return pd.DataFrame()
