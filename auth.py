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


def _registrar_acceso(username: str, resultado: str,
                      tipo: str = None, identificador: str = None):
    """v16: deja constancia del intento de login en la tabla accesos.

    Va envuelto en try/except a propósito y NO relanza: si la bitácora falla
    —porque la tabla no existe todavía, o Supabase va lento— el promotor tiene
    que poder entrar igual. Medir nunca debe estorbarle a la operación.
    """
    try:
        sb = _get_client()
        sb.table('accesos').insert({
            'username': username,
            'tipo': tipo,
            'identificador': identificador,
            'resultado': resultado,
        }).execute()
    except Exception as e:
        print(f"[ACCESOS WARN] no se pudo registrar el acceso: {e}")


def _esta_vencida(row: dict) -> bool:
    """¿Ya venció la contraseña de este usuario?

    Vive aparte porque lo usan dos caminos —el login normal y la restauración
    desde la cookie— y si cada uno trajera su propia copia, tarde o temprano
    uno de los dos se quedaría atrás.
    """
    if not row.get('password_expira'):
        return False
    try:
        fecha_exp = datetime.fromisoformat(row['password_expira'].replace('Z', '+00:00'))
        if fecha_exp.tzinfo:
            return fecha_exp < datetime.now(fecha_exp.tzinfo)
        return fecha_exp < datetime.now()
    except Exception:
        return False


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
            _registrar_acceso(usuario_normalizado, 'NO_EXISTE')
            return None  # usuario no existe

        row = r.data[0]

        if not row.get('activo', True):
            _registrar_acceso(usuario_normalizado, 'INACTIVO',
                              row.get('tipo'), row.get('identificador'))
            return None  # usuario desactivado

        # Verificar contraseña con bcrypt EN PYTHON
        stored_hash = row['password_hash']
        password_bytes = password.encode('utf-8')
        hash_bytes = stored_hash.encode('utf-8')

        try:
            valido = bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            _registrar_acceso(usuario_normalizado, 'PASSWORD',
                              row.get('tipo'), row.get('identificador'))
            return None  # hash corrupto

        if not valido:
            _registrar_acceso(usuario_normalizado, 'PASSWORD',
                              row.get('tipo'), row.get('identificador'))
            return None  # contraseña incorrecta

        # Verificar expiración
        expirada = _esta_vencida(row)

        # La contraseña era correcta. Si venció, app.py no lo deja pasar, así
        # que se registra aparte: no fue una sesión iniciada.
        _registrar_acceso(usuario_normalizado,
                          'EXPIRADA' if expirada else 'OK',
                          row.get('tipo'), row.get('identificador'))

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


def recuperar_usuario(username: str) -> dict:
    """v17: relee al usuario para restaurar una sesión desde la cookie.

    A propósito NO recibe contraseña: la firma de la cookie ya probó quién es.
    Lo que sí hace es volver a leer rol, ruta y estado desde la base, en vez de
    confiar en lo que traiga la cookie. Así, una cookie de ayer no revive a
    alguien con la ruta vieja, ni deja entrar a quien ya fue dado de baja o a
    quien se le venció la contraseña mientras tanto.

    Devuelve None si por cualquier razón no debe pasar; el que llama se encarga
    de mandarlo al login.
    """
    try:
        sb = _get_client()
        r = sb.table('usuarios').select(
            'tipo, identificador, nombre, activo, password_expira'
        ).eq('username', username).limit(1).execute()

        if not r.data:
            return None

        row = r.data[0]
        tipo, ident = row.get('tipo'), row.get('identificador')

        if not row.get('activo', True):
            _registrar_acceso(username, 'INACTIVO', tipo, ident)
            return None

        if _esta_vencida(row):
            _registrar_acceso(username, 'EXPIRADA', tipo, ident)
            return None

        # Se registra como COOKIE y no como OK a propósito: no volvió a teclear
        # la contraseña. Separarlos deja ver cuánta gente entra sola y cuánta
        # de verdad inicia sesión.
        _registrar_acceso(username, 'COOKIE', tipo, ident)

        return {
            'tipo': row['tipo'],
            'identificador': row['identificador'],
            'nombre': row['nombre'],
            'username': username,
            'expirada': False,
        }

    except Exception as e:
        # Si la base no responde, se pide contraseña. Nunca se deja pasar a
        # ciegas solo porque la cookie venía bien firmada.
        print(f"[AUTH RESTORE ERROR] {e}")
        return None


def cerrar_sesion():
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Estas dos banderas se ponen DESPUÉS de vaciar, y son lo único que
    # sobrevive al cierre de sesión:
    #
    # _borrar_cookie  la orden de quitar la cookie del celular. No se ejecuta
    #                 aquí porque todos los que llaman a cerrar_sesion() hacen
    #                 st.rerun() de inmediato, y ese rerun se llevaría la orden
    #                 entre las patas antes de que llegue al navegador. app.py
    #                 la ejecuta en el render siguiente, que es tranquilo.
    #
    # _no_restaurar   impide que la app vuelva a entrar sola en lo que queda de
    #                 esta conexión. Hace falta porque st.context.cookies lee de
    #                 los encabezados que el navegador mandó al conectarse, y
    #                 esos ya no cambian: sin esta bandera, el siguiente render
    #                 encontraría la cookie vieja y el "cerrar sesión" no
    #                 serviría de nada.
    st.session_state['_borrar_cookie'] = True
    st.session_state['_no_restaurar'] = True


def esta_autenticado() -> bool:
    return st.session_state.get('autenticado', False)


def get_usuario_actual() -> dict:
    return st.session_state.get('usuario', None)


def get_periodo_actual() -> str:
    return st.session_state.get('periodo_id', None)


def set_periodo_actual(periodo_id: str):
    st.session_state['periodo_id'] = periodo_id
