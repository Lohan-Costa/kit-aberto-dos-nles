"""O B01 de ponta a ponta (encurtado para 2,5 s): gerar os seis perfis numa pasta temporária e
conferir cada arquivo — e conferir que o verificador ACUSA um arquivo estragado (sem isso, "passou"
não prova nada)."""
import copy
import json
import os
import shutil
import tempfile
import unittest

from lab import ffmpeg, gerar, verificar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEITA = os.path.join(RAIZ, "receitas", "base", "B01.json")



def _verdade(pasta):
    with open(os.path.join(pasta, "verdade.json"), encoding="utf-8") as fh:
        return json.load(fh)


try:
    ffmpeg.achar("ffmpeg"), ffmpeg.achar("ffprobe")
    SEM_FFMPEG = None
except FileNotFoundError as e:
    SEM_FFMPEG = str(e)


@unittest.skipIf(SEM_FFMPEG, f"PULADO — sem ffmpeg: {SEM_FFMPEG}")
class TesteB01(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pasta = tempfile.mkdtemp(prefix="lab-b01-")
        gerar.gerar(RECEITA, cls.pasta, segundos=2.5, avisar=lambda *_: None)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.pasta, ignore_errors=True)

    def test_os_seis_perfis_conferem(self):
        rel = verificar.verificar(self.pasta)
        falhas = [(a["arquivo"], x) for a in rel["arquivos"] for x in a["conferencias"] if not x["ok"]]
        self.assertEqual(falhas, [])
        perfis = {a["perfil"] for a in _verdade(self.pasta)["arquivos"]}
        self.assertEqual(perfis, {"mp4-h264", "mov-prores", "mxf-op1a", "mxf-xdcam50", "mxf-opatom", "wav-bwf"})
        self.assertEqual(len(rel["arquivos"]), 8)    # o OP-Atom são 3 arquivos (V01, A01, A02)
        # o rótulo do container tem de dizer CLIP-wrapped (o ffmpeg diz frame-wrapped e o Premiere recusa o vídeo)
        with open(os.path.join(self.pasta, "B01_MXF-OPATOM", "B01_V01.mxf"), "rb") as fh:
            v = fh.read(65536)
        self.assertIn(bytes.fromhex("060e2b340401010a0d01030102110200"), v)
        self.assertNotIn(bytes.fromhex("060e2b340401010a0d01030102110100"), v)
        # costurados: a MESMA identidade de clipe nos 3, e cada um com as trilhas V1, A1, A2 (+ TC)
        umids = set()
        for nome in ("B01_V01", "B01_A01", "B01_A02"):
            info = ffmpeg.sondar(os.path.join(self.pasta, "B01_MXF-OPATOM", nome + ".mxf"))
            umids.add(info["format"]["tags"]["material_package_umid"])
            self.assertEqual([s.get("tags", {}).get("track_name") for s in info["streams"]], ["V1", "A1", "A2"])
        self.assertEqual(len(umids), 1)
        self.assertEqual([f for f in os.listdir(os.path.join(self.pasta, "B01_MXF-OPATOM")) if f.endswith(".ffmpeg.mxf")], [])

    def test_verificador_acusa_canais_trocados_e_tc_errado(self):
        origem = os.path.join(self.pasta, "B01_MOV-PRORES.mov")
        estragado = os.path.join(self.pasta, "estragado.mov")
        ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-v", "error", "-y", "-i", origem, "-map", "0:v", "-map", "0:a",
                      "-c:v", "copy", "-af", "pan=stereo|c0=c1|c1=c0", "-c:a", "pcm_s24le",
                      "-timecode", "01:00:00:01", estragado])
        verdade = _verdade(self.pasta)
        esp = copy.deepcopy(next(a for a in verdade["arquivos"] if a["perfil"] == "mov-prores"))
        esp["arquivo"] = "estragado.mov"
        falhas = {x["conferencia"] for x in verificar.verificar_arquivo(self.pasta, esp) if not x["ok"]}
        self.assertEqual(falhas, {"timecode", "A1 canal 1 tom (Hz)", "A1 canal 2 tom (Hz)"})


if __name__ == "__main__":
    unittest.main()


@unittest.skipIf(SEM_FFMPEG, f"PULADO — sem ffmpeg: {SEM_FFMPEG}")
class TesteB02(unittest.TestCase):
    """23,976 e 29,97 drop-frame atravessando o minuto (01:00:59;15 → 01:01:00;02), em 1,5 s."""

    def test_taxas_fracionarias_e_drop_frame_conferem(self):
        pasta = tempfile.mkdtemp(prefix="lab-b02-")
        try:
            gerar.gerar(os.path.join(RAIZ, "receitas", "base", "B02.json"), pasta, segundos=1.5,
                        avisar=lambda *_: None, so=["2398", "2997DF"])
            rel = verificar.verificar(pasta)
            falhas = [(a["arquivo"], x) for a in rel["arquivos"] for x in a["conferencias"] if not x["ok"]]
            self.assertEqual(falhas, [])
            self.assertEqual(len(rel["arquivos"]), 4)
            df = next(a for a in _verdade(pasta)["arquivos"] if a["drop_frame"])
            self.assertEqual(df["tc_inicio"], "01:00:59;15")
        finally:
            shutil.rmtree(pasta, ignore_errors=True)
