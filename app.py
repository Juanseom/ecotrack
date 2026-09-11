"""EcoTrack — registra tu huella de carbono diaria escribiendo en español.

Esta capa es solo interfaz: toda la lógica vive en el paquete `ecotrack`.
"""

from __future__ import annotations

import streamlit as st

from ecotrack.ai import hay_clave, parse_inteligente
from ecotrack.calculator import (
    ETIQUETAS_CATEGORIA,
    Resumen,
    equivalencias,
    reparto_ordenado,
    resumir,
    sugerencias,
    supera_doble_meta,
    veredicto,
)
from ecotrack.factors import META_PARIS_2030_DIARIO, PROMEDIO_MUNDIAL_DIARIO
from ecotrack.parser import Activity

EJEMPLOS = (
    "Hoy comí carne y viajé 20km en bus",
    "Desayuné dos huevos con café y me fui en bici",
    "Almorcé pollo con arroz y pedí un uber de 8 km",
    "Vi Netflix 4 horas y usé el aire acondicionado toda la tarde",
    "Tiré dos bolsas de basura y reciclé",
)

COLOR_CATEGORIA = {
    "Alimentación": "#f4a261",
    "Transporte": "#4cc9a4",
    "Energía": "#8ab6f9",
    "Residuos": "#c9b896",
}

COLOR_NIVEL = {"bajo": "#4cc9a4", "medio": "#f4a261", "alto": "#e76f51"}

CSS = """
<style>
  .bloque-hero { padding: 0.5rem 0 1.25rem 0; }
  .bloque-hero h1 { font-size: 2.6rem; margin: 0; letter-spacing: -0.02em; }
  .bloque-hero p { opacity: 0.75; margin: 0.35rem 0 0 0; font-size: 1.02rem; }
  .tarjeta {
    border: 1px solid rgba(255,255,255,0.12); border-radius: 14px;
    padding: 1.1rem 1.25rem; margin-bottom: 0.85rem;
    background: rgba(255,255,255,0.03);
  }
  .cifra { font-size: 3.4rem; font-weight: 700; line-height: 1; }
  .cifra small { font-size: 1.1rem; font-weight: 500; opacity: 0.7; }
  .veredicto { font-size: 1rem; opacity: 0.85; margin-top: 0.5rem; }
  .fila-barra {
    display: flex; align-items: center; gap: 0.75rem; margin: 0.45rem 0;
    font-size: 0.93rem;
  }
  .fila-barra .nombre { width: 34%; opacity: 0.9; }
  .fila-barra .pista {
    flex: 1; height: 10px; border-radius: 99px;
    background: rgba(255,255,255,0.09); overflow: hidden;
  }
  .fila-barra .relleno { height: 100%; border-radius: 99px; }
  .fila-barra .valor { width: 5.5rem; text-align: right; font-variant-numeric: tabular-nums; }
  .etiqueta-asumido {
    font-size: 0.72rem; padding: 0.1rem 0.45rem; border-radius: 99px;
    background: rgba(244,162,97,0.18); color: #f4a261; margin-left: 0.4rem;
  }
  .etiqueta-dominante {
    font-size: 0.72rem; padding: 0.1rem 0.45rem; border-radius: 99px;
    background: rgba(231,111,81,0.22); color: #e76f51; margin-left: 0.4rem;
  }
  .fila-barra.dominante {
    background: rgba(231,111,81,0.12);
    border-radius: 10px;
    padding: 0.4rem 0.5rem;
    outline: 1px solid rgba(231,111,81,0.45);
  }
  .motor { font-size: 0.8rem; opacity: 0.6; }
</style>
"""


