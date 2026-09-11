"""Pruebas de la agregación de huella."""

import unittest

from ecotrack.calculator import (
    equivalencias,
    resumir,
    sugerencias,
    veredicto,
)
from ecotrack.parser import parse


class TestResumir(unittest.TestCase):
    def setUp(self):
        self.lectura = parse("Hoy comí carne y viajé 20km en bus")
        self.resumen = resumir(self.lectura.actividades)

    def test_suma_el_total(self):
        esperado = sum(a.kg_co2e for a in self.lectura.actividades)
        self.assertAlmostEqual(self.resumen.total_kg, esperado, places=2)

    def test_agrupa_por_categoria(self):
        self.assertEqual(
            set(self.resumen.por_categoria),
            {"Alimentación", "Transporte"},
        )

    def test_identifica_el_mayor_aporte(self):
        self.assertEqual(self.resumen.mayor_aporte.etiqueta, "Carne de res")

    def test_compara_contra_las_referencias(self):
        self.assertGreater(self.resumen.vs_meta_paris, 1.0)
        self.assertLess(self.resumen.vs_mundial, 1.0)


class TestCasosBorde(unittest.TestCase):
    def test_dia_vacio(self):
        resumen = resumir([])
        self.assertEqual(resumen.total_kg, 0)
        self.assertIsNone(resumen.mayor_aporte)
        self.assertEqual(veredicto(resumen)[0], "bajo")

    def test_dia_sin_emisiones_no_tiene_mayor_aporte(self):
        resumen = resumir(parse("fui 5 km en bici").actividades)
        self.assertEqual(resumen.total_kg, 0)
        self.assertIsNone(resumen.mayor_aporte)

    def test_sin_equivalencias_si_no_hay_emisiones(self):
        self.assertEqual(equivalencias(0), {})


class TestVeredicto(unittest.TestCase):
    def test_dia_ligero_es_bajo(self):
        resumen = resumir(parse("desayune fruta y fui en bici").actividades)
        self.assertEqual(veredicto(resumen)[0], "bajo")

    def test_dia_pesado_es_alto(self):
        resumen = resumir(parse("comi carne y viaje 300 km en avion").actividades)
        self.assertEqual(veredicto(resumen)[0], "alto")


class TestSugerencias(unittest.TestCase):
    def test_sin_actividades_no_sugiere_nada(self):
        self.assertEqual(sugerencias([]), [])

    def test_sugiere_sobre_lo_que_mas_pesa(self):
        consejos = sugerencias(parse("comi carne y viaje 20km en bus").actividades)
        self.assertTrue(consejos[0].startswith("Carne de res"))

    def test_sugiere_sobre_residuos(self):
        consejos = sugerencias(parse("tire dos bolsas de basura").actividades)
        self.assertTrue(consejos[0].startswith("Bolsa de basura"))


class TestResiduos(unittest.TestCase):
    def test_agrupa_residuos_en_su_categoria(self):
        resumen = resumir(parse("recicle y desperdicie comida").actividades)
        self.assertEqual(set(resumen.por_categoria), {"Residuos"})
        self.assertGreater(resumen.total_kg, 0)


if __name__ == "__main__":
    unittest.main()
