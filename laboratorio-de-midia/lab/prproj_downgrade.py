"""DOWNGRADE de um .prproj: salvo por um Premiere mais novo → aberto por um mais velho.

O Premiere recusa um projeto de formato mais novo que o dele (banco, prproj/escrita.md §11b). O laboratório salva os
MESMOS casos em cada versão e mede a `Version` de cada elemento (resultados/ESTRUTURA_PRPROJ.md); a tabela `VERSOES`
abaixo é essa medição. Rebaixar = trocar a versão de cada elemento pela da versão-alvo, e mais nada: medido em
2026-10-07, o 25.6.5 abre um 26.0.2 assim com tudo idêntico (os campos que o 26 omite o 25 preenche sozinho).

    python3 -m lab.prproj_downgrade origem.prproj destino.prproj [versão-alvo, padrão 25.6.5]

⚠️ A tabela só conhece os elementos que os casos do laboratório produzem. Recurso novo (bin, merged, multicam, efeito,
título, cor) = caso novo no laboratório, salvo por cada versão, e a tabela estendida — antes de confiar.
"""
from __future__ import annotations

import gzip
import os
import re
import sys

from .prproj_estrutura import ler_xml

#: versão do Premiere → {elemento: Version que ela grava}. Só os elementos que mudam entre as versões medidas
#: (macOS, casos B01–B07): 25.6.5 e 26.0.2 em 2026-10-06/07, o Beta 27.1.0 em 2026-10-07.
VERSOES = {
    "25.6.5": {"Project": "43", "AudioClipTrack": "6", "AudioComponentChain": "3", "AudioComponentParam": "9",
               "AudioSettings": "7", "AudioStream": "7", "AudioTrack": "11", "AudioTrackInlet": "3",
               "ClipLoggingInfo": "9", "Component": "6", "Sequence": "11", "Track": "3", "TrackItem": "3",
               "VideoSettings": "9", "VideoStream": "21", "Clip": "18", "Media": "30",
               # B07 (efeitos, transição, título, bin inteligente)
               "VideoTransitionTrackItem": "5", "VideoComponentParam": "9", "PointComponentParam": "3",
               "ArbVideoComponentParam": "2", "QueryDefinition": "2",
               # projetos reais (2026-10-07): o CANAL-K COPA, salvo pelo 25.6.5, é a referência do 25
               "AudioTransitionTrackItem": "3", "TimeComponentParam": "8"},
    "26.0.2": {"Project": "45", "AudioClipTrack": "7", "AudioComponentChain": "4", "AudioComponentParam": "10",
               "AudioSettings": "8", "AudioStream": "8", "AudioTrack": "12", "AudioTrackInlet": "4",
               "ClipLoggingInfo": "10", "Component": "7", "Sequence": "12", "Track": "4", "TrackItem": "4",
               "VideoSettings": "10", "VideoStream": "22", "Clip": "18", "Media": "30",
               "VideoTransitionTrackItem": "6", "VideoComponentParam": "10", "PointComponentParam": "4",
               "ArbVideoComponentParam": "3", "QueryDefinition": "3",
               "AudioTransitionTrackItem": "4", "TimeComponentParam": "9"},       # do PRODUCAO-I, salvo pelo 26.3
    "27.1.0": {"Project": "46", "AudioClipTrack": "7", "AudioComponentChain": "4", "AudioComponentParam": "10",
               "AudioSettings": "8", "AudioStream": "8", "AudioTrack": "12", "AudioTrackInlet": "4",
               "ClipLoggingInfo": "10", "Component": "7", "Sequence": "12", "Track": "4", "TrackItem": "4",
               "VideoSettings": "10", "VideoStream": "24", "Clip": "19", "Media": "31",
               "VideoTransitionTrackItem": "6", "VideoComponentParam": "10", "PointComponentParam": "4",
               "ArbVideoComponentParam": "3", "QueryDefinition": "3",
               "AudioTransitionTrackItem": "4", "TimeComponentParam": "9"},       # ⚠️ inferido = 26 (não medido no 27)
}
# ── 2023 (23.2, Project 41) ─────────────────────────────────────────────────────────────────────────────────────
# Medido nos 6 projetos salvos pelo 23.2 que moram no SSD (MIDIAS DE TESTES, os testes de merged do Órbita/PRODE — no
# Windows) contra o CANAL-K COPA (25.6.5): dos 104 elementos em comum, só estes 11 mudam. ⚠️ Os elementos de EFEITO,
# velocidade, LUT e legenda nunca apareceram num projeto do 23 do SSD: ficam com a versão do 25 (o projeto do 24 tem as
# MESMAS versões de efeito do 25 — `inferido` que o 23 também), até um teste no 2023 do Windows.
_MUDA_25_PARA_23 = {"Project": ("43", "41"), "ProjectSettings": ("21", "18"), "Media": ("30", "27"),
                    "VideoStream": ("21", "19"), "MasterClip": ("12", "11"), "SubClip": ("6", "5"),
                    "ClipLoggingInfo": ("9", "8"), "IngestSettings": ("2", "1"), "VideoClipTrackItem": ("8", "6"),
                    "AudioClipTrackItem": ("11", "6"), "AudioFilterComponent": ("4", "3")}
# ⛔ NÃO descer o `VideoFilterComponent` 9 → 8 (o 22.4 grava 8): os campos são os mesmos, mas a CONVERSÃO 8 → 9 muda o
# texto dos parâmetros — com 8, o 25 abriu o CANAL-K COPA com o Look criativo de 14 Lumetri estragado ("Fuji ETERNA 250D
# Fuji 3510 (by Adobe)" → "\ufefe"). Com 9 a sanidade passou sem diferença (2026-10-07).
for _v in ("25.6.5", "26.0.2", "27.1.0"):          # estes não mudam do 25 para o 26/27 (medido nos casos e nos reais)
    for _k, (_v25, _) in _MUDA_25_PARA_23.items():
        VERSOES[_v].setdefault(_k, _v25)
VERSOES["23.2"] = {k: v for k, v in VERSOES["25.6.5"].items()}
VERSOES["23.2"].update({k: v23 for k, (_, v23) in _MUDA_25_PARA_23.items()})

#: campos que o 23.2 nunca escreve — confirmado pelo Órbita (`DRAMASYNC/src-python/prproj/alvo.py`, um projeto com
#: eles removidos abriu no 23.2 em 2026-09-17)
CAMPOS_NOVOS_DEPOIS_DO_23 = {
    "ProjectSettings": ("ColorAwareEffectsEnabled",),
    "VideoStream": ("OriginalColorSpace",),
    "VideoClipTrackItem": ("ToneMapSettings",),
    "AudioClipTrackItem": ("PreRenderComponentChainHashVersion",),
    "VideoTrackGroup": ("AutoInputGamutCompressionEnabled", "IsColorAwareEffectsEnabledSameAsProject",
                        "IsGraphicsWhiteSameAsProject", "OutputColorSpace", "ToneMappingDesaturation"),
}
#: o `CaptureSettings` v10 que o 23.2 grava (o `DummyCaptureSettings` v1 do 25 é o nome novo dele — mesma ClassID)
CAPTURA_2023 = (("RecordModuleDisplayName", "DV"), ("SupportedFileExtension", "avi"),
                ("RecorderID", "0ae2b9b7-6efc-424f-aadf-1a2dedd5e8ff"), ("VideoFrameRate", "8475667200"),
                ("VideoFrameSize", "0,0,720,480"), ("VideoCompressorFourCC", "0"), ("AudioCompressorFourCC", "1380013856"),
                ("AudioCompressorDisplayName", "Uncompressed"), ("AudioFrameRate", "7938000"), ("AudioSampleType", "3"),
                ("AudioChannelType", "1"), ("AbortCaptureOnDroppedFrames", "false"))


