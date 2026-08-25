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
    # v15: lo usa la guía "cómo se calcula mi bono" para explicar de dónde
    # sale el denominador (totales = elegibles + mayo/depto).
    'TIENDAS_MAYO_DEPTO': 'tiendas_mayo_depto',
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


# ============================================================
# INCIDENCIAS  (v10)
# ============================================================
import io
import uuid as _uuid
from datetime import datetime as _dt


def _comprimir_foto(file_bytes: bytes, max_lado: int = 1280, calidad: int = 72) -> bytes:
    """Comprime y redimensiona una foto para subirla ligera (celular con datos móviles).
    Devuelve JPEG. Si Pillow no está o falla, devuelve los bytes originales."""
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(file_bytes))
        img = ImageOps.exif_transpose(img)          # respeta orientación del celular
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        img.thumbnail((max_lado, max_lado))          # mantiene proporción
        out = io.BytesIO()
        img.save(out, format='JPEG', quality=calidad, optimize=True)
        return out.getvalue()
    except Exception as e:
        print(f"[COMPRIMIR_FOTO WARN] {e}")
        return file_bytes


def subir_foto_incidencia(file_bytes: bytes, ruta: str, curt: str) -> str:
    """Comprime y sube una foto al bucket PÚBLICO 'incidencias'.
    Devuelve la URL pública permanente (clicable en el CSV)."""
    sb = _get_client()
    comprimida = _comprimir_foto(file_bytes)
    stamp = _dt.now().strftime('%Y%m%d_%H%M%S')
    nombre = f"{ruta}/{curt}_{stamp}_{_uuid.uuid4().hex[:8]}.jpg"
    sb.storage.from_('incidencias').upload(
        nombre, comprimida, {'content-type': 'image/jpeg', 'upsert': 'false'}
    )
    # URL pública permanente
    return sb.storage.from_('incidencias').get_public_url(nombre)


def guardar_incidencia(curt: str, ruta: str, periodo_id: str, tipo: str,
                       semana: int, comentario: str, fotos_paths: list,
                       reportada_por: str, tienda: str = None,
                       cadena: str = None, canal: str = None,
                       link_trax: str = None, incidencia: str = None,
                       categoria: str = None, productos: list = None) -> bool:
    """Inserta una incidencia. fotos_paths: lista de 1 a 3 rutas de Storage.
    La incidencia nace en estado PENDIENTE (default de la tabla).

    v13: 'tipo' es el KPI afectado; 'incidencia' es el motivo específico.
    'categoria' y 'productos' solo se llenan cuando el motivo es de producto
    (no reconocido / reconocido incorrectamente). productos=['TODOS'] significa
    toda la categoría."""
    sb = _get_client()
    registro = {
        'curt': str(curt), 'ruta': ruta, 'periodo_id': periodo_id,
        'tienda': tienda, 'cadena': cadena, 'canal': canal,
        'tipo': tipo, 'semana': int(semana) if semana is not None else None,
        'comentario': comentario, 'fotos': fotos_paths,
        'reportada_por': reportada_por, 'link_trax': link_trax,
        'incidencia': incidencia, 'categoria': categoria,
        'productos': productos or None,
    }
    sb.table('incidencias').insert(registro).execute()
    return True


# ============================================================
# CATÁLOGO DE PRODUCTOS  (v13, tabla productos)
# ============================================================
@st.cache_data(ttl=1800, show_spinner=False)
def get_productos(kpi: str = None, categoria: str = None) -> pd.DataFrame:
    """v14: SKUs activos que aplican al KPI indicado.

    Cada KPI mide un universo distinto, por eso el catálogo trae una bandera
    por KPI en vez de una sola lista:
      OOS          -> aplica_oos  (91: todo lo que sale en los archivos OOS)
      EXHIBICIONES -> aplica_exh  (113: whisky+tequila+vodka+Baileys+Zacapa)
      SOS *        -> aplica_sos filtrado por la categoría del KPI

    DataFrame vacío si la tabla todavía no existe (la app degrada sin romperse).
    """
    try:
        sb = _get_client()
        q = sb.table('productos').select('categoria, producto, marca').eq('activo', True)
        if kpi == 'OOS':
            q = q.eq('aplica_oos', True)
        elif kpi == 'EXHIBICIONES':
            q = q.eq('aplica_exh', True)
        elif kpi and str(kpi).startswith('SOS'):
            q = q.eq('aplica_sos', True)
        if categoria:
            q = q.eq('categoria', str(categoria).upper())
        r = q.order('producto').execute()
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except Exception as e:
        print(f"[PRODUCTOS ERROR] {e}")
        return pd.DataFrame()


def resolver_incidencia(incidencia_id: int, autorizar: bool, resuelta_por: str,
                        motivo_rechazo: str = None) -> bool:
    """v11: el supervisor autoriza o rechaza una incidencia.
    autorizar=True → AUTORIZADA; False → NO_AUTORIZADA."""
    from datetime import datetime as _dt2
    sb = _get_client()
    registro = {
        'estado': 'AUTORIZADA' if autorizar else 'NO_AUTORIZADA',
        'resuelta_por': resuelta_por,
        'resuelta_en': _dt2.now().isoformat(),
        'motivo_rechazo': (motivo_rechazo or None) if not autorizar else None,
    }
    sb.table('incidencias').update(registro).eq('id', int(incidencia_id)).execute()
    return True


@st.cache_data(ttl=60, show_spinner=False)
def get_incidencias_de_tienda(curt: str, periodo_id: str) -> pd.DataFrame:
    """Incidencias ya reportadas en una tienda (para mostrarlas en el detalle)."""
    sb = _get_client()
    r = sb.table('incidencias').select('*').eq('curt', str(curt)).eq('periodo_id', periodo_id).order('created_at', desc=True).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()


