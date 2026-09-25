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


def comprimir_foto(file_bytes: bytes, max_lado: int = 1280, calidad: int = 72) -> bytes:
    """Comprime y redimensiona una foto para subirla ligera (celular con datos móviles).
    Devuelve JPEG. Si Pillow no está o falla, devuelve los bytes originales.

    v22: se llama al AGREGAR la foto al formulario, no solo al guardar, para que
    la sesión no cargue fotos de 10 MB. Si la foto ya viene como JPG del tamaño
    final y derecha (la galería nueva la manda así desde el celular), se deja
    igual para no comprimirla dos veces."""
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(file_bytes))
        if (img.format == 'JPEG' and max(img.size) <= max_lado and len(file_bytes) <= 600_000
                and img.getexif().get(0x0112, 1) == 1):
            return file_bytes
        if img.format == 'JPEG':
            img.draft('RGB', (max_lado, max_lado))   # la decodifica ya reducida: rápido y sin memoria de más
        img = ImageOps.exif_transpose(img)          # respeta orientación del celular
        if img.mode in ('RGBA', 'LA', 'P'):
            rgba = img.convert('RGBA')              # lo transparente queda blanco, no negro
            fondo = Image.new('RGB', rgba.size, (255, 255, 255))
            fondo.paste(rgba, mask=rgba.split()[-1])
            img = fondo
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((max_lado, max_lado))          # mantiene proporción
        out = io.BytesIO()
        img.save(out, format='JPEG', quality=calidad, optimize=True)
        return out.getvalue()
    except Exception as e:
        print(f"[COMPRIMIR_FOTO WARN] {e}")
        return file_bytes


_comprimir_foto = comprimir_foto   # el nombre de antes, por si algo lo sigue llamando así


def subir_foto_incidencia(file_bytes: bytes, ruta: str, curt: str) -> str:
    """Comprime y sube una foto al bucket PÚBLICO 'incidencias'.
    Devuelve la URL pública permanente (clicable en el CSV)."""
    sb = _get_client()
    comprimida = comprimir_foto(file_bytes)
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
# BORRADOR DE INCIDENCIA  (v18)
#
# El formulario a medio llenar vivía solo en la memoria del servidor: si el
# celular descartaba la pestaña mientras el promotor iba por el link de Trax,
# regresaba con todo en blanco. Estas tres funciones guardan el avance.
#
# Ninguna se cachea a propósito: un borrador cambia todo el tiempo y un valor
# viejo en caché sería justo lo contrario de lo que se busca.
#
# Las tres tragan sus errores. Perder un borrador es una molestia; tirar el
# formulario mientras alguien lo llena es un problema de verdad.
# ============================================================
def get_borrador(username: str, curt: str) -> dict:
    """El avance guardado de este promotor en esta tienda, o None."""
    try:
        sb = _get_client()
        r = (sb.table('incidencias_borrador')
               .select('datos, periodo_id')
               .eq('username', username).eq('curt', str(curt))
               .limit(1).execute())
        return r.data[0] if r.data else None
    except Exception as e:
        print(f"[BORRADOR GET] {e}")
        return None


def guardar_borrador(username: str, curt: str, periodo_id: str, datos: dict) -> bool:
    """Guarda o pisa el avance. Una fila por promotor y tienda."""
    try:
        sb = _get_client()
        sb.table('incidencias_borrador').upsert({
            'username': username,
            'curt': str(curt),
            'periodo_id': periodo_id,
            'datos': datos,
            'guardado_at': _dt.now().isoformat(),
        }, on_conflict='username,curt').execute()
        return True
    except Exception as e:
        print(f"[BORRADOR SET] {e}")
        return False


def borrar_borrador(username: str, curt: str) -> bool:
    """Tira el borrador. Se llama al guardar la incidencia y al cancelar."""
    try:
        sb = _get_client()
        (sb.table('incidencias_borrador').delete()
           .eq('username', username).eq('curt', str(curt)).execute())
        return True
    except Exception as e:
        print(f"[BORRADOR DEL] {e}")
        return False


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


