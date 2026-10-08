"""
VALIDACIÓN DEL CLIENTE (v24) — la pantalla del usuario tipo 'cliente'.

Es de computadora, como el tablero del director: el CSS ancho se mete solo
cuando se pinta esta pantalla y vive únicamente en la sesión del cliente. Si
un promotor entra al mismo tiempo, su app se ve como siempre.

Tres vistas, con los colores de ATLAS (styles/theme.py y el tablero):
  Validar      la cola a la izquierda y, a la derecha, el expediente de una
               incidencia: evidencia, qué reclama, el seguimiento de la misma
               tienda y KPI, qué dicen los datos, su historia y la decisión.
  Seguimiento  las tiendas donde el mismo KPI se reclamó en varias semanas.
  Resumen      avance, desgloses y el Excel de INCIDENCIAS FINALES del cierre.

Los cálculos viven en validacion_calc.py; leer y escribir, en data.py.

OJO con el HTML: todo lo que escribió alguien (comentarios, motivos, nombres)
pasa por _e() antes de pintarse, y los saltos de línea se vuelven <br>. Un
renglón en blanco dentro de st.markdown corta el bloque HTML y lo que sigue
sale como texto; un "$" puede pintarse como fórmula.
"""
import html as _html

import pandas as pd
import streamlit as st

import render as r
import validacion_calc as vc
from auth import cerrar_sesion
from components.incidencias import etiqueta_motivo
from data import (get_estructura_periodo, get_historial_incidencia, get_incidencias_validacion,
                  get_kpis_tiendas, get_periodos_director, get_series_incidencias,
                  limpiar_cache_validacion, validar_incidencia)

VISTAS = [
    ('validar', 'Validar', ':material/fact_check:'),
    ('seguimiento', 'Seguimiento', ':material/timeline:'),
    ('resumen', 'Resumen', ':material/insights:'),
]
TITULOS = {'validar': 'Validar incidencias', 'seguimiento': 'Incidencias que se repiten',
           'resumen': 'Resumen del mes'}
PERIODOS_VISIBLES = 6
TANDA_COLA = 60          # tarjetas de la cola por tanda
TANDA_SEGUIMIENTO = 25
FILTRO_ESTADO = {'PENDIENTE': 'Por validar', 'APROBADA': 'Aprobadas', 'NO_APROBADA': 'No aprobadas',
                 'TODAS': 'Todas'}
FILTRO_KPI = {'todos': 'Todos', 'SOS': 'SOS', 'EXHIBICIONES': 'Exhibiciones', 'OOS': 'OOS'}
SUPERVISOR = {'AUTORIZADA': 'Autorizada', 'PENDIENTE': 'Sin revisar', 'NO_AUTORIZADA': 'No autorizada'}
ESTADO_CLIENTE = {vc.PENDIENTE: ('Por validar', 'y'), vc.APROBADA: ('Aprobada', 'g'),
                  vc.NO_APROBADA: ('No aprobada', 'r')}
MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre',
         'octubre', 'noviembre', 'diciembre')

