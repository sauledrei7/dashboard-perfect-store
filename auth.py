"""
Autenticación contra Supabase con bcrypt verificado EN PYTHON.

¿Por qué Python y no SQL?
Porque pgcrypto's crypt() tiene problemas con hashes generados por
Python's bcrypt ($2b$ vs $2a$). Hacer la verificación en Python:
- Es 100% confiable
- No depende de extensiones de PostgreSQL
- Misma seguridad: bcrypt sigue siendo bcrypt
"""
import streamlit as st
import bcrypt
from datetime import datetime
from data import _get_client


def normalizar_usuario(input_usuario: str) -> str:
    """Acepta variaciones del username y lo normaliza."""
    u = input_usuario.strip().lower()
    if u.startswith("promotor"):
        num = ''.join(c for c in u.replace("promotor", "") if c.isdigit())
        if num.isdigit():
            return f"promotor_{int(num):02d}"
    if u.startswith("supervisor"):
        if '@' in u:
            u = u.split('@')[0]
        return u
    return u


def autenticar(input_usuario: str, password: str) -> dict:
    """
    Valida contraseña EN PYTHON con bcrypt.
    
    Returns:
        dict con: tipo, identificador, nombre, username, expirada
        None si falla
    """
    usuario_normalizado = normalizar_usuario(input_usuario)
    sb = _get_client()

    try:
        # Obtener el hash y datos del usuario
        r = sb.table('usuarios').select(
            'id, password_hash, tipo, identificador, nombre, password_expira, activo'
        ).eq('username', usuario_normalizado).limit(1).execute()

        if not r.data:
            return None  # usuario no existe

        row = r.data[0]

        if not row.get('activo', True):
            return None  # usuario desactivado

        # Verificar contraseña con bcrypt EN PYTHON
        stored_hash = row['password_hash']
        password_bytes = password.encode('utf-8')
        hash_bytes = stored_hash.encode('utf-8')

        try:
            valido = bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            return None  # hash corrupto

        if not valido:
            return None  # contraseña incorrecta

        # Verificar expiración
        expirada = False
        if row.get('password_expira'):
            try:
                fecha_exp = datetime.fromisoformat(row['password_expira'].replace('Z', '+00:00'))
                expirada = fecha_exp < datetime.now(fecha_exp.tzinfo) if fecha_exp.tzinfo else fecha_exp < datetime.now()
            except Exception:
                pass

        return {
            'tipo': row['tipo'],
            'identificador': row['identificador'],
            'nombre': row['nombre'],
            'username': usuario_normalizado,
            'expirada': expirada,
        }

    except Exception as e:
        # No mostramos el detalle técnico al usuario (evita filtrar info interna).
        # El detalle queda en los logs del servidor para diagnóstico.
        print(f"[AUTH ERROR] {e}")
        st.error("No pudimos validar tu acceso en este momento. Intenta de nuevo en unos segundos.")
        return None


def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def esta_autenticado() -> bool:
    return st.session_state.get('autenticado', False)


def get_usuario_actual() -> dict:
    return st.session_state.get('usuario', None)


def get_periodo_actual() -> str:
    return st.session_state.get('periodo_id', None)


def set_periodo_actual(periodo_id: str):
    st.session_state['periodo_id'] = periodo_id
