"""Parser opcional con la API de Claude, con fallback al parser determinista.

Reparto de responsabilidades a propósito: el modelo SOLO extrae entidades
(qué comiste, cómo te moviste, cuánto). Los kg CO2e los calcula siempre este
código con los factores de `ecotrack.factors`, para que ningún número de
emisiones salga de un modelo de lenguaje.

Si no hay clave de API, si la librería no está instalada o si la llamada
falla, `parse_inteligente` devuelve el resultado del parser determinista.
"""

from __future__ import annotations

import json
import os
import re

from ecotrack.factors import ALIMENTOS, ENERGIA, RESIDUOS, TRANSPORTES
from ecotrack.parser import Activity, Lectura, parse

MODELO = "claude-opus-5"

_ALIMENTOS_POR_CLAVE = {f.clave: f for f in ALIMENTOS}
_TRANSPORTES_POR_CLAVE = {f.clave: f for f in TRANSPORTES}
_ENERGIA_POR_CLAVE = {f.clave: f for f in ENERGIA}
_RESIDUOS_POR_CLAVE = {f.clave: f for f in RESIDUOS}


def hay_clave() -> bool:
    """Indica si hay una clave de API configurada en el entorno."""
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _catalogo() -> str:
    """Construye el catálogo de claves válidas a partir de los factores."""
    alimentos = ", ".join(f.clave for f in ALIMENTOS)
    transportes = ", ".join(f.clave for f in TRANSPORTES)
    energia = ", ".join(f.clave for f in ENERGIA)
    residuos = ", ".join(f.clave for f in RESIDUOS)
    return (
        f"alimentacion: {alimentos}\n"
        f"transporte: {transportes}\n"
        f"energia: {energia}\n"
        f"residuos: {residuos}"
    )


SISTEMA = f"""Extraes actividades de un texto en español sobre el día de una persona.

Devuelves SOLO un objeto JSON, sin explicación y sin bloque de código, así:
{{"actividades": [{{"categoria": "...", "clave": "...", "cantidad": 1.0, "asumido": false}}],
  "no_reconocido": ["..."]}}

Reglas:
- "clave" debe ser exactamente una de este catálogo:
{_catalogo()}
- "cantidad" significa: porciones para alimentacion, kilómetros para
  transporte, horas o usos para energia, bolsas o kilogramos para
  residuos (porciones si es comida_desperdiciada).
- Si el usuario no dio la cantidad, estima la más razonable y marca
  "asumido": true.
- Convierte duraciones a kilómetros usando una velocidad realista del modo
  (bus urbano ~20 km/h, carro ~35 km/h, bici ~15 km/h).
- Lo que no encaje en el catálogo va en "no_reconocido" como texto literal.
- NUNCA calcules emisiones ni CO2: eso lo hace el programa.
"""


def _actividad_desde_json(item: dict) -> Activity | None:
    """Convierte un item extraído por el modelo en una Activity con su huella."""
    categoria = str(item.get("categoria", "")).strip()
    clave = str(item.get("clave", "")).strip()
    try:
        cantidad = float(item.get("cantidad", 1))
    except (TypeError, ValueError):
        return None
    if cantidad <= 0:
        return None
    asumido = bool(item.get("asumido", False))

    if categoria == "alimentacion" and clave in _ALIMENTOS_POR_CLAVE:
        factor = _ALIMENTOS_POR_CLAVE[clave]
        return Activity(
            categoria, factor.etiqueta, cantidad, factor.unidad,
            round(cantidad * factor.kg_co2e_por_porcion, 3), asumido,
            f"{cantidad:g} {factor.unidad}(s) de {factor.porcion_kg * 1000:g} g",
        )
    if categoria == "transporte" and clave in _TRANSPORTES_POR_CLAVE:
        factor = _TRANSPORTES_POR_CLAVE[clave]
        return Activity(
            categoria, factor.etiqueta, round(cantidad, 2), "km",
            round(cantidad * factor.kg_co2e_por_km, 3), asumido,
            f"{cantidad:g} km",
        )
    if categoria == "energia" and clave in _ENERGIA_POR_CLAVE:
        factor = _ENERGIA_POR_CLAVE[clave]
        return Activity(
            categoria, factor.etiqueta, round(cantidad, 2), factor.unidad,
            round(cantidad * factor.kg_co2e_por_unidad, 3), asumido,
            f"{cantidad:g} {factor.unidad}(s)",
        )
    if categoria == "residuos" and clave in _RESIDUOS_POR_CLAVE:
        factor = _RESIDUOS_POR_CLAVE[clave]
        return Activity(
            categoria, factor.etiqueta, round(cantidad, 2), factor.unidad,
            round(cantidad * factor.kg_co2e_por_unidad, 3), asumido,
            f"{cantidad:g} {factor.unidad}(s)",
        )
    return None


def _extraer_json(texto: str) -> dict | None:
    """Recupera el objeto JSON de la respuesta, tolerando texto alrededor."""
    if (m := re.search(r"\{.*\}", texto, re.DOTALL)) is None:
        return None
    try:
        datos = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return datos if isinstance(datos, dict) else None


def parse_con_claude(texto: str) -> Lectura | None:
    """Interpreta la frase con Claude. Devuelve None si no se pudo."""
    if not hay_clave():
        return None
    try:
        import anthropic
    except ImportError:
        return None

    try:
        cliente = anthropic.Anthropic()
        respuesta = cliente.messages.create(
            model=MODELO,
            max_tokens=2000,
            output_config={"effort": "low"},
            system=SISTEMA,
            messages=[{"role": "user", "content": texto}],
        )
    except Exception:  # red, clave inválida, límite de uso: caemos al fallback
        return None

    if respuesta.stop_reason == "refusal":
        return None

    salida = "".join(b.text for b in respuesta.content if b.type == "text")
    if (datos := _extraer_json(salida)) is None:
        return None

    actividades = [
        actividad
        for item in datos.get("actividades", [])
        if isinstance(item, dict)
        and (actividad := _actividad_desde_json(item)) is not None
    ]
    no_reconocido = [
        str(x) for x in datos.get("no_reconocido", []) if str(x).strip()
    ]
    if not actividades and not no_reconocido:
        return None

    return Lectura(tuple(actividades), tuple(no_reconocido))


def parse_inteligente(texto: str) -> tuple[Lectura, str]:
    """Interpreta la frase con Claude si se puede, si no con el parser local.

    Devuelve (lectura, motor) donde motor es "claude" o "local", para que la
    interfaz pueda decir con qué se calculó.
    """
    if (lectura := parse_con_claude(texto)) is not None:
        return lectura, "claude"
    return parse(texto), "local"
