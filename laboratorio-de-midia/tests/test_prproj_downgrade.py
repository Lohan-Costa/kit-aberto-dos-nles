"""O rebaixador 26 → 25: com os projetos que o próprio Premiere salvou (resultados/*/prproj, no Git), o 26 rebaixado
tem de ficar com as MESMAS versões do 25 em todo elemento — e só a Version muda, nada mais no XML."""
import glob
import os
import re
import tempfile
import unittest

from lab import prproj_downgrade, prproj_estrutura

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SO_DO_27 = {"B09_COR"}      # casos cujo projeto do 27 tem recurso que só ele tem


class TestDowngrade(unittest.TestCase):
    def test_so_a_versao_da_tabela_muda(self):
        xml = ('<Project ObjectID="1" ClassID="x" Version="45"><Track Version="4"><IsLocked>false</IsLocked></Track>'
               '<VideoTrack Version="4"/><Component ObjectID="2" ClassID="y" Version="7"/><Track Version="9"/></Project>')
        novo, cont = prproj_downgrade.rebaixar_xml(xml)
        self.assertIn('<Project ObjectID="1" ClassID="x" Version="43">', novo)
        self.assertIn('<Track Version="3">', novo)
        self.assertIn('<VideoTrack Version="4"/>', novo)        # outro elemento: intocado
        self.assertIn('<Track Version="9"/>', novo)             # versão que não é a do 26: intocada
        self.assertEqual(cont, {"Project": 1, "Track": 1, "Component": 1})
        self.assertEqual(re.sub(r'Version="\d+"', "", novo), re.sub(r'Version="\d+"', "", xml))

    def test_cada_caso_rebaixado_fica_com_as_versoes_do_destino(self):
        """Cada caso salvo por cada versão, rebaixado para cada versão mais velha: a MESMA estrutura do destino nativo.
        Um elemento novo que a tabela não conhece (um recurso novo num caso) faz isto falhar — de propósito."""
        pares = [("26.0.2", "25.6.5"), ("27.1.0", "26.0.2"), ("27.1.0", "25.6.5")]
        casos = sorted(glob.glob(os.path.join(RAIZ, "resultados", "B0*", "prproj")))
        self.assertGreaterEqual(len(casos), 7, "faltam os projetos salvos em resultados/*/prproj")
        feitos = 0
        with tempfile.TemporaryDirectory() as tmp:
            for pasta in casos:
                for de, para in pares:
                    origem = os.path.join(pasta, f"premiere-{de}-darwin.prproj")
                    nativo = os.path.join(pasta, f"premiere-{para}-darwin.prproj")
                    if not (os.path.isfile(origem) and os.path.isfile(nativo)):
                        continue
                    saida = os.path.join(tmp, "rebaixado.prproj")
                    r = prproj_downgrade.rebaixar(origem, saida, para)
                    self.assertEqual(r["sobrou_versao_de_origem"], {}, origem)
                    cmp = prproj_estrutura.comparar(prproj_estrutura.impressao(nativo), prproj_estrutura.impressao(saida))
                    self.assertEqual(cmp["elementos_versao_difere"], {}, f"{origem} → {para}")
                    self.assertEqual(cmp["Project"][0], cmp["Project"][1])
                    feitos += 1
        self.assertGreaterEqual(feitos, 21)


    def test_campos_de_audio_iguais_ao_destino_nativo(self):
        """O que o 26 omite e o 25 precisa (layout, tipo de canal, taxa da cadeia/trilha de áudio): o rebaixado tem de
        trazer EXATAMENTE os do 25 nativo — o clipe mono do merged virou estéreo quando o padrão estava errado (B08)."""
        import collections
        import xml.etree.ElementTree as ET

        def pares(x):
            c = collections.Counter()
            for tag in ("AudioComponentChain", "AudioTrack", "AudioTrackInlet"):
                for el in ET.fromstring(x.encode()).iter(tag):
                    if "ObjectRef" in el.attrib or len(el) == 0:
                        continue
                    c[(tag, el.findtext("AudioChannelLayout"), el.findtext("ChannelType"), el.findtext("FrameRate"),
                       el.findtext("AutomationMode"))] += 1
            return c

        with tempfile.TemporaryDirectory() as tmp:
            for pasta in sorted(glob.glob(os.path.join(RAIZ, "resultados", "B0*", "prproj"))):
                nativo = os.path.join(pasta, "premiere-25.6.5-darwin.prproj")
                for de in ("26.0.2", "27.1.0"):
                    # o B09 do 27 tem conteúdo que o 25 não tem (Apple Log, os efeitos de cor novos): não é o mesmo projeto
                    if de == "27.1.0" and os.path.basename(os.path.dirname(pasta)) in SO_DO_27:
                        continue
                    origem = os.path.join(pasta, f"premiere-{de}-darwin.prproj")
                    if not (os.path.isfile(origem) and os.path.isfile(nativo)):
                        continue
                    saida = os.path.join(tmp, "r.prproj")
                    prproj_downgrade.rebaixar(origem, saida, "25.6.5")
                    self.assertEqual(pares(prproj_estrutura.ler_xml(saida)), pares(prproj_estrutura.ler_xml(nativo)), origem)


    def test_look_da_lumetri_vai_para_o_popup(self):
        """O 23.2 lê o Look pela posição no menu (ParameterID 25); o nome (96) sozinho mostra "None" (COPA, 2026-10-07)."""
        import base64
        import xml.etree.ElementTree as ET

        def lumetri(oid, nome, popup):
            b64 = base64.b64encode((nome + "\x00").encode("utf-16-le")).decode()
            return (f'<VideoFilterComponent ObjectID="{oid}" ClassID="c" Version="9"><Component Version="6"><Params Version="1">'
                    f'<Param Index="0" ObjectRef="{oid}1"/><Param Index="1" ObjectRef="{oid}2"/></Params></Component>'
                    f'<MatchName>AE.ADBE Lumetri</MatchName></VideoFilterComponent>'
                    f'<ArbVideoComponentParam ObjectID="{oid}1" ClassID="a" Version="2"><ParameterID>96</ParameterID>'
                    f'<StartKeyframeValue Encoding="base64">{b64}</StartKeyframeValue></ArbVideoComponentParam>'
                    f'<VideoComponentParam ObjectID="{oid}2" ClassID="v" Version="9"><ParameterID>25</ParameterID>'
                    f'<StartKeyframe>0,{popup},0,0,0,0,0,0</StartKeyframe></VideoComponentParam>')

        xml = ("<PremiereData>" + lumetri(1, "Fuji ETERNA 250D Fuji 3510 (by Adobe)", 0) + lumetri(2, "SL BIG HDR", 0)
               + lumetri(3, "MEU LOOK.cube", 0) + lumetri(4, "", 0) + "</PremiereData>")
        raiz = ET.fromstring(xml)
        cont = prproj_downgrade.look_da_lumetri(raiz)
        popup = {p.get("ObjectID"): p.findtext("StartKeyframe").split(",")[1] for p in raiz.iter("VideoComponentParam")}
        self.assertEqual(popup["12"], "5")                       # medido no 23.2 nativo
        self.assertEqual(popup["22"], str(4 + prproj_downgrade.LOOKS_CRIATIVOS.index("SL BIG HDR")))
        self.assertEqual(popup["22"], "17")                      # "SL BIG" (16) vem antes, como no menu
        self.assertEqual(popup["32"], "0")                       # fora da lista: intocado e contado
        self.assertEqual(popup["42"], "0")                       # sem Look: intocado
        self.assertEqual(cont, {"look no popup da Lumetri": 2, "look fora da lista: MEU LOOK.cube": 1})
        self.assertEqual(len(prproj_downgrade.LOOKS_CRIATIVOS), 65)


    def test_crop_do_motion_vira_efeito_crop(self):
        """O crop do Motion (25) vira o efeito Crop no 23.2, o PRIMEIRO da pilha (prova por pixel no 23.2, 2026-10-07:
        com Transform e com blur na pilha, só antes deles deu 0%). Crop zerado só sai."""
        import xml.etree.ElementTree as ET

        def motion(oid, valores):
            ps = "".join(f'<Param Index="{i}" ObjectRef="{oid}{i}"/>' for i in range(4))
            objs = "".join(f'<VideoComponentParam ObjectID="{oid}{i}" ClassID="x" Version="9"><ParameterID>{8 + i}</ParameterID>'
                           f'<Name>Crop {n}</Name><StartKeyframe>-91445760000000000,{v}.,0,0,0,0,0,0</StartKeyframe></VideoComponentParam>'
                           for i, (n, v) in enumerate(zip(("Left", "Top", "Right", "Bottom"), valores)))
            return (f'<VideoFilterComponent ObjectID="{oid}" ClassID="c" Version="9"><Component Version="6"><Params Version="1">{ps}'
                    f'</Params><ID>1</ID><Intrinsic>true</Intrinsic></Component><MatchName>AE.ADBE Motion</MatchName></VideoFilterComponent>' + objs)

        def filtro(oid, match, cid):
            return (f'<VideoFilterComponent ObjectID="{oid}" ClassID="c" Version="9"><Component Version="6"><ID>{cid}</ID>'
                    f'<Intrinsic>false</Intrinsic></Component><MatchName>{match}</MatchName></VideoFilterComponent>')

        def cadeia(oid, refs):
            return (f'<VideoComponentChain ObjectID="{oid}" ClassID="k" Version="3"><ComponentChain Version="3"><Components Version="1">'
                    + "".join(f'<Component Index="{i}" ObjectRef="{r}"/>' for i, r in enumerate(refs)) + '</Components></ComponentChain></VideoComponentChain>')

        xml = ("<PremiereData>" + cadeia(1, [10, 20, 30]) + motion(10, (50, 0, 0, 0)) + filtro(20, "AE.ADBE Gaussian Blur 2", 3)
               + filtro(30, "AE.ADBE Geometry", 4)
               + cadeia(2, [40, 50]) + motion(40, (0, 10, 0, 20)) + filtro(50, "AE.ADBE Gaussian Blur 2", 3)
               + cadeia(3, [60]) + motion(60, (0, 0, 0, 0)) + "</PremiereData>")
        raiz = ET.fromstring(xml)
        cont = prproj_downgrade.crop_do_motion(raiz)
        objs = {e.get("ObjectID"): e for e in raiz if e.get("ObjectID")}

        def pilha(oid):
            return [objs[c.get("ObjectRef")].findtext("MatchName") for c in objs[oid].find("ComponentChain/Components")]

        self.assertEqual(pilha("1"), ["AE.ADBE Motion", "AE.ADBE AECrop", "AE.ADBE Gaussian Blur 2", "AE.ADBE Geometry"])
        self.assertEqual(pilha("2"), ["AE.ADBE Motion", "AE.ADBE AECrop", "AE.ADBE Gaussian Blur 2"])
        self.assertEqual(pilha("3"), ["AE.ADBE Motion"])
        self.assertEqual(cont, {"crop do Motion tirado": 3, "crop do Motion → efeito Crop": 2})
        crop = [e for e in raiz if e.findtext("MatchName") == "AE.ADBE AECrop"][1]
        vals = [objs[r.get("ObjectRef")].findtext("StartKeyframe").split(",")[1] for r in crop.find("Component/Params")]
        self.assertEqual(vals, ["0.", "10.", "0.", "20.", "false", "0"])
        self.assertEqual(crop.findtext("Component/ID"), "4")       # um ID novo na cadeia
        for m in ("10", "40", "60"):                                 # o Motion fica sem os 4 parâmetros de corte
            self.assertEqual(len(objs[m].find("Component/Params")), 0)


    def test_lut_do_clipe_vira_lumetri(self):
        """A LUT de entrada do clipe (LUTAsset do 26) vira uma Lumetri do 23 com a MESMA LUT embutida, primeiro na pilha,
        e o .cube reconstruído bate com o original (B09; prova por pixel no 23.2 em 2026-10-07: 50,3 dB)."""
        import base64
        import xml.etree.ElementTree as ET
        origem = os.path.join(RAIZ, "resultados", "B09_COR", "prproj", "premiere-26.0.2-darwin.prproj")
        with tempfile.TemporaryDirectory() as tmp:
            saida = os.path.join(tmp, "b09.prproj")
            r = prproj_downgrade.rebaixar(origem, saida, "23.2", caminho_luts_no_destino="X:\\LUTS")
            self.assertEqual(r["campos_devolvidos"].get("LUT do clipe → Lumetri Input LUT"), 1)
            cubo = os.path.join(tmp, "LAB B09 QUENTE.cube")
            self.assertTrue(os.path.isfile(cubo))
            with open(cubo) as fh:
                linhas = [l for l in fh if l[:1].isdigit()]
            self.assertEqual(len(linhas), 17 ** 3)
            xml = prproj_estrutura.ler_xml(saida)
        raiz = ET.fromstring(xml.encode())
        objs = {e.get("ObjectID"): e for e in raiz if e.get("ObjectID")}
        lut26 = base64.b64decode(re.search(r"<LUTAsset .*?<Blob[^>]*>([^<]+)</Blob>", prproj_estrutura.ler_xml(origem), re.S).group(1).strip())
        def params(c):
            return {objs[p.get("ObjectRef")].findtext("ParameterID"): objs[p.get("ObjectRef")] for p in c.find("Component/Params")}
        lum = [e for e in raiz if e.tag == "VideoFilterComponent" and e.findtext("MatchName") == "AE.ADBE Lumetri"
               and params(e).get("98") is not None and (params(e)["98"].findtext("StartKeyframeValue") or "").strip()
               and base64.b64decode(params(e)["98"].findtext("StartKeyframeValue"))[20:] == lut26]
        self.assertEqual(len(lum), 1)                    # a da LUT do clipe (o B09 também ganha as do S-Log3)
        ps = params(lum[0])
        emb = base64.b64decode(ps["98"].findtext("StartKeyframeValue"))
        self.assertEqual(emb[20:], lut26)                                                            # a MESMA LUT
        self.assertEqual(int.from_bytes(emb[16:20], "little"), len(lut26))                           # e o tamanho dela
        blob = base64.b64decode(ps["1"].findtext("StartKeyframeValue"))
        self.assertIn(b"<hash>" + emb[:16].hex().upper().encode() + b"</hash>", blob)                # a chave nos 2 lugares
        self.assertEqual(ps["5"].findtext("StartKeyframe").split(",")[1], "1")                      # [Custom]
        self.assertIn("X:\\LUTS\\LAB B09 QUENTE.cube", base64.b64decode(ps["4"].findtext("StartKeyframeValue")).decode("utf-16-le"))
        guids = set()                                   # cada Lumetri nova com o seu <guid> (o 23.2 confunde as iguais)
        for e in raiz:
            if e.tag == "VideoFilterComponent" and e.findtext("MatchName") == "AE.ADBE Lumetri" and params(e).get("98") is not None \
                    and (params(e)["98"].findtext("StartKeyframeValue") or "").strip():
                guids.add(re.search(rb'<guid>"([^"]+)"', base64.b64decode(params(e)["1"].findtext("StartKeyframeValue"))).group(1))
        self.assertEqual(len(guids), 3)                 # LUT do clipe + S-Log3 em 709 + S-Log3 em ACEScct
        cadeia = [c for c in raiz.iter("VideoComponentChain") if c.find("ComponentChain/Components") is not None
                  and any(x.get("ObjectRef") == lum[0].get("ObjectID") for x in c.find("ComponentChain/Components"))]
        self.assertEqual(len(cadeia), 1)


    def test_marcador_do_que_nao_existe(self):
        """ARRIRAW HDE e sequência em ACEScct ganham marcador no 23.2 (lidos pela API do 23.2 em 2026-10-07), ligado na
        sequência e nos clipes dela."""
        import json
        import xml.etree.ElementTree as ET
        origem = os.path.join(RAIZ, "resultados", "B09_COR", "prproj", "premiere-26.0.2-darwin.prproj")
        with tempfile.TemporaryDirectory() as tmp:
            saida = os.path.join(tmp, "b09.prproj")
            r = prproj_downgrade.rebaixar(origem, saida, "23.2")
            raiz = ET.fromstring(prproj_estrutura.ler_xml(saida).encode())
        self.assertEqual(r["campos_devolvidos"].get("marcador: RETIRADO"), 1)
        self.assertEqual(r["campos_devolvidos"].get("marcador: COR APROXIMADA"), 1)
        objs = {(e.get("ObjectID") or e.get("ObjectUID")): e for e in raiz}
        nomes = {}
        for s in [e for e in raiz if e.tag == "Sequence"]:
            mo = s.find("MarkerOwner")
            if mo is None:
                continue
            lista = objs[mo.find("Markers").get("ObjectRef")]
            nomes[s.findtext("Name")] = [json.loads(objs[m.find("Second").get("ObjectRef")].findtext("DVAMarker"))["DVAMarker"]["mName"]
                                         for m in lista.find("Markers")]
            donos = sum(1 for e in raiz for d in e.iter("Markers") if d.get("ObjectRef") == lista.get("ObjectID"))
            self.assertEqual(donos, 3, s.findtext("Name"))            # a sequência + o clipe de vídeo e o de áudio dela
        self.assertEqual(nomes, {"SEQ ARRI": ["RETIRADO: ARRIRAW HDE não abre no 2023"],
                                 "SEQ SONY ACES": ["COR APROXIMADA: sequência em ACEScct"]})


    def test_fade_novo_vira_constant_power(self):
        """O "Custom Fade" (fade curvo das alças, 25+) vira o "Constant Power" do 23.2, sem os campos de curva
        (COPA salva pelo 23.2 em 2026-10-07: 91 Constant Power, 0 Custom Fade)."""
        import xml.etree.ElementTree as ET
        def tr(oid, nome, extra=""):
            return (f'<AudioTransitionTrackItem ObjectID="{oid}" ClassID="a" Version="3"><TransitionTrackItem Version="3">'
                    f'<DisplayName>{nome}</DisplayName><MatchName>{nome}</MatchName></TransitionTrackItem>'
                    f'<FrameRate>5292000</FrameRate>{extra}</AudioTransitionTrackItem>')
        raiz = ET.fromstring("<PremiereData>" + tr(1, "Custom Fade", "<FadeShapeType>1</FadeShapeType><FadeShapeValue>13</FadeShapeValue>"
                             "<CrossfadeSymmetry>0</CrossfadeSymmetry>") + tr(2, "Constant Power", "<FadeShapeValue>19</FadeShapeValue>")
                             + "</PremiereData>")
        cont = prproj_downgrade.fade_novo(raiz)
        self.assertEqual(cont, {"fade novo (Custom Fade) → Constant Power": 1})
        for el in raiz:
            self.assertEqual(el.findtext("TransitionTrackItem/MatchName"), "Constant Power")
            self.assertEqual(el.findtext("TransitionTrackItem/DisplayName"), "Constant Power")
            self.assertIsNone(el.find("FadeShapeValue")); self.assertIsNone(el.find("FadeShapeType"))
            self.assertEqual(el.findtext("FrameRate"), "5292000")


if __name__ == "__main__":
    unittest.main()