CSS_CLIENTE = """
<style>
[data-testid="stMainBlockContainer"], .main .block-container, .stMainBlockContainer {
  max-width: 1480px !important; padding: 1.6rem 2.2rem 3rem !important; }
[data-testid="stAppViewContainer"] { background: #FAFBFF; }
/* menú lateral */
[class*="st-key-clinav_"] button { background: transparent !important; color: #6B7BB8 !important; border: 0 !important;
  box-shadow: none !important; justify-content: flex-start !important; padding: 9px 12px !important;
  font-weight: 400 !important; border-radius: 10px !important; }
[class*="st-key-clinav_"] button:hover { background: #F4F7FE !important; transform: none !important; }
[class*="st-key-clinav_"] button > div { justify-content: flex-start !important; }
.st-key-clinav_ACTIVO button { background: #FDF0F7 !important; color: #B83D7A !important; font-weight: 500 !important;
  box-shadow: inset 0 0 0 0.5px #F8D3E5 !important; }
/* botones secundarios */
[class*="st-key-clilink_"] button, .st-key-cli_salir button, .st-key-vdec_cambiar button, .st-key-vdec_cancelar button,
.st-key-vdec_pend button, .st-key-vdec_cancel2 button, [class*="st-key-cliabrir_"] button, .st-key-cli_mas_btn button,
.st-key-cli_seg_mas_btn button { background: #fff !important; color: #B83D7A !important; border: 0.5px solid #F8D3E5 !important;
  padding: 7px 12px !important; font-size: 13px !important; box-shadow: none !important; }
[class*="st-key-clilink_"] button:hover, .st-key-cli_salir button:hover, .st-key-vdec_cambiar button:hover,
.st-key-vdec_cancelar button:hover, .st-key-vdec_pend button:hover, .st-key-vdec_cancel2 button:hover,
[class*="st-key-cliabrir_"] button:hover, .st-key-cli_mas_btn button:hover, .st-key-cli_seg_mas_btn button:hover {
  background: #FDF0F7 !important; transform: none !important; }
[class*="st-key-clilink_"] button:disabled { color: #9AA6D1 !important; border-color: #DCE4F5 !important; background: #F4F7FE !important; }
.st-key-vdec_no button { background: #fff !important; color: #B5303F !important; border: 0.5px solid #F4BCC3 !important;
  box-shadow: none !important; }
.st-key-vdec_no button:hover { background: #FCE8EB !important; transform: none !important; }
.st-key-vdec_confirmar button { background: #B5303F !important; color: #fff !important; }
.st-key-vdec_confirmar button:disabled { background: #EDF0F8 !important; color: #9AA6D1 !important; }
.stDownloadButton button { background: linear-gradient(135deg,#FF6FA8 0%,#4F7BE8 100%) !important; color: #fff !important;
  border: 0 !important; border-radius: 12px !important; padding: 12px 20px !important; font-weight: 500 !important; }
/* selectores de botones */
[data-testid="stBaseButton-segmented_control"] { background: #fff !important; color: #6B7BB8 !important;
  border-color: #DCE4F5 !important; font-size: 13px !important; }
[data-testid="stBaseButton-segmented_controlActive"] { background: #FDF0F7 !important; color: #B83D7A !important;
  border-color: #F8D3E5 !important; font-weight: 500 !important; font-size: 13px !important; }
.st-key-cli_periodo [data-testid="stButtonGroup"] { display: flex; justify-content: flex-end; }
[data-testid="stBaseButton-pills"] { background: #fff !important; color: #6B7BB8 !important; border-color: #DCE4F5 !important; }
[data-testid="stBaseButton-pillsActive"] { background: #FCE8EB !important; color: #B5303F !important;
  border-color: #F4BCC3 !important; font-weight: 500 !important; }
.st-key-vdecide [data-testid="stBaseButton-pillsActive"] { background: #FCE8EB !important; }
[class*="st-key-viraser_"] [data-testid="stBaseButton-pillsActive"] { background: #FDF0F7 !important;
  color: #B83D7A !important; border-color: #F8D3E5 !important; }
/* tarjetas con widgets adentro: el borde lo pinta el contenedor de afuera */
[data-testid="stVerticalBlockBorderWrapper"]:has(> [class*="st-key-vcard_"]) { background: #fff;
  border-radius: 14px !important; border-color: #DCE4F5 !important; padding: 16px 18px !important; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> [class*="st-key-vcard_seg"]) { border: 1.5px solid #F8D3E5 !important; }
/* barra de decisión: se queda abajo mientras se lee el expediente */
.st-key-vdecide { position: sticky; bottom: 10px; z-index: 20; background: #fff; border: 0.5px solid #C8D6F4;
  border-radius: 16px; padding: 14px 18px; box-shadow: 0 8px 24px rgba(31,42,92,.12); }
/* bloques que se tocan enteros: un botón invisible encima */
[class*="st-key-vclic_"] { position: relative; gap: 0 !important; }
[class*="st-key-vclic_"] [class*="st-key-vbtn_"] { position: absolute !important; inset: 0; z-index: 4; margin: 0 !important; }
[class*="st-key-vbtn_"] .stButton, [class*="st-key-vbtn_"] button { width: 100% !important; height: 100% !important;
  min-height: 0 !important; }
[class*="st-key-vbtn_"] button { opacity: 0 !important; padding: 0 !important; transform: none !important;
  box-shadow: none !important; cursor: pointer !important; }
[class*="st-key-vbtn_"] button:focus-visible { opacity: 1 !important; background: transparent !important;
  outline: 2px solid #FF6FA8 !important; }
[class*="st-key-vclic_"]:hover .vq { border-color: #FF8DBD; }
[class*="st-key-vclic_"]:hover .vfoto { border-color: #FF8DBD; }
/* renglones sin st.columns (Streamlit 1.45 solo deja anidar columnas un nivel):
   vfila_ = botones y texto en fila, el texto con .vcrece se lleva el espacio;
   vpar_ = bloques del mismo ancho, lado a lado */
[class*="st-key-vfila_"] { flex-direction: row !important; flex-wrap: wrap; align-items: center; gap: 8px 10px !important; }
[class*="st-key-vfila_"] > div { width: auto !important; flex: 0 0 auto; min-width: 0; }
[class*="st-key-vfila_"] > div:has(.vcrece) { flex: 1 1 260px; }
[class*="st-key-vfila_"] .vpos, [class*="st-key-vfila_"] .vdec-s, [class*="st-key-vfila_"] .vdec-r { padding-top: 0; }
[class*="st-key-vpar_"] { flex-direction: row !important; align-items: stretch; gap: 12px !important; }
[class*="st-key-vpar_"] > div { flex: 1 1 0 !important; min-width: 0 !important; width: auto !important; }
.st-key-vpar_fotos > div { flex: 0 0 calc((100% - 24px) / 3) !important; }
/* Streamlit fuerza 1rem a <p> y quita 1rem abajo a cada markdown */
.vcard, .vhero, .vaviso, .vgrid, .vvacio { margin-bottom: 12px !important; }
/* marca y usuario */
.vmarca { display: flex; align-items: center; gap: 12px; padding: 4px 6px 18px; }
.vmarca .vlogo { width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center;
  background: linear-gradient(135deg,#FF6FA8 0%,#FF8DBD 50%,#4F7BE8 100%); }
.vmarca b { font-size: 19px; font-weight: 500; letter-spacing: .14em; display: block; color: #1F2A5C; }
.vmarca small { font-size: 11px; color: #C56FA0; }
.vyo { display: flex; align-items: center; gap: 10px; background: #F4F7FE; border: 0.5px solid #DCE4F5; border-radius: 12px;
  padding: 10px 12px; margin-bottom: 14px; }
.vyo .vav { width: 34px; height: 34px; border-radius: 50%; color: #fff; display: grid; place-items: center; font-size: 12px;
  font-weight: 500; flex: none; background: linear-gradient(135deg,#FF6FA8 0%,#4F7BE8 100%); }
.vyo b { display: block; font-size: 13px; font-weight: 500; color: #1F2A5C; }
.vyo span { font-size: 11px; color: #6B7BB8; }
.vnavt { font-size: 11px; color: #9AA6D1; letter-spacing: .08em; margin: 0 0 4px 10px; }
.vpie { font-size: 11px; color: #9AA6D1; line-height: 1.5; margin: 14px 6px 0; }
/* encabezado */
.vtop .vhola { font-size: 13px; color: #6B7BB8; }
.vtop .vtit { font-size: 25px; font-weight: 500; color: #1F2A5C; line-height: 1.2; margin-top: 2px; }
.vtop .vsubt { font-size: 12px; color: #C56FA0; margin-top: 3px; }
.vlbl { font-size: 12px; color: #6B7BB8; margin: 0 0 -6px; }
.vaviso { display: flex; gap: 10px; align-items: center; background: #FDF0E8; border: 0.5px solid #F1D2B8; border-radius: 10px;
  padding: 9px 14px; font-size: 13px; color: #98580E; }
.vaviso-azul { background: #F4F7FE; border-color: #DCE4F5; color: #6B7BB8; }
.vaviso b { font-weight: 500; }
.vvacio { background: #F4F7FE; border: 0.5px solid #DCE4F5; border-radius: 10px; padding: 18px; text-align: center;
  font-size: 13px; color: #6B7BB8; }
/* piezas */
.vcard { background: #fff; border: 0.5px solid #DCE4F5; border-radius: 14px; padding: 16px 18px; color: #1F2A5C; }
.vct { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.vct-h { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 500; color: #1F2A5C; }
.vct-n { width: 22px; height: 22px; border-radius: 50%; background: #FDF0F7; border: 0.5px solid #F8D3E5; color: #B83D7A;
  font-size: 12px; font-weight: 500; display: grid; place-items: center; flex: none; }
.vct-s { font-size: 12px; color: #6B7BB8; }
.vp { display: inline-block; text-align: center; border-radius: 7px; padding: 3px 9px; font-size: 12px; font-weight: 500;
  white-space: nowrap; }
.vp-g { background: #E8F5EC; color: #1E5C36; } .vp-y { background: #FDF0E8; color: #98580E; }
.vp-r { background: #FCE8EB; color: #B5303F; } .vp-n { background: #F4F7FE; color: #1F2A5C; }
.vt { display: inline-block; font-size: 11px; border-radius: 999px; padding: 2px 9px; font-weight: 500; white-space: nowrap; }
.vt-b { background: #EEF3FE; color: #4055C8; } .vt-rosa { background: #FDF0F7; color: #B83D7A; box-shadow: inset 0 0 0 0.5px #F8D3E5; }
.vt-y { background: #FDF0E8; color: #98580E; } .vt-g { background: #E8F5EC; color: #1E5C36; }
.vt-r { background: #FCE8EB; color: #B5303F; } .vt-n { color: #9AA6D1; }
/* cola */
.vcola-h { display: flex; justify-content: space-between; align-items: baseline; font-size: 15px; font-weight: 500; color: #1F2A5C; }
.vcola-h span { font-size: 12px; font-weight: 400; color: #6B7BB8; }
.vbar { height: 8px; border-radius: 999px; background: #EDF0F8; overflow: hidden; margin: 8px 0 4px; }
.vbar i { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg,#FF6FA8,#4F7BE8); }
.vq { display: flex; flex-direction: column; gap: 5px; padding: 11px 12px; border-radius: 12px; background: #fff;
  border: 0.5px solid #DCE4F5; color: #1F2A5C; margin-bottom: 8px; }
.vq-act { background: #FDF0F7 !important; border: 1.5px solid #FF6FA8 !important; }
.vq-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 12px; color: #6B7BB8; }
.vq-t { font-size: 14px; font-weight: 500; line-height: 1.3; }
.vq-m { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 12px; color: #6B7BB8; }
.vsup-ok { color: #2D8A4E; } .vsup-no { color: #B5303F; } .vsup-p { color: #98580E; }
.vcuenta { font-size: 12px; color: #6B7BB8; text-align: center; margin: 4px 0 8px; }
/* expediente */
.vpos { font-size: 12px; color: #6B7BB8; padding-top: 10px; }
.vhero { background: linear-gradient(135deg,#FF6FA8 0%,#FF8DBD 50%,#4F7BE8 100%); border-radius: 16px; padding: 20px 24px;
  color: #fff; }
.vhero-c { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 13px; }
.vchip { font-size: 12px; font-weight: 500; background: rgba(255,255,255,.2); border: 0.5px solid rgba(255,255,255,.55);
  padding: 3px 10px; border-radius: 999px; }
.vchip-b { font-size: 12px; font-weight: 500; background: #fff; padding: 3px 10px; border-radius: 999px; }
.vhero-t { font-size: 26px; font-weight: 500; line-height: 1.2; margin: 8px 0 4px; }
.vhero-s { font-size: 13px; opacity: .95; line-height: 1.5; }
.vfoto { border: 0.5px solid #DCE4F5; border-radius: 10px; background: #F4F7FE; padding: 6px; }
.vfoto img { width: 100%; height: 150px; object-fit: cover; border-radius: 6px; display: block; }
.vfoto span { display: block; font-size: 12px; color: #6B7BB8; margin-top: 5px; }
.vtrax { display: flex; align-items: center; justify-content: center; gap: 8px; min-height: 42px; border: 0.5px solid #F8D3E5;
  border-radius: 12px; background: #fff; font-size: 14px; font-weight: 500; color: #B83D7A !important;
  text-decoration: none !important; margin-top: 10px; }
.vtrax:hover { background: #FDF0F7; }
.vtrax-no { color: #9AA6D1 !important; border-color: #DCE4F5; background: #F4F7FE; cursor: default; }
.vlab { font-size: 12px; color: #6B7BB8; margin-bottom: 3px; }
.vmot { font-size: 16px; font-weight: 500; margin-bottom: 12px; }
.vcom { background: #F4F7FE; border: 0.5px solid #DCE4F5; border-radius: 10px; padding: 12px 14px; font-size: 14px;
  line-height: 1.5; margin-bottom: 12px; overflow-wrap: anywhere; }
.vchips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.vquien { font-size: 12px; color: #6B7BB8; }
/* tira de seguimiento */
.vtira { display: grid; grid-template-columns: repeat(auto-fill, minmax(92px, 1fr)); gap: 8px; margin-bottom: 12px; }
.vtc { display: flex; flex-direction: column; gap: 4px; padding: 8px 9px; border-radius: 10px; color: #1F2A5C; }
.vtc-sin { background: #F4F7FE; border: 0.5px solid #EDF0F8; }
.vtc-inc { background: #fff; border: 0.5px solid #C8D6F4; }
.vtc-act { background: #FDF0F7; border: 1.5px solid #FF6FA8; }
.vtc-s { font-size: 12px; font-weight: 500; } .vtc-s span { font-weight: 400; color: #6B7BB8; }
.vtc-v { font-size: 12.5px; font-weight: 500; } .vtc-e { font-size: 11px; }
.vc-g { color: #1E5C36; } .vc-y { color: #98580E; } .vc-r { color: #B5303F; } .vc-n { color: #6B7BB8; }
.vlect { display: flex; flex-direction: column; gap: 6px; background: #FDF0F7; border: 0.5px solid #F8D3E5; border-radius: 10px;
  padding: 12px 14px; font-size: 14px; line-height: 1.45; }
/* qué dicen los datos */
.vdatos { display: grid; grid-template-columns: minmax(0,1fr) 250px; gap: 26px; align-items: stretch; }
.vbars { position: relative; height: 168px; border-bottom: 0.5px solid #C8D6F4; display: flex; justify-content: space-around;
  align-items: flex-end; padding: 0 10px; }
.vbars-col { display: flex; flex-direction: column; align-items: center; gap: 5px; width: 110px; position: relative; z-index: 1; }
.vbars-col b { font-size: 14px; font-weight: 500; }
.vbars-col i { display: block; width: 60px; border-radius: 6px 6px 0 0; }
.vbars-rec i { box-shadow: 0 0 0 3px #fff, 0 0 0 5px #FF6FA8; }
.vbars-obj { position: absolute; left: 0; right: 0; border-top: 2px dashed #B83D7A; z-index: 2; }
.vbars-obj span { position: absolute; right: 4px; bottom: 3px; font-size: 12px; font-weight: 500; color: #B83D7A;
  background: #fff; padding: 0 4px; }
.vbars-lab { display: flex; justify-content: space-around; padding: 6px 10px 0; }
.vbars-lab div { width: 110px; text-align: center; font-size: 12px; color: #6B7BB8; }
.vbars-lab .vrec { color: #1F2A5C; font-weight: 500; }
.vmes { display: flex; flex-direction: column; gap: 8px; justify-content: center; }
.vmes-v { font-size: 30px; font-weight: 500; line-height: 1; }
.vmes-n { font-size: 12px; color: #6B7BB8; line-height: 1.45; }
.voos { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
.voos div { display: flex; flex-direction: column; gap: 3px; border-radius: 12px; padding: 12px 14px; }
.voos b { font-size: 22px; font-weight: 500; }
.voos-ok { background: #E8F5EC; border: 0.5px solid #BBDFC4; } .voos-no { background: #FCE8EB; border: 0.5px solid #F4BCC3; }
.voos-n { background: #F4F7FE; border: 0.5px solid #DCE4F5; } .voos-rec { box-shadow: inset 0 0 0 1.5px #FF6FA8; }
.vhist { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; border-top: 0.5px solid #EDF0F8; padding-top: 12px;
  margin-top: 14px; font-size: 12px; color: #6B7BB8; }
.vhechos { display: flex; flex-direction: column; gap: 8px; margin-top: 14px; }
.vhecho { display: flex; gap: 10px; align-items: flex-start; font-size: 14px; line-height: 1.45; border-radius: 10px;
  padding: 10px 12px; }
.vhecho-nada { background: #FDF0E8; color: #6E4210; } .vhecho-info { background: #F4F7FE; color: #1F2A5C; }
.vhecho i { width: 8px; height: 8px; border-radius: 50%; margin-top: 7px; flex: none; }
.vhecho-nada i { background: #E8A53D; } .vhecho-info i { background: #4F7BE8; }
/* historia */
.vtl { display: flex; flex-direction: column; gap: 10px; }
.vtl-i { display: flex; gap: 12px; align-items: flex-start; }
.vtl-i i { width: 12px; height: 12px; border-radius: 50%; margin-top: 4px; flex: none; box-sizing: border-box; }
.vtl-i b { display: block; font-size: 14px; font-weight: 500; }
.vtl-i span { display: block; font-size: 12px; color: #6B7BB8; line-height: 1.4; overflow-wrap: anywhere; }
/* decisión */
.vdec-t { font-size: 15px; font-weight: 500; color: #1F2A5C; margin-bottom: 4px; }
.vdec-s { font-size: 13px; color: #6B7BB8; padding-top: 12px; }
.vdec-r { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 13px; color: #6B7BB8; padding-top: 6px; }
/* seguimiento y resumen */
.vgrupo { display: grid; grid-template-columns: minmax(0,1fr); gap: 10px; }
.vgrupo-t { font-size: 16px; font-weight: 500; line-height: 1.3; }
.vgrid { display: grid; gap: 14px; }
.vg2 { grid-template-columns: repeat(2, minmax(0,1fr)); }
.vheroR { background: linear-gradient(135deg,#FF6FA8 0%,#FF8DBD 50%,#4F7BE8 100%); border-radius: 16px; color: #fff;
  display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); overflow: hidden; margin-bottom: 14px; }
.vheroR > div { padding: 20px 22px; display: flex; flex-direction: column; }
.vheroR > div + div { border-left: 0.5px solid rgba(255,255,255,.3); }
.vheroR span { font-size: 13px; opacity: .95; }
.vheroR b { font-size: 38px; font-weight: 500; line-height: 1; margin: 8px 0 6px; }
.vheroR small { font-size: 12px; opacity: .92; }
.vkpi { display: grid; grid-template-columns: 118px minmax(0,1fr) 150px; gap: 10px; align-items: center; padding: 6px 0;
  font-size: 13px; }
.vkpi small { font-size: 12px; color: #6B7BB8; text-align: right; }
.vapil { height: 8px; border-radius: 999px; background: #EDF0F8; display: flex; overflow: hidden; }
.vapil i { display: block; height: 100%; }
.vleg { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11.5px; color: #6B7BB8; margin-top: 10px; }
.vleg i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
table.vtab { width: 100%; border-collapse: collapse; font-size: 13px; border: 0 !important; margin: 0; display: table; }
table.vtab th { font-size: 11px; font-weight: 500; color: #9AA6D1; text-align: center; padding: 0 6px 8px; white-space: nowrap;
  border: 0 !important; background: transparent !important; }
table.vtab td { padding: 7px 6px; border: 0 !important; border-top: 0.5px solid #EDF0F8 !important; text-align: center;
  color: #1F2A5C; background: transparent !important; }
table.vtab tr { background: transparent !important; }
table.vtab .vi { text-align: left; }
.vcierre { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: #6B7BB8; line-height: 1.5; }
.vcierre b { font-size: 15px; font-weight: 500; color: #1F2A5C; }
</style>
"""