#: Os Looks criativos da Lumetri que o Premiere instala (`Lumetri/LUTs/Creative`): a MESMA lista de 65 no 23.2, no 24.6 e
#: no 25.2 (Windows, 2026-10-07), na ordem do menu = nome sem extensão em ordem alfabética sem caixa (o print do menu
#: aberto no 23.2 mostra "SL BIG" antes de "SL BIG HDR"; a ordem dos ARQUIVOS é outra).
LOOKS_CRIATIVOS = (
    'CineSpace2383sRGB6bit', 'Fuji ETERNA 250D Fuji 3510 (by Adobe)', 'Fuji ETERNA 250D Kodak 2395 (by Adobe)',
    'Fuji F125 Kodak 2393 (by Adobe)', 'Fuji F125 Kodak 2395 (by Adobe)', 'Fuji REALA 500D Kodak 2393 (by Adobe)',
    'Kodak 5205 Fuji 3510 (by Adobe)', 'Kodak 5218 Kodak 2383 (by Adobe)', 'Kodak 5218 Kodak 2395 (by Adobe)',
    'Monochrome Fuji ETERNA 250D Kodak 2395 (by Adobe)', 'Monochrome Kodak 5205 Fuji 3510 (by Adobe)',
    'Monochrome Kodak 5218 Kodak 2395 (by Adobe)', 'SL BIG', 'SL BIG HDR', 'SL BIG LDR', 'SL BIG MINUS BLUE',
    'SL BLEACH HDR', 'SL BLEACH LDR', 'SL BLEACH NDR', 'SL BLUE COLD', 'SL BLUE DAY4NITE', 'SL BLUE ICE',
    'SL BLUE INTENSE', 'SL BLUE MOON', 'SL BLUE STEEL', 'SL CLEAN FUJI A HDR', 'SL CLEAN FUJI A LDR',
    'SL CLEAN FUJI A NDR', 'SL CLEAN FUJI B', 'SL CLEAN FUJI B SOFT', 'SL CLEAN FUJI C', 'SL CLEAN KODAK A HDR',
    'SL CLEAN KODAK A LDR', 'SL CLEAN KODAK A NDR', 'SL CLEAN KODAK B', 'SL CLEAN KODAK B SOFT',
    'SL CLEAN KODAK B ULTRASOFT', 'SL CLEAN KODAK C', 'SL CLEAN KODAK C HDR', 'SL CLEAN STRAIGHT HDR',
    'SL CLEAN STRAIGHT LDR', 'SL CLEAN STRAIGHT NDR', 'SL CROSS HDR', 'SL CROSS LDR', 'SL CROSS NDR', 'SL GOLD HEAT',
    'SL GOLD ORANGE', 'SL GOLD RUSH HDR', 'SL GOLD RUSH LDR', 'SL GOLD TOBACCO', 'SL GOLD WESTERN', 'SL IRON HDR',
    'SL IRON LDR', 'SL IRON NDR', 'SL MATRIX BLUE', 'SL MATRIX GREEN', 'SL MATRIX MARS', 'SL NEUTRAL START',
    'SL NOIR 1965', 'SL NOIR HDR', 'SL NOIR LDR', 'SL NOIR NOUVELLE', 'SL NOIR NOUVELLE RED', 'SL NOIR RED WAVE',
    'SL NOIR TRI-X',
)
#: as 4 primeiras posições do menu Look: None, [Custom], Browse… e o separador
LOOK_PRIMEIRA_POSICAO = 4


def _texto_b64_utf16(el) -> str:
    import base64
    v = el.find("StartKeyframeValue")
    if v is None or not (v.text or "").strip():
        return ""
    try:
        return base64.b64decode(v.text.strip()).decode("utf-16-le").rstrip("\x00")
    except (ValueError, UnicodeDecodeError):
        return ""


def look_da_lumetri(raiz) -> dict:
    """O 23.2 mostra o Look pelo POPUP (ParameterID 25 = posição no menu), não pelo nome (ParameterID 96) nem pela LUT
    do Blob (ID 1): projeto do 25 com o 25 em 0 abre no 23 com "None", mesmo com nome e LUT no arquivo (COPA,
    2026-10-07). Preenche o 25 pela posição do nome na lista do menu. Look fora da lista (um .cube do editor) fica como
    está e é contado — o 23 deve precisar do [Custom] + caminho, ainda não medido.
    Provado no 23.2: com 25 = 5 o menu mostra "Fuji ETERNA 250D Fuji 3510 (by Adobe)" e o frame muda (99–100% dos pixels)."""
    objs = {el.get("ObjectID"): el for el in raiz if el.get("ObjectID")}
    posicao = {n.lower(): LOOK_PRIMEIRA_POSICAO + i for i, n in enumerate(LOOKS_CRIATIVOS)}
    cont: dict[str, int] = {}
    for comp in raiz.iter("VideoFilterComponent"):
        if comp.findtext("MatchName") != "AE.ADBE Lumetri" or comp.find("Component/Params") is None:
            continue
        params = {}
        for ref in comp.find("Component/Params"):
            p = objs.get(ref.get("ObjectRef"))
            if p is not None:
                params[p.findtext("ParameterID")] = p
        nome = _texto_b64_utf16(params["96"]) if "96" in params else ""
        popup = params.get("25")
        if not nome or popup is None or popup.find("StartKeyframe") is None:
            continue
        if nome.lower() not in posicao:
            cont[f"look fora da lista: {nome}"] = cont.get(f"look fora da lista: {nome}", 0) + 1
            continue
        partes = (popup.findtext("StartKeyframe") or "").split(",")
        alvo = str(posicao[nome.lower()])
        if len(partes) > 1 and partes[1] != alvo:
            partes[1] = alvo
            popup.find("StartKeyframe").text = ",".join(partes)
            cont["look no popup da Lumetri"] = cont.get("look no popup da Lumetri", 0) + 1
    return cont


#: o efeito Crop (`AE.ADBE AECrop`) como o 23.2 grava (B07 salvo pelo 23.2.0, 2026-10-07): ClassID de cada parâmetro
_CROP_23 = (("Left", "fe47129e-6c94-4fc0-95d5-c056a517aaf3", 2, "0", "100"),
            ("Top", "fe47129e-6c94-4fc0-95d5-c056a517aaf3", 2, "0", "100"),
            ("Right", "fe47129e-6c94-4fc0-95d5-c056a517aaf3", 2, "0", "100"),
            ("Bottom", "fe47129e-6c94-4fc0-95d5-c056a517aaf3", 2, "0", "100"),
            (" ", "cc12343e-f113-4d3b-ae05-b287db77d461", 4, "false", "true"),          # Zoom
            ("Edge Feather", "6e02e8bb-2569-46b2-8ab1-4ab11c43e9c8", 1, "-30000", "30000"))
_FILTRO_CLASSID = "d10da199-beea-4dd1-b941-ed3a78766d50"


