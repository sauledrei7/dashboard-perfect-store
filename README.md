# 🛒 Dashboard Perfect Store — v7 (Supabase)

Dashboard móvil para 308 usuarios (278 promotores + 30 supervisores) que
muestra su bono mensual. Lee datos de Supabase con HTTPS y bcrypt.

## 🚀 Cómo correrlo localmente

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Verificar que el archivo .streamlit/secrets.toml existe (con tu URL + anon key)
# 3. Correr
streamlit run app.py
```

Se abre en `http://localhost:8501`.

## 🔑 Credenciales de prueba

Todas las contraseñas siguen el patrón `{username}_2026`.

| Usuario | Contraseña | Qué verás |
|---|---|---|
| `promotor_43` | `promotor_43_2026` | 🔒 Candado cerrado |
| `promotor_159` | `promotor_159_2026` | 100% bono |
| `promotor_146` | `promotor_146_2026` | Bono bajo |
| `supervisor20` | `supervisor20_2026` | 🔒 Supervisor candado cerrado |
| `supervisor14` | `supervisor14_2026` | Mejor supervisor |

## 📁 Estructura

```
dashboard/
├── app.py                  # Entrada + login + router + selector periodo
├── data.py                 # Cliente Supabase + queries + adaptadores
├── auth.py                 # Login con bcrypt vs verificar_password()
├── render.py               # Helper para HTML limpio
├── requirements.txt
├── .streamlit/
│   └── secrets.toml        # URL + anon key (NO subir a GitHub)
├── styles/
│   └── theme.py            # Paleta rosa/azul/blanco
└── components/
    ├── promotor_resumen.py
    ├── promotor_tiendas.py
    ├── tienda_detalle.py
    ├── supervisor_resumen.py
    └── supervisor_promotores.py
```

## 🔄 Periodos

El dashboard muestra un selector arriba con todos los periodos cargados.
Al cambiar, se actualiza toda la pantalla con los datos de ese mes.

## 🔐 Seguridad

- HTTPS automático (cuando deploy en Streamlit Cloud)
- Contraseñas hasheadas con bcrypt (no en texto plano)
- Base de datos Supabase con cifrado AES-256
- Row Level Security activado
- `.streamlit/secrets.toml` NUNCA se sube a GitHub (está en `.gitignore`)

## 🌐 Deploy a producción

1. Subir a GitHub (sin `.streamlit/secrets.toml`)
2. Crear app en https://streamlit.io/cloud
3. En "Advanced settings" → Secrets, pegar el contenido del archivo `secrets.toml`
4. Click Deploy → obtienes URL pública con HTTPS