# ============================================================
# Utilidades
# ============================================================
def _e(x) -> str:
    """Texto seguro para meterlo en HTML: escapa, y un $ no se vuelve fórmula."""
    return _html.escape(vc.texto(x) if not isinstance(x, str) else x.strip(), quote=True).replace('$', '&#36;')


def _parrafos(x) -> str:
    return '<br>'.join(_e(linea) for linea in vc.texto(x).splitlines() if linea.strip())


def _url_segura(url) -> str:
    u = vc.texto(url)
    return u if u.lower().startswith(('https://', 'http://')) else ''


def _supervisor(ctx, f) -> str:
    """Quién decide por el supervisor: el que la resolvió o, si nadie, el de la ruta."""
    quien = f['resuelta_por'] or ctx['ruta_sup'].get(f['ruta'], '')
    return quien.split('@')[0] if quien else 'el supervisor'


def _control(etiqueta, opciones, key, defecto, fmt=str, al_cambiar=None):
    """Selector de botones que nunca se queda en blanco (st.segmented_control deja
    des-seleccionar tocando la opción activa): regresa a la última elegida."""
    opciones = list(opciones)
    previo = st.session_state.get(f'{key}__ok', defecto)
    if st.session_state.get(key) not in opciones:
        st.session_state[key] = previo if previo in opciones else opciones[0]

    def formato(x):
        try:
            return str(fmt(x))
        except Exception:
            return str(x)

    valor = st.segmented_control(etiqueta, opciones, format_func=formato, key=key,
                                 label_visibility='collapsed', on_change=al_cambiar)
    if valor is None:
        st.rerun()
    st.session_state[f'{key}__ok'] = valor
    return valor


def _clic(key, contenido, ayuda, al_tocar=None, args=()) -> bool:
    """Un bloque de HTML que se toca entero: lleva un botón invisible encima.
    Con al_tocar corre como callback; sin él, regresa True si lo tocaron (un
    st.dialog no se puede abrir desde un callback)."""
    with st.container(key=f"vclic_{key}"):
        r.html(contenido)
        return st.button(ayuda, key=f"vbtn_{key}", on_click=al_tocar, args=args, use_container_width=True)


def _vacio(texto):
    r.html(f'<div class="vvacio">{texto}</div>')


def _titulo(n, texto, sub=''):
    return (f'<div class="vct"><div class="vct-h"><span class="vct-n">{n}</span>{texto}</div>'
            + (f'<span class="vct-s">{sub}</span>' if sub else '') + '</div>')


def _nombre_periodo(periodos, pid) -> str:
    fila = periodos[periodos['periodo_id'] == pid]
    if len(fila) == 0:
        return str(pid)
    fila = fila.iloc[0]
    # El año sale de la fecha y no de la columna 'anio', que viene adelantada un año.
    anio = str(fila.get('fecha_fin') or '')[:4]
    return f"{str(fila.get('mes') or pid).strip().capitalize()} {anio}".strip()


def _fechas_semana(periodos, pid, semana) -> str:
    """'7 al 13 de septiembre'. Las semanas de TRAX empiezan en lunes y el
    periodo arranca en su semana_inicio."""
    fila = periodos[periodos['periodo_id'] == pid]
    if len(fila) == 0 or semana is None or pd.isna(semana):
        return ''
    fila = fila.iloc[0]
    ini = pd.to_datetime(fila.get('fecha_inicio'), errors='coerce')
    s0 = vc.numero(fila.get('semana_inicio'))
    if pd.isna(ini) or s0 is None:
        return ''
    ini = ini + pd.Timedelta(days=7 * (int(semana) - int(s0)))
    fin = ini + pd.Timedelta(days=6)
    if ini.month == fin.month:
        return f"{ini.day} al {fin.day} de {MESES[fin.month - 1]}"
    return f"{ini.day} de {MESES[ini.month - 1]} al {fin.day} de {MESES[fin.month - 1]}"


# ============================================================
# Navegación (se llaman como callbacks: corren antes del render siguiente,
# que es el único momento en que se puede mover el estado de un widget)
# ============================================================
def _ir_a(inc_id, periodo=None, ver_todas=False):
    st.session_state['cli_sel'] = int(inc_id)
    st.session_state['cli_vista'] = 'validar'
    st.session_state.pop('cli_rechazando', None)
    st.session_state.pop('cli_cambiando', None)
    if periodo and periodo != st.session_state.get('periodo_id'):
        st.session_state['periodo_id'] = periodo
        st.session_state['cli_periodo'] = periodo
        st.session_state['cli_periodo__ok'] = periodo
        st.session_state['cli_mas'] = TANDA_COLA
    if ver_todas:
        st.session_state['cli_f_estado'] = 'TODAS'
        st.session_state['cli_f_estado__ok'] = 'TODAS'


def _ir_desde_pastillas(key, destinos):
    elegido = st.session_state.get(key)
    if elegido in destinos:
        inc_id, periodo = destinos[elegido]
        _ir_a(inc_id, periodo, ver_todas=True)


def _nueva_lista():
    """Cambió un filtro: la selección vuelve a la primera de la lista nueva."""
    st.session_state.pop('cli_sel', None)
    st.session_state.pop('cli_rechazando', None)
    st.session_state.pop('cli_cambiando', None)
    st.session_state['cli_mas'] = TANDA_COLA


def _cambiar_periodo():
    _nueva_lista()
    st.session_state['periodo_id'] = st.session_state.get('cli_periodo')


def _ver_vista(vista):
    st.session_state['cli_vista'] = vista


# ============================================================
# Marco
# ============================================================
def render(usuario: dict, periodo_id: str):
    vista = st.session_state.get('cli_vista', 'validar')
    if vista not in TITULOS:
        vista = 'validar'
    r.html(CSS_CLIENTE.replace('clinav_ACTIVO', f'clinav_{vista}'))

    aviso = st.session_state.pop('cli_toast', None)
    if aviso:
        st.toast(aviso)

    try:
        periodos = get_periodos_director()
        todas = vc.preparar(get_series_incidencias())
    except Exception as e:
        # El detalle va al log; en pantalla, un mensaje que se entienda.
        print(f"[CLIENTE INICIO] {e}")
        st.error("No pudimos cargar las incidencias en este momento. Intenta recargar la página en unos segundos.")
        if st.button("Salir", key="cli_salir"):
            cerrar_sesion()
            st.rerun()
        return
    if len(periodos) == 0:
        st.warning("No hay datos cargados todavía.")
        return

    periodo_id = _periodo_inicial(periodos, todas, periodo_id)
    nav, cuerpo = st.columns([1, 4.9], gap="large")
    ctx = None
    with cuerpo:
        periodo_id = _encabezado(periodos, todas, periodo_id, vista)
        try:
            inc = vc.ordenar(vc.preparar(get_incidencias_validacion(periodo_id)))
            estructura = get_estructura_periodo(periodo_id)
        except Exception as e:
            print(f"[CLIENTE PERIODO] {periodo_id}: {e}")
            st.error("No pudimos leer las incidencias de este periodo. Si acaban de subir la v24, "
                     "revisa que ya se corrió el SQL 06_validacion_cliente_v24.sql.")
        else:
            ctx = _contexto(usuario, periodos, periodo_id, inc, todas, estructura)
            {'validar': _validar, 'seguimiento': _seguimiento, 'resumen': _resumen}[vista](ctx)
    with nav:
        _menu(usuario, vista, ctx)