def crop_do_motion(raiz) -> dict:
    """O CORTE DENTRO DO MOTION (params 8–11 "Crop Left/Top/Right/Bottom", novo do 25) não existe no 23.2: ele descarta
    e o clipe abre sem o corte (PRODUCAO-I: 3 clipes com 14%). Vira o efeito Crop (`AE.ADBE AECrop`), que o Premiere aplica
    antes do Motion: o corte fica preso à imagem e anda com a posição/escala do Motion, como o crop do Motion (autor,
    2026-10-07: "a imagem é deslocada junto ao crop").
    Posição na pilha: o PRIMEIRO efeito (antes de qualquer outro da pilha) — o corte do Motion age como um corte na
    FONTE. Medido no 23.2 contra o 25.6.5, por pixel (caso CROP, 2026-10-07, 0% = igual): crop 50% + posição, crop misto
    + escala 80% (sem pilha) 0%; com TRANSFORM na pilha, Crop depois dele 10,9% e antes 0% (Crop seguido de Transform
    deixa o corte fixo no quadro — o uso do autor para dividir a tela em 50%); com GAUSSIAN BLUR, Crop depois dele 1,4%
    (o blur aumenta a área do clipe e o Crop mede a % sobre ela: borda 24 px fora) e antes 0%; com Lumetri, 0%.
    Keyframes copiados (não medidos por pixel); crop todo em zero só sai."""
    import xml.etree.ElementTree as ET
    objs = {el.get("ObjectID"): el for el in raiz if el.get("ObjectID")}
    proximo = max((int(k) for k in objs if k.isdigit()), default=0) + 1
    cadeias = {}
    for ch in raiz.iter("VideoComponentChain"):
        comps = ch.find("ComponentChain/Components")
        if comps is not None:
            for c in comps:
                cadeias.setdefault(c.get("ObjectRef"), []).append(comps)
    cont: dict[str, int] = {}
    for motion in [el for el in raiz if el.tag == "VideoFilterComponent" and el.findtext("MatchName") == "AE.ADBE Motion"]:
        params = motion.find("Component/Params")
        if params is None:
            continue
        crop = {}
        for ref in list(params):
            p = objs.get(ref.get("ObjectRef"))
            if p is not None and p.findtext("ParameterID") in ("8", "9", "10", "11") and (p.findtext("Name") or "").startswith("Crop"):
                crop[p.findtext("ParameterID")] = p
                params.remove(ref)
                raiz.remove(p)
        if not crop:
            continue
        for n, ref in enumerate(params):
            ref.set("Index", str(n))
        def valor(p):
            partes = (p.findtext("StartKeyframe") or "").split(",")
            return partes[1] if len(partes) > 1 else "0."
        usado = any(valor(p) not in ("0.", "0", "") or (p.findtext("Keyframes") or "").strip() for p in crop.values())
        cont["crop do Motion tirado"] = cont.get("crop do Motion tirado", 0) + 1
        if not usado:
            continue
        filtro_id, proximo = str(proximo), proximo + 1
        novo = ET.Element("VideoFilterComponent", {"ObjectID": filtro_id, "ClassID": _FILTRO_CLASSID, "Version": "9"})
        comp = ET.SubElement(novo, "Component", {"Version": "6"})
        lista = ET.SubElement(comp, "Params", {"Version": "1"})
        ids_na_cadeia = []
        for comps in cadeias.get(motion.get("ObjectID"), []):
            ids_na_cadeia += [objs[c.get("ObjectRef")].findtext("Component/ID") for c in comps if c.get("ObjectRef") in objs]
        meu_id = max([int(i) for i in ids_na_cadeia if i and i.isdigit()] + [2]) + 1
        ET.SubElement(comp, "ID").text = str(meu_id)
        ET.SubElement(comp, "DisplayName").text = "Crop"
        ET.SubElement(comp, "Bypass").text = "false"
        ET.SubElement(comp, "Intrinsic").text = "false"
        ET.SubElement(comp, "ArchivedType").text = "0"
        ET.SubElement(novo, "MatchName").text = "AE.ADBE AECrop"
        ET.SubElement(novo, "VideoFilterType").text = "2"
        param_objs = []
        for i, (nome, classe, controle, baixo, alto) in enumerate(_CROP_23):
            pid, proximo = str(proximo), proximo + 1
            ET.SubElement(lista, "Param", {"Index": str(i), "ObjectRef": pid})
            p = ET.Element("VideoComponentParam", {"ObjectID": pid, "ClassID": classe, "Version": "9"})
            ET.SubElement(p, "Name").text = nome
            origem = crop.get(str(8 + i)) if i < 4 else None
            ET.SubElement(p, "IsTimeVarying").text = (origem.findtext("IsTimeVarying") if origem is not None
                                                      and origem.find("IsTimeVarying") is not None else "false")
            ET.SubElement(p, "ParameterControlType").text = str(controle)
            if origem is not None:
                ET.SubElement(p, "StartKeyframe").text = origem.findtext("StartKeyframe")
                if origem.find("Keyframes") is not None:
                    ET.SubElement(p, "Keyframes").text = origem.findtext("Keyframes")
                    cont["crop animado"] = cont.get("crop animado", 0) + 1
            else:
                ET.SubElement(p, "StartKeyframe").text = "-91445760000000000,%s,0,0,0,0,0,0" % ("false" if i == 4 else "0")
            ET.SubElement(p, "LowerBound").text = baixo
            ET.SubElement(p, "UpperBound").text = alto
            ET.SubElement(p, "ParameterID").text = str(i + 1)
            if i == 5:
                ET.SubElement(p, "LowerUIBound").text = "-100"
                ET.SubElement(p, "UpperUIBound").text = "100"
            param_objs.append(p)
        pos = list(raiz).index(motion) + 1
        for el in [novo] + param_objs:
            raiz.insert(pos, el)
            pos += 1
        for comps in cadeias.get(motion.get("ObjectID"), []):
            # PRIMEIRO da pilha: logo depois dos intrínsecos (Opacidade, Movimento, Remapeamento) — ver a docstring
            pos_c = sum(1 for c in comps if c.get("ObjectRef") in objs
                        and objs[c.get("ObjectRef")].findtext("Component/Intrinsic") == "true")
            comps.insert(pos_c, ET.Element("Component", {"Index": "0", "ObjectRef": filtro_id}))
            for n, c in enumerate(comps):
                c.set("Index", str(n))
        cont["crop do Motion → efeito Crop"] = cont.get("crop do Motion → efeito Crop", 0) + 1
    return cont


#: a Lumetri com Input LUT [Custom] como o 23.2 grava (molde tirado de um projeto nativo do 23.2.0, 2026-10-07)
MOLDE_LUMETRI_LUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moldes", "lumetri-input-lut-23.2.xml")
#: o parâmetro 98 "Embedded LUTs" = 16 bytes de CHAVE + o tamanho da LUT (uint32) + a LUT ITX3; a mesma chave vai no Blob
#: da Lumetri (`<embeddedlut><hash>…</hash><filename>caminho</filename>`). Medido no 23.2.0 (2026-10-07).