def render_barra(nombre: str, valor: float, maximo: float, color: str,
                 sufijo: str = "kg", extra_class: str = "") -> str:
    """Devuelve el HTML de una barra horizontal proporcional."""
    ancho = 0 if maximo <= 0 else min(100, valor / maximo * 100)
    clases = "fila-barra" + (f" {extra_class}" if extra_class else "")
    return (
        f'<div class="{clases}"><div class="nombre">{nombre}</div>'
        f'<div class="pista"><div class="relleno" style="width:{ancho:.1f}%;'
        f'background:{color}"></div></div>'
        f'<div class="valor">{valor:.2f} {sufijo}</div></div>'
    )


def render_filas_actividades(
    actividades: list[Activity], resumen: Resumen
) -> str:
    """Barras de cada actividad, de mayor a menor, con dominante si aplica."""
    maximo = max(a.kg_co2e for a in actividades) or 1.0
    filas = ""
    for actividad, es_dominante in reparto_ordenado(actividades, resumen):
        etiqueta_cat = ETIQUETAS_CATEGORIA[actividad.categoria]
        marca = ""
        if actividad.asumido:
            marca += '<span class="etiqueta-asumido">asumido</span>'
        if es_dominante:
            marca += '<span class="etiqueta-dominante">lo que más pesa</span>'
        nombre = (
            f"{actividad.etiqueta}{marca}<br>"
            f'<span style="opacity:0.55;font-size:0.8rem">{actividad.detalle}</span>'
        )
        filas += render_barra(
            nombre, actividad.kg_co2e, maximo,
            COLOR_CATEGORIA.get(etiqueta_cat, "#8ab6f9"),
            extra_class="dominante" if es_dominante else "",
        )
    return filas


def render_resultado(resumen: Resumen, actividades: list[Activity]) -> None:
    """Pinta el bloque principal de resultados del día."""
    nivel, mensaje = veredicto(resumen)
    color = COLOR_NIVEL[nivel]

    izquierda, derecha = st.columns([1, 1.25])

    with izquierda:
        st.markdown(
            f'<div class="tarjeta"><div class="cifra" style="color:{color}">'
            f"{resumen.total_kg:.2f}<small> kg CO₂e</small></div>"
            f'<div class="veredicto">{mensaje}</div></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Meta diaria 2030: {META_PARIS_2030_DIARIO} kg · "
            f"Promedio mundial: {PROMEDIO_MUNDIAL_DIARIO} kg"
        )
        st.progress(min(1.0, resumen.total_kg / META_PARIS_2030_DIARIO))
        st.caption(
            f"Vas en el {resumen.vs_meta_paris * 100:.0f} % de la meta diaria "
            f"y en el {resumen.vs_mundial * 100:.0f} % del promedio mundial."
        )

    with derecha:
        if actividades and supera_doble_meta(resumen):
            st.markdown(
                '<div class="tarjeta"><b>Reparto del día · duplicaste la meta</b>'
                f"{render_filas_actividades(actividades, resumen)}</div>",
                unsafe_allow_html=True,
            )
        elif resumen.por_categoria:
            maximo = max(resumen.por_categoria.values())
            barras = "".join(
                render_barra(nombre, valor, maximo,
                             COLOR_CATEGORIA.get(nombre, "#8ab6f9"))
                for nombre, valor in sorted(
                    resumen.por_categoria.items(),
                    key=lambda par: par[1], reverse=True,
                )
            )
            st.markdown(
                f'<div class="tarjeta"><b>Reparto del día</b>{barras}</div>',
                unsafe_allow_html=True,
            )

    if actividades and not supera_doble_meta(resumen):
        st.markdown("#### Detalle de lo registrado")
        st.markdown(
            f'<div class="tarjeta">{render_filas_actividades(actividades, resumen)}</div>',
            unsafe_allow_html=True,
        )

    consejos = sugerencias(actividades)
    if consejos:
        st.markdown("#### Qué mover primero")
        for consejo in consejos:
            st.markdown(f"- {consejo}")

    if (equivalente := equivalencias(resumen.total_kg)):
        st.markdown("#### Para dimensionarlo")
        columnas = st.columns(len(equivalente))
        for columna, (titulo, valor) in zip(columnas, equivalente.items()):
            columna.metric(titulo, valor)