def _contexto(usuario, periodos, periodo_id, inc, todas, estructura) -> dict:
    est = estructura if len(estructura) else pd.DataFrame(columns=['ruta', 'supervisor', 'area_manager'])
    marcas = vc.marcas_serie(todas)
    return {
        'usuario': usuario, 'periodos': periodos, 'periodo_id': periodo_id, 'inc': inc, 'todas': todas,
        'marcas': marcas, 'semanas': vc.semanas_en_orden(periodos),
        'ruta_sup': {r_: vc.texto(s) for r_, s in zip(est['ruta'], est['supervisor'])},
        'ruta_area': {r_: vc.texto(a) for r_, a in zip(est['ruta'], est['area_manager'])},
        'grupos': _grupos(todas, marcas, periodo_id),
    }


def _periodo_inicial(periodos, todas, periodo_id):
    """Al entrar, el mes con incidencias por validar más reciente de los dos
    últimos (en los primeros días del mes todavía se está validando el
    anterior). Si no hay, el último mes con incidencias."""
    ids = vc.orden_periodos(periodos)
    if not st.session_state.get('cli_periodo_listo'):
        st.session_state['cli_periodo_listo'] = True
        pend = set(todas.loc[todas['validacion_cliente'] == vc.PENDIENTE, 'periodo_id'])
        con_inc = [p for p in ids if p in set(todas['periodo_id'])]
        candidatos = [p for p in ids[-2:] if p in pend]
        periodo_id = candidatos[-1] if candidatos else (con_inc[-1] if con_inc else ids[-1])
    if periodo_id not in ids:
        periodo_id = ids[-1]
    st.session_state['periodo_id'] = periodo_id
    return periodo_id


def _menu(usuario, vista, ctx):
    nombre = vc.texto(usuario.get('nombre')) or vc.texto(usuario.get('username')) or 'Cliente'
    iniciales = ''.join(p[0] for p in nombre.split()[:2]).upper() or 'CL'
    r.html('<div class="vmarca"><div class="vlogo"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
           'stroke="#fff" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="9.2" cy="19.6" r="1.35"/>'
           '<circle cx="17.6" cy="19.6" r="1.35"/><path d="M2.6 3.6h2.5l2.3 10.9a1.7 1.7 0 0 0 1.7 1.3h8.3a1.7 1.7 0 0 0 1.6-1.3'
           'l1.5-6.6H6.1"/></svg></div><div><b>ATLAS</b><small>Perfect Store</small></div></div>'
           f'<div class="vyo"><div class="vav">{_e(iniciales)}</div><div><b>{_e(nombre)}</b>'
           '<span>Validación del cliente</span></div></div><p class="vnavt">INCIDENCIAS</p>')
    cuentas = {}
    if ctx is not None:
        cuentas = {'validar': int((ctx['inc']['validacion_cliente'] == vc.PENDIENTE).sum()),
                   'seguimiento': len(ctx['grupos'])}
    for vid, etiqueta, icono in VISTAS:
        n = cuentas.get(vid)
        st.button(f"{etiqueta} · {n}" if n else etiqueta, key=f"clinav_{vid}", icon=icono,
                  use_container_width=True, on_click=_ver_vista, args=(vid,))
    st.write("")
    if st.button("Actualizar datos", key="clilink_actualizar", icon=":material/refresh:", use_container_width=True):
        limpiar_cache_validacion(todo=True)
        st.rerun()
    if st.button("Salir", key="cli_salir", use_container_width=True):
        cerrar_sesion()
        st.rerun()
    r.html('<p class="vpie">Validar = por validar del mes.<br>Seguimiento = tiendas con el mismo KPI '
           'reclamado en varias semanas.</p>')


def _encabezado(periodos, todas, periodo_id, vista):
    izq, der = st.columns([2.2, 2])
    # Solo los meses que tienen incidencias: los de antes de que existieran (mayo,
    # junio, julio) no le dicen nada al cliente.
    orden = vc.orden_periodos(periodos)
    con_inc = set(todas['periodo_id'])
    ids = [p for p in orden if p in con_inc][-PERIODOS_VISIBLES:]
    ids = sorted(set(ids) | {periodo_id}, key=lambda p: orden.index(p) if p in orden else len(orden))
    pend = todas[todas['validacion_cliente'] == vc.PENDIENTE].groupby('periodo_id').size().to_dict()

    def etiqueta(pid):
        mes = _nombre_periodo(periodos, pid).split(' ')[0]
        return f"{mes} · {pend[pid]}" if pend.get(pid) else mes

    with der:
        r.html('<p class="vlbl" style="text-align:right">📅 Periodo · por validar</p>')
        st.session_state['cli_periodo__ok'] = periodo_id
        periodo_id = _control('Periodo', ids, 'cli_periodo', periodo_id, etiqueta, al_cambiar=_cambiar_periodo)
    fila = periodos[periodos['periodo_id'] == periodo_id]
    semanas = ''
    if len(fila):
        s_ini, s_fin = int(fila.iloc[0]['semana_inicio']), int(fila.iloc[0]['semana_fin'])
        semanas = f" · semana {s_ini}" if s_ini == s_fin else f" · semanas {s_ini}–{s_fin}"
    nombre = vc.texto((st.session_state.get('usuario') or {}).get('nombre')) or 'cliente'
    with izq:
        r.html(f'<div class="vtop"><div class="vhola">Hola, {_e(nombre)}</div><div class="vtit">{TITULOS[vista]}</div>'
               f'<div class="vsubt">{_e(_nombre_periodo(periodos, periodo_id))}{semanas}</div></div>')
    return periodo_id


# ============================================================
# VALIDAR
# ============================================================
def _validar(ctx):
    inc = ctx['inc']
    if len(inc) == 0:
        _vacio("Este periodo no tiene incidencias levantadas.")
        return
    col_cola, col_exp = st.columns([1.32, 3.1], gap="medium")
    with col_cola:
        visibles, sel = _cola(ctx)
    with col_exp:
        if sel is None:
            _vacio("No hay incidencias con este filtro.")
        else:
            _expediente(ctx, sel, visibles)


def _filtrar(ctx, estado, kpi):
    v = ctx['inc']
    if estado != 'TODAS':
        v = v[v['validacion_cliente'] == estado]
    if kpi == 'SOS':
        v = v[v['tipo'].str.startswith('SOS')]
    elif kpi != 'todos':
        v = v[v['tipo'] == kpi]
    q = vc.texto(st.session_state.get('cli_f_buscar')).upper()
    if q:
        v = v[v['tienda'].str.upper().str.contains(q, regex=False) | (v['curt'] == q)
              | v['ruta'].str.upper().str.contains(q, regex=False) | v['folio'].str.contains(q, regex=False)]
    areas = st.session_state.get('cli_f_area') or []
    if areas:
        v = v[v['ruta'].map(ctx['ruta_area']).isin(areas)]
    sup = st.session_state.get('cli_f_sup') or []
    if sup:
        v = v[v['estado'].isin(sup)]
    semanas = st.session_state.get('cli_f_semana') or []
    if semanas:
        v = v[v['semana'].isin(semanas)]
    if st.session_state.get('cli_f_repite'):
        v = v[v['id'].map(ctx['marcas']['semanas_serie']).fillna(1) > 1]
    return v


def _cola(ctx):
    inc = ctx['inc']
    n = len(inc)
    hechas = int((inc['validacion_cliente'] != vc.PENDIENTE).sum())
    avance = round(hechas / n * 100) if n else 0
    with st.container(border=True, key="vcard_cola"):
        r.html(f'<div class="vcola-h">Cola de validación<span>{hechas} de {n} validadas</span></div>'
               f'<div class="vbar"><i style="width:{avance}%"></i></div>')
        cuenta = inc['validacion_cliente'].value_counts()
        estado = _control('Estado', list(FILTRO_ESTADO), 'cli_f_estado', 'PENDIENTE',
                          lambda k: f"{FILTRO_ESTADO[k]} · {n if k == 'TODAS' else int(cuenta.get(k, 0))}",
                          al_cambiar=_nueva_lista)
        kpi = _control('KPI', list(FILTRO_KPI), 'cli_f_kpi', 'todos', FILTRO_KPI.get, al_cambiar=_nueva_lista)
        st.text_input("Buscar", key="cli_f_buscar", placeholder="Tienda, CURT, promotor o folio",
                      label_visibility="collapsed", on_change=_nueva_lista, icon=":material/search:")
        activos = sum(bool(st.session_state.get(k)) for k in ('cli_f_area', 'cli_f_sup', 'cli_f_semana', 'cli_f_repite'))
        with st.popover(f"Más filtros · {activos}" if activos else "Más filtros", icon=":material/tune:",
                        use_container_width=True):
            areas = sorted({a for a in ctx['ruta_area'].values() if a})
            st.multiselect("Área", areas, key="cli_f_area", on_change=_nueva_lista, placeholder="Todas")
            st.multiselect("Lo que dijo el supervisor", list(SUPERVISOR), format_func=SUPERVISOR.get,
                           key="cli_f_sup", on_change=_nueva_lista, placeholder="Todo")
            semanas = sorted(int(s) for s in inc['semana'].dropna().unique())
            st.multiselect("Semana", semanas, format_func=lambda s: f"S{s}", key="cli_f_semana",
                           on_change=_nueva_lista, placeholder="Todas")
            st.toggle("Solo las que se repiten", key="cli_f_repite", on_change=_nueva_lista)

        visibles = _filtrar(ctx, estado, kpi)
        ids = visibles['id'].tolist()
        sel_id = st.session_state.get('cli_sel')
        if sel_id not in set(inc['id']):
            sel_id = ids[0] if ids else None
            st.session_state['cli_sel'] = sel_id
        mostrar = st.session_state.get('cli_mas', TANDA_COLA)
        if len(visibles) == 0:
            _vacio("No hay incidencias con este filtro.")
        with st.container(height=640, border=False, key="vcola_lista"):
            for _, f in visibles.head(mostrar).iterrows():
                _clic(f"q{f['id']}", _tarjeta_cola(ctx, f, f['id'] == sel_id), f"Abrir {f['folio']}",
                      _ir_a, (int(f['id']),))
            if len(visibles) > mostrar:
                r.html(f'<div class="vcuenta">Van {mostrar} de {len(visibles)}</div>')
                if st.button(f"Ver {min(TANDA_COLA, len(visibles) - mostrar)} más", key="cli_mas_btn",
                             use_container_width=True):
                    st.session_state['cli_mas'] = mostrar + TANDA_COLA
                    st.rerun()
    sel = inc[inc['id'] == sel_id]
    return visibles, (sel.iloc[0] if len(sel) else None)


