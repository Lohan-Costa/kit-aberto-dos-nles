"""A máscara de objeto do 2026 no rebaixamento para o 2023 (`lab/prproj_mascara.py`), com o projeto de rotoscopia do autor
(resultados/B10_ROTO/premiere-26.0.2-autor, no Git). O 23.2 real abriu o resultado e o recorte saiu idêntico ao gabarito
nativo (2026-10-08, pela ponte) — aqui se confere a estrutura."""
import collections
import gzip
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

from lab import ffmpeg, prproj_downgrade

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEM = os.path.join(RAIZ, "resultados", "B10_ROTO", "premiere-26.0.2-autor", "rotoscopia_teste_premiere26.prproj")


def _tem_ffmpeg():
    try:
        ffmpeg.achar("ffmpeg")
        return True
    except Exception:
        return False


@unittest.skipUnless(_tem_ffmpeg(), "PULADO — sem ffmpeg")
class TestMascaraDeObjeto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.destino = os.path.join(cls.dir, "B10 ROTO - para 2023.prproj")
        cls.r = prproj_downgrade.rebaixar(ORIGEM, cls.destino, "23.2")
        with open(cls.destino, "rb") as fh:
            cls.raiz = ET.fromstring(gzip.decompress(fh.read()))
        cls.objs = {(e.get("ObjectID") or e.get("ObjectUID")): e for e in cls.raiz if e.get("ObjectID") or e.get("ObjectUID")}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_contagem(self):
        c = self.r["campos_devolvidos"]
        self.assertEqual(c.get("máscara de objeto → Track Matte"), 1)          # o clipe 0–12 s, Opacidade, 3 passadas
        self.assertEqual(c.get("máscara de objeto retirada"), 1)               # o clipe 64,4 s, na Lumetri, sem .prmf
        self.assertEqual(c.get("quadros com máscara no matte"), 272)

    def test_sem_referencia_quebrada_nem_id_repetido(self):
        ids = collections.Counter((e.get("ObjectID") or e.get("ObjectUID")) for e in self.raiz
                                  if e.get("ObjectID") or e.get("ObjectUID"))
        self.assertEqual([k for k, v in ids.items() if v > 1], [])
        falta = [(e.tag, x.get("ObjectRef") or x.get("ObjectURef")) for e in self.raiz if e.tag != "Project"
                 for x in e.iter() if (x.get("ObjectRef") or x.get("ObjectURef")) and (x.get("ObjectRef") or x.get("ObjectURef")) not in self.objs]
        self.assertEqual(falta, [])

    def test_track_matte_aponta_para_v2_em_luma(self):
        tm = [e for e in self.raiz if e.findtext("MatchName") == "AE.ADBE Legacy Key Track Matte"]
        self.assertEqual(len(tm), 1)
        params = {self.objs[p.get("ObjectRef")].findtext("ParameterID"): self.objs[p.get("ObjectRef")].findtext("StartKeyframe").split(",")[1]
                  for p in tm[0].findall("Component/Params/Param")}
        self.assertEqual(params, {"1": "2", "2": "1", "3": "false"})

    def test_nenhuma_mascara_de_objeto_sobra(self):
        from lab import prproj_mascara as pm
        tipos = [pm._tipo_e_ids(self.objs, e)[0] for e in self.raiz if e.findtext("MatchName") == "AE.ADBE AEMask2"]
        self.assertNotIn("4", tipos)

    def test_matte_ao_lado_com_a_duracao_da_midia(self):
        pasta = os.path.splitext(self.destino)[0] + " MATTES"
        arqs = os.listdir(pasta)
        self.assertEqual(len(arqs), 1)
        # ⚠️ JSON, não CSV: o ffprobe 9.0.2 (Homebrew) repete a linha do stream no CSV quando se pede `stream_tags`
        # (o stream sem a tag, uma vazia, o stream com a tag) — retorno do kit aberto, 2026-11-25; o 9.1 não repete
        r = subprocess.run([ffmpeg.achar("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_frames,width,height,r_frame_rate:stream_tags=timecode", "-of", "json",
                            os.path.join(pasta, arqs[0])], capture_output=True, text=True).stdout
        s = json.loads(r)["streams"][0]
        self.assertEqual((s["width"], s["height"], s["r_frame_rate"], s["nb_frames"], s["tags"]["timecode"]),
                         (1920, 1080, "25/1", "300", "01:00:00:00"))


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(_tem_ffmpeg(), "PULADO — sem ffmpeg")
class TestTrilhaDoMatte(unittest.TestCase):
    """V2 e V3 ocupadas no trecho da máscara (o B10 a 30% em cada canto, salvo pelo 26.0.2): o matte vai para uma trilha NOVA,
    nada se sobrescreve. No 23.2 real (2026-10-08): os dois clipes de cima intactos e o recorte idêntico ao do caso simples."""

    def test_sem_trilha_livre_cria_uma(self):
        orig = os.path.join(RAIZ, "resultados", "B10_ROTO", "premiere-26.0.2-trilhas", "B10 ROTO TRILHAS.prproj")
        with tempfile.TemporaryDirectory() as d:
            prj = os.path.join(d, "B10 ROTO TRILHAS.prproj")
            shutil.copy(orig, prj)
            shutil.copytree(os.path.splitext(ORIGEM)[0] + " Masks", os.path.join(d, "B10 ROTO TRILHAS Masks"),
                            ignore=shutil.ignore_patterns("._*"))
            dest = os.path.join(d, "saida.prproj")
            r = prproj_downgrade.rebaixar(prj, dest, "23.2")
            with open(dest, "rb") as fh:
                raiz = ET.fromstring(gzip.decompress(fh.read()))
        self.assertEqual(r["campos_devolvidos"].get("trilha de vídeo criada para o matte"), 1)
        objs = {(e.get("ObjectID") or e.get("ObjectUID")): e for e in raiz if e.get("ObjectID") or e.get("ObjectUID")}
        g = next(e for e in raiz if e.tag == "VideoTrackGroup")
        trilhas = [objs[t.get("ObjectURef")] for t in g.find("TrackGroup/Tracks")]
        nomes = [[objs[objs[i.get("ObjectRef")].find("ClipTrackItem/SubClip").get("ObjectRef")].findtext("Name")
                  for i in (t.find("ClipTrack/ClipItems/TrackItems") or [])] for t in trilhas]
        self.assertEqual([len(n) for n in nomes], [6, 1, 1, 1])                    # V2 e V3 intactas, o matte na V4
        self.assertIn("MATTE", nomes[3][0])
        self.assertEqual([t.findtext("ClipTrack/Track/ID") for t in trilhas], ["1", "2", "3", "4"])
        self.assertEqual(g.findtext("TrackGroup/NextTrackID"), "5")
        tm = next(e for e in raiz if e.findtext("MatchName") == "AE.ADBE Legacy Key Track Matte")
        matte = next(objs[p.get("ObjectRef")] for p in tm.findall("Component/Params/Param") if objs[p.get("ObjectRef")].findtext("ParameterID") == "1")
        self.assertEqual(matte.findtext("StartKeyframe").split(",")[1], "4")


@unittest.skipUnless(_tem_ffmpeg(), "PULADO — sem ffmpeg")
class TestMascarasDeForma(unittest.TestCase):
    """Retângulo/elipse/caneta do 26 (`AEMask2`) → a máscara do 23 (`AE.ADBE AEMask`) com o tracking assado. No 23.2 real
    (2026-10-08): 13 quadros contra o render do 26, área IoU 0,989–1,000, diferença média ≤ 0,11/255."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        dest = os.path.join(cls.dir, "formas.prproj")
        cls.r = prproj_downgrade.rebaixar(ORIGEM, dest, "23.2")
        with open(dest, "rb") as fh:
            cls.raiz = ET.fromstring(gzip.decompress(fh.read()))
        cls.objs = {(e.get("ObjectID") or e.get("ObjectUID")): e for e in cls.raiz if e.get("ObjectID") or e.get("ObjectUID")}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_contagem(self):
        c = self.r["campos_devolvidos"]
        self.assertEqual((c.get("máscara (elipse) → máscara do 23"), c.get("máscara (retângulo) → máscara do 23"),
                          c.get("máscara (caneta) → máscara do 23"), c.get("quadros de tracking assados no caminho")), (1, 1, 2, 810))

    def test_caminho_por_quadro_e_ordem_dos_filhos(self):
        mascaras = [e for e in self.raiz if e.findtext("MatchName") == "AE.ADBE AEMask"]
        self.assertEqual(len(mascaras), 4)
        kfs = []
        for m in mascaras:
            p6 = next(self.objs[p.get("ObjectRef")] for p in m.findall("Component/Params/Param")
                      if self.objs[p.get("ObjectRef")].findtext("ParameterID") == "6")
            # a ordem que o 23.2 grava (com outra, "project appears to be damaged")
            self.assertEqual([c.tag for c in p6], ["Name", "ParameterControlType", "StartKeyframePosition", "Keyframes",
                                                   "StartKeyframeValue", "ParameterID"])
            self.assertTrue(p6.find("StartKeyframeValue").get("BinaryHash"))
            kfs.append(len([x for x in p6.findtext("Keyframes").split(";") if x]))
        self.assertEqual(sorted(kfs), [2, 270, 270, 270])

    def test_nenhum_binario_orfao(self):
        """Um valor binário VAZIO com `BinaryHash` aponta para o conteúdo de mesmo hash noutro ponto do arquivo; sem ele, o
        23.2 diz "damaged" (o molde da máscara trazia um vazio do PRODUCAO-C — medido 2026-10-08)."""
        com = {e.get("BinaryHash") for e in self.raiz.iter() if e.get("BinaryHash") and (e.text or "").strip()}
        orfaos = [e.tag for e in self.raiz.iter() if e.get("BinaryHash") and not (e.text or "").strip() and e.get("BinaryHash") not in com]
        self.assertEqual(orfaos, [])
