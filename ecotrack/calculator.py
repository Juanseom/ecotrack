"""Agrega actividades en totales, comparaciones y equivalencias."""

from __future__ import annotations

from dataclasses import dataclass

from ecotrack.factors import (
    KG_CO2E_ABSORBIDOS_POR_ARBOL_AL_ANO,
    KG_CO2E_POR_CARGA_DE_CELULAR,
    META_PARIS_2030_DIARIO,
    PROMEDIO_LATAM_DIARIO,
    PROMEDIO_MUNDIAL_DIARIO,
)
from ecotrack.parser import Activity

ETIQUETAS_CATEGORIA: dict[str, str] = {
    "alimentacion": "Alimentación",
    "transporte": "Transporte",
    "energia": "Energía",
    "residuos": "Residuos",
}


@dataclass(frozen=True)
class Resumen:
    """Totales de un día de actividades."""

    total_kg: float
    por_categoria: dict[str, float]
    mayor_aporte: Activity | None
    vs_mundial: float  # proporción frente al promedio mundial diario
    vs_latam: float
    vs_meta_paris: float


def resumir(actividades: tuple[Activity, ...] | list[Activity]) -> Resumen:
    """Suma las actividades y las compara con las referencias diarias."""
    total = round(sum(a.kg_co2e for a in actividades), 3)

    por_categoria: dict[str, float] = {}
    for actividad in actividades:
        etiqueta = ETIQUETAS_CATEGORIA[actividad.categoria]
        por_categoria[etiqueta] = round(
            por_categoria.get(etiqueta, 0.0) + actividad.kg_co2e, 3
        )

    mayor = max(actividades, key=lambda a: a.kg_co2e, default=None)
    if mayor is not None and mayor.kg_co2e <= 0:
        mayor = None

    return Resumen(
        total_kg=total,
        por_categoria=por_categoria,
        mayor_aporte=mayor,
        vs_mundial=round(total / PROMEDIO_MUNDIAL_DIARIO, 3),
        vs_latam=round(total / PROMEDIO_LATAM_DIARIO, 3),
        vs_meta_paris=round(total / META_PARIS_2030_DIARIO, 3),
    )


def equivalencias(total_kg: float) -> dict[str, str]:
    """Traduce los kg CO2e a comparaciones cotidianas."""
    if total_kg <= 0:
        return {}
    dias_de_arbol = total_kg / (KG_CO2E_ABSORBIDOS_POR_ARBOL_AL_ANO / 365)
    cargas = total_kg / KG_CO2E_POR_CARGA_DE_CELULAR
    km_en_carro = total_kg / 0.171  # [DEFRA] auto de gasolina mediano
    return {
        "Un árbol tardaría": f"{dias_de_arbol:,.0f} días en absorberlo",
        "Equivale a recorrer": f"{km_en_carro:,.0f} km en carro",
        "O a cargar tu celular": f"{cargas:,.0f} veces",
    }


def veredicto(resumen: Resumen) -> tuple[str, str]:
    """Devuelve (nivel, mensaje) para el semáforo de la interfaz.

    Nivel es "bajo", "medio" o "alto" según la meta climática de 2030.
    """
    if resumen.total_kg == 0:
        return "bajo", "Aún no hay nada registrado hoy."
    if resumen.vs_meta_paris <= 0.6:
        return "bajo", "Muy por debajo de la meta climática diaria. Así se ve un día ligero."
    if resumen.vs_meta_paris <= 1.0:
        return "medio", "Dentro de la meta de 2030, pero sin margen de sobra."
    if resumen.vs_meta_paris <= 2.0:
        return "alto", "Por encima de la meta diaria. Mira qué actividad pesa más."
    return "alto", "Muy por encima de la meta. Un solo cambio hoy movería bastante la aguja."


def supera_doble_meta(resumen: Resumen) -> bool:
    """Indica si el total del día supera el doble de la meta 2030."""
    return resumen.vs_meta_paris > 2.0


def reparto_ordenado(
    actividades: tuple[Activity, ...] | list[Activity],
    resumen: Resumen,
) -> list[tuple[Activity, bool]]:
    """Devuelve las actividades de mayor a menor huella.

    El segundo valor es True solo en la actividad dominante, y únicamente
    cuando el día supera el doble de la meta. Asume que `resumen` se calculó
    con las mismas actividades.
    """
    ordenadas = sorted(actividades, key=lambda a: a.kg_co2e, reverse=True)
    destacar = supera_doble_meta(resumen) and resumen.mayor_aporte is not None
    return [
        (actividad, destacar and actividad == resumen.mayor_aporte)
        for actividad in ordenadas
    ]


def sugerencias(actividades: tuple[Activity, ...] | list[Activity]) -> list[str]:
    """Propone acciones concretas a partir de lo que más pesó en el día."""
    if not actividades:
        return []

    ordenadas = sorted(actividades, key=lambda a: a.kg_co2e, reverse=True)
    consejos: list[str] = []
    for actividad in ordenadas[:2]:
        if actividad.kg_co2e <= 0.05:
            continue
        if actividad.categoria == "alimentacion":
            consejos.append(
                f"{actividad.etiqueta} fue {actividad.kg_co2e:.1f} kg. Cambiar esa "
                "porción por legumbres baja alrededor del 90 %."
            )
        elif actividad.categoria == "transporte":
            consejos.append(
                f"{actividad.etiqueta} ({actividad.cantidad:g} km) costó "
                f"{actividad.kg_co2e:.1f} kg. En metro o bici ese trayecto baja "
                "a una fracción."
            )
        elif actividad.categoria == "residuos":
            consejos.append(_consejo_residuo(actividad))
        else:
            consejos.append(
                f"{actividad.etiqueta} sumó {actividad.kg_co2e:.1f} kg. Una hora "
                "menos al día son varios kilos al mes."
            )
    return consejos


def _consejo_residuo(actividad: Activity) -> str:
    """Consejo concreto según el tipo de residuo que más pesó."""
    if actividad.etiqueta == "Comida desperdiciada":
        return (
            f"{actividad.etiqueta} fue {actividad.kg_co2e:.1f} kg. Guardar las "
            "sobras o servir menos evita esa huella de producción."
        )
    if actividad.etiqueta == "Reciclaje":
        return (
            f"{actividad.etiqueta} sumó {actividad.kg_co2e:.1f} kg. Separar "
            "sigue siendo mucho más liviano que mandar lo mismo a la basura."
        )
    return (
        f"{actividad.etiqueta} sumó {actividad.kg_co2e:.1f} kg. Reciclar o "
        "compostar esa fracción corta el metano del relleno sanitario."
    )