def _tarjeta_cola(ctx, f, activo) -> str:
    est_txt, tono = ESTADO_CLIENTE[f['validacion_cliente']]
    sup = SUPERVISOR.get(f['estado'], 'Sin revisar')
    quien = _supervisor(ctx, f)
    if f['estado'] == 'AUTORIZADA':
        sup_html = f'<span class="vsup-ok">✓ {sup} por {_e(quien)}</span>'
    elif f['estado'] == 'NO_AUTORIZADA':
        sup_html = f'<span class="vsup-no">✕ No la autorizó {_e(quien)}</span>'
    else:
        sup_html = f'<span class="vsup-p">◷ Sin revisar por {_e(quien)}</span>'
    marca = ctx['marcas'].loc[f['id']] if f['id'] in ctx['marcas'].index else None
    extra = ''
    if marca is not None and marca['semanas_serie'] > 1:
        extra += f'<span class="vt vt-rosa">Se repite · {int(marca["semanas_serie"])}</span>'
    if marca is not None and marca['iguales'] > 1:
        extra += f'<span class="vt vt-y">Duplicada · {int(marca["iguales"])}</span>'
    semana = f"S{int(f['semana'])}" if pd.notna(f['semana']) else 'sin semana'
    kpi_cls = 'vt-rosa' if f['tipo'] == 'OOS' else 'vt-b'
    return (f'<div class="vq{" vq-act" if activo else ""}">'
            f'<div class="vq-top"><span>{f["folio"]} · {semana}</span><span class="vp vp-{tono}">{est_txt}</span></div>'
            f'<div class="vq-t">{_e(f["tienda"]) or "CURT " + _e(f["curt"])}</div>'
            f'<div class="vq-m"><span class="vt {kpi_cls}">{vc.KPI_NOMBRE.get(f["tipo"], _e(f["tipo"]))}</span>'
            f'<span>{_e(f["ruta"])}</span></div>'
            f'<div class="vq-m">{sup_html}{extra}</div></div>')


# ------------------------------------------------------------
# Expediente
# ------------------------------------------------------------
def _expediente(ctx, f, visibles):
    # El expediente ya está dentro de una columna que está dentro de otra, y Streamlit
    # 1.45 no deja anidar más columnas: sus renglones son contenedores que el CSS
    # acomoda en fila (st-key-vfila_ y st-key-vpar_).
    ids = visibles['id'].tolist()
    pos = ids.index(f['id']) if f['id'] in ids else None
    txt = (f"Incidencia {pos + 1} de {len(ids)} en la lista" if pos is not None
           else "Esta incidencia no está en la lista con los filtros de ahora")
    with st.container(key="vfila_pos"):
        r.html(f'<div class="vpos vcrece">{txt}</div>')
        if ids:
            ant = ids[(pos - 1) % len(ids)] if pos is not None else ids[0]
            sig = ids[(pos + 1) % len(ids)] if pos is not None else ids[0]
            st.button("‹ Anterior", key="clilink_ant", on_click=_ir_a, args=(ant,),
                      disabled=len(ids) < 2 and pos is not None)
            st.button("Siguiente ›", key="clilink_sig", on_click=_ir_a, args=(sig,),
                      disabled=len(ids) < 2 and pos is not None)

    aviso = st.session_state.pop('cli_aviso', None)
    if aviso:
        r.html(f'<div class="vaviso">⚠️ <span>{_e(aviso)}</span></div>')

    try:
        k = get_kpis_tiendas((f['curt'],))
    except Exception as e:
        print(f"[CLIENTE KPIS] {f['curt']}: {e}")
        k = None
    rt_mes = None
    if k is not None and len(k['rt']):
        fila = k['rt'][k['rt']['periodo_id'] == f['periodo_id']]
        rt_mes = fila.iloc[0] if len(fila) else None

    _hero(ctx, f, rt_mes)
    with st.container(key="vpar_exp"):
        with st.container(key="vcol_evid"):
            _evidencia(f)
        with st.container(key="vcol_recl"):
            _reclamo(f)
    _seguimiento_bloque(ctx, f, k)
    _datos(ctx, f, k, rt_mes)
    _historia(ctx, f)
    _decision(ctx, f, visibles)


def _hero(ctx, f, rt_mes):
    est_txt, tono = ESTADO_CLIENTE[f['validacion_cliente']]
    color = {'y': '#98580E', 'g': '#1E5C36', 'r': '#B5303F'}[tono]
    marca = ctx['marcas'].loc[f['id']] if f['id'] in ctx['marcas'].index else None
    chips = (f'<span>{f["folio"]}</span>'
             f'<span class="vchip">{vc.KPI_NOMBRE.get(f["tipo"], _e(f["tipo"]))}'
             + (f' · semana {int(f["semana"])}' if pd.notna(f['semana']) else '') + '</span>'
             f'<span class="vchip-b" style="color:{color}">{est_txt}</span>')
    if marca is not None and marca['semanas_serie'] > 1:
        chips += f'<span class="vchip-b" style="color:#B83D7A">Se repite · {int(marca["semanas_serie"])} semanas</span>'
    if marca is not None and marca['iguales'] > 1:
        chips += f'<span class="vchip-b" style="color:#98580E">Duplicada · {int(marca["iguales"])} en la misma semana</span>'
    datos_tienda = [f"CURT {_e(f['curt'])}"]
    canal = f['canal'] or (vc.texto(rt_mes.get('canal')) if rt_mes is not None else '')
    cadena = f['cadena'] or (vc.texto(rt_mes.get('cadena')) if rt_mes is not None else '')
    if canal:
        datos_tienda.append(_e(canal.capitalize()))
    if cadena:
        datos_tienda.append(_e(cadena.title()))
    if rt_mes is not None:
        datos_tienda.append('hoy es Perfect Store' if vc.si(rt_mes.get('es_ps')) else 'hoy no es Perfect Store')
    sup = ctx['ruta_sup'].get(f['ruta'], '')
    area = ctx['ruta_area'].get(f['ruta'], '')
    gente = [f"Promotor {_e(f['ruta'])}"]
    if sup:
        gente.append(f"Supervisor {_e(sup.split('@')[0])}")
    if area:
        gente.append(_e(area))
    fechas = _fechas_semana(ctx['periodos'], f['periodo_id'], f['semana'])
    if fechas:
        gente.append(f"Semana {int(f['semana'])}: {fechas}")
    r.html(f'<div class="vhero"><div class="vhero-c">{chips}</div>'
           f'<div class="vhero-t">{_e(f["tienda"]) or "Tienda sin nombre"}</div>'
           f'<div class="vhero-s">{" · ".join(datos_tienda)}</div>'
           f'<div class="vhero-s">{" · ".join(gente)}</div></div>')


@st.dialog("Evidencia", width="large")
def _ver_foto(url, titulo):
    r.html(f'<div class="vdec-t">{_e(titulo)}</div>')
    st.image(url, use_container_width=True)
    r.html(f'<a class="vtrax" href="{_e(url)}" target="_blank" rel="noopener noreferrer">Abrir la foto en otra pestaña</a>')


def _evidencia(f):
    fotos = [u for u in (_url_segura(x) for x in f['fotos']) if u][:3]
    with st.container(border=True, key="vcard_evid"):
        r.html(_titulo(1, 'Evidencia', '1 foto' if len(fotos) == 1 else f'{len(fotos)} fotos'))
        if fotos:
            with st.container(key="vpar_fotos"):
                for i, url in enumerate(fotos):
                    if _clic(f"foto{f['id']}_{i}",
                             f'<div class="vfoto"><img src="{_e(url)}" alt="Foto {i + 1}" loading="lazy">'
                             f'<span>Foto {i + 1} · ampliar</span></div>', f"Ampliar la foto {i + 1}"):
                        _ver_foto(url, f"{f['folio']} · foto {i + 1} de {len(fotos)}")
        else:
            _vacio("Esta incidencia no trae fotos.")
        trax = _url_segura(f['url_trax'])
        if trax:
            r.html(f'<a class="vtrax" href="{_e(trax)}" target="_blank" rel="noopener noreferrer">'
                   '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                   'stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5'
                   'a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>Abrir la visita en TRAX</a>')
        else:
            r.html('<div class="vtrax vtrax-no">Sin link de TRAX</div>')


def _reclamo(f):
    motivo = etiqueta_motivo(f['incidencia']) or 'Sin motivo (incidencia anterior a v13)'
    prods = f['productos']
    if prods:
        if 'TODOS' in prods:
            chips = f'<span class="vt vt-rosa">Todos los de {_e(f["categoria"].lower() or "la categoría")}</span>'
        else:
            chips = ''.join(f'<span class="vt vt-rosa">{_e(p)}</span>' for p in prods)
        prods_html = f'<div class="vlab">Productos que señala</div><div class="vchips">{chips}</div>'
    else:
        prods_html = ''
    comentario = _parrafos(f['comentario']) or '<span style="color:#9AA6D1">Sin comentario.</span>'
    cuando = vc.fecha_corta(f['created_at'])
    r.html(f'<div class="vcard">{_titulo(2, "Qué reclama")}'
           f'<div class="vlab">Motivo</div><div class="vmot">{_e(motivo)}</div>'
           f'<div class="vcom">“{comentario}”</div>{prods_html}'
           f'<div class="vquien">Levantada por {_e(f["ruta"])}' + (f' · {cuando}' if cuando else '') + '</div></div>')


