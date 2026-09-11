"""Pruebas de la interfaz con el framework de pruebas de Streamlit.

Ejecutan `app.py` de verdad y verifican que renderiza sin excepciones.
"""

import unittest

from streamlit.testing.v1 import AppTest

from app import EJEMPLOS

FRASE = "Hoy comí carne y viajé 20km en bus"


def arrancar() -> AppTest:
    return AppTest.from_file("app.py", default_timeout=30).run()


def enviar(at: AppTest, texto: str) -> AppTest:
    """Escribe la frase y pulsa el botón de calcular.

    Se busca por etiqueta a propósito: tras el primer envío aparece el botón
    "Empezar un día nuevo" al final, y tomar el último borraría el registro.
    """
    at.text_area[0].set_value(texto)
    calcular = next(b for b in at.button if b.label == "Calcular mi huella")
    calcular.click().run()
    return at


class TestArranque(unittest.TestCase):
    def test_arranca_sin_excepciones(self):
        self.assertEqual(arrancar().exception, [])

    def test_muestra_el_estado_inicial(self):
        at = arrancar()
        self.assertTrue(at.info)
        self.assertEqual(at.session_state["registro"], [])


class TestFlujoPrincipal(unittest.TestCase):
    def setUp(self):
        self.at = enviar(arrancar(), FRASE)

    def test_no_lanza_excepciones(self):
        self.assertEqual(self.at.exception, [])

    def test_muestra_las_actividades(self):
        textos = " ".join(m.value for m in self.at.markdown)
        self.assertIn("Carne de res", textos)
        self.assertIn("Bus", textos)

    def test_muestra_las_equivalencias(self):
        self.assertEqual(len(self.at.metric), 3)


class TestCasosBorde(unittest.TestCase):
    def test_avisa_cuando_no_entiende(self):
        at = enviar(arrancar(), "fui a bailar salsa toda la noche")
        self.assertEqual(at.exception, [])
        self.assertTrue(at.warning)

    def test_acumula_varios_registros(self):
        at = enviar(arrancar(), "comi pollo")
        at = enviar(at, "fui 10 km en carro")
        self.assertEqual(len(at.session_state["registro"]), 2)
        self.assertEqual(at.exception, [])

    def test_el_boton_de_ejemplo_precarga_la_entrada(self):
        at = arrancar()
        at.button[0].click().run()
        self.assertIn(at.text_area[0].value, EJEMPLOS)


if __name__ == "__main__":
    unittest.main()
