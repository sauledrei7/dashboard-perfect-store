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

## 🔑 Credenciales

Las contraseñas **no se documentan aquí** (ni en ningún archivo del repo). Se
entregan a cada persona por un canal privado.

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
- Contraseñas hasheadas con bcrypt (no en texto plano), verificadas en Python
- Base de datos Supabase con cifrado AES-256
- Row Level Security activado; el filtro por rol se hace en el código de la app
- `.streamlit/secrets.toml` NUNCA se sube a GitHub (está en `.gitignore`)
- Todo texto que escribe una persona se escapa antes de pintarse en HTML
  (`render.texto()` y `render.url()`)

## 🌐 Deploy a producción

1. Subir a GitHub (sin `.streamlit/secrets.toml`)
2. Crear app en https://streamlit.io/cloud
3. En "Advanced settings" → Secrets, pegar el contenido del archivo `secrets.toml`
4. Click Deploy → obtienes URL pública con HTTPS