def _valor_celda(tipo, v) -> tuple:
    """(texto, clase de color) de una semana en la tira."""
    if not v:
        return '—', 'vc-n'
    if v.get('trax'):
        return 'incidencia TRAX', 'vc-n'
    if v.get('sin_dato'):
        return '—', 'vc-n'
    if tipo == 'OOS':
        if v['sin_obj']:
            return 'sin encuestas', 'vc-n'
        return ('todas contestadas', 'vc-g') if v['nc'] == 0 else (f"{v['nc']} sin contestar", 'vc-r')
    if v['ok'] is None:
        return vc.valor_txt(tipo, v['v']), 'vc-n'
    return vc.valor_txt(tipo, v['v']), 'vc-g' if v['ok'] else 'vc-r'


def _estado_corto(estado) -> tuple:
    return {vc.APROBADA: ('aprobada', 'vt-g'), vc.NO_APROBADA: ('no aprobada', 'vt-r'),
            vc.PENDIENTE: ('por validar', 'vt-y')}.get(estado, ('por validar', 'vt-y'))


def _tira_html(ctx, t, tipo) -> str:
    celdas = ''
    for c in t['celdas']:
        valor, clase = _valor_celda(tipo, c['valor'])
        incs = c['incidencias']
        if incs:
            principal = next((x for x in incs if c['actual'] and x['id'] == c.get('_actual_id')), incs[0])
            txt, cls = _estado_corto(principal['validacion_cliente'])
            if len(incs) > 1:
                txt += f" ×{len(incs)}"
            if c['actual']:
                txt = 'esta · ' + txt
            estado = f'<span class="vt {cls}">{txt}</span>'
        else:
            estado = '<span class="vt vt-n">sin incidencia</span>'
        caja = 'vtc-act' if c['actual'] else ('vtc-inc' if incs else 'vtc-sin')
        mes = vc.mes_corto(ctx['periodos'], c['periodo'])
        celdas += (f'<div class="vtc {caja}"><div class="vtc-s">S{c["semana"]} <span>· {_e(mes)}</span></div>'
                   f'<div class="vtc-v {clase}">{_e(valor)}</div><div class="vtc-e">{estado}</div></div>')
    return f'<div class="vtira">{celdas}</div>'


def _seguimiento_bloque(ctx, f, k):
    serie = vc.serie_de(ctx['todas'], f['curt'], f['tipo'])
    n_sem = serie.dropna(subset=['semana']).drop_duplicates(['periodo_id', 'semana']).shape[0]
    otras = serie[serie['id'] != f['id']]
    kpi = vc.KPI_NOMBRE.get(f['tipo'], f['tipo'])
    if n_sem <= 1:
        dup = ''
        if len(otras):
            dup = (f'<div class="vlect" style="margin-top:10px">Hay otra incidencia de esta tienda, KPI y semana: '
                   + ', '.join(f"{o['folio']} ({_estado_corto(o['validacion_cliente'])[0]})" for _, o in otras.iterrows())
                   + '. Si dicen lo mismo, basta con aprobar una.</div>')
        r.html(f'<div class="vcard">{_titulo(3, "Seguimiento · misma tienda, mismo KPI", "1 semana")}'
               f'<div style="font-size:14px;color:#6B7BB8">Es la primera semana en que se reclama {_e(kpi)} en esta '
               f'tienda.</div>{dup}</div>')
        if len(otras):
            _pastillas_serie(ctx, f, otras)
        return
    valores = vc.valores_semana(k['ds'], k['os'], f['tipo']) if k is not None else {}
    t = vc.tira(serie, valores, ctx['semanas'], f['id'])
    for c in t['celdas']:
        c['_actual_id'] = f['id']
    with st.container(border=True, key="vcard_seg"):
        r.html(_titulo(3, "Seguimiento · misma tienda, mismo KPI", f"{len(serie)} incidencias · {n_sem} semanas"))
        r.html(_tira_html(ctx, t, f['tipo']))
        lect = vc.lecturas(serie, t, f['tipo'], f['incidencia'])
        r.html('<div class="vlect">' + ''.join(f'<div>{_e(x)}</div>' for x in lect) + '</div>')
        if len(otras):
            _pastillas_serie(ctx, f, otras)


def _pastillas_serie(ctx, f, otras):
    """Para brincar a otra incidencia de la misma serie (puede ser de otro mes)."""
    destinos = {}
    for _, o in otras.iterrows():
        sem = f"S{int(o['semana'])}" if pd.notna(o['semana']) else 's/semana'
        etiqueta = f"{sem} · {vc.mes_corto(ctx['periodos'], o['periodo_id'])} · {o['folio']}"
        destinos[etiqueta] = (int(o['id']), o['periodo_id'])
    key = f"viraser_{f['id']}"
    with st.container(key=f"viraser_c{f['id']}"):
        r.html('<div class="vlab" style="margin-top:10px">Abrir otra de la serie</div>')
        st.pills("Abrir otra de la serie", list(destinos), key=key, label_visibility="collapsed",
                 on_change=_ir_desde_pastillas, args=(key, destinos))


def _barras(ctx, f, valores_mes, semanas_mes) -> str:
    """Las semanas del mes contra el objetivo, con la reclamada marcada."""
    tipo = f['tipo']
    vals = [v['v'] for v in valores_mes.values() if v.get('v') is not None]
    obj = next((v['obj'] for v in valores_mes.values() if v.get('obj') is not None), None)
    sin_obj = obj is None or obj <= 0
    tope = max(vals + [0 if sin_obj else obj, 5 if tipo == 'EXHIBICIONES' else 1]) * 1.2
    alto = 128
    cols, etiquetas = '', ''
    for s in semanas_mes:
        v = valores_mes.get((f['periodo_id'], s))
        rec = pd.notna(f['semana']) and s == int(f['semana'])
        if not v or v.get('v') is None:
            txt = 'TRAX' if v and v.get('trax') else '—'
            cols += (f'<div class="vbars-col{" vbars-rec" if rec else ""}"><b style="color:#9AA6D1">{txt}</b>'
                     f'<i style="height:4px;background:#DCE4F5"></i></div>')
        else:
            h = max(4, round(v['v'] / tope * alto))
            if v['ok'] is None:
                color = '#9AA6D1'
            elif v['ok']:
                color = '#2D8A4E'
            elif not sin_obj and v['v'] >= obj * 0.85:
                color = '#E8A53D'
            else:
                color = '#D94557'
            cols += (f'<div class="vbars-col{" vbars-rec" if rec else ""}"><b>{vc.valor_txt(tipo, v["v"])}</b>'
                     f'<i style="height:{h}px;background:{color}"></i></div>')
        etiquetas += f'<div class="{"vrec" if rec else ""}">S{s}{" · reclamada" if rec else ""}</div>'
    linea = ''
    if not sin_obj:
        linea = (f'<div class="vbars-obj" style="bottom:{round(obj / tope * alto)}px">'
                 f'<span>objetivo {vc.objetivo_txt(tipo, obj)}</span></div>')
    return f'<div><div class="vbars">{linea}{cols}</div><div class="vbars-lab">{etiquetas}</div></div>'


def _datos(ctx, f, k, rt_mes):
    tipo, per = f['tipo'], f['periodo_id']
    if k is None:
        r.html(f'<div class="vcard">{_titulo(4, "Qué dicen los datos")}'
               '<div class="vvacio">No pudimos leer lo que midió TRAX en esta tienda. Intenta con "Actualizar datos".</div></div>')
        return
    ds_mes = k['ds'][k['ds']['periodo_id'] == per] if len(k['ds']) else k['ds']
    os_mes = k['os'][k['os']['periodo_id'] == per] if len(k['os']) else k['os']
    valores = vc.valores_semana(ds_mes, os_mes, tipo)
    semanas_mes = [s for p, s in ctx['semanas'] if p == per]
    mes = vc.mes_kpi(rt_mes, os_mes, tipo)
    kpi = vc.KPI_NOMBRE.get(tipo, tipo)

    if tipo == 'OOS':
        sub = 'Encuestas de agotados de esta tienda, por semana'
        tarjetas = ''
        for s in semanas_mes:
            v = valores.get((per, s))
            rec = pd.notna(f['semana']) and s == int(f['semana'])
            if not v:
                cls, grande, chico = 'voos-n', '—', 'sin datos'
            elif v['sin_obj']:
                cls, grande, chico = 'voos-n', '0', 'sin encuestas'
            else:
                cls = 'voos-ok' if v['nc'] == 0 else 'voos-no'
                grande = f"{v['cont']} de {v['obj']}"
                chico = 'todas contestadas' if v['nc'] == 0 else f"{v['nc']} sin contestar"
            tarjetas += (f'<div class="{cls}{" voos-rec" if rec else ""}"><span class="vlab">Semana {s}'
                         f'{" · la reclamada" if rec else ""}</span><b>{grande}</b><span>{chico}</span></div>')
        if mes and not mes['sin_obj']:
            total = (f'<div class="vmes-n" style="margin-top:10px">En el mes: {mes["cont"]} de {mes["obj"]} contestadas'
                     f' · {mes["nc"]} sin contestar.</div>')
        else:
            total = ''
        cuerpo = f'<div class="voos">{tarjetas}</div>{total}'
    else:
        sub = ('Puntos de exhibición por semana contra su objetivo' if tipo == 'EXHIBICIONES'
               else 'SOS por semana contra el objetivo de esta tienda')
        if mes is None:
            panel = '<div class="vmes"><div class="vmes-n">Sin resumen del mes para esta tienda.</div></div>'
        else:
            if mes['ok']:
                pill = '<span class="vp vp-g">Cumple</span>'
            elif mes['sin_obj']:
                pill = '<span class="vp vp-n">Sin objetivo</span>'
            else:
                pill = '<span class="vp vp-r">No cumple</span>'
            obj_txt = ('Sin objetivo cargado.' if mes['sin_obj']
                       else f"Objetivo de la tienda: {vc.objetivo_txt(tipo, mes['obj'])}.")
            titulo_mes = 'Promedio del mes' if tipo == 'EXHIBICIONES' else f'{kpi} del mes'
            panel = (f'<div class="vmes"><div class="vlab">{titulo_mes} · última corrida</div>'
                     f'<div class="vmes-v">{vc.valor_txt(tipo, mes["v"])}</div><div>{pill}</div>'
                     f'<div class="vmes-n">{obj_txt} {_e(mes["nota"])}</div></div>')
        cuerpo = f'<div class="vdatos">{_barras(ctx, f, valores, semanas_mes)}{panel}</div>'

    hist = vc.historia_meses(k['rt'], k['os'], tipo, ctx['periodos'], per)
    pills = ''.join(f'<span class="vp {"vp-g" if h["ok"] else ("vp-n" if h["ok"] is None else "vp-r")}">'
                    f'{_e(h["mes"])}: {_e(h["texto"])}</span>' for h in hist)
    hist_html = f'<div class="vhist">En los últimos meses {pills}</div>' if pills else ''

    hechos_html = ''
    if f['validacion_cliente'] == vc.PENDIENTE and pd.notna(f['semana']):
        es_ps = rt_mes is not None and vc.si(rt_mes.get('es_ps'))
        lista = vc.hechos(tipo, int(f['semana']), valores.get((per, int(f['semana']))), mes, es_ps)
        if lista:
            hechos_html = ('<div class="vhechos"><div class="vlab">Antes de decidir</div>'
                           + ''.join(f'<div class="vhecho vhecho-{tono}"><i></i><span>{_e(t)}</span></div>'
                                     for tono, t in lista) + '</div>')
    r.html(f'<div class="vcard">{_titulo(4, "Qué dicen los datos", sub)}{cuerpo}{hist_html}{hechos_html}</div>')


