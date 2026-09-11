"""Pruebas del parser de lenguaje natural."""

import unittest

from ecotrack.parser import normalizar, parse


def etiquetas(texto: str) -> list[str]:
    return [a.etiqueta for a in parse(texto).actividades]


class TestNormalizar(unittest.TestCase):
    def test_quita_tildes_y_mayusculas(self):
        self.assertEqual(normalizar("Comí CAFÉ"), "comi cafe")

    def test_colapsa_espacios(self):
        self.assertEqual(normalizar("  hoy   comi  "), "hoy comi")


class TestCasoDelEnunciado(unittest.TestCase):
    """El ejemplo exacto que pide el escenario de EcoTrack."""

    def setUp(self):
        self.lectura = parse("Hoy comí carne y viajé 20km en bus")

    def test_reconoce_ambas_actividades(self):
        self.assertEqual(
            [a.etiqueta for a in self.lectura.actividades],
            ["Carne de res", "Bus"],
        )

    def test_usa_los_km_indicados(self):
        bus = self.lectura.actividades[1]
        self.assertEqual(bus.cantidad, 20)
        self.assertFalse(bus.asumido)

    def test_no_deja_texto_sin_reconocer(self):
        self.assertEqual(self.lectura.no_reconocido, ())


class TestTransporte(unittest.TestCase):
    def test_convierte_minutos_a_km(self):
        bus = parse("fui 30 minutos en bus").actividades[0]
        self.assertAlmostEqual(bus.cantidad, 10.0)  # 0.5 h a 20 km/h
        self.assertTrue(bus.asumido)

    def test_asume_distancia_si_falta(self):
        moto = parse("fui en moto").actividades[0]
        self.assertTrue(moto.asumido)
        self.assertGreater(moto.kg_co2e, 0)

    def test_prefiere_el_alias_mas_especifico(self):
        self.assertEqual(etiquetas("fui 10 km en carro electrico"),
                         ["Carro eléctrico"])

    def test_bici_y_caminar_no_emiten(self):
        self.assertEqual(parse("fui 5 km en bici").actividades[0].kg_co2e, 0.0)

    def test_cuadras_se_convierten_a_km(self):
        caminata = parse("camine 10 cuadras").actividades[0]
        self.assertAlmostEqual(caminata.cantidad, 1.0)


class TestAlimentos(unittest.TestCase):
    def test_lee_cantidad_numerica(self):
        huevos = parse("desayune 3 huevos").actividades[0]
        self.assertEqual(huevos.cantidad, 3)
        self.assertFalse(huevos.asumido)

    def test_lee_cantidad_escrita_en_palabras(self):
        self.assertEqual(parse("comi dos hamburguesas").actividades[0].cantidad, 2)

    def test_asume_una_porcion_si_no_hay_cantidad(self):
        pollo = parse("almorce pollo").actividades[0]
        self.assertEqual(pollo.cantidad, 1)
        self.assertTrue(pollo.asumido)

    def test_reconoce_varios_alimentos_en_una_clausula(self):
        self.assertCountEqual(
            etiquetas("almorce pollo con arroz"),
            ["Pollo", "Arroz"],
        )

    def test_la_res_pesa_mas_que_las_legumbres(self):
        res = parse("comi carne").actividades[0].kg_co2e
        legumbres = parse("comi lentejas").actividades[0].kg_co2e
        self.assertGreater(res, legumbres * 10)


class TestEnergia(unittest.TestCase):
    def test_lee_horas_de_aire_acondicionado(self):
        aire = parse("use el aire acondicionado 3 horas").actividades[0]
        self.assertEqual(aire.cantidad, 3)
        self.assertFalse(aire.asumido)

    def test_ducha_cuenta_como_un_uso(self):
        ducha = parse("me duche").actividades[0]
        self.assertEqual(ducha.unidad, "uso")


class TestResiduos(unittest.TestCase):
    def test_lee_bolsas_de_basura(self):
        basura = parse("tire dos bolsas de basura").actividades[0]
        self.assertEqual(basura.etiqueta, "Bolsa de basura")
        self.assertEqual(basura.categoria, "residuos")
        self.assertEqual(basura.cantidad, 2)
        self.assertFalse(basura.asumido)
        self.assertGreater(basura.kg_co2e, 0)

    def test_asume_una_bolsa_si_no_hay_cantidad(self):
        basura = parse("saque la basura").actividades[0]
        self.assertEqual(basura.cantidad, 1)
        self.assertTrue(basura.asumido)

    def test_lee_kilos_de_basura(self):
        basura = parse("tire 3 kg de basura").actividades[0]
        self.assertEqual(basura.unidad, "kg")
        self.assertEqual(basura.cantidad, 3)
        self.assertFalse(basura.asumido)

    def test_reconoce_reciclaje(self):
        recicle = parse("recicle").actividades[0]
        self.assertEqual(recicle.etiqueta, "Reciclaje")
        self.assertTrue(recicle.asumido)

    def test_prefiere_reciclaje_sobre_basura(self):
        self.assertEqual(
            etiquetas("tire una bolsa de reciclaje"),
            ["Reciclaje"],
        )

    def test_reciclaje_emite_menos_que_la_basura(self):
        basura = parse("tire una bolsa de basura").actividades[0].kg_co2e
        recicle = parse("tire una bolsa de reciclaje").actividades[0].kg_co2e
        self.assertGreater(basura, recicle * 10)

    def test_comida_desperdiciada(self):
        comida = parse("desperdicie comida").actividades[0]
        self.assertEqual(comida.etiqueta, "Comida desperdiciada")
        self.assertEqual(comida.unidad, "porción")
        self.assertTrue(comida.asumido)

    def test_no_cuenta_como_comida_consumida(self):
        lectura = parse("desperdicie pollo")
        self.assertEqual(etiquetas("desperdicie pollo"), ["Comida desperdiciada"])
        self.assertEqual(lectura.no_reconocido, ())


class TestLoQueNoEntiende(unittest.TestCase):
    def test_no_inventa_actividades(self):
        lectura = parse("fui a bailar salsa toda la noche")
        self.assertEqual(lectura.actividades, ())
        self.assertEqual(len(lectura.no_reconocido), 1)

    def test_texto_vacio_no_falla(self):
        self.assertEqual(parse("").actividades, ())
        self.assertEqual(parse("   ").no_reconocido, ())

    def test_mezcla_reconocido_y_no_reconocido(self):
        lectura = parse("comi pollo y estuve programando un rato")
        self.assertEqual(len(lectura.actividades), 1)
        self.assertEqual(len(lectura.no_reconocido), 1)


if __name__ == "__main__":
    unittest.main()