def main() -> None:
    """Punto de entrada de la aplicación."""
    st.set_page_config(page_title="EcoTrack", page_icon="🌱", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)

    if "registro" not in st.session_state:
        st.session_state.registro = []
    if "entrada" not in st.session_state:
        st.session_state.entrada = ""

    st.markdown(
        '<div class="bloque-hero"><h1>🌱 EcoTrack</h1>'
        "<p>Cuéntame tu día en una frase y te digo cuánto CO₂ costó.</p></div>",
        unsafe_allow_html=True,
    )

    st.caption("¿Sin ideas? Prueba con uno de estos:")
    columnas = st.columns(len(EJEMPLOS))
    for columna, ejemplo in zip(columnas, EJEMPLOS):
        etiqueta = ejemplo if len(ejemplo) <= 22 else ejemplo[:20] + "…"
        if columna.button(etiqueta, key=f"ej_{ejemplo}", use_container_width=True):
            st.session_state.entrada = ejemplo

    with st.form("registro_diario", clear_on_submit=False):
        texto = st.text_area(
            "¿Qué hiciste hoy?",
            value=st.session_state.entrada,
            placeholder="Hoy comí carne y viajé 20km en bus",
            height=90,
            label_visibility="collapsed",
        )
        enviado = st.form_submit_button("Calcular mi huella", type="primary",
                                        use_container_width=True)

    if enviado and texto.strip():
        lectura, motor = parse_inteligente(texto)
        st.session_state.registro.append((texto.strip(), lectura, motor))
        st.session_state.entrada = ""

    if not st.session_state.registro:
        st.info(
            "Escribe en lenguaje natural: comidas, trayectos, consumo del "
            "hogar y residuos. EcoTrack no adivina lo que no entiende, te lo dice."
        )
        return

    actividades = [
        actividad
        for _, lectura, _ in st.session_state.registro
        for actividad in lectura.actividades
    ]
    resumen = resumir(actividades)

    st.divider()
    render_resultado(resumen, actividades)

    no_reconocido = [
        frase
        for _, lectura, _ in st.session_state.registro
        for frase in lectura.no_reconocido
    ]
    if no_reconocido:
        st.warning(
            "No supe medir esto, así que no lo conté: "
            + "; ".join(f"«{frase}»" for frase in no_reconocido)
        )

    with st.expander(f"Tus {len(st.session_state.registro)} registro(s) de hoy"):
        for frase, lectura, motor in st.session_state.registro:
            subtotal = sum(a.kg_co2e for a in lectura.actividades)
            st.markdown(
                f"**{frase}** — {subtotal:.2f} kg  \n"
                f'<span class="motor">interpretado por: {motor}</span>',
                unsafe_allow_html=True,
            )

    if st.button("Empezar un día nuevo"):
        st.session_state.registro = []
        st.rerun()

    with st.sidebar:
        st.markdown("### Cómo lo calcula")
        st.markdown(
            "Los factores de emisión vienen de **Poore & Nemecek (2018)** para "
            "alimentos, de **DEFRA (2023)** para transporte, energía y "
            "residuos, y de la **FAO (2013)** para comida desperdiciada. "
            "Todo en kg CO₂e de ciclo de vida."
        )
        motor_activo = "Claude (`claude-opus-5`)" if hay_clave() else "parser local"
        st.markdown(f"**Motor de interpretación:** {motor_activo}")
        if not hay_clave():
            st.caption(
                "Define `ANTHROPIC_API_KEY` para interpretar frases más libres. "
                "Sin clave, el parser determinista cubre el caso de uso."
            )
        st.caption(
            "Aun con Claude activo, los kg CO₂e siempre los calcula el código "
            "local: el modelo solo identifica actividades."
        )


if __name__ == "__main__":
    main()
