# Vibe Report — EcoTrack

## Cómo configuré las reglas del agente

El `.cursorrules` no lo escribí como una lista de buenos deseos ("código
limpio", "usa buenas prácticas"), porque eso un modelo ya lo cree estar
haciendo. Lo escribí como **restricciones verificables**: la UI vive solo en
`app.py` y no calcula nada; cada factor de emisión debe citar su fuente en un
comentario; cuando el parser asume un dato, tiene que marcarlo con
`asumido=True` y la interfaz tiene que decirlo.

Dos reglas fueron las que más trabajo hicieron. La primera: *"nunca inventes un
número de CO₂e; si no hay factor, marca la actividad como no reconocida"*. La
segunda: *"si te paso un traceback, arregla la causa raíz, no lo envuelvas en
un try/except"*. Ambas existen porque son exactamente las salidas fáciles que
un agente toma cuando quiere que el código deje de fallar.

## Qué costó delegar

Lo más incómodo fue aceptar que ya no reviso línea por línea, sino
**comportamientos**: dejé de preguntarme "¿esta función está bien escrita?" y
empecé a preguntarme "¿qué pasa si el usuario escribe algo que no está en el
catálogo?".

El momento más útil fue uno de desacuerdo. El agente usó 99,5 kg CO₂e/kg para
la carne de res, que es el valor del hato de carne puro en Poore & Nemecek. Es
defendible, pero para un calculador de consumo el promedio ponderado global
(~60) es más honesto. No lo detecté leyendo el código: lo detecté porque un
plato de carne daba 15 kg y el número no pasaba el olfato. **La revisión se
mudó del código al resultado.**

También aprendí que delegar mal se paga rápido. La primera versión de las
pruebas fallaba con `ImportError` por un `__init__.py` que faltaba en `tests/`.
Bastó pasar el traceback; el agente diagnosticó y corrigió el origen. Ese ciclo
—describir el síntoma, no la solución— es el núcleo del flujo.

## De escribir código a orquestar una visión

La diferencia práctica es dónde gasto la atención. Antes se me iba en sintaxis
y en recordar APIs. Ahora se va en decisiones de producto: ¿qué pasa cuando la
app no entiende?, ¿confío en un LLM para calcular emisiones?

Esa última pregunta definió la arquitectura. Decidí que Claude **solo extrae
entidades** y que los kg CO₂e los calcula siempre el código local con factores
citados. Un LLM es excelente entendiendo "me fui en buseta media hora" y es
justamente donde no debe estar un número que el usuario va a creerse. Esa
decisión no la tomó el agente: la tomé yo y él la ejecutó en cuatro archivos.

Ahí está el cambio. El agente escribe mejor y más rápido que yo. Lo que no hace
es decidir qué merece existir, dónde está el límite de lo que la app promete, y
cuándo un número correcto según la fuente sigue siendo el número equivocado
para el usuario. Vibe coding no es dejar de pensar: es mover el pensamiento
hacia arriba.
