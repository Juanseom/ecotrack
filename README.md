# 🌱 EcoTrack

MVP de EcoTrack: registra tu huella de carbono diaria **escribiendo una frase
en español**. Escribes *"Hoy comí carne y viajé 20km en bus"* y la app
identifica las actividades, las convierte a kg CO₂e y te dice qué mover primero.

| | |
|---|---|
| **Stack** | Python 3.11+ · Streamlit · sin base de datos |
| **Despliegue** | Replit (autoscale, puerto 8080) |
| **IA** | Claude (`claude-opus-5`) opcional para interpretar, con fallback local |
| **Pruebas** | 39 pruebas con `unittest` (lógica + interfaz) |

## Cómo correrlo

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Abre <http://localhost:8080>.

## Arquitectura

La interfaz no calcula nada; la lógica no sabe nada de Streamlit.

```
app.py                  Interfaz Streamlit. Solo presentación.
ecotrack/
  factors.py            Factores de emisión + su fuente. Solo datos.
  parser.py             Texto en español → actividades. Determinista, sin red.
  calculator.py         Actividades → totales, veredicto, equivalencias.
  ai.py                 Parser con Claude + fallback al parser local.
tests/                  Pruebas de parser, calculator e interfaz.
```

### La decisión de diseño importante

Cuando hay `ANTHROPIC_API_KEY`, Claude interpreta la frase — pero **solo
identifica actividades y cantidades**. Los kg CO₂e los calcula siempre
`ecotrack/factors.py` con factores citados. Así ningún número de emisiones sale
de un modelo de lenguaje, que es exactamente donde un LLM no es de fiar.

Sin clave, el parser determinista cubre el caso de uso completo. La app nunca
depende de la red para funcionar.

### Lo que no entiende, no lo inventa

Si escribes *"fui a bailar salsa toda la noche"*, EcoTrack no estima un número:
te dice que no supo medirlo y lo excluye del total.

## Factores de emisión

- **Alimentos**: Poore & Nemecek (2018), *Science* 360(6392) — ciclo de vida
  completo, mediana global por kg de producto.
- **Transporte y energía**: UK DEFRA GHG Conversion Factors (2023) — por
  pasajero-km.
- **Red eléctrica**: IEA (2023), 0,35 kg CO₂e/kWh (promedio latinoamericano).

Cada valor cita su fuente en un comentario junto al número, en `factors.py`.

## Pruebas

```bash
python -m unittest discover -s tests -t .
```

## Despliegue en Replit

`.replit` ya define el comando de arranque, el puerto y el target `autoscale`.
Importa el repositorio en Replit y pulsa **Deploy**. Si quieres el modo con
Claude, añade `ANTHROPIC_API_KEY` en el panel **Secrets** (nunca en un archivo).

## Alcance del MVP

Dentro: comida, transporte y energía del hogar; un día de registro en memoria.
Fuera a propósito: login, base de datos, histórico persistente, multiusuario.