def itx3_para_cube(dados: bytes, titulo: str) -> str:
    """A LUT binária (ITX3) que o Premiere embute → .cube de texto. Cabeçalho de 40 bytes: 'ITX3', tamanho, canais, 0,
    domínio mínimo (3 float) e máximo (3 float); depois tamanho³ × 3 float32. Conferido contra o .cube original do B09
    (diferença máxima 2,6e-8)."""
    import struct
    n, canais, _ = struct.unpack("<III", dados[4:16])
    dmin = struct.unpack("<3f", dados[16:28]); dmax = struct.unpack("<3f", dados[28:40])
    vals = struct.unpack("<%df" % (n ** 3 * 3), dados[40:40 + n ** 3 * 12])
    linhas = [f'TITLE "{titulo}"', f"LUT_3D_SIZE {n}", "DOMAIN_MIN %g %g %g" % dmin, "DOMAIN_MAX %g %g %g" % dmax]
    linhas += ["%.6f %.6f %.6f" % vals[i:i + 3] for i in range(0, len(vals), 3)]
    return "\n".join(linhas) + "\n"


#: COR LOG: o espaço de cor sobrescrito no clipe (Interpret Footage do 25/26) não existe no 23.2 (o override dele fica
#: desabilitado e a lista de LUTs técnicas não tem Sony). A conversão do 26 foi MEDIDA com uma carta 17³ interpretada como
#: o log (`saida/bancadas/slog3`, 26.0.2 Mac, 2026-10-07) e virou uma LUT por espaço de trabalho da sequência.
COR_LOG = {
    # medidos no 26.0.2 Mac com a carta 33³ (`lab/bancadas/carta_log.py`, 2026-10-08; a 17³ errava nos logs íngremes —
    # LogC4/RED 31 dB no 23.2); a chave é o `colorProfileName` que o 26 grava no `OverriddenColorSpace` (= o nome do menu)
    "Apple Log/Rec. 2020": {"": "apple-log-rec-2020-rec709-26.0.2-33.cube", "ACEScct": "apple-log-rec-2020-acescct-26.0.2-33.cube"},
    "ARRI LogC3/Wide Gamut3": {"": "arri-logc3-wide-gamut3-rec709-26.0.2-33.cube", "ACEScct": "arri-logc3-wide-gamut3-acescct-26.0.2-33.cube"},
    "ARRI LogC4/Wide Gamut4": {"": "arri-logc4-wide-gamut4-rec709-26.0.2-33.cube", "ACEScct": "arri-logc4-wide-gamut4-acescct-26.0.2-33.cube"},
    "Canon Log/Cinema Gamut": {"": "canon-log-cinema-gamut-rec709-26.0.2-33.cube", "ACEScct": "canon-log-cinema-gamut-acescct-26.0.2-33.cube"},
    "Canon Log2/Cinema Gamut": {"": "canon-log2-cinema-gamut-rec709-26.0.2-33.cube", "ACEScct": "canon-log2-cinema-gamut-acescct-26.0.2-33.cube"},
    "Canon Log3/Cinema Gamut": {"": "canon-log3-cinema-gamut-rec709-26.0.2-33.cube", "ACEScct": "canon-log3-cinema-gamut-acescct-26.0.2-33.cube"},
    "DJI D-Log/D-Gamut": {"": "dji-d-log-d-gamut-rec709-26.0.2-33.cube", "ACEScct": "dji-d-log-d-gamut-acescct-26.0.2-33.cube"},
    "Fuji F-Log/Rec. 2020": {"": "fuji-f-log-rec-2020-rec709-26.0.2-33.cube", "ACEScct": "fuji-f-log-rec-2020-acescct-26.0.2-33.cube"},
    "Fuji F-Log2/Rec. 2020": {"": "fuji-f-log2-rec-2020-rec709-26.0.2-33.cube", "ACEScct": "fuji-f-log2-rec-2020-acescct-26.0.2-33.cube"},
    "Leica L-Log/Rec. 2020": {"": "leica-l-log-rec-2020-rec709-26.0.2-33.cube", "ACEScct": "leica-l-log-rec-2020-acescct-26.0.2-33.cube"},
    "Nikon N-Log/Rec2020": {"": "nikon-n-log-rec2020-rec709-26.0.2-33.cube", "ACEScct": "nikon-n-log-rec2020-acescct-26.0.2-33.cube"},
    "Panasonic V-Log/V-Gamut": {"": "panasonic-v-log-v-gamut-rec709-26.0.2-33.cube", "ACEScct": "panasonic-v-log-v-gamut-acescct-26.0.2-33.cube"},
    "Red Log3G10/Wide Gamut": {"": "red-log3g10-wide-gamut-rec709-26.0.2-33.cube", "ACEScct": "red-log3g10-wide-gamut-acescct-26.0.2-33.cube"},
    "Sony S-Log/S-Gamut": {"": "sony-s-log-s-gamut-rec709-26.0.2-33.cube", "ACEScct": "sony-s-log-s-gamut-acescct-26.0.2-33.cube"},
    "Sony S-Log2/S-Gamut": {"": "sony-s-log2-s-gamut-rec709-26.0.2-33.cube", "ACEScct": "sony-s-log2-s-gamut-acescct-26.0.2-33.cube"},
    "Sony S-Log3/S-Gamut3": {"": "sony-s-log3-s-gamut3-rec709-26.0.2-33.cube", "ACEScct": "sony-s-log3-s-gamut3-acescct-26.0.2-33.cube"},
    "Sony S-Log3/S-Gamut3.Cine": {"": "sony-s-log3-s-gamut3-cine-rec709-26.0.2-33.cube", "ACEScct": "sony-s-log3-s-gamut3-cine-acescct-26.0.2-33.cube"},
}