def _historia(ctx, f):
    def punto(color, hueco=False):
        return f'border:2px solid {color}' if hueco else f'background:{color}'

    items = [(punto('#4F7BE8'), f"Levantada por {f['ruta']}", vc.fecha_corta(f['created_at']))]
    quien = _supervisor(ctx, f)
    if f['estado'] == 'AUTORIZADA':
        items.append((punto('#2D8A4E'), f"Autorizada por {quien}", vc.fecha_corta(f['resuelta_en'])))
    elif f['estado'] == 'NO_AUTORIZADA':
        detalle = vc.fecha_corta(f['resuelta_en'])
        if f['motivo_rechazo']:
            detalle += f" · “{f['motivo_rechazo']}”"
        items.append((punto('#D94557'), f"No la autorizó {quien}", detalle))
    else:
        items.append((punto('#E8A53D'), f"Sin revisar por {quien}", 'El supervisor todavía no la autoriza ni la rechaza.'))

    hist = get_historial_incidencia(int(f['id']))
    if len(hist):
        for _, h in hist.iterrows():
            dec, por = vc.texto(h.get('decision')), vc.texto(h.get('por')) or 'el cliente'
            cuando = vc.fecha_corta(h.get('creado_at'))
            if dec == vc.APROBADA:
                items.append((punto('#2D8A4E'), f"Aprobada por {por}", cuando))
            elif dec == vc.NO_APROBADA:
                detalle = cuando + (f" · {vc.texto(h.get('motivo'))}" if vc.texto(h.get('motivo')) else '')
                if vc.texto(h.get('comentario')):
                    detalle += f" · “{vc.texto(h.get('comentario'))}”"
                items.append((punto('#D94557'), f"No aprobada por {por}", detalle))
            else:
                items.append((punto('#9AA6D1'), f"{por} la regresó a por validar", cuando))
    elif f['validacion_cliente'] != vc.PENDIENTE:
        # Decisiones que llegaron sin historial (las de agosto, cargadas del Excel).
        por = f['validada_por'] or 'el cliente'
        detalle = vc.fecha_corta(f['validada_en']) or 'sin fecha'
        if f['validacion_cliente'] == vc.APROBADA:
            items.append((punto('#2D8A4E'), f"Aprobada por {por}", detalle))
        else:
            if f['motivo_cliente']:
                detalle += f" · {f['motivo_cliente']}"
            items.append((punto('#D94557'), f"No aprobada por {por}", detalle))
    if f['validacion_cliente'] == vc.PENDIENTE:
        items.append((punto('#E8A53D', hueco=True), 'Por validar', 'Falta la decisión del cliente.'))
    filas = ''.join(f'<div class="vtl-i"><i style="{estilo}"></i><div><b>{_e(t)}</b><span>{_e(d)}</span></div></div>'
                    for estilo, t, d in items)
    r.html(f'<div class="vcard">{_titulo(5, "Historia de esta incidencia")}<div class="vtl">{filas}</div></div>')


# ------------------------------------------------------------
# Decisión
# ------------------------------------------------------------
def _siguiente_pendiente(visibles, actual_id):
    """La siguiente por validar de la lista, dando la vuelta; None si no queda."""
    ids = visibles['id'].tolist()
    estados = dict(zip(visibles['id'], visibles['validacion_cliente']))
    if not ids:
        return None
    ini = ids.index(actual_id) if actual_id in ids else -1
    for paso in range(1, len(ids) + 1):
        cand = ids[(ini + paso) % len(ids)]
        if cand != actual_id and estados.get(cand) == vc.PENDIENTE:
            return cand
    return None


def _decidir(ctx, f, decision, visibles, motivo=None, comentario=None):
    usuario = ctx['usuario']
    por = vc.texto(usuario.get('username')) or vc.texto(usuario.get('identificador')) or 'cliente'
    siguiente = _siguiente_pendiente(visibles, f['id']) if decision != vc.PENDIENTE else None
    try:
        fila = validar_incidencia(int(f['id']), decision, por, f['validacion_cliente'], motivo, comentario)
    except Exception as e:
        print(f"[CLIENTE VALIDAR] {f['id']}: {e}")
        st.error("No se pudo guardar la decisión. Revisa tu conexión e intenta otra vez.")
        return
    limpiar_cache_validacion()
    st.session_state.pop('cli_rechazando', None)
    st.session_state.pop('cli_cambiando', None)
    if fila is None:
        st.session_state['cli_aviso'] = ("Alguien más cambió esta incidencia mientras la revisabas. "
                                         "Te enseño cómo quedó; si hace falta, decide otra vez.")
    else:
        txt = {vc.APROBADA: 'aprobada', vc.NO_APROBADA: 'no aprobada', vc.PENDIENTE: 'otra vez por validar'}[decision]
        st.session_state['cli_toast'] = f"{f['folio']} {txt}"
        if siguiente is not None:
            st.session_state['cli_sel'] = siguiente
    st.rerun()


def _decision(ctx, f, visibles):
    estado = f['validacion_cliente']
    rechazando = st.session_state.get('cli_rechazando') == f['id']
    cambiando = st.session_state.get('cli_cambiando') == f['id']
    with st.container(key="vdecide"):
        if rechazando:
            r.html('<div class="vdec-t">¿Por qué no se aprueba?</div>')
            motivo = st.pills("Motivo", vc.MOTIVOS_NO, key=f"cli_motivo_{f['id']}", label_visibility="collapsed")
            comentario = st.text_area("Comentario para el promotor (opcional; obligatorio con «Otro»)",
                                      key=f"cli_coment_{f['id']}", height=80, max_chars=500,
                                      placeholder="Por ejemplo: la foto no deja ver el anaquel completo.")
            with st.container(key="vfila_dec"):
                confirmar = st.button("Confirmar: no aprobada", key="vdec_confirmar", disabled=not motivo)
                cancelar = st.button("Cancelar", key="vdec_cancelar")
            if cancelar:
                st.session_state.pop('cli_rechazando', None)
                st.rerun()
            if confirmar:
                if motivo == vc.MOTIVO_OTRO and not vc.texto(comentario):
                    st.error("Con «Otro», escribe en el comentario por qué no se aprueba.")
                else:
                    _decidir(ctx, f, vc.NO_APROBADA, visibles, motivo, vc.texto(comentario))
        elif estado == vc.PENDIENTE or cambiando:
            pendiente = cancelar = False
            with st.container(key="vfila_dec"):
                aprobar = st.button("Aprobar", key="vdec_aprobar", icon=":material/check:")
                no_aprobar = st.button("No aprobar", key="vdec_no", icon=":material/close:")
                if cambiando:
                    pendiente = st.button("Dejarla por validar", key="vdec_pend")
                    cancelar = st.button("Cancelar", key="vdec_cancel2")
                else:
                    r.html('<div class="vdec-s vcrece">Al decidir pasa sola a la siguiente por validar.</div>')
            if aprobar:
                if estado == vc.APROBADA:
                    st.session_state.pop('cli_cambiando', None)
                    st.rerun()
                _decidir(ctx, f, vc.APROBADA, visibles)
            if no_aprobar:
                st.session_state['cli_rechazando'] = f['id']
                st.rerun()
            if pendiente:
                _decidir(ctx, f, vc.PENDIENTE, visibles)
            if cancelar:
                st.session_state.pop('cli_cambiando', None)
                st.rerun()
        else:
            txt, tono = ESTADO_CLIENTE[estado]
            detalle = f"Por {_e(f['validada_por'] or 'el cliente')}"
            if f['validada_en']:
                detalle += f" · {vc.fecha_corta(f['validada_en'])}"
            if estado == vc.NO_APROBADA and f['motivo_cliente']:
                detalle += f" · Motivo: {_e(f['motivo_cliente'])}"
            if f['comentario_cliente']:
                detalle += f" · “{_e(f['comentario_cliente'])}”"
            with st.container(key="vfila_dec"):
                r.html(f'<div class="vdec-r vcrece"><span class="vp vp-{tono}">{txt}</span><span>{detalle}</span></div>')
                cambiar = st.button("Cambiar decisión", key="vdec_cambiar")
            if cambiar:
                st.session_state['cli_cambiando'] = f['id']
                st.rerun()


