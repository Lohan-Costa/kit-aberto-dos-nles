"""O pacote multicam: a régua (pura) e uma geração curta (TC presente ou ausente como a receita manda)."""
import json
import os
import tempfile
import unittest

from lab import conferir_multicam, ffmpeg, multicam

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _verdade():
    return {"caso": "MX", "arquivos": [
        {"arquivo": "CAM 1/a.mov", "inicio_na_cena_s": 4.0, "atraso_ms": 3},
        {"arquivo": "CAM 2/b.mov", "inicio_na_cena_s": 6.0, "atraso_ms": 9},
        {"arquivo": "SOM DIRETO/s.wav", "inicio_na_cena_s": 2.0, "atraso_ms": 0},
    ]}


class Regua(unittest.TestCase):
    def test_sync_certo_em_qualquer_origem(self):
        # a sequência começa 100 s "depois" da cena: só a posição relativa importa
        resumo = [("V1", "a.mov", 104.0, 110), ("V2", "b.mov", 106.0, 110), ("A1", "s.wav", 102.0, 120)]
        r = conferir_multicam.conferir(_verdade(), resumo, 25)
        self.assertEqual(r["pior_erro_quadros"], 0)
        self.assertTrue(r["veredito"].startswith("certo"))

    def test_erro_de_dois_quadros_aparece(self):
        resumo = [("V1", "a.mov", 104.0, 110), ("V2", "b.mov", 106.08, 110), ("A1", "s.wav", 102.0, 120)]
        r = conferir_multicam.conferir(_verdade(), resumo, 25)
        self.assertAlmostEqual(r["pior_erro_quadros"], 2.0, places=2)
        self.assertFalse(r["veredito"].startswith("certo"))

    def test_arquivo_que_faltou(self):
        r = conferir_multicam.conferir(_verdade(), [("V1", "a.mov", 4.0, 9)], 25)
        self.assertEqual(r["fora_da_sequencia"], 2)


class Geracao(unittest.TestCase):
    def test_m02_cameras_sem_tc_e_som_com_bext(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = multicam.gerar(os.path.join(RAIZ, "receitas", "multicam", "M02_SEM_TC.json"), tmp, 6,
                                   avisar=lambda *_: None)
            v = json.load(open(os.path.join(pasta, "verdade.json"), encoding="utf-8"))
            cams = [a for a in v["arquivos"] if not a["som"]]
            self.assertTrue(cams and all(a["tc"] is None for a in cams))
            s = ffmpeg.sondar(os.path.join(pasta, cams[0]["arquivo"]))
            self.assertFalse(any(st.get("codec_type") == "data" for st in s["streams"]))
            som = next(a for a in v["arquivos"] if a["som"])
            self.assertIsNotNone(som["time_reference"])

    def test_m05_slow_quatro_vezes_mais_longo_e_mudo(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = multicam.gerar(os.path.join(RAIZ, "receitas", "multicam", "M05_SLOW.json"), tmp, 9,
                                   avisar=lambda *_: None)
            v = json.load(open(os.path.join(pasta, "verdade.json"), encoding="utf-8"))
            slow = [a for a in v["arquivos"] if a["fps_captura"]]
            self.assertTrue(slow)
            for a in slow:
                self.assertAlmostEqual(a["duracao_do_arquivo_s"], 4 * a["duracao_na_cena_s"], places=2)
                self.assertIsNone(a["audio"])


if __name__ == "__main__":
    unittest.main()
