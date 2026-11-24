"""B10 ROTO: a máscara gerada tem de bater com o `verdade.json` (área e caixa da pessoa), e o movimento não é linear."""
import json
import math
import os
import subprocess
import tempfile
import unittest

from lab import ffmpeg, roto

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEITA = os.path.join(RAIZ, "receitas", "base", "B10_ROTO.json")


def _tem_ffmpeg():
    try:
        ffmpeg.achar("ffmpeg")
        return True
    except Exception:
        return False


class TestRoto(unittest.TestCase):
    def test_trajeto_nao_linear(self):
        with open(RECEITA, encoding="utf-8") as fh:
            r = json.load(fh)
        q = roto.trajeto(r, 300)
        vel = [math.dist((q[i]["pes_x"], q[i]["pes_y"]), (q[i - 1]["pes_x"], q[i - 1]["pes_y"])) for i in range(1, 300)]
        self.assertLess(min(vel), 0.35 * max(vel))                 # quase para no meio
        self.assertLess(q[0]["pes_x"], 0)                          # entra de fora, pelo canto inferior esquerdo
        self.assertGreater(q[0]["pes_y"], r["altura"])
        self.assertGreater(q[-1]["pes_x"], r["largura"])           # sai pela direita, em cima
        self.assertLess(q[-1]["pes_y"], r["altura"] / 2)
        self.assertLess(q[-1]["escala"], q[0]["escala"])           # encolhe com a distância

    @unittest.skipUnless(_tem_ffmpeg(), "PULADO — sem ffmpeg")
    def test_mascara_bate_com_a_verdade(self):
        with tempfile.TemporaryDirectory() as tmp:
            roto.gerar(RECEITA, tmp, segundos=2, avisar=lambda *_: None)
            v = json.load(open(os.path.join(tmp, "verdade.json"), encoding="utf-8"))
            for q in (12, 30):
                info = v["quadros"][q]
                cru = subprocess.run([ffmpeg.achar("ffmpeg"), "-v", "error", "-i", os.path.join(tmp, v["arquivos"]["mascara"]),
                                      "-vf", f"select=eq(n\\,{q}),format=gray", "-fps_mode", "passthrough", "-frames:v", "1",
                                      "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
                w, h = v["formato"]["largura"], v["formato"]["altura"]
                area = sum(1 for b in cru if b >= 126)              # 50% em faixa de vídeo (16..235) ≈ 126
                self.assertLess(abs(area - info["area_px"]) / info["area_px"], 0.02, f"quadro {q}")
                xs = [i % w for i, b in enumerate(cru) if b >= 126]
                ys = [i // w for i, b in enumerate(cru) if b >= 126]
                x0, y0, x1, y1 = info["caixa"]
                self.assertLessEqual(abs(min(xs) - x0), 2); self.assertLessEqual(abs(max(xs) + 1 - x1), 2)
                self.assertLessEqual(abs(min(ys) - y0), 2); self.assertLessEqual(abs(max(ys) + 1 - y1), 2)


if __name__ == "__main__":
    unittest.main()