# ============================================================
# TABLERO DEL DIRECTOR  (v20)
#
# El director ve las 4 áreas juntas, y eso choca con un límite que el resto de
# la app nunca toca: la API de Supabase regresa como máximo N filas por
# consulta (1,000 de fábrica) y NO avisa cuando se queda corta. Un promotor
# pide 6 tiendas; el director pide 4,000 respuestas OOS de un solo mes. Sin
# paginar, el tablero enseñaría números incompletos sin ningún error.
#
# v20.1 — velocidad. La primera versión pedía todo en fila (40 consultas, una
# tras otra) y guardaba la caché 5 minutos. Ahora:
#   - La primera tanda de cada tabla pide también el CONTEO total. Con él se
#     sabe cuántas tandas faltan y se piden todas a la vez.
#   - Las tablas de un mismo periodo se piden al mismo tiempo (_leer_varios).
#   - De oos_respuestas solo se lee el periodo y los 3 anteriores: es lo que
#     cubre la ventana de 9 semanas. Antes se leía la historia completa, que
#     crece cada mes. Cada mes se guarda aparte (_OOS_MES), así septiembre y
#     agosto no leen julio cada uno por su lado; y los meses que faltan se
#     piden en el mismo lote paralelo que el resto de las tablas.
#   - Los datos de la corrida viven 1 hora en caché (solo cambian cuando se
#     sube una corrida nueva, y para eso está el botón "Actualizar datos").
#     Incidencias y accesos siguen en 2 minutos: esos cambian todo el día.
#
# Sigue sin fiarse de "llegaron menos de 1,000, ya acabé": si el conteo no
# llega o no cuadra, se completa a la antigua, tanda por tanda hasta una vacía.
#
# Los cálculos viven en director_calc.py (pandas puro, sin Streamlit). Aquí
# solo se lee y se cachea.
# ============================================================
import threading
import time
from concurrent.futures import ThreadPoolExecutor

_TANDA = 1000
_HILOS_TANDAS = 4       # tandas de una misma tabla a la vez
_HILOS_TABLAS = 5       # tablas a la vez
TTL_CORRIDA = 3600      # datos que solo cambian cuando se sube una corrida
TTL_VIVO = 120          # incidencias y accesos
PERIODOS_OOS_ATRAS = 3  # periodos anteriores que se leen de oos_respuestas
COLUMNAS_TIENDA_DIRECTOR = ('ruta, canal, tienda_visitada, es_ps, sos_whisky, sos_tequila, '
                            'sos_vodka, obj_whisky, obj_tequila, obj_vodka, cumplio_4')
COLUMNAS_OOS_DIRECTOR = 'ruta, periodo_id, semana, motivo, veces'

# Respuestas OOS por mes: periodo_id -> (cuándo se leyó, DataFrame). Vive en el
# proceso, igual que st.cache_data, y dura lo mismo que los datos de la corrida.
_OOS_MES = {}
_OOS_CANDADO = threading.Lock()


def _leer_todo(tabla: str, columnas: str = '*', eq: dict = None, gte: dict = None,
               en: dict = None, sb=None) -> pd.DataFrame:
    """Toda la tabla (con filtros) sin importar el límite de filas de la API.

    Ordena por id para que las tandas no se encimen ni se salten filas.
    sb se pasa cuando esto corre en un hilo: el cliente se saca antes, en el
    hilo de Streamlit.
    """
    sb = sb or _get_client()

    def pedir(desde, contar=False):
        q = sb.table(tabla).select(columnas, count='exact') if contar else sb.table(tabla).select(columnas)
        for campo, valor in (eq or {}).items():
            q = q.eq(campo, valor)
        for campo, valor in (gte or {}).items():
            q = q.gte(campo, valor)
        for campo, valores in (en or {}).items():
            q = q.in_(campo, list(valores))
        return q.order('id').range(desde, desde + _TANDA - 1).execute()

    primera = pedir(0, contar=True)
    filas = list(primera.data or [])
    total = getattr(primera, 'count', None)

    if total is not None and filas and len(filas) < total:
        # El tamaño real de tanda es lo que llegó: si el panel tiene un tope
        # menor que 1,000, se respeta sin saltarse filas.
        paso = len(filas)
        with ThreadPoolExecutor(max_workers=_HILOS_TANDAS) as ex:
            for lote in ex.map(lambda d: pedir(d).data or [], range(paso, total, paso)):
                filas.extend(lote)

    if total is None or len(filas) < total:
        # Sin conteo, o el conteo no cuadró (entró algo mientras se leía):
        # se sigue a la antigua hasta una tanda vacía.
        while filas or total is None:
            lote = pedir(len(filas)).data or []
            if not lote:
                break
            filas.extend(lote)
    return pd.DataFrame(filas)


