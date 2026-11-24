"""A máscara de objeto do Premiere 2026 (.prmf): o índice (FlatBuffers), o GDeflate e a máscara contra a perfeita do B10.
Os .prmf vêm do projeto de rotoscopia do autor (resultados/B10_ROTO/premiere-26.0.2-autor, no Git)."""
import glob
import hashlib
import os
import subprocess
import unittest

from lab import ffmpeg, gdeflate, prmf

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, "resultados", "B10_ROTO", "premiere-26.0.2-autor", "rotoscopia_teste_premiere26 Masks")
GRANDE = os.path.join(PASTA, "7d695d77-11c9-40ab-a570-834c275a824c.prmf")
MASCARA_B10 = os.path.join(RAIZ, "saida", "base", "B10_ROTO", "B10_ROTO_MASCARA_MOV-PRORES.mov")


class TestPrmf(unittest.TestCase):
    def test_indice(self):
        qs = prmf.ler(GRANDE)
        self.assertEqual(len(qs), 250)
        self.assertAlmostEqual(qs[0]["segundos"], 2.0)
        q3 = next(q for q in qs if abs(q["segundos"] - 3.0) < 1e-6)
        self.assertEqual(q3["caixa"], [389, 426, 238, 517])          # (x, y, largura, altura) = a verdade do B10 no q75
        self.assertEqual(q3["quadro_inteiro"], (1920, 1080))

    def test_gdeflate_igual_a_referencia(self):
        """O 1º quadro descomprimido tem o md5 que o libdeflate da NVIDIA (referência do GDeflate) deu em 2026-10-07; os 281
        quadros dos 3 .prmf foram conferidos um a um contra ela no mesmo dia."""
        q = prmf.ler(GRANDE)[0]
        with open(GRANDE, "rb") as fh:
            fh.seek(q["pos"]); dados = fh.read(q["tam"])
        cru = gdeflate.descomprimir(dados)
        self.assertEqual(len(cru), 17600)
        self.assertEqual(hashlib.md5(cru).hexdigest(), "3c3c1581325e3ad815a3692cadd2b0e6")

    def test_todos_os_quadros_decodificam(self):
        for arq in glob.glob(os.path.join(PASTA, "*.prmf")):
            for q in prmf.ler(arq):
                m = prmf.mascara(q)
                if m is not None:
                    linhas, w2, h2 = m
                    self.assertEqual((len(linhas), len(linhas[0])), (h2, w2))

    @unittest.skipUnless(os.path.isfile(MASCARA_B10), "PULADO — gere o B10 (python3 -m lab.roto receitas/base/B10_ROTO.json)")
    def test_mascara_bate_com_a_perfeita(self):
        q = next(q for q in prmf.ler(GRANDE) if abs(q["segundos"] - 4.0) < 1e-6)
        a = prmf.alfa_quadro_inteiro(q)
        p = subprocess.run([ffmpeg.achar("ffmpeg"), "-v", "error", "-i", MASCARA_B10, "-vf", "select=eq(n\\,100),format=gray",
                            "-fps_mode", "passthrough", "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
        inter = sum(1 for x, y in zip(a, p) if x >= 128 and y >= 126)
        uniao = sum(1 for x, y in zip(a, p) if x >= 128 or y >= 126)
        self.assertGreater(inter / uniao, 0.92)                       # 0,936 medido (a borda fina o Premiere refina na hora)


if __name__ == "__main__":
    unittest.main()