def get_incidencias_periodo(periodo_id: str, area_manager: str = None,
                            supervisor: str = None, ruta: str = None) -> pd.DataFrame:
    """Todas las incidencias del periodo, con filtro opcional por ámbito.
    Se usa para el export a Excel."""
    sb = _get_client()
    q = sb.table('incidencias').select('*').eq('periodo_id', periodo_id)
    if ruta:
        q = q.eq('ruta', ruta)
    r = q.order('created_at', desc=True).execute()
    df = pd.DataFrame(r.data) if r.data else pd.DataFrame()
    if len(df) == 0:
        return df
    # Filtros por supervisor/AM: mapear vía kpis_promotor (ruta -> supervisor/am)
    if (supervisor or area_manager):
        kp = get_promotores_de_supervisor(supervisor, periodo_id) if supervisor \
             else get_promotores_de_am(area_manager, periodo_id)
        rutas_validas = set(kp['ruta'].tolist()) if len(kp) > 0 else set()
        df = df[df['ruta'].isin(rutas_validas)]
    return df


def firmar_url_foto(path_o_url: str, expira_seg: int = 3600) -> str:
    """Bucket público: la foto ya es una URL directa; se devuelve tal cual.
    (Se mantiene la firma de la función por compatibilidad con la bandeja.)"""
    if not path_o_url:
        return ''
    if str(path_o_url).startswith('http'):
        return path_o_url
    # fallback: si por alguna razón llega un path, construir URL pública
    try:
        sb = _get_client()
        return sb.storage.from_('incidencias').get_public_url(path_o_url)
    except Exception as e:
        print(f"[URL_FOTO WARN] {e}")
        return ''


def get_incidencias_ambito(periodo_id: str, area_manager: str = None,
                           supervisor: str = None) -> pd.DataFrame:
    """Incidencias del periodo filtradas por ámbito (para la bandeja visual).
    AM ve las de todos sus promotores; supervisor las de los suyos."""
    return get_incidencias_periodo(periodo_id, area_manager=area_manager, supervisor=supervisor)


@st.cache_data(ttl=60, show_spinner=False)
def get_conteo_incidencias_ruta(ruta: str, periodo_id: str) -> dict:
    """v12: Cuántas incidencias levantó ESTE promotor en la app, por estado y por tipo.
    Solo conteos (la autorización sigue viviendo en la bandeja del supervisor)."""
    vacio = {'TOTAL': 0, 'PENDIENTES': 0, 'AUTORIZADAS': 0, 'NO_AUTORIZADAS': 0, 'POR_TIPO': {}}
    try:
        sb = _get_client()
        r = sb.table('incidencias').select('estado, tipo').eq('ruta', ruta).eq('periodo_id', periodo_id).execute()
        if not r.data:
            return vacio
        df = pd.DataFrame(r.data)
        estados = df['estado'].fillna('PENDIENTE') if 'estado' in df.columns else pd.Series(dtype=str)
        return {
            'TOTAL': int(len(df)),
            'PENDIENTES': int((estados == 'PENDIENTE').sum()),
            'AUTORIZADAS': int((estados == 'AUTORIZADA').sum()),
            'NO_AUTORIZADAS': int((estados == 'NO_AUTORIZADA').sum()),
            'POR_TIPO': df['tipo'].value_counts().to_dict() if 'tipo' in df.columns else {},
        }
    except Exception as e:
        print(f"[CONTEO_INCIDENCIAS ERROR] {e}")
        return vacio


# ============================================================
# OOS — RESPUESTAS POR MOTIVO  (v12, tabla oos_respuestas)
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def get_oos_respuestas_ruta(ruta: str, periodo_id: str) -> pd.DataFrame:
    """v12: Cuántas veces contestó cada motivo de OOS esta ruta en el periodo.
    Una fila por (semana, motivo) con el conteo. El motivo 'SIN CONTESTAR' agrupa
    las que el promotor dejó sin responder (las que castigan el multiplicador).

    Devuelve DataFrame vacío si la tabla todavía no existe en Supabase, para que
    la pantalla siga funcionando sin el bloque (mismo patrón que get_oos_tienda)."""
    try:
        sb = _get_client()
        r = (sb.table('oos_respuestas').select('*')
             .eq('ruta', ruta).eq('periodo_id', periodo_id)
             .order('semana').execute())
        return pd.DataFrame(r.data) if r.data else pd.DataFrame()
    except Exception as e:
        print(f"[OOS_RESPUESTAS ERROR] {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_oos_ruta_por_semana(ruta: str, periodo_id: str) -> pd.DataFrame:
    """v12: OOS de TODA la ruta agregado por semana (suma de sus tiendas).
    Se arma desde oos_tienda_semana, que ya trae la columna ruta."""
    try:
        sb = _get_client()
        r = (sb.table('oos_tienda_semana')
             .select('semana, obj_oos, contestadas_oos, no_cont_oos')
             .eq('ruta', ruta).eq('periodo_id', periodo_id).execute())
        if not r.data:
            return pd.DataFrame()
        df = pd.DataFrame(r.data)
        agg = df.groupby('semana', as_index=False)[['obj_oos', 'contestadas_oos', 'no_cont_oos']].sum()
        agg['pct_contestadas'] = agg.apply(
            lambda x: (x['contestadas_oos'] / x['obj_oos'] * 100) if x['obj_oos'] > 0 else None, axis=1
        )
        return agg.sort_values('semana')
    except Exception as e:
        print(f"[OOS_RUTA_SEMANA ERROR] {e}")
        return pd.DataFrame()