def _leer_varios(consultas: dict) -> dict:
    """Varias tablas al mismo tiempo. consultas = {nombre: (tabla, columnas, filtros)}."""
    sb = _get_client()
    with ThreadPoolExecutor(max_workers=_HILOS_TABLAS) as ex:
        futuros = {nombre: ex.submit(_leer_todo, tabla, columnas, sb=sb, **filtros)
                   for nombre, (tabla, columnas, filtros) in consultas.items()}
        return {nombre: f.result() for nombre, f in futuros.items()}


@st.cache_data(ttl=TTL_CORRIDA, show_spinner=False)
def get_periodos_director() -> pd.DataFrame:
    """Periodos del más viejo al más nuevo, con sus semanas."""
    sb = _get_client()
    r = sb.table('periodos').select('*').order('fecha_inicio').execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()


def _contexto_periodo(periodo_id: str):
    """(fila del periodo, lista ordenada de periodos, periodo más reciente)."""
    periodos = get_periodos_director()
    fila = periodos[periodos['periodo_id'] == periodo_id]
    if len(fila) == 0:
        return None, [], None
    ids = periodos['periodo_id'].tolist()
    return fila.iloc[0].to_dict(), ids, ids[-1]


@st.cache_data(ttl=TTL_CORRIDA, show_spinner=False)
def get_tablero_director(periodo_id: str) -> dict:
    """Todo lo que el tablero pinta de UN periodo, ya calculado.

    Las áreas se agrupan con el maestro del periodo más reciente (ver
    director_calc). Las incidencias NO van aquí: cambian todo el día y se
    pegan al pintar, con su propia caché corta.
    """
    import director_calc as dc

    fila, ids, reciente = _contexto_periodo(periodo_id)
    if fila is None:
        return None
    pos = ids.index(periodo_id)
    del_periodo = {'eq': {'periodo_id': periodo_id}}
    consultas = {
        'kp': ('kpis_promotor', '*', del_periodo),
        'ks': ('kpis_supervisor', '*', del_periodo),
        'rt': ('resumen_tienda', COLUMNAS_TIENDA_DIRECTOR, del_periodo),
    }
    if reciente != periodo_id:
        consultas['kp_reciente'] = ('kpis_promotor', 'ruta, supervisor, area_manager', {'eq': {'periodo_id': reciente}})
    # Los meses de OOS que ya se tienen no se vuelven a pedir; los que faltan
    # viajan en el mismo lote que las otras tablas.
    meses_oos = ids[max(0, pos - PERIODOS_OOS_ATRAS): pos + 1]
    ahora = time.time()
    with _OOS_CANDADO:
        guardados = {m: df for m, (cuando, df) in _OOS_MES.items()
                     if m in meses_oos and ahora - cuando < TTL_CORRIDA}
    for m in meses_oos:
        if m not in guardados:
            consultas[f'oos:{m}'] = ('oos_respuestas', COLUMNAS_OOS_DIRECTOR, {'eq': {'periodo_id': m}})
    t = _leer_varios(consultas)
    with _OOS_CANDADO:
        for m in meses_oos:
            if f'oos:{m}' in t:
                _OOS_MES[m] = (ahora, t[f'oos:{m}'])
    if len(t['kp']) == 0:
        return None

    ruta_area, sup_area = dc.mapa_areas(t.get('kp_reciente', t['kp']))
    ventana = [t[f'oos:{m}'] if f'oos:{m}' in t else guardados[m] for m in meses_oos]
    ventana = [v for v in ventana if len(v)]
    orr = dc.preparar_respuestas(pd.concat(ventana, ignore_index=True) if ventana else pd.DataFrame(),
                                 ruta_area, orden_periodos=ids)
    P = dc.tablero_periodo(fila, t['kp'], t['ks'], t['rt'], orr, ruta_area, sup_area)
    P['leido'] = pd.Timestamp.now(tz='UTC').isoformat()
    return P


