"""As contas do convertido (roteiro 4, 2026-10-09): onde o original cai e o fator certo do relink."""
import unittest

from lab import convertido


class TesteGeometria(unittest.TestCase):
    def test_mesma_proporcao_a_regra_das_larguras_acerta(self):
        g = convertido.geometria(3840, 2160, None, 1920, 1080, "fit")
        self.assertEqual(g["fator_relink"], 0.5)
        self.assertTrue(g["regra_acerta"])
        self.assertEqual(g["imagem_util"], [0.0, 0.0, 1920.0, 1080.0])

    def test_tarja_cabe_pela_largura(self):
        g = convertido.geometria(4096, 2160, None, 1920, 1080, "fit")
        self.assertAlmostEqual(g["fator_relink"], 1920 / 4096)
        self.assertTrue(g["regra_acerta"])
        self.assertEqual(g["imagem_util"], [0.0, 33.75, 1920.0, 1012.5])

    def test_corte_erra_a_regra(self):
        g = convertido.geometria(4096, 2160, None, 1920, 1080, "fill")
        self.assertEqual(g["fator_relink"], 0.5)          # pela ALTURA
        self.assertFalse(g["regra_acerta"])
        self.assertEqual(g["imagem_util"], [-64.0, 0.0, 2048.0, 1080.0])

    def test_vertical_com_pillarbox(self):
        g = convertido.geometria(1080, 1920, None, 1920, 1080, "fit")
        self.assertAlmostEqual(g["fator_relink"], 1080 / 1920)
        self.assertAlmostEqual(g["regra_das_larguras"], 1920 / 1080)
        self.assertFalse(g["regra_acerta"])

    def test_anamorfico_desespremido(self):
        g = convertido.geometria(1440, 1080, "2:1", 1920, 1080, "fit")
        self.assertAlmostEqual(g["fator_relink"], 1920 / 2880)
        self.assertEqual(g["original_visto"], [2880.0, 1080.0])
        self.assertFalse(g["regra_acerta"])

    def test_stretch_nao_e_uniforme(self):
        g = convertido.geometria(4096, 2160, None, 1920, 1080, "stretch")
        self.assertEqual(g["fator_relink"], [1920 / 4096, 0.5])
        self.assertFalse(g["regra_acerta"])

    def test_modo_desconhecido(self):
        with self.assertRaises(ValueError):
            convertido.geometria(1920, 1080, None, 1920, 1080, "zoom")


if __name__ == "__main__":
    unittest.main()
