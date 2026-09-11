"""Factores de emisión usados por EcoTrack.

Este módulo es solo datos: no contiene lógica. Todos los factores están en
kg CO2e (dióxido de carbono equivalente) e incluyen el ciclo de vida completo
cuando la fuente lo reporta así.

Fuentes:
  [PN18]  Poore & Nemecek (2018), "Reducing food's environmental impacts
          through producers and consumers", Science 360(6392) — alimentos.
  [DEFRA] UK Government GHG Conversion Factors for Company Reporting (2023)
          — transporte, energía y residuos.
  [IEA]   IEA Emission Factors (2023) — intensidad de la red eléctrica.
  [FAO13] FAO (2013), "Food Wastage Footprint: Impacts on Natural Resources"
          — comida desperdiciada.

Son estimaciones de divulgación para un MVP, no un inventario certificado.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FactorAlimento:
    """Factor de emisión de un alimento y su porción de referencia."""

    clave: str
    etiqueta: str
    kg_co2e_por_kg: float
    porcion_kg: float
    unidad: str  # nombre de la porción, p. ej. "porción", "taza"
    alias: tuple[str, ...] = field(default_factory=tuple)

    @property
    def kg_co2e_por_porcion(self) -> float:
        """Emisión de una porción estándar, en kg CO2e."""
        return self.kg_co2e_por_kg * self.porcion_kg


@dataclass(frozen=True)
class FactorTransporte:
    """Factor de emisión de un modo de transporte, por pasajero-km."""

    clave: str
    etiqueta: str
    kg_co2e_por_km: float
    velocidad_kmh: float  # para convertir "20 minutos en bus" a km
    km_por_defecto: float  # se asume si el usuario no dice la distancia
    alias: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FactorEnergia:
    """Factor de emisión de un consumo energético del hogar."""

    clave: str
    etiqueta: str
    kg_co2e_por_unidad: float
    unidad: str  # "hora", "uso"
    usos_por_defecto: float
    alias: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FactorResiduo:
    """Factor de emisión de un residuo doméstico, por unidad de referencia."""

    clave: str
    etiqueta: str
    kg_co2e_por_kg: float
    kg_por_unidad: float  # masa de una bolsa o porción estándar
    unidad: str  # "bolsa", "porción"
    alias: tuple[str, ...] = field(default_factory=tuple)

    @property
    def kg_co2e_por_unidad(self) -> float:
        """Emisión de una unidad estándar, en kg CO2e."""
        return self.kg_co2e_por_kg * self.kg_por_unidad


# --- Alimentos -------------------------------------------------------------
# kg_co2e_por_kg: mediana global del ciclo de vida completo [PN18].
# porcion_kg: porción estándar de consumo doméstico.

ALIMENTOS: tuple[FactorAlimento, ...] = (
    FactorAlimento(
        # [PN18] promedio ponderado entre hato de carne (99.5) y hato
        # lechero (33.3), que en la producción global pesan casi igual.
        "res", "Carne de res", 60.0, 0.150, "porción",
        ("res", "carne", "carne de res", "bistec", "bife", "hamburguesa",
         "churrasco", "lomo", "asado", "carne roja", "ternera"),
    ),
    FactorAlimento(
        "cordero", "Cordero", 39.7, 0.150, "porción",  # [PN18] 39.7
        ("cordero", "borrego", "oveja"),
    ),
    FactorAlimento(
        "cerdo", "Cerdo", 12.3, 0.150, "porción",  # [PN18] 12.3
        ("cerdo", "chancho", "tocino", "jamon", "salchicha", "chorizo",
         "costillas"),
    ),
    FactorAlimento(
        "pollo", "Pollo", 9.9, 0.150, "porción",  # [PN18] 9.9
        ("pollo", "pechuga", "gallina", "pavo", "nuggets"),
    ),
    FactorAlimento(
        "pescado", "Pescado", 13.6, 0.150, "porción",  # [PN18] pescado de cultivo
        ("pescado", "salmon", "atun", "tilapia", "mojarra", "trucha",
         "mariscos", "camarones"),
    ),
    FactorAlimento(
        "queso", "Queso", 23.9, 0.050, "porción",  # [PN18] 23.9
        ("queso", "quesito", "mozzarella"),
    ),
    FactorAlimento(
        "huevos", "Huevos", 4.7, 0.060, "unidad",  # [PN18] 4.7; 1 huevo = 60 g
        ("huevo", "huevos", "omelette", "tortilla de huevo"),
    ),
    FactorAlimento(
        "leche", "Leche", 3.2, 0.250, "vaso",  # [PN18] 3.2 kg/L
        ("leche", "yogur", "yogurt", "batido"),
    ),
    FactorAlimento(
        "arroz", "Arroz", 4.5, 0.150, "porción",  # [PN18] 4.45
        ("arroz",),
    ),
    FactorAlimento(
        "pan", "Pan y cereales", 1.6, 0.100, "porción",  # [PN18] 1.6
        ("pan", "arepa", "tostada", "cereal", "pasta", "espagueti", "tortilla"),
    ),
    FactorAlimento(
        "legumbres", "Legumbres", 0.9, 0.150, "porción",  # [PN18] 0.9
        ("frijoles", "lentejas", "garbanzos", "legumbres", "frijol", "arvejas"),
    ),
    FactorAlimento(
        "verduras", "Verduras y ensalada", 0.5, 0.200, "porción",  # [PN18] 0.5
        ("ensalada", "verduras", "vegetales", "brocoli", "lechuga", "tomate",
         "zanahoria", "papa", "papas", "sopa"),
    ),
    FactorAlimento(
        "fruta", "Fruta", 0.7, 0.150, "porción",  # [PN18] 0.7
        ("fruta", "frutas", "manzana", "banano", "naranja", "mango"),
    ),
    FactorAlimento(
        "cafe", "Café", 16.5, 0.012, "taza",  # [PN18] 16.5; 12 g por taza
        ("cafe", "tinto", "capuchino", "latte"),
    ),
    FactorAlimento(
        "chocolate", "Chocolate", 46.7, 0.030, "porción",  # [PN18] 46.7
        ("chocolate", "cacao"),
    ),
)

# --- Transporte ------------------------------------------------------------
# kg_co2e_por_km: emisión por pasajero-km [DEFRA 2023].

TRANSPORTES: tuple[FactorTransporte, ...] = (
    FactorTransporte(
        "carro", "Carro (gasolina)", 0.171, 35.0, 10.0,  # [DEFRA] auto mediano
        ("carro", "auto", "coche", "automovil", "camioneta", "conduje",
         "manejé", "maneje"),
    ),
    FactorTransporte(
        "carro_electrico", "Carro eléctrico", 0.047, 35.0, 10.0,  # [DEFRA]
        ("carro electrico", "auto electrico", "electrico", "tesla"),
    ),
    FactorTransporte(
        "taxi", "Taxi o app de viajes", 0.211, 25.0, 8.0,  # [DEFRA] taxi urbano
        ("taxi", "uber", "didi", "cabify", "indriver"),
    ),
    FactorTransporte(
        "moto", "Moto", 0.114, 40.0, 10.0,  # [DEFRA] motocicleta mediana
        ("moto", "motocicleta", "scooter"),
    ),
    FactorTransporte(
        "bus", "Bus", 0.102, 20.0, 8.0,  # [DEFRA] bus urbano
        ("bus", "buseta", "autobus", "colectivo", "transmilenio", "sitp",
         "transporte publico", "micro"),
    ),
    FactorTransporte(
        "metro", "Metro o tren", 0.035, 35.0, 10.0,  # [DEFRA] light rail
        ("metro", "tren", "subte", "metrocable", "tranvia"),
    ),
    FactorTransporte(
        "avion", "Avión (vuelo corto)", 0.246, 700.0, 500.0,  # [DEFRA] doméstico
        ("avion", "vuelo", "vole"),
    ),
    FactorTransporte(
        "bici", "Bicicleta", 0.0, 15.0, 5.0,  # sin emisiones directas
        ("bici", "bicicleta", "ciclovia", "patineta", "scooter electrico"),
    ),
    FactorTransporte(
        "caminar", "Caminar", 0.0, 5.0, 2.0,  # sin emisiones directas
        ("camine", "caminé", "caminando", "a pie", "trote", "corri", "corrí"),
    ),
)

# --- Energía del hogar -----------------------------------------------------
# Base: 0.35 kg CO2e por kWh, promedio de red latinoamericana [IEA 2023].

KG_CO2E_POR_KWH = 0.35  # [IEA 2023]

ENERGIA: tuple[FactorEnergia, ...] = (
    FactorEnergia(
        "aire", "Aire acondicionado", 1.0 * KG_CO2E_POR_KWH, "hora", 2.0,
        ("aire acondicionado", "aire", "clima", "ac"),
    ),
    FactorEnergia(
        "calefaccion", "Calefacción", 1.5 * KG_CO2E_POR_KWH, "hora", 2.0,
        ("calefaccion", "calefactor", "estufa electrica"),
    ),
    FactorEnergia(
        "ducha", "Ducha caliente", 2.1 * KG_CO2E_POR_KWH, "uso", 1.0,
        ("ducha", "duche", "duché", "bañe", "bañé", "regadera"),
    ),
    FactorEnergia(
        "secadora", "Secadora de ropa", 2.5 * KG_CO2E_POR_KWH, "uso", 1.0,
        ("secadora",),
    ),
    FactorEnergia(
        "computador", "Computador o consola", 0.15 * KG_CO2E_POR_KWH, "hora", 4.0,
        ("computador", "computadora", "pc", "laptop", "portatil", "consola",
         "playstation", "xbox", "videojuegos"),
    ),
    FactorEnergia(
        "streaming", "Streaming de video", 0.08 * KG_CO2E_POR_KWH, "hora", 2.0,
        ("netflix", "streaming", "youtube", "series", "television", "tele",
         "tv"),
    ),
)

# --- Residuos --------------------------------------------------------------
# kg_co2e_por_kg: tratamiento o huella citada. kg_por_unidad: porción típica,
# el mismo criterio que las porciones de alimento (no es un factor inventado).

RESIDUOS: tuple[FactorResiduo, ...] = (
    FactorResiduo(
        # [DEFRA 2023] household residual waste, landfill: 0.44664 kg CO2e/kg.
        "bolsa_basura", "Bolsa de basura", 0.44664, 5.0, "bolsa",
        ("bolsa de basura", "bolsas de basura", "tire la basura",
         "bote la basura", "saque la basura", "saco la basura",
         "eche la basura", "bolsa de desechos", "basura"),
    ),
    FactorResiduo(
        # [DEFRA 2023] reciclaje closed-loop de papel y cartón: 21.28 kg
        # CO2e/t = 0.0213 kg CO2e/kg; proxy del reciclaje doméstico mixto.
        "reciclaje", "Reciclaje", 0.0213, 5.0, "bolsa",
        ("bolsa de reciclaje", "bolsas de reciclaje", "reciclables",
         "reciclaje", "reciclar", "reciclado", "recicle"),
    ),
    FactorResiduo(
        # [FAO13] 3.3 Gt CO2e / 1.3 Gt de comida desperdiciada = 2.54 kg/kg.
        "comida_desperdiciada", "Comida desperdiciada", 2.54, 0.250, "porción",
        ("comida desperdiciada", "desperdicio de comida", "desperdicie comida",
         "comida a la basura", "tire las sobras", "tire la comida",
         "tire comida", "eche la comida", "se echo a perder",
         "desperdicie", "desperdicio"),
    ),
)

# --- Referencias de comparación (kg CO2e por día) --------------------------

PROMEDIO_MUNDIAL_DIARIO = 12.8  # 4.7 t/año per cápita [IEA 2023]
PROMEDIO_LATAM_DIARIO = 7.4     # 2.7 t/año per cápita [IEA 2023]
META_PARIS_2030_DIARIO = 6.3    # 2.3 t/año para la ruta de 1.5 °C [IPCC]

# Equivalencias para dar contexto al número
KG_CO2E_ABSORBIDOS_POR_ARBOL_AL_ANO = 21.0  # árbol maduro promedio
KG_CO2E_POR_CARGA_DE_CELULAR = 0.0084       # [DEFRA] 12 Wh por carga