# ============================================================
# SEGUIMIENTO
# ============================================================
def _grupos(todas, marcas, periodo_id) -> list:
    """Las series (misma tienda y KPI) con incidencias en 2 o más semanas y al
    menos una en este periodo. Primero las que tienen más por validar."""
    if len(todas) == 0:
        return []
    t = todas.join(marcas['semanas_serie'], on='id')
    del_mes = t[(t['periodo_id'] == periodo_id) & (t['semanas_serie'] > 1)]
    grupos = []
    for (curt, tipo), sub in del_mes.groupby(['curt', 'tipo']):
        serie = t[(t['curt'] == curt) & (t['tipo'] == tipo)]
        grupos.append({'curt': curt, 'tipo': tipo, 'semanas': int(sub['semanas_serie'].iloc[0]),
                       'pendientes': int((serie['validacion_cliente'] == vc.PENDIENTE).sum()),
                       'ultima': sub.sort_values(['semana', 'id']).iloc[-1]})
    return sorted(grupos, key=lambda g: (-g['pendientes'], -g['semanas'], g['curt'], g['tipo']))


def _seguimiento(ctx):
    grupos = ctx['grupos']
    r.html('<div class="vaviso vaviso-azul">🔁 <span>Tiendas donde el mismo KPI se reclamó en más de una semana, contando '
           'meses anteriores. <b>Si el motivo se repite cada semana, conviene resolverlo de raíz con TRAX</b> (catálogo o '
           'imagen) en vez de validarlo semana por semana.</span></div>')
    if not grupos:
        _vacio("En este periodo ninguna tienda tiene el mismo KPI reclamado en más de una semana.")
        return
    mostrar = st.session_state.get('cli_seg_n', TANDA_SEGUIMIENTO)
    visibles = grupos[:mostrar]
    try:
        k = get_kpis_tiendas(tuple(sorted({g['curt'] for g in visibles})))
    except Exception as e:
        print(f"[CLIENTE SEGUIMIENTO] {e}")
        k = None
    inc_mes = ctx['inc'].set_index('id')
    for i, g in enumerate(visibles):
        serie = vc.serie_de(ctx['todas'], g['curt'], g['tipo'])
        ult = g['ultima']
        if k is not None:
            valores = vc.valores_semana(k['ds'][k['ds']['curt'].astype(str) == g['curt']],
                                        k['os'][k['os']['curt'].astype(str) == g['curt']], g['tipo'])
        else:
            valores = {}
        t = vc.tira(serie, valores, ctx['semanas'], None)
        lect = vc.lecturas(serie, t, g['tipo'], ult['incidencia'])
        cuenta = serie['validacion_cliente'].value_counts()
        tienda = inc_mes.loc[ult['id'], 'tienda'] if ult['id'] in inc_mes.index else ''
        ruta = inc_mes.loc[ult['id'], 'ruta'] if ult['id'] in inc_mes.index else ''
        sup = ctx['ruta_sup'].get(ruta, '').split('@')[0]
        kpi_cls = 'vt-rosa' if g['tipo'] == 'OOS' else 'vt-b'
        with st.container(border=True, key=f"vcard_grupo{i}"):
            izq, der = st.columns([5, 1.25])
            with izq:
                r.html(f'<div class="vgrupo"><div class="vq-m"><span class="vt {kpi_cls}">'
                       f'{vc.KPI_NOMBRE.get(g["tipo"], _e(g["tipo"]))}</span>'
                       f'<span class="vt vt-rosa">{g["semanas"]} semanas con incidencia</span></div>'
                       f'<div class="vgrupo-t">{_e(tienda) or "CURT " + _e(g["curt"])}</div>'
                       f'<div class="vq-m">{_e(ruta)}' + (f' · supervisor {_e(sup)}' if sup else '')
                       + f' · CURT {_e(g["curt"])}</div>{_tira_html(ctx, t, g["tipo"])}'
                       f'<div class="vq-m" style="color:#1F2A5C">{_e(lect[1] if len(lect) > 1 else lect[0])}</div></div>')
            with der:
                r.html(f'<div class="vcuenta" style="text-align:right">{int(cuenta.get(vc.APROBADA, 0))} aprobadas · '
                       f'{int(cuenta.get(vc.NO_APROBADA, 0))} no aprobadas · {int(cuenta.get(vc.PENDIENTE, 0))} por validar</div>')
                st.button(f"Abrir la de la S{int(ult['semana'])}", key=f"cliabrir_{i}", use_container_width=True,
                          on_click=_ir_a, args=(int(ult['id']), ctx['periodo_id'], True))
    if len(grupos) > mostrar:
        if st.button(f"Ver {min(TANDA_SEGUIMIENTO, len(grupos) - mostrar)} más", key="cli_seg_mas_btn"):
            st.session_state['cli_seg_n'] = mostrar + TANDA_SEGUIMIENTO
            st.rerun()


# ============================================================
# RESUMEN
# ============================================================
def _pct(a, b) -> str:
    return f"{round(a / b * 100)}%" if b else '—'


def _resumen(ctx):
    inc = ctx['inc']
    R = vc.resumen(inc, ctx['ruta_area'])
    if R['total'] == 0:
        _vacio("Este periodo no tiene incidencias levantadas.")
        return
    r.html('<div class="vheroR">'
           f'<div><span>Incidencias del mes</span><b>{R["total"]}</b><small>levantadas por los promotores</small></div>'
           f'<div><span>Por validar</span><b>{R["pendientes"]}</b><small>'
           + ('ya no falta ninguna' if R['pendientes'] == 0 else f'faltan {R["pendientes"]}') + '</small></div>'
           f'<div><span>Aprobadas</span><b>{R["aprobadas"]}</b><small>{_pct(R["aprobadas"], R["total"])} del total</small></div>'
           f'<div><span>No aprobadas</span><b>{R["no_aprobadas"]}</b><small>{_pct(R["no_aprobadas"], R["total"])} del total</small></div>'
           '</div>')

    filas_kpi = ''
    for x in R['por_kpi']:
        if x['total'] == 0:
            continue
        a = x['aprobadas'] / x['total'] * 100
        n = x['no_aprobadas'] / x['total'] * 100
        filas_kpi += (f'<div class="vkpi"><span>{vc.KPI_NOMBRE[x["kpi"]]}</span><div class="vapil">'
                      f'<i style="width:{a:.1f}%;background:#2D8A4E"></i><i style="width:{n:.1f}%;background:#D94557"></i></div>'
                      f'<small>{x["aprobadas"]} · {x["no_aprobadas"]} · {x["pendientes"]} de {x["total"]}</small></div>')
    leyenda = ('<div class="vleg"><span><i style="background:#2D8A4E"></i>Aprobadas</span>'
               '<span><i style="background:#D94557"></i>No aprobadas</span>'
               '<span><i style="background:#EDF0F8"></i>Por validar</span></div>')

    cab = ''.join(f'<th>{t}</th>' for t in ('Aprobadas', 'No aprobadas', 'Por validar'))
    cruce = ''
    for s, etiqueta in (('AUTORIZADA', 'Autorizadas'), ('NO_AUTORIZADA', 'No autorizadas'), ('PENDIENTE', 'Sin revisar')):
        celdas = ''.join(f'<td>{R["cruce"].get((s, c), 0)}</td>' for c in vc.ESTADOS_CLIENTE[1:] + (vc.PENDIENTE,))
        cruce += f'<tr><td class="vi">{etiqueta}</td>{celdas}</tr>'
    r.html('<div class="vgrid vg2">'
           f'<div class="vcard"><div class="vct"><div class="vct-h">Por KPI</div><span class="vct-s">aprobadas · no · por validar</span></div>'
           f'{filas_kpi}{leyenda}</div>'
           f'<div class="vcard"><div class="vct"><div class="vct-h">Lo que dijo el supervisor y lo que decidió el cliente</div></div>'
           f'<table class="vtab"><tr><th class="vi">Supervisor</th>{cab}</tr>{cruce}</table></div></div>')

    filas_area = ''.join(f'<tr><td class="vi">{_e(x["area"])}</td><td>{x["total"]}</td><td>{x["aprobadas"]}</td>'
                         f'<td>{x["no_aprobadas"]}</td><td>{x["pendientes"]}</td></tr>' for x in R['por_area'])
    motivos = ''.join(f'<tr><td class="vi">{_e(m)}</td><td>{n}</td></tr>' for m, n in R['motivos_no']) \
        or '<tr><td class="vi" colspan="2">Todavía no hay incidencias no aprobadas.</td></tr>'
    r.html('<div class="vgrid vg2">'
           f'<div class="vcard"><div class="vct"><div class="vct-h">Por área</div></div><table class="vtab">'
           f'<tr><th class="vi">Área</th><th>Total</th><th>Aprobadas</th><th>No aprobadas</th><th>Por validar</th></tr>'
           f'{filas_area}</table></div>'
           f'<div class="vcard"><div class="vct"><div class="vct-h">Por qué no se aprobaron</div></div><table class="vtab">'
           f'<tr><th class="vi">Motivo</th><th>Incidencias</th></tr>{motivos}</table></div></div>')

    mes = _nombre_periodo(ctx['periodos'], ctx['periodo_id']).split(' ')[0].upper()
    ultima = f" La última decisión fue el {vc.fecha_corta(R['ultima'])}." if R['ultima'] is not None else ''
    falta = (f" <b style='font-size:13px;color:#98580E'>Faltan {R['pendientes']} por validar:</b> en el archivo salen "
             f"con VALIDACION FINAL vacía y el cierre las toma como no aprobadas." if R['pendientes'] else '')
    with st.container(border=True, key="vcard_cierre"):
        izq, der = st.columns([3, 1.2])
        with izq:
            r.html('<div class="vcierre"><b>Para el cierre</b><span>El archivo de incidencias finales con la columna '
                   'VALIDACION FINAL ya llena, con el mismo formato de agosto: va a <code>input/</code> del mes y el '
                   f'cierre lo lee como siempre.{ultima}{falta}</span></div>')
        with der:
            try:
                datos = vc.excel_finales(inc, hoja=f"INCIDENCIAS ATLAS {mes}")
            except Exception as e:
                print(f"[CLIENTE EXCEL] {e}")
                st.error("No se pudo armar el archivo.")
            else:
                st.download_button("Descargar incidencias finales", data=datos, file_name="INCIDENCIAS FINALES.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="clidl_excel", on_click="ignore", icon=":material/download:",
                                   use_container_width=True)
