"""
Paleta de colores y estilos del dashboard.
Basada en los mockups validados con el usuario.
"""

# Colores principales
COLOR_PINK_PRIMARY = "#FF6FA8"
COLOR_PINK_LIGHT = "#FF8DBD"
COLOR_PINK_PALE = "#FDF0F7"
COLOR_PINK_BORDER = "#F8D3E5"
COLOR_PINK_TEXT = "#B83D7A"
COLOR_PINK_TEXT_LIGHT = "#C56FA0"

COLOR_BLUE_PRIMARY = "#4F7BE8"
COLOR_BLUE_DARK = "#4055C8"
COLOR_BLUE_PALE = "#EEF3FE"
COLOR_BLUE_BG = "#F4F7FE"
COLOR_BLUE_BORDER = "#DCE4F5"
COLOR_BLUE_BORDER_DARK = "#C8D6F4"
COLOR_NAVY = "#1F2A5C"
COLOR_TEXT_SECONDARY = "#6B7BB8"

# Semáforos
COLOR_GREEN = "#2D8A4E"
COLOR_GREEN_PALE = "#E8F5EC"
COLOR_GREEN_BORDER = "#BBDFC4"
COLOR_GREEN_TEXT = "#1E5C36"

COLOR_AMBER = "#E8A53D"
COLOR_AMBER_PALE = "#FDF0E8"

COLOR_RED = "#D94557"
COLOR_RED_DARK = "#B5303F"
COLOR_RED_PALE = "#FCE8EB"
COLOR_RED_BORDER = "#F4BCC3"

COLOR_GRAY_LIGHT = "#E8E8E8"
COLOR_WHITE = "#FFFFFF"

# CSS global a inyectar en la app
CSS_GLOBAL = f"""
<style>
    /* Reset y fuente */
    .stApp {{
        background: {COLOR_WHITE};
    }}

    /* Ocultar elementos default de streamlit */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{display:none;}}

    /* Container principal */
    .main .block-container {{
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 480px;
    }}

    /* Tipografía */
    body, .stMarkdown, p, span {{
        color: {COLOR_NAVY};
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}

    /* Inputs */
    .stTextInput input {{
        border-radius: 10px;
        border: 0.5px solid {COLOR_BLUE_BORDER};
        padding: 12px;
        font-size: 14px;
    }}

    .stTextInput input:focus {{
        border-color: {COLOR_PINK_PRIMARY};
        box-shadow: 0 0 0 2px {COLOR_PINK_PALE};
    }}

    /* Botones */
    .stButton button {{
        background: linear-gradient(135deg, {COLOR_PINK_PRIMARY} 0%, {COLOR_BLUE_PRIMARY} 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 20px;
        font-size: 14px;
        font-weight: 500;
        width: 100%;
        transition: transform 0.1s;
    }}

    .stButton button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(255, 111, 168, 0.3);
    }}

    /* Selectbox */
    .stSelectbox > div > div {{
        background: {COLOR_BLUE_BG};
        border-radius: 10px;
        border: 0.5px solid {COLOR_BLUE_BORDER};
    }}

    /* Tarjetas custom */
    .card {{
        background: {COLOR_WHITE};
        border-radius: 12px;
        padding: 14px;
        border: 0.5px solid {COLOR_BLUE_BORDER};
        margin-bottom: 10px;
    }}

    /* Bono hero */
    .bono-hero {{
        background: linear-gradient(135deg, {COLOR_PINK_PRIMARY} 0%, {COLOR_PINK_LIGHT} 50%, {COLOR_BLUE_PRIMARY} 100%);
        border-radius: 16px;
        padding: 22px;
        color: white;
        text-align: center;
    }}

    .bono-hero-bloqueado {{
        background: linear-gradient(135deg, {COLOR_PINK_PRIMARY} 0%, {COLOR_PINK_LIGHT} 50%, {COLOR_BLUE_PRIMARY} 100%);
        border-radius: 16px;
        padding: 22px;
        color: white;
        text-align: center;
        position: relative;
        overflow: hidden;
    }}

    .bono-hero-bloqueado::after {{
        content: "";
        position: absolute;
        inset: 0;
        background: rgba(255,255,255,0.55);
        backdrop-filter: blur(2px);
    }}

    .bono-pct-grande {{
        font-size: 52px;
        font-weight: 500;
        line-height: 1;
        margin: 0;
    }}

    /* Candado abierto */
    .candado-abierto {{
        background: {COLOR_GREEN_PALE};
        border: 0.5px solid {COLOR_GREEN_BORDER};
        border-radius: 12px;
        padding: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;
    }}

    /* Candado cerrado */
    .candado-cerrado {{
        background: {COLOR_RED_PALE};
        border: 0.5px solid {COLOR_RED_BORDER};
        border-radius: 12px;
        padding: 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;
    }}

    /* KPI cards */
    .kpi-card-rosa {{
        background: {COLOR_PINK_PALE};
        border: 0.5px solid {COLOR_PINK_BORDER};
        border-radius: 12px;
        padding: 14px;
        text-align: center;
    }}

    .kpi-card-azul {{
        background: {COLOR_BLUE_PALE};
        border: 0.5px solid {COLOR_BLUE_BORDER_DARK};
        border-radius: 12px;
        padding: 14px;
        text-align: center;
    }}

    /* Tarjeta tienda */
    .tienda-card {{
        background: {COLOR_WHITE};
        border-radius: 12px;
        padding: 12px 14px;
        border: 0.5px solid {COLOR_BLUE_BORDER};
        margin-bottom: 8px;
    }}

    /* Tarjeta tienda no PS */
    .tienda-card-rojo {{
        background: {COLOR_WHITE};
        border-radius: 12px;
        padding: 12px 14px;
        border: 0.5px solid {COLOR_RED_BORDER};
        margin-bottom: 8px;
    }}
</style>
"""


def color_semaforo(valor, objetivo):
    """Retorna color semáforo según valor vs objetivo. valor y objetivo en escala 0-1 o 0-100."""
    if valor is None or valor == 0:
        return COLOR_RED
    pct = valor / objetivo if objetivo > 0 else 0
    if pct >= 1.0:
        return COLOR_GREEN
    elif pct >= 0.85:
        return COLOR_AMBER
    else:
        return COLOR_RED


def carita_segun_bono(bono_pct):
    """Retorna emoji según el % de bono."""
    if bono_pct >= 80:
        return "😄"
    elif bono_pct >= 50:
        return "🙂"
    elif bono_pct >= 30:
        return "😐"
    else:
        return "😟"


def mensaje_segun_bono(bono_pct):
    """Mensaje motivacional según el bono."""
    if bono_pct >= 80:
        return "¡Vas excelente!"
    elif bono_pct >= 60:
        return "¡Vas bien!"
    elif bono_pct >= 40:
        return "Puedes mejorar"
    elif bono_pct > 0:
        return "Necesitas empujar"
    else:
        return "Atención urgente"