@st.cache_data(ttl=TTL_CORRIDA, show_spinner=False)
def get_resumen_director(periodo_id: str) -> dict:
    """Solo país y áreas de un periodo: lo que usa la gráfica de tendencia."""
    import director_calc as dc

    fila, ids, reciente = _contexto_periodo(periodo_id)
    if fila is None:
        return None
    del_periodo = {'eq': {'periodo_id': periodo_id}}
    consultas = {
        'kp': ('kpis_promotor', '*', del_periodo),
        'rt': ('resumen_tienda', COLUMNAS_TIENDA_DIRECTOR, del_periodo),
    }
    if reciente != periodo_id:
        consultas['kp_reciente'] = ('kpis_promotor', 'ruta, supervisor, area_manager', {'eq': {'periodo_id': reciente}})
    t = _leer_varios(consultas)
    if len(t['kp']) == 0:
        return None
    ruta_area, _ = dc.mapa_areas(t.get('kp_reciente', t['kp']))
    return dc.resumen_ligero(fila, t['kp'], t['rt'], ruta_area)


@st.cache_data(ttl=TTL_VIVO, show_spinner=False)
def get_incidencias_director(periodo_id: str) -> pd.DataFrame:
    """Incidencias del periodo, sin fotos ni comentarios: solo lo que se cuenta."""
    try:
        return _leer_todo('incidencias', 'ruta, tipo, incidencia, estado, created_at, resuelta_en',
                          eq={'periodo_id': periodo_id})
    except Exception as e:
        print(f"[DIRECTOR INCIDENCIAS] {e}")
        return pd.DataFrame()


@st.cache_data(ttl=TTL_VIVO, show_spinner=False)
def get_conteo_incidencias_director(periodo_id: str) -> dict:
    """Por ruta: incidencias de 'no reconocido' y de OOS levantadas en ATLAS.
    Se pegan al Foco OOS al pintar, para que no esperen la hora del tablero."""
    import director_calc as dc
    inc = get_incidencias_director(periodo_id)
    if len(inc) == 0:
        return {'nr': {}, 'oos': {}}
    return {
        'nr': inc[inc['incidencia'] == dc.INCIDENCIA_NO_RECONOCIDO].groupby('ruta').size().to_dict(),
        'oos': inc[inc['tipo'] == 'OOS'].groupby('ruta').size().to_dict(),
    }


@st.cache_data(ttl=TTL_VIVO, show_spinner=False)
def get_uso_director(periodo_id: str, dias: int = 35) -> dict:
    """Quién entra a ATLAS y cómo se atienden las incidencias.

    De usuarios se leen SOLO username, tipo, identificador y activo: el hash
    de la contraseña nunca sale de la base para esta pantalla.
    """
    import director_calc as dc
    try:
        # Con 'Z' y sin '+00:00': un '+' mal codificado en la URL se vuelve espacio.
        desde = (pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=dias)).strftime('%Y-%m-%dT%H:%M:%SZ')
        _, ids, reciente = _contexto_periodo(periodo_id)
        reciente = reciente or periodo_id
        consultas = {
            'usuarios': ('usuarios', 'username, tipo, identificador, activo', {}),
            'accesos': ('accesos', 'username, resultado, entro_at', {'gte': {'entro_at': desde}}),
            'kp': ('kpis_promotor', 'ruta, supervisor, area_manager', {'eq': {'periodo_id': periodo_id}}),
        }
        if reciente != periodo_id:
            consultas['kp_reciente'] = ('kpis_promotor', 'ruta, supervisor, area_manager', {'eq': {'periodo_id': reciente}})
        t = _leer_varios(consultas)
        ruta_area, _ = dc.mapa_areas(t.get('kp_reciente', t['kp']))
        return dc.uso_atlas(t['usuarios'], t['accesos'], get_incidencias_director(periodo_id), t['kp'], ruta_area)
    except Exception as e:
        print(f"[DIRECTOR USO] {e}")
        return None


def limpiar_cache_director():
    """Botón "Actualizar datos": olvida lo guardado para que se relea todo.
    También la lista de periodos de la app, por si se acaba de subir un mes."""
    with _OOS_CANDADO:
        _OOS_MES.clear()
    for funcion in (get_periodos_director, get_tablero_director, get_resumen_director,
                    get_incidencias_director, get_conteo_incidencias_director,
                    get_uso_director, listar_periodos):
        funcion.clear()
