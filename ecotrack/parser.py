"""Convierte una frase en español a una lista de actividades con su huella.

Es un parser determinista: no usa red ni modelos. `ecotrack.ai` lo envuelve
con un parser basado en Claude y cae de vuelta aquí si no hay clave de API.

Ejemplo:
    >>> [a.etiqueta for a in parse("Hoy comí carne y viajé 20km en bus")]
    ['Carne de res', 'Bus']
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ecotrack.factors import (
    ALIMENTOS,
    ENERGIA,
    RESIDUOS,
    TRANSPORTES,
    FactorAlimento,
    FactorEnergia,
    FactorResiduo,
    FactorTransporte,
)


@dataclass(frozen=True)
class Activity:
    """Una actividad reconocida y su huella estimada."""

    categoria: str  # "alimentacion" | "transporte" | "energia" | "residuos"
    etiqueta: str
    cantidad: float
    unidad: str
    kg_co2e: float
    asumido: bool  # True si el parser rellenó un dato que el usuario no dio
    detalle: str


@dataclass(frozen=True)
class Lectura:
    """Resultado de interpretar una frase completa."""

    actividades: tuple[Activity, ...]
    no_reconocido: tuple[str, ...]


# Palabras numéricas frecuentes en habla cotidiana.
NUMEROS_ESCRITOS: dict[str, float] = {
    "medio": 0.5, "media": 0.5, "un": 1, "una": 1, "uno": 1,
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
    "doce": 12, "quince": 15, "veinte": 20, "treinta": 30,
    "cuarenta": 40, "cincuenta": 50, "cien": 100,
}

# Separadores de cláusulas: "comí carne y fui en bus" -> dos cláusulas.
_SEPARADORES = re.compile(
    r"\s*(?:,|;|\.|\+|\by\b|\be\b|\btambien\b|\bademas\b|\bluego\b|"
    r"\bdespues\b|\bmas tarde\b|\bpor la tarde\b|\bpor la noche\b)\s*"
)

_DISTANCIA = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(km|kms|kilometro|kilometros|k\b|cuadras?|m\b|metros)"
)
_DURACION = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(h\b|hr|hrs|hora|horas|min|mins|minuto|minutos)"
)
_NUMERO = re.compile(r"(\d+(?:[.,]\d+)?)")
_PESO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|kilos|kilogramos)\b")

# Ruido que no aporta significado y ensucia el listado de "no reconocido".
_RELLENO = frozenset({
    "hoy", "ayer", "mañana", "manana", "el", "la", "los", "las", "de", "del",
    "en", "con", "un", "una", "unos", "unas", "al", "a", "por", "para", "que",
    "me", "mi", "yo", "fui", "estuve", "hice", "tuve", "algo", "poco", "mucho",
    "casa", "trabajo", "oficina", "universidad", "colegio", "hoy dia",
}) 


def normalizar(texto: str) -> str:
    """Pasa a minúsculas y quita tildes, para comparar alias sin sorpresas."""
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sin_tildes).strip()


def _a_float(texto: str) -> float:
    """Convierte '2,5' o '2.5' a float."""
    return float(texto.replace(",", "."))


def _cantidad_en(clausula: str, alias: str) -> tuple[float, bool]:
    """Busca la cantidad que acompaña a un alias. Devuelve (cantidad, asumido)."""
    antes = clausula.split(alias)[0].split()
    for palabra in reversed(antes[-3:]):
        if _NUMERO.fullmatch(palabra):
            return _a_float(palabra), False
        if palabra in NUMEROS_ESCRITOS:
            return NUMEROS_ESCRITOS[palabra], False
    return 1.0, True


def _km_en(clausula: str, factor: FactorTransporte) -> tuple[float, bool, str]:
    """Deduce la distancia de un trayecto. Devuelve (km, asumido, detalle)."""
    if (m := _DISTANCIA.search(clausula)) is not None:
        valor, unidad = _a_float(m.group(1)), m.group(2)
        if unidad.startswith("cuadra"):
            return valor * 0.1, False, f"{valor:g} cuadras ≈ {valor * 0.1:g} km"
        if unidad in {"m", "metros"}:
            return valor / 1000, False, f"{valor:g} m"
        return valor, False, f"{valor:g} km"

    if (m := _DURACION.search(clausula)) is not None:
        valor, unidad = _a_float(m.group(1)), m.group(2)
        horas = valor if unidad.startswith(("h", "hr")) else valor / 60
        km = horas * factor.velocidad_kmh
        return km, True, f"{valor:g} {unidad} a {factor.velocidad_kmh:g} km/h"

    return (
        factor.km_por_defecto,
        True,
        f"distancia no indicada, se asumen {factor.km_por_defecto:g} km",
    )


def _buscar_alias(clausula: str, alias: tuple[str, ...]) -> str | None:
    """Devuelve el alias más largo presente en la cláusula, o None."""
    encontrados = [
        a for a in alias
        if re.search(rf"(?<![a-z]){re.escape(a)}", clausula) is not None
    ]
    return max(encontrados, key=len) if encontrados else None


def _leer_transporte(clausula: str) -> Activity | None:
    """Reconoce un trayecto en la cláusula, si lo hay."""
    candidatos: list[tuple[str, FactorTransporte]] = []
    for factor in TRANSPORTES:
        if (alias := _buscar_alias(clausula, factor.alias)) is not None:
            candidatos.append((alias, factor))
    if not candidatos:
        return None

    # El alias más específico gana: "carro electrico" sobre "carro".
    _, factor = max(candidatos, key=lambda par: len(par[0]))
    km, asumido, detalle = _km_en(clausula, factor)
    return Activity(
        categoria="transporte",
        etiqueta=factor.etiqueta,
        cantidad=round(km, 2),
        unidad="km",
        kg_co2e=round(km * factor.kg_co2e_por_km, 3),
        asumido=asumido,
        detalle=detalle,
    )


def _leer_energia(clausula: str) -> Activity | None:
    """Reconoce un consumo energético del hogar en la cláusula, si lo hay."""
    candidatos: list[tuple[str, FactorEnergia]] = []
    for factor in ENERGIA:
        if (alias := _buscar_alias(clausula, factor.alias)) is not None:
            candidatos.append((alias, factor))
    if not candidatos:
        return None

    _, factor = max(candidatos, key=lambda par: len(par[0]))
    if factor.unidad == "hora" and (m := _DURACION.search(clausula)) is not None:
        valor = _a_float(m.group(1))
        unidad_texto = m.group(2)
        cantidad = valor if unidad_texto.startswith(("h", "hr")) else valor / 60
        asumido = False
        detalle = f"{valor:g} {unidad_texto}"
    else:
        cantidad, asumido = factor.usos_por_defecto, True
        detalle = f"duración no indicada, se asumen {cantidad:g} {factor.unidad}(s)"

    return Activity(
        categoria="energia",
        etiqueta=factor.etiqueta,
        cantidad=round(cantidad, 2),
        unidad=factor.unidad,
        kg_co2e=round(cantidad * factor.kg_co2e_por_unidad, 3),
        asumido=asumido,
        detalle=detalle,
    )


def _leer_alimentos(clausula: str) -> list[Activity]:
    """Reconoce todos los alimentos mencionados en la cláusula."""
    encontrados: list[tuple[str, FactorAlimento]] = []
    for factor in ALIMENTOS:
        if (alias := _buscar_alias(clausula, factor.alias)) is not None:
            encontrados.append((alias, factor))
    if not encontrados:
        return []

    # "hamburguesa" y "pan" pueden coincidir a la vez: nos quedamos con el
    # alias más largo por cada factor distinto, y descartamos los solapados.
    encontrados.sort(key=lambda par: len(par[0]), reverse=True)
    usados: list[str] = []
    actividades: list[Activity] = []
    for alias, factor in encontrados:
        if any(alias in previo for previo in usados):
            continue
        usados.append(alias)
        porciones, asumido = _cantidad_en(clausula, alias)
        actividades.append(
            Activity(
                categoria="alimentacion",
                etiqueta=factor.etiqueta,
                cantidad=porciones,
                unidad=factor.unidad,
                kg_co2e=round(porciones * factor.kg_co2e_por_porcion, 3),
                asumido=asumido,
                detalle=(
                    f"{porciones:g} {factor.unidad}(s) de {factor.porcion_kg * 1000:g} g"
                ),
            )
        )
    return actividades


def _cantidad_residuo(
    clausula: str, alias: str, factor: FactorResiduo
) -> tuple[float, bool, str, str]:
    """Deduce masa o unidades de un residuo. Devuelve cantidad, asumido,
    detalle y unidad de la Activity."""
    if (m := _PESO.search(clausula)) is not None:
        kg = _a_float(m.group(1))
        return kg, False, f"{kg:g} kg", "kg"

    unidades, asumido = _cantidad_en(clausula, alias)
    masa_g = factor.kg_por_unidad * 1000
    detalle = f"{unidades:g} {factor.unidad}(s) de {masa_g:g} g"
    if asumido:
        detalle = (
            f"cantidad no indicada, se asume {unidades:g} {factor.unidad}"
        )
    return unidades, asumido, detalle, factor.unidad


def _leer_residuos(clausula: str) -> Activity | None:
    """Reconoce un residuo doméstico en la cláusula, si lo hay."""
    candidatos: list[tuple[str, FactorResiduo]] = []
    for factor in RESIDUOS:
        if (alias := _buscar_alias(clausula, factor.alias)) is not None:
            candidatos.append((alias, factor))
    if not candidatos:
        return None

    alias, factor = max(candidatos, key=lambda par: len(par[0]))
    cantidad, asumido, detalle, unidad = _cantidad_residuo(
        clausula, alias, factor
    )
    if unidad == "kg":
        kg_co2e = cantidad * factor.kg_co2e_por_kg
    else:
        kg_co2e = cantidad * factor.kg_co2e_por_unidad
    return Activity(
        categoria="residuos",
        etiqueta=factor.etiqueta,
        cantidad=round(cantidad, 2),
        unidad=unidad,
        kg_co2e=round(kg_co2e, 3),
        asumido=asumido,
        detalle=detalle,
    )


def _residuo(clausula: str, reconocido: bool) -> str | None:
    """Devuelve la cláusula si no se entendió nada útil de ella."""
    if reconocido:
        return None
    palabras = [p for p in clausula.split() if p not in _RELLENO and len(p) > 2]
    return clausula.strip() if palabras else None


def parse(texto: str) -> Lectura:
    """Interpreta una frase en español y devuelve sus actividades con huella.

    Asume una frase por día, en primera persona. Lo que no reconoce no lo
    estima: lo devuelve en `no_reconocido` para que la interfaz lo muestre.
    """
    if not texto or not texto.strip():
        return Lectura(actividades=(), no_reconocido=())

    normalizado = normalizar(texto)
    actividades: list[Activity] = []
    no_reconocido: list[str] = []

    for clausula in _SEPARADORES.split(normalizado):
        if not clausula.strip():
            continue
        de_la_clausula: list[Activity] = []
        if (transporte := _leer_transporte(clausula)) is not None:
            de_la_clausula.append(transporte)
        if (energia := _leer_energia(clausula)) is not None:
            de_la_clausula.append(energia)
        residuo = _leer_residuos(clausula)
        if residuo is not None:
            de_la_clausula.append(residuo)
        # Si desperdició comida, no la contamos también como consumida.
        if residuo is None or residuo.etiqueta != "Comida desperdiciada":
            de_la_clausula.extend(_leer_alimentos(clausula))

        actividades.extend(de_la_clausula)
        if (resto := _residuo(clausula, bool(de_la_clausula))) is not None:
            no_reconocido.append(resto)

    return Lectura(
        actividades=tuple(actividades),
        no_reconocido=tuple(no_reconocido),
    )