def cube_para_itx3(texto: str) -> bytes:
    """.cube de texto → a LUT binária ITX3 que o Premiere embute (o inverso de `itx3_para_cube`)."""
    import struct
    n, vals, dmin, dmax = None, [], (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
    for l in texto.splitlines():
        l = l.strip()
        if l.startswith("LUT_3D_SIZE"):
            n = int(l.split()[1])
        elif l.startswith("DOMAIN_MIN"):
            dmin = tuple(float(v) for v in l.split()[1:4])
        elif l.startswith("DOMAIN_MAX"):
            dmax = tuple(float(v) for v in l.split()[1:4])
        elif l and (l[0].isdigit() or l[0] in "-."):
            vals += [float(v) for v in l.split()[:3]]
    return b"ITX3" + struct.pack("<III", n, 3, 0) + struct.pack("<3f", *dmin) + struct.pack("<3f", *dmax) + struct.pack("<%df" % len(vals), *vals)


def lut_embutida(raiz, caminho_luts: str) -> tuple[dict, dict]:
    """Duas cores do 25/26 que o 23.2 só sabe fazer pela LUMETRI (Basic Correction > Input LUT): o Interpret Footage dele
    tem a LUT e o espaço de cor desabilitados. Cada clipe na timeline ganha uma Lumetri (o molde do 23.2) como PRIMEIRO
    efeito, com a LUT embutida (o 23.2 guarda o ITX3 no parâmetro 98 "Embedded LUTs" e usa a embutida; o caminho do .cube
    também vai, mas pasta inexistente deu o mesmo frame):
    1. a LUT DE ENTRADA DO CLIPE (`VideoStream/InputLUTAsset` → `LUTAsset`, o ITX3 no Blob) — a MESMA LUT. Prova por pixel
       (B09 SEQ LUT, 26.0.2 Mac × 23.2.0 Windows, 2026-10-07): 27,5 → 50,3 dB;
    2. a COR LOG (`OverriddenColorSpace` em `COR_LOG`) — a LUT medida do 26, a da sequência em ACEScct se for o caso.
    Devolve (contagem, {nome do .cube: texto do .cube}) — o .cube é reconstruído da LUT binária, sem precisar do original."""
    import base64
    import copy
    import json as _json
    import hashlib
    import struct
    import uuid
    import xml.etree.ElementTree as ET
    objs = {(el.get("ObjectID") or el.get("ObjectUID")): el for el in raiz if el.get("ObjectID") or el.get("ObjectUID")}

    def ref(el):
        return objs.get(el.get("ObjectRef") or el.get("ObjectURef")) if el is not None else None

    luts = {}          # Media → [(nome, ITX3, id, None)] ; log: (nome por espaço, None, None, {espaço: (nome, ITX3)})
    for med in [el for el in raiz if el.tag == "Media"]:
        chave = med.get("ObjectID") or med.get("ObjectUID")
        vs = ref(med.find("VideoStream"))
        if vs is None:
            continue
        sobre = vs.findtext("OverriddenColorSpace") or ""
        try:
            nome_cs = _json.loads(sobre).get("baseColorProfile", {}).get("colorProfileName", "") if sobre.strip() else ""
        except ValueError:
            nome_cs = ""
        if nome_cs in COR_LOG:
            por_espaco = {}
            for esp, arq in COR_LOG[nome_cs].items():
                with open(os.path.join(os.path.dirname(MOLDE_LUMETRI_LUT), arq), encoding="utf-8") as fh:
                    por_espaco[esp] = (arq, cube_para_itx3(fh.read()))
            luts.setdefault(chave, []).append(("log", nome_cs, por_espaco))
        la = ref(vs.find("InputLUTAsset"))
        if la is not None and la.findtext("Blob"):
            luts.setdefault(chave, []).append(("lut", la.findtext("Filename") or "LUT.cube",
                                               (base64.b64decode(la.findtext("Blob").strip()), la.findtext("Id"))))
    cont: dict[str, int] = {}
    cubos = {}
    if not luts:
        return cont, cubos
    # o espaço de trabalho da sequência de cada clipe (ACEScct no 26: `VideoTrackGroup/WorkingColorSpace`)
    espaco_do_ti = {}
    for g in [el for el in raiz if el.tag == "VideoTrackGroup"]:
        w = g.findtext("WorkingColorSpace") or ""
        esp = "ACEScct" if "ACEScct" in w else ""
        for t in (g.find("TrackGroup/Tracks") or []):
            vt = ref(t)
            for it in ((vt.find("ClipTrack/ClipItems/TrackItems") if vt is not None else None) or []):
                espaco_do_ti[it.get("ObjectRef")] = esp
    molde = ET.parse(MOLDE_LUMETRI_LUT).getroot()
    m_comp, m_params = molde[0], {el.get("ObjectID"): el for el in molde[1:]}
    m_por_id = {el.findtext("ParameterID"): el for el in molde[1:]}
    caminho_molde = base64.b64decode(m_por_id["4"].findtext("StartKeyframeValue").strip()).decode("utf-16-le").rstrip("\x00")
    proximo = max((int(k) for k in objs if k and k.isdigit()), default=0) + 1

    def pôr_lumetri(ti, chain, nome, itx, lid):
        nonlocal proximo
        caminho = caminho_luts.rstrip("/\\") + ("\\" if "\\" in caminho_luts else "/") + nome
        cubos[nome] = itx3_para_cube(itx, os.path.splitext(nome)[0])
        chave_lut = hashlib.md5(itx).digest()          # qualquer 16 bytes servem, desde que iguais no 98 e no Blob
        novos, mapa = [], {}
        for oid in m_params:
            mapa[oid] = str(proximo); proximo += 1
        comp = copy.deepcopy(m_comp); comp.set("ObjectID", str(proximo)); proximo += 1
        for pr in comp.find("Component/Params"):
            pr.set("ObjectRef", mapa[pr.get("ObjectRef")])
        for oid, el in m_params.items():
            el = copy.deepcopy(el); el.set("ObjectID", mapa[oid])
            pid = el.findtext("ParameterID"); v = el.find("StartKeyframeValue")
            if pid == "4":
                v.text = base64.b64encode((caminho + "\x00").encode("utf-16-le")).decode()
            elif pid == "98":
                # 16 bytes de id + o TAMANHO da LUT (uint32): nos nativos do 23.2 os 4 últimos bytes são 74 e6 00 00 =
                # 58996 = o ITX3. Com tamanho 0 o 23.2 aplicou a MESMA LUT em todas as Lumetri do projeto (2026-10-07)
                v.text = base64.b64encode(chave_lut + struct.pack("<I", len(itx)) + itx).decode()
            elif pid == "1":
                b = base64.b64decode(v.text.strip())
                b = b.replace(caminho_molde.encode("latin-1"), caminho.encode("latin-1", "replace"))
                # ⛔ cada Lumetri tem um <guid> próprio no Blob: com o MESMO guid (o do molde) o 23.2 aplicou a LUT de
                # uma cópia na outra (B09: a SEQ SONY saiu com a LUT "QUENTE" da SEQ LUT, 2026-10-07)
                b = re.sub(rb'<guid>"[0-9a-fA-F-]+"</guid>', ('<guid>"%s"</guid>' % uuid.uuid4()).encode(), b, count=1)
                # ⭐ a CHAVE da LUT embutida: `<embeddedlut><hash>` no Blob = os 16 primeiros bytes do parâmetro 98. O 23.2
                # acha a LUT por ela (hash do molde em todas = a mesma LUT em todas; hash diferente do 98 = LUT ignorada)
                b = re.sub(rb"<hash>[0-9A-Fa-f]{32}</hash>", b"<hash>" + chave_lut.hex().upper().encode() + b"</hash>", b)
                v.text = base64.b64encode(b).decode()
            novos.append(el)
        lista = chain.find("ComponentChain/Components")
        if lista is None:                 # o 26 omite a lista quando só há o Motion/Opacidade padrão (DefaultMotion)
            cc = chain.find("ComponentChain")
            if cc is None:
                cc = ET.SubElement(chain, "ComponentChain", {"Version": "3"})
            lista = ET.SubElement(cc, "Components", {"Version": "1"})
        ids = [ref(c).findtext("Component/ID") for c in lista if ref(c) is not None]
        comp.find("Component/ID").text = str(max([int(i) for i in ids if i and i.isdigit()] + [2]) + 1)
        pos = sum(1 for c in lista if ref(c) is not None and ref(c).findtext("Component/Intrinsic") == "true")
        lista.insert(pos, ET.Element("Component", {"Index": "0", "ObjectRef": comp.get("ObjectID")}))
        for n, c in enumerate(lista):
            c.set("Index", str(n))
        at = list(raiz).index(chain) + 1
        for el in [comp] + novos:
            raiz.insert(at, el); at += 1
        objs[comp.get("ObjectID")] = comp

    for ti in [el for el in raiz if el.tag == "VideoClipTrackItem"]:
        sub = ref(ti.find("ClipTrackItem/SubClip")); clip = ref(sub.find("Clip")) if sub is not None else None
        src = ref(clip.find("Clip/Source")) if clip is not None else None
        med = ref(src.find("MediaSource/Media")) if src is not None else None
        chain = ref(ti.find("ClipTrackItem/ComponentOwner/Components"))
        chave = (med.get("ObjectID") or med.get("ObjectUID")) if med is not None else None
        if chave not in luts or chain is None:
            continue
        # a LUT do clipe primeiro e o log depois: cada uma entra na 1ª posição da pilha, então o log fica ANTES
        for tipo, a, b in sorted(luts[chave], key=lambda x: x[0] != "lut"):
            if tipo == "lut":
                itx, lid = b
                pôr_lumetri(ti, chain, a, itx, lid)
                cont["LUT do clipe → Lumetri Input LUT"] = cont.get("LUT do clipe → Lumetri Input LUT", 0) + 1
            else:
                esp = espaco_do_ti.get(ti.get("ObjectID"), "")
                nome, itx = b.get(esp, b[""])
                pôr_lumetri(ti, chain, nome, itx, str(uuid.uuid5(uuid.NAMESPACE_URL, nome)))
                chave_c = f"cor log {a} → Lumetri (LUT medida{', ACEScct' if esp else ''})"
                cont[chave_c] = cont.get(chave_c, 0) + 1
    return cont, cubos

_MARKERS_CLASSID = "bee50706-b524-416c-9f03-b596ce5f6866"
_MARKER_CLASSID = "a45508e0-3ff7-4d04-90a7-2e0dfff4c910"
ASSINATURA_MARCADOR = "Rebaixado para o Premiere 2023 pelo laboratório de mídia (Ciclo Media)."


def marcadores_do_que_nao_existe(raiz, extras: list | None = None) -> dict:
    """Regra do autor (2026-10-07): recurso que não existe na versão de destino → retirar e deixar um MARCADOR explicando.
    Marcador de sequência (o formato que o 23.2 grava, B07: `Markers` 4 com a lista {guid → `Marker` 3} e o JSON
    `DVAMarker`). A lista é a MESMA da sequência e do clipe de vídeo/áudio dela no projeto; o 26 omite a lista quando não há
    marcador — então ela é criada e ligada nos três.
    - ARRIRAW HDE (.arx): o 23.2 não lê ("File format not supported", B09) → marcador no início de cada clipe.
    - Sequência em ACEScct: o 23.2 não tem espaço de trabalho ACES → marcador no início (a cor dos clipes log foi aproximada
      pela LUT medida, ver `lut_embutida`)."""
    import json as _json
    import uuid
    import xml.etree.ElementTree as ET
    objs = {(el.get("ObjectID") or el.get("ObjectUID")): el for el in raiz if el.get("ObjectID") or el.get("ObjectUID")}

    def ref(el):
        return objs.get(el.get("ObjectRef") or el.get("ObjectURef")) if el is not None else None

    proximo = max((int(k) for k in objs if k and k.isdigit()), default=0) + 1
    notas: dict[str, list] = {}                     # UID da sequência → [(ticks, nome, comentário)]
    for uid_extra, ticks, nome, comentario in (extras or []):     # de outras conversões (ex.: `prproj_mascara`)
        notas.setdefault(uid_extra, []).append((ticks, nome, comentario + " " + ASSINATURA_MARCADOR))
    for sq in [el for el in raiz if el.tag == "Sequence"]:
        uid = sq.get("ObjectUID") or sq.get("ObjectID")
        for tg in sq.findall("TrackGroups/TrackGroup"):
            g = ref(tg.find("Second"))
            if g is None:
                continue
            if g.tag == "VideoTrackGroup" and "ACEScct" in (g.findtext("WorkingColorSpace") or ""):
                notas.setdefault(uid, []).append((0, "COR APROXIMADA: sequência em ACEScct",
                    "No original esta sequência trabalhava em ACEScct, que o Premiere 2023 não tem. Ela abre em Rec.709; os "
                    "clipes em log receberam uma Lumetri com a conversão do 2026 medida (diferença pequena). Confira a cor. "
                    + ASSINATURA_MARCADOR))
            if g.tag != "VideoTrackGroup":
                continue
            for t in (g.find("TrackGroup/Tracks") or []):
                vt = ref(t)
                for it in ((vt.find("ClipTrack/ClipItems/TrackItems") if vt is not None else None) or []):
                    ti = ref(it)
                    if ti is None or ti.tag != "VideoClipTrackItem":
                        continue
                    sub = ref(ti.find("ClipTrackItem/SubClip")); clip = ref(sub.find("Clip")) if sub is not None else None
                    src = ref(clip.find("Clip/Source")) if clip is not None else None
                    med = ref(src.find("MediaSource/Media")) if src is not None else None
                    arq = (med.findtext("FilePath") or med.findtext("ActualMediaFilePath") or "") if med is not None else ""
                    if arq.lower().endswith(".arx"):
                        nome = arq.replace("\\", "/").split("/")[-1]
                        notas.setdefault(uid, []).append((int(ti.findtext("ClipTrackItem/TrackItem/Start") or 0),
                            "RETIRADO: ARRIRAW HDE não abre no 2023",
                            f"O clipe {nome} é ARRIRAW HDE (.arx), formato que o Premiere 2023 não lê: ele fica offline. "
                            "Transcodifique (ex.: ProRes 4444 XQ ou ARRIRAW sem HDE) e reconecte. " + ASSINATURA_MARCADOR))
    cont: dict[str, int] = {}
    if not notas:
        return cont
    # os clipes de cada sequência no projeto (Video/AudioClip cujo Source é a SequenceSource dela)
    clipes_da_seq: dict[str, list] = {}
    for el in raiz:
        if el.tag in ("VideoClip", "AudioClip"):
            src = ref(el.find("Clip/Source"))
            if src is not None and src.find("SequenceSource/Sequence") is not None:
                clipes_da_seq.setdefault(src.find("SequenceSource/Sequence").get("ObjectURef"), []).append(el)
    for sq in [el for el in raiz if el.tag == "Sequence"]:
        uid = sq.get("ObjectUID") or sq.get("ObjectID")
        if uid not in notas:
            continue
        mo = sq.find("MarkerOwner")
        lista_obj = ref(mo.find("Markers")) if mo is not None else None
        if lista_obj is None:
            lista_obj = ET.Element("Markers", {"ObjectID": str(proximo), "ClassID": _MARKERS_CLASSID, "Version": "4"}); proximo += 1
            ET.SubElement(lista_obj, "Markers", {"Version": "1"})
            ET.SubElement(lista_obj, "ByGUID").text = "byGUID"
            ET.SubElement(lista_obj, "LastMetadataState").text = "00000000-0000-0000-0000-000000000000"
            ET.SubElement(lista_obj, "LastContentState").text = "00000000-0000-0000-0000-000000000000"
            raiz.insert(list(raiz).index(sq), lista_obj)
            objs[lista_obj.get("ObjectID")] = lista_obj
            for dono, pai in [(sq, sq)] + [(c, c.find("Clip")) for c in clipes_da_seq.get(uid, [])]:
                if pai is None or pai.find("MarkerOwner") is not None:
                    continue
                novo = ET.Element("MarkerOwner", {"Version": "1"})
                ET.SubElement(novo, "Markers", {"ObjectRef": lista_obj.get("ObjectID")})
                pos = 1 if len(pai) and pai[0].tag == "Node" else 0
                pai.insert(pos, novo)
        lista = lista_obj.find("Markers")
        for ticks, nome, comentario in notas[uid]:
            mid = str(uuid.uuid4())
            m = ET.Element("Marker", {"ObjectID": str(proximo), "ClassID": _MARKER_CLASSID, "Version": "3"}); proximo += 1
            ET.SubElement(m, "DVAMarker").text = _json.dumps({"DVAMarker": {"mComment": comentario, "mMarkerID": mid, "mName": nome,
                                                             "mStartTime": {"ticks": ticks}, "mType": "Comment"}}, ensure_ascii=False)
            raiz.insert(list(raiz).index(lista_obj) + 1, m)
            item = ET.SubElement(lista, "Marker", {"Version": "1", "Index": str(len(lista))})
            ET.SubElement(item, "First").text = mid
            ET.SubElement(item, "Second", {"ObjectRef": m.get("ObjectID")})
            chave = "marcador: " + nome.split(":")[0]
            cont[chave] = cont.get(chave, 0) + 1
    return cont


def fade_novo(raiz) -> dict:
    """O FADE NOVO de áudio ("Custom Fade", o fade curvo e ajustável das alças de fade do 25+: `FadeShapeType`/`FadeShapeValue`)
    não existe no 23.2: ele abre com "transition missing: Custom Fade" e guarda um lugar vazio (COPA: 48). Vira o fade padrão
    do 23.2, o "Constant Power", com a mesma duração e alinhamento (decisão do autor, 2026-10-07). O 23.2 não grava os campos
    de curva em transição nenhuma (COPA salva por ele): saem de todas."""
    cont: dict[str, int] = {}
    for el in raiz:
        if el.tag != "AudioTransitionTrackItem":
            continue
        tt = el.find("TransitionTrackItem")
        if tt is not None and tt.findtext("MatchName") == "Custom Fade":
            tt.find("MatchName").text = "Constant Power"
            if tt.find("DisplayName") is not None:
                tt.find("DisplayName").text = "Constant Power"
            cont["fade novo (Custom Fade) → Constant Power"] = cont.get("fade novo (Custom Fade) → Constant Power", 0) + 1
        for campo in ("FadeShapeType", "FadeShapeValue", "CrossfadeSymmetry"):
            for f in el.findall(campo):
                el.remove(f)
    return cont


def para_2023(xml: str, caminho_luts: str | None = None, origem: str | None = None,
              destino: str | None = None) -> tuple[str, dict, dict]:
    """O que além das versões o 23.2 precisa: tirar os campos que ele não conhece, trocar o bloco de captura, pôr o
    Look da Lumetri no popup, converter o crop do Motion no efeito Crop e (com `origem`/`destino`) a máscara de objeto em
    Track Matte (`prproj_mascara`)."""
    import xml.etree.ElementTree as ET
    raiz = ET.fromstring(xml.encode("utf-8"))
    cont: dict[str, int] = {}
    for el in raiz.iter():
        for tag in CAMPOS_NOVOS_DEPOIS_DO_23.get(el.tag, ()):
            for filho in el.findall(tag):
                el.remove(filho)
                cont[f"tirou {el.tag}.{tag}"] = cont.get(f"tirou {el.tag}.{tag}", 0) + 1
    for n, obj in enumerate(list(raiz)):
        if obj.tag == "DummyCaptureSettings":
            novo = ET.Element("CaptureSettings", {"ObjectID": obj.get("ObjectID"), "ClassID": obj.get("ClassID"), "Version": "10"})
            for tag, valor in CAPTURA_2023:
                ET.SubElement(novo, tag).text = valor
            raiz.remove(obj)
            raiz.insert(n, novo)
            cont["DummyCaptureSettings → CaptureSettings 10"] = cont.get("DummyCaptureSettings → CaptureSettings 10", 0) + 1
    cont.update(look_da_lumetri(raiz))
    cont.update(crop_do_motion(raiz))
    cont.update(fade_novo(raiz))
    cubos = {}
    if caminho_luts:
        c_lut, cubos = lut_embutida(raiz, caminho_luts)
        cont.update(c_lut)
    notas = []
    if origem and destino:                          # a máscara de objeto do 2026 → Track Matte (precisa dos .prmf ao lado)
        from . import prproj_mascara
        c_masc, notas = prproj_mascara.converter(raiz, origem, destino)
        cont.update(c_masc)
    from . import prproj_mascara as _pm                 # retângulo / elipse / caneta (com tracking) → a máscara do 23
    c_forma, _ = _pm.formas_para_mascara_antiga(raiz)
    cont.update(c_forma)
    cont.update(marcadores_do_que_nao_existe(raiz, notas))
    return '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(raiz, encoding="unicode"), cont, cubos


#: compatibilidade: o par medido primeiro
VERSOES_26_PARA_25 = {k: (VERSOES["26.0.2"][k], VERSOES["25.6.5"][k])
                      for k in VERSOES["25.6.5"] if VERSOES["26.0.2"][k] != VERSOES["25.6.5"][k]}


#: Os campos que o 26.0.2 deixa de gravar quando valem o PADRÃO dele e que o 25.6.5 precisa (medido 2026-10-07, B07:
#: sem o `FrameRate` da cadeia de áudio o 25 abre o clipe SEM os componentes de Volume — o ajuste de volume se perde).
#: elemento → [(campo, valor padrão, ordem em que o 25 grava os filhos)]. Ausente no arquivo = o padrão do 26.
CAMPOS_PADRAO_25 = {
    # ⚠️ na cadeia de áudio o padrão do 26 é MONO: ele omite o layout E o ChannelType do clipe mono (e grava os dois no
    # estéreo) — tratado à parte em `devolver_campos` (B08: o som direto dentro do merged virava estéreo)
    "AudioComponentChain": ([("FrameRate", "5292000"), ("AutomationMode", "1")],
                            ["DefaultVol", "DefaultVolumeComponentID", "DefaultChannelVolumeComponentID", "ComponentChain",
                             "AudioChannelLayout", "ChannelType", "FrameRate", "AutomationMode"]),
    "AudioTrack": ([("ChannelType", "1"), ("FrameRate", "5292000"), ("AutomationMode", "1"), ("Solo", "0"), ("MutedBySolo", "0")],
                   ["ComponentOwner", "Panner", "ID", "ChannelType", "FrameRate", "AutomationMode", "SubType", "Assign",
                    "NextPannerID", "Solo", "MutedBySolo"]),
    "AudioTrackInlet": ([("ChannelType", "1"), ("FrameRate", "5292000")], ["Sources", "AudioChannelLayout", "ChannelType", "FrameRate"]),
    "AudioClipTrack": ([("RecordChannel", "0")], ["ClipTrack", "AudioTrack", "RecordChannel"]),
    "Track": ([("IsLocked", "false"), ("IsMuted", "false"), ("IsSyncLocked", "true")],
              ["Node", "ID", "IsLocked", "MediaType", "Index", "IsMuted", "IsSyncLocked"]),
    "Component": ([("Bypass", "false"), ("ArchivedType", "0")], ["Node", "Params", "Keyframes", "ID", "DisplayName", "Bypass", "ArchivedType"]),
    "TrackItem": ([("Start", "0")], ["Node", "Start", "End"]),
    "VideoStream": ([("InputLUTSpecified", "false")], []),
    "PointComponentParam": ([("IsTimeVarying", "false")], ["Node", "IsTimeVarying", "ParameterControlType", "ParameterID", "Name"]),
    "ArbVideoComponentParam": ([("IsTimeVarying", "false")], ["Node", "IsTimeVarying", "ParameterControlType", "ParameterID", "Name"]),
    # a VELOCIDADE do clipe (remapeamento de tempo): constantes nos 94 do CANAL-K COPA (25.6.5)
    "TimeComponentParam": ([("IsTimeVarying", "true"), ("IsLocked", "false"), ("DiscontinuousInterpolate", "false"),
                            ("ParameterControlType", "21"), ("RangeLocked", "false")],
                           ["IsTimeVarying", "IsLocked", "DiscontinuousInterpolate", "ParameterControlType", "Name", "LowerBound",
                            "UpperBound", "StartKeyframe", "Keyframes", "CurrentValue", "ParameterID", "RangeLocked"]),
    # a transição de ÁUDIO: o FadeShapeValue do "Constant Power" é sempre 19 (43/43 no CANAL-K COPA); o do "Custom Fade"
    # é escolha do editor (o 26 grava) — tratado em `devolver_campos`
    "AudioTransitionTrackItem": ([("FrameRate", "5292000"), ("FadeShapeType", "1"), ("CrossfadeSymmetry", "0")],
                                 ["TransitionTrackItem", "AudioChannelLayout", "ChannelType", "FrameRate", "FadeShapeType",
                                  "FadeShapeValue", "CrossfadeSymmetry"]),
}


def devolver_campos(xml: str, campos: dict) -> tuple[str, dict]:
    """Põe de volta, em cada elemento da tabela, o campo que falta, no lugar em que a versão-alvo o grava."""
    import xml.etree.ElementTree as ET
    raiz = ET.fromstring(xml.encode("utf-8"))
    cont: dict[str, int] = {}
    for el in raiz.iter():
        # só o elemento de verdade: `<Component Index="0" ObjectRef="221"/>` e afins são REFERÊNCIAS, não se mexe
        if el.tag not in campos or "ObjectRef" in el.attrib or "ObjectURef" in el.attrib or len(el) == 0:
            continue
        faltam, ordem = campos[el.tag]
        if el.tag == "AudioTransitionTrackItem":
            extra = []
            if el.find("ChannelType") is None:
                lay = el.find("AudioChannelLayout")
                n = lay.text.count("channellabel") if lay is not None and lay.text else 2
                extra.append(("ChannelType", {1: "0", 2: "1"}.get(n)))
            if el.find("FadeShapeValue") is None and el.findtext("TransitionTrackItem/MatchName") == "Constant Power":
                extra.append(("FadeShapeValue", "19"))
            faltam = [x for x in extra if x[1] is not None] + list(faltam)
        if el.tag == "AudioComponentChain" and el.find("ChannelType") is None:
            lay = el.find("AudioChannelLayout")
            n = lay.text.count("channellabel") if lay is not None and lay.text else 1
            extra = [("ChannelType", {1: "0", 2: "1"}.get(n))]
            if lay is None:
                extra.insert(0, ("AudioChannelLayout", '[{"channellabel":0}]'))
            faltam = [x for x in extra if x[1] is not None] + list(faltam)
        tem = [ch.tag for ch in el]
        for campo, valor in faltam:
            if campo in tem:
                continue
            novo = ET.Element(campo)
            novo.text = valor
            # depois do último irmão que vem ANTES dele na ordem da versão-alvo (sem ordem conhecida: no fim)
            pos = len(el)
            if campo in ordem:
                antes = set(ordem[:ordem.index(campo)])
                pos = max([n + 1 for n, ch in enumerate(el) if ch.tag in antes], default=0)
            el.insert(pos, novo)
            tem = [ch.tag for ch in el]
            cont[f"{el.tag}.{campo}"] = cont.get(f"{el.tag}.{campo}", 0) + 1
    return '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(raiz, encoding="unicode"), cont


def versao_de(xml: str) -> str:
    """Quem salvou, pela versão do `Project` (a única que muda a cada versão do Premiere)."""
    m = re.search(r'<Project [^>]*ClassID="[^"]+"[^>]*Version="(\d+)"', xml)
    achadas = [v for v, t in VERSOES.items() if m and t["Project"] == m.group(1)]
    if not achadas:
        raise ValueError(f"Project Version {m.group(1) if m else '?'} não está na tabela VERSOES")
    return achadas[0]


def rebaixar_xml(xml: str, para: str = "25.6.5", de: str | None = None) -> tuple[str, dict]:
    """Troca a `Version` de cada elemento que difere entre `de` e `para`. Devolve o XML e as trocas por elemento."""
    de = de or versao_de(xml)
    mapa = {k: (VERSOES[de][k], VERSOES[para][k]) for k in VERSOES[de] if VERSOES[de][k] != VERSOES[para][k]}
    contagem: dict[str, int] = {}
    if not mapa:
        return xml, contagem

    def troca(m: re.Match) -> str:
        nome, meio, versao = m.group(1), m.group(2), m.group(3)
        origem, alvo = mapa[nome]
        if versao != origem:
            return m.group(0)
        contagem[nome] = contagem.get(nome, 0) + 1
        return f'<{nome}{meio} Version="{alvo}"'

    novo = re.sub(r'<(%s)((?: [^>]*?)?) Version="(\d+)"' % "|".join(mapa), troca, xml)
    return novo, contagem


def rebaixar(origem: str, destino: str, para: str = "25.6.5", campos: bool = True,
             caminho_luts_no_destino: str | None = None) -> dict:
    """`caminho_luts_no_destino`: a pasta dos .cube COMO A MÁQUINA QUE VAI ABRIR a vê (o 23 guarda o caminho); os .cube
    são gravados ao lado do `destino`. Padrão: a própria pasta do destino."""
    xml = ler_xml(origem)
    de = versao_de(xml)
    novo, contagem = rebaixar_xml(xml, para, de)
    devolvidos = {}
    if para in ("25.6.5", "23.2") and de not in ("25.6.5", "23.2") and campos:
        novo, devolvidos = devolver_campos(novo, CAMPOS_PADRAO_25)
    cubos = {}
    if para == "23.2":
        novo, d23, cubos = para_2023(novo, caminho_luts_no_destino or os.path.dirname(os.path.abspath(destino)),
                                     origem, destino)
        devolvidos.update(d23)
        for nome, texto in cubos.items():
            with open(os.path.join(os.path.dirname(os.path.abspath(destino)), nome), "w", encoding="utf-8") as fh:
                fh.write(texto)
    sobrou = {n: v for n in VERSOES[de] if VERSOES[de][n] != VERSOES[para][n]
              for v in re.findall(r'<%s(?: [^>]*?)? Version="(%s)"' % (n, VERSOES[de][n]), novo)}
    with open(destino, "wb") as fh:
        fh.write(gzip.compress(novo.encode("utf-8")))
    return {"de": de, "para": para, "trocas": contagem, "campos_devolvidos": devolvidos, "sobrou_versao_de_origem": sobrou}


if __name__ == "__main__":
    print(rebaixar(sys.argv[1], sys.argv[2], *(sys.argv[3:4] or [])))
