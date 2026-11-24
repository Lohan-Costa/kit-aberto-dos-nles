"""As contas que não precisam de ffmpeg: TC, frequências, fonte de pixels, faixas de código."""
import unittest

from lab import audio, fonte_pixel, tc, video


class TesteTC(unittest.TestCase):
    def test_ida_e_volta_sem_drop(self):
        for b in (24, 25, 30, 50, 60):
            for q in (0, 1, b - 1, b * 3600, b * 86400 - 1):
                self.assertEqual(tc.tc_para_quadros(tc.quadros_para_tc(q, b), b), q)
        self.assertEqual(tc.tc_para_quadros("01:00:00:00", 25), 90000)

    def test_drop_frame_pula_numeros_nao_quadros(self):
        # 29,97 DF: depois de 00:00:59;29 vem 00:01:00;02
        q = tc.tc_para_quadros("00:00:59;29", 30, df=True)
        self.assertEqual(tc.quadros_para_tc(q + 1, 30, df=True), "00:01:00;02")
        # minuto múltiplo de 10 não pula
        q = tc.tc_para_quadros("00:09:59;29", 30, df=True)
        self.assertEqual(tc.quadros_para_tc(q + 1, 30, df=True), "00:10:00;00")
        # uma hora de DF = 107892 quadros (3600 s × 29,97 arredondado)
        self.assertEqual(tc.tc_para_quadros("01:00:00;00", 30, df=True), 107892)
        for q in range(0, 200000, 997):
            self.assertEqual(tc.tc_para_quadros(tc.quadros_para_tc(q, 30, True), 30, True), q)
        with self.assertRaises(ValueError):
            tc.tc_para_quadros("00:01:00;00", 30, df=True)

    def test_rotulo_do_drop_frame(self):
        q = tc.tc_para_quadros("01:00:59;29", 30, df=True)
        self.assertEqual(tc.rotulo(q, 30, True), tc.tc_para_quadros("01:00:59:29", 30))
        # o quadro seguinte tem o rótulo ;02: dois números a mais, nenhum quadro a mais
        self.assertEqual(tc.rotulo(q + 1, 30, True) - tc.rotulo(q, 30, True), 3)
        self.assertEqual(tc.rotulo(12345, 25), 12345)

    def test_base_da_taxa(self):
        self.assertEqual(tc.base(tc.taxa("23.976")), 24)
        self.assertEqual(tc.base(tc.taxa("59.94")), 60)


class TesteAudio(unittest.TestCase):
    def test_formula_do_organograma(self):
        self.assertEqual(audio.hz(1, 1), 300)
        self.assertEqual(audio.hz(1, 16), 1800)
        self.assertEqual(audio.hz(2, 1), 2000)
        self.assertEqual(audio.hz(4, 1), 5400)
        todas = [audio.hz(f, c) for f in range(1, 5) for c in range(1, 17)]
        self.assertEqual(len(set(todas)), 64)      # nenhuma frequência repetida entre fontes

    def test_claque_no_primeiro_quadro_do_segundo_de_tc(self):
        fps = tc.taxa("29.97")
        q = tc.tc_para_quadros("01:00:59;15", 30, df=True)
        inst = audio.instantes_claque(q, 30, True, fps, 90)
        # 15 quadros até o ;02 do minuto 1, depois 28 (do ;02 ao ;29), depois 30
        self.assertEqual([x * fps for x in inst], [15, 43, 73])
        q = tc.tc_para_quadros("01:00:00:00", 25)
        self.assertEqual(audio.instantes_claque(q, 25, False, tc.taxa("25"), 60), [0, 1, 2])

    def test_claque_no_segundo_inteiro_de_tc(self):
        fps = tc.taxa("25")
        self.assertEqual(audio.primeira_claque(90000, 25, fps), 0)
        self.assertEqual(audio.primeira_claque(90000 + 20, 25, fps) * 25, 5)   # FF=20 → 5 quadros até FF=00
        self.assertAlmostEqual(float(audio.periodo_claque(24, tc.taxa("23.976"))), 1.001)


class TesteDesenho(unittest.TestCase):
    def test_fonte_tem_o_texto_do_quadro(self):
        for texto in ("CAM 1 · TAKE 1", "25 FPS · 1920×1080", "B01 FORMATOS · MXF-XDCAM50", "QUADRO"):
            self.assertTrue(fonte_pixel.retangulos(texto, 0, 0, 4))
        with self.assertRaises(ValueError):
            fonte_pixel.retangulos("ÁUDIO", 0, 0, 4)

    def test_faixas_cobrem_a_largura_sem_buraco(self):
        for w, h in ((1920, 1080), (1080, 1920), (4096, 2160), (2048, 858)):
            cel = video.faixas(w, h)["celulas"]
            self.assertEqual(cel[0][0], 0)
            self.assertEqual(cel[-1][1], w)
            self.assertTrue(all(a[1] == b[0] for a, b in zip(cel, cel[1:])))


if __name__ == "__main__":
    unittest.main()
