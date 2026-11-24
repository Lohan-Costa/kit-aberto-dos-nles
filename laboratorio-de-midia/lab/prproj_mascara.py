"""A MÁSCARA DE OBJETO do Premiere 2026 (`AE.ADBE AEMask2`, Type 4) no rebaixamento para o 2023, que não a tem.

Decisão do autor (2026-10-07): recurso que não existe no destino → converter quando der, senão retirar + MARCADOR.
- Máscara de objeto na OPACIDADE com os `.prmf` achados → o resultado vira um VÍDEO DE MATTE (`lab/prmf.py`, branco = objeto),
  um clipe na PRIMEIRA trilha de vídeo acima que esteja LIVRE no trecho (nada se sobrescreve — camada de ajuste, efeito, título
  ficam onde estão; sem trilha livre, uma trilha NOVA no topo), e o clipe ganha o **Track Matte Key** (Matte = aquela trilha, Composite Using = luma).
  Medido no 23.2 real (Windows, 2026-10-08): o gabarito nativo dá o recorte exato do matte (IoU 1,000) e o Premiere esconde a
  trilha do matte sozinho.
- Sem os `.prmf` (a pasta `<projeto> Masks` não veio), ou a máscara noutro efeito (Lumetri…) → retirada + marcador.

O clipe do matte e o Track Matte Key são CLONADOS do gabarito salvo pelo próprio 23.2 (`lab/moldes/track-matte-23.2.xml`),
com os ids renovados e o arquivo, a duração e os pontos do clipe de origem.
"""
from __future__ import annotations

import base64
import copy
import os
import re
import subprocess
import uuid

MOLDE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moldes", "track-matte-23.2.xml")
TICKS = 254016000000
GUID = rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def _objs(raiz) -> dict:
    return {(el.get("ObjectID") or el.get("ObjectUID")): el for el in raiz if el.get("ObjectID") or el.get("ObjectUID")}


def _ref(objs, el):
    return objs.get(el.get("ObjectRef") or el.get("ObjectURef")) if el is not None else None


def _param(objs, comp, pid: str):
    for p in comp.findall("Component/Params/Param"):
        o = _ref(objs, p)
        if o is not None and o.findtext("ParameterID") == pid:
            return o
    return None


def _tipo_e_ids(objs, mascara) -> tuple[str | None, list[str]]:
    """(Type da máscara — 4 = objeto, ids dos `.prmf` no param 24 "Controlador": ASCII num FlatBuffers em base64)."""
    p22 = _param(objs, mascara, "22")
    sk = (p22.findtext("StartKeyframe") or "") if p22 is not None else ""
    tipo = sk.split(",")[1] if sk.count(",") else None
    p24 = _param(objs, mascara, "24")
    v = re.sub(r"\s", "", (p24.findtext("StartKeyframeValue") or "") if p24 is not None else "")
    ids = []
    if v:
        b = base64.b64decode(v + "=" * (-len(v) % 4))
        ids = [g.decode() for g in re.findall(GUID, b)]
    return tipo, ids


def _midia_do_item(objs, ti):
    sub = _ref(objs, ti.find("ClipTrackItem/SubClip"))
    clip = _ref(objs, sub.find("Clip")) if sub is not None else None
    src = _ref(objs, clip.find("Clip/Source")) if clip is not None else None
    med = _ref(objs, src.find("MediaSource/Media")) if src is not None else None
    vs = _ref(objs, med.find("VideoStream")) if med is not None else None
    mc = _ref(objs, sub.find("MasterClip")) if sub is not None else None
    log = _ref(objs, mc.find("LoggingInfo")) if mc is not None else None
    return {"sub": sub, "clip": clip, "src": src, "media": med, "stream": vs, "master": mc, "log": log}


def _matte(prmfs: list[str], saida: str, fps: float, quadros: int, largura: int, altura: int, tc_ticks: int) -> int:
    """Grava o vídeo de matte (ProRes 422 HQ, branco = objeto) juntando as passadas (união). Devolve os quadros com máscara."""
    from . import ffmpeg, prmf
    limiar = bytes(255 if v >= 128 else 0 for v in range(256))
    m: dict[int, bytes] = {}
    for arq in prmfs:
        for q in prmf.ler(arq):
            if not (q["caixa"] and (q["tam"] or 0) > 16):
                continue
            n = round(q["segundos"] * fps)
            a = bytes(prmf.alfa_quadro_inteiro(q, largura, altura)).translate(limiar)
            if n in m:
                a = (int.from_bytes(m[n], "big") | int.from_bytes(a, "big")).to_bytes(len(a), "big")
            m[n] = a
    base = round(fps)
    f = round(tc_ticks / TICKS * fps)
    tc = f"{f // base // 3600:02d}:{f // base // 60 % 60:02d}:{f // base % 60:02d}:{f % base:02d}"
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    cmd = [ffmpeg.achar("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{largura}x{altura}",
           "-framerate", str(fps), "-i", "-", "-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le",
           "-timecode", tc, saida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    vazio = bytes(largura * altura)
    for n in range(quadros):
        p.stdin.write(m.get(n, vazio))
    p.stdin.close()
    if p.wait():
        raise RuntimeError("o ffmpeg não gravou o matte")
    return sum(1 for n in m if n < quadros)


class _Molde:
    """O gabarito do 23.2: o clipe do matte (12 objetos + o item do bin) e o Track Matte Key (componente + 3 parâmetros)."""

    def __init__(self, caminho: str = MOLDE):
        import xml.etree.ElementTree as ET
        self.raiz = ET.parse(caminho).getroot()
        self.objs = _objs(self.raiz)
        tm = next(el for el in self.raiz if el.tag == "VideoFilterComponent" and el.findtext("MatchName") == "AE.ADBE Legacy Key Track Matte")
        self.track_matte = [tm] + [_ref(self.objs, p) for p in tm.findall("Component/Params/Param")]
        cpi = next(el for el in self.raiz if el.tag == "ClipProjectItem" and "MATTE" in (el.findtext("ProjectItem/Name") or ""))
        mc = cpi.find("MasterClip").get("ObjectURef")
        ti = next(el for el in self.raiz if el.tag == "VideoClipTrackItem"
                  and _ref(self.objs, el.find("ClipTrackItem/SubClip")).find("MasterClip").get("ObjectURef") == mc)
        vistos, pilha = set(), [ti.get("ObjectID")]
        while pilha:
            k = pilha.pop()
            if k in vistos or k not in self.objs:
                continue
            vistos.add(k)
            for x in self.objs[k].iter():
                r = x.get("ObjectRef") or x.get("ObjectURef")
                if r:
                    pilha.append(r)
        self.clipe = [self.objs[k] for k in vistos] + [cpi]
        self.item, self.cpi = ti, cpi


def _clonar(elementos: list, proximo: list) -> tuple[list, dict]:
    """Cópias com ObjectID/ObjectUID novos e as referências internas trocadas. `proximo` = [próximo ObjectID numérico]."""
    novo_id = {}
    for el in elementos:
        if el.get("ObjectID"):
            novo_id[el.get("ObjectID")] = str(proximo[0]); proximo[0] += 1
        else:
            novo_id[el.get("ObjectUID")] = str(uuid.uuid4())
    copias = []
    for el in elementos:
        c = copy.deepcopy(el)
        if c.get("ObjectID"):
            c.set("ObjectID", novo_id[c.get("ObjectID")])
        else:
            c.set("ObjectUID", novo_id[c.get("ObjectUID")])
        for x in c.iter():
            for a in ("ObjectRef", "ObjectURef"):
                if x.get(a) in novo_id:
                    x.set(a, novo_id[x.get(a)])
        for tag in ("ClipID", "FileKey"):
            for x in c.iter(tag):
                x.text = str(uuid.uuid4())
        copias.append(c)
    return copias, novo_id


def _texto(el, caminho: str, valor) -> None:
    x = el.find(caminho)
    if x is not None:
        x.text = str(valor)


def _ocupada(objs, trilha, inicio: int, fim: int) -> bool:
    """Algum clipe (inclusive camada de ajuste, título, gráfico) da trilha encosta em [inicio, fim)?"""
    for x in (trilha.find("ClipTrack/ClipItems/TrackItems") or []):
        o = _ref(objs, x)
        if o is None:
            continue
        a = int(o.findtext("ClipTrackItem/TrackItem/Start") or o.findtext("TrackItem/Start") or 0)
        b = int(o.findtext("ClipTrackItem/TrackItem/End") or o.findtext("TrackItem/End") or 0)
        if a < fim and b > inicio:
            return True
    return False


def _trilha_para_o_matte(raiz, objs, grupo, trilhas: list, n_trilha: int, inicio: int, fim: int) -> tuple:
    """A PRIMEIRA trilha de vídeo ACIMA do clipe que esteja livre no trecho (nada se sobrescreve: camada de ajuste, efeito,
    título… ficam onde estão); se nenhuma estiver, uma trilha NOVA no topo. Devolve (trilha, índice 0-based, criada?)."""
    import xml.etree.ElementTree as ET
    for k in range(n_trilha + 1, len(trilhas)):
        if trilhas[k] is not None and not _ocupada(objs, trilhas[k], inicio, fim):
            return trilhas[k], k, False
    modelo = trilhas[-1]
    nova = copy.deepcopy(modelo)
    nova.set("ObjectUID", str(uuid.uuid4()))
    ci = nova.find("ClipTrack/ClipItems")
    for filho in list(ci):
        if filho.tag == "TrackItems":
            ci.remove(filho)
    ti = nova.find("ClipTrack/TransitionItems")
    for filho in list(ti if ti is not None else []):
        if filho.tag == "TrackItems":
            ti.remove(filho)
    tg = grupo.find("TrackGroup")
    proximo_id = int(tg.findtext("NextTrackID") or len(trilhas) + 1)
    idx = len(trilhas)
    nova.find("ClipTrack/Track/ID").text = str(proximo_id)
    for caminho in ("ClipTrack/Track/Index", "ClipTrack/ClipItems/Index", "ClipTrack/TransitionItems/Index"):
        x = nova.find(caminho)
        if x is not None:
            x.text = str(idx)
    tg.find("NextTrackID").text = str(proximo_id + 1)
    lista = tg.find("Tracks")
    ET.SubElement(lista, "Track", {"Index": str(idx), "ObjectURef": nova.get("ObjectUID")})
    raiz.insert(list(raiz).index(modelo) + 1, nova)
    objs[nova.get("ObjectUID")] = nova
    trilhas.append(nova)
    return nova, idx, True


def converter(raiz, origem: str, destino: str) -> tuple[dict, list]:
    """Converte as máscaras de objeto da árvore `raiz` (já no formato do 23.2). `origem` = o .prproj original (para achar a
    pasta `<projeto> Masks` ao lado dele); os mattes vão em `<destino sem extensão> MATTES/`.
    Devolve (contagem, notas para marcador [(uid da sequência, ticks, nome, comentário)])."""
    import xml.etree.ElementTree as ET
    objs = _objs(raiz)
    pasta_masks = os.path.join(os.path.dirname(os.path.abspath(origem)),
                               os.path.splitext(os.path.basename(origem))[0] + " Masks")
    pasta_mattes = os.path.splitext(os.path.abspath(destino))[0] + " MATTES"
    proximo = [max((int(k) for k in objs if k and k.isdigit()), default=0) + 1]
    molde = None
    cont: dict[str, int] = {}
    notas: list = []
    raiz_bin = next((el for el in raiz if el.tag == "RootProjectItem"), None)
    for sq in [el for el in raiz if el.tag == "Sequence"]:
        uid = sq.get("ObjectUID") or sq.get("ObjectID")
        g = None
        for tg in sq.findall("TrackGroups/TrackGroup"):
            x = _ref(objs, tg.find("Second"))
            if x is not None and x.tag == "VideoTrackGroup":
                g = x
        if g is None:
            continue
        trilhas = [_ref(objs, t) for t in (g.find("TrackGroup/Tracks") or [])]
        for n_trilha, vt in enumerate(trilhas):
            itens = vt.find("ClipTrack/ClipItems/TrackItems") if vt is not None else None
            for it in list(itens if itens is not None else []):
                ti = _ref(objs, it)
                if ti is None or ti.tag != "VideoClipTrackItem":
                    continue
                cadeia = _ref(objs, ti.find("ClipTrackItem/ComponentOwner/Components"))
                if cadeia is None:
                    continue
                for c in list(cadeia.findall("ComponentChain/Components/Component")):
                    comp = _ref(objs, c)
                    if comp is None:
                        continue
                    for sc in list(comp.findall("SubComponents/SubComponent")):
                        masc = _ref(objs, sc)
                        if masc is None or masc.findtext("MatchName") != "AE.ADBE AEMask2":
                            continue
                        tipo, ids = _tipo_e_ids(objs, masc)
                        if tipo != "4":
                            continue
                        inicio = int(ti.findtext("ClipTrackItem/TrackItem/Start") or 0)
                        fim = int(ti.findtext("ClipTrackItem/TrackItem/End"))
                        prmfs = [os.path.join(pasta_masks, i + ".prmf") for i in ids
                                 if os.path.isfile(os.path.join(pasta_masks, i + ".prmf"))]
                        # retira a máscara (o 2023 não tem a de objeto) — sempre
                        comp.find("SubComponents").remove(sc)
                        for p in masc.findall("Component/Params/Param"):
                            po = _ref(objs, p)
                            if po is not None and po in list(raiz):
                                raiz.remove(po)
                        raiz.remove(masc)
                        m = _midia_do_item(objs, ti)
                        nome_clipe = (m["sub"].findtext("Name") if m["sub"] is not None else "") or "clipe"
                        if comp.findtext("MatchName") != "AE.ADBE Opacity" or not prmfs or m["stream"] is None:
                            motivo = ("a máscara estava num efeito (" + (comp.findtext("Component/DisplayName") or "?") +
                                      ") — o 2023 só recorta pela Opacidade/Track Matte" if comp.findtext("MatchName") != "AE.ADBE Opacity"
                                      else "os arquivos da máscara (.prmf) não vieram com o projeto" if not prmfs
                                      else "a mídia do clipe não foi lida")
                            notas.append((uid, inicio, "RETIRADO: máscara de objeto",
                                          f"O clipe {nome_clipe} tinha uma máscara de objeto, que o Premiere 2023 não tem, e não deu "
                                          f"para convertê-la: {motivo}. Refaça a máscara à mão (caneta com keyframes) se precisar."))
                            cont["máscara de objeto retirada"] = cont.get("máscara de objeto retirada", 0) + 1
                            continue
                        # o matte
                        fr = int(m["stream"].findtext("FrameRate"))
                        fps = TICKS / fr
                        dur = int(m["stream"].findtext("Duration") or 0)
                        quadros = round(dur / fr)
                        w, h = [int(v) for v in (m["stream"].findtext("FrameRect") or "0,0,1920,1080").split(",")[2:]]
                        alt = int(m["media"].findtext("AlternateStart") or 0) if m["media"] is not None else 0
                        arq_matte = os.path.join(pasta_mattes, f"{os.path.splitext(nome_clipe)[0]} MATTE {ids[0][:8]}.mov")
                        com = _matte(prmfs, arq_matte, fps, quadros, w, h, alt)
                        # o clipe do matte, clonado do gabarito
                        molde = molde or _Molde()
                        copias, mapa = _clonar(molde.clipe, proximo)
                        por_tag = {}
                        for el in copias:
                            por_tag.setdefault(el.tag, []).append(el)
                        nome = os.path.basename(arq_matte)
                        rel = os.path.relpath(arq_matte, os.path.dirname(os.path.abspath(destino)))
                        med = por_tag["Media"][0]
                        _texto(med, "RelativePath", rel.replace("/", "\\") if "\\" in (med.findtext("RelativePath") or "") else rel)
                        _texto(med, "FilePath", arq_matte)
                        _texto(med, "ActualMediaFilePath", arq_matte)
                        _texto(med, "Title", nome)
                        _texto(med, "AlternateStart", alt)
                        vs = por_tag["VideoStream"][0]
                        for campo in ("FrameRate", "FrameRect", "Duration"):
                            _texto(vs, campo, m["stream"].findtext(campo))
                        _texto(por_tag["VideoMediaSource"][0], "OriginalDuration",
                               m["src"].findtext("OriginalDuration") if m["src"] is not None else dur)
                        lg = por_tag["ClipLoggingInfo"][0]
                        _texto(lg, "ClipName", nome)
                        _texto(lg, "MediaInPoint", alt)
                        _texto(lg, "MediaOutPoint", alt + dur)
                        _texto(lg, "MediaFrameRate", fr)
                        for tag, cam in (("MasterClip", "Name"), ("SubClip", "Name"), ("ClipProjectItem", "ProjectItem/Name")):
                            for el in por_tag.get(tag, []):
                                _texto(el, cam, nome)
                        novo_ti = next(el for el in copias if el.get("ObjectID") == mapa[molde.item.get("ObjectID")])
                        _texto(novo_ti, "ClipTrackItem/TrackItem/Start", inicio)
                        _texto(novo_ti, "ClipTrackItem/TrackItem/End", fim)
                        sub_novo = next(el for el in copias if el.tag == "SubClip")
                        vc = next(el for el in copias if el.get("ObjectID") == sub_novo.find("Clip").get("ObjectRef"))
                        _texto(vc, "Clip/InPoint", m["clip"].findtext("Clip/InPoint") or 0)
                        _texto(vc, "Clip/OutPoint", m["clip"].findtext("Clip/OutPoint") or dur)
                        for el in copias:
                            raiz.append(el)
                            objs[el.get("ObjectID") or el.get("ObjectUID")] = el
                        # no bin raiz e na trilha de cima
                        if raiz_bin is not None:
                            itens_bin = raiz_bin.find("ProjectItemContainer/Items")
                            ET.SubElement(itens_bin, "Item", {"Index": str(len(itens_bin)),
                                          "ObjectURef": next(el for el in copias if el.tag == "ClipProjectItem").get("ObjectUID")})
                        acima, n_matte, criada = _trilha_para_o_matte(raiz, objs, g, trilhas, n_trilha, inicio, fim)
                        if criada:
                            cont["trilha de vídeo criada para o matte"] = cont.get("trilha de vídeo criada para o matte", 0) + 1
                        ci = acima.find("ClipTrack/ClipItems")
                        lista = ci.find("TrackItems")
                        if lista is None:
                            lista = ET.Element("TrackItems", {"Version": "1"})
                            ci.insert(0, lista)
                        ET.SubElement(lista, "TrackItem", {"Index": str(len(lista)), "ObjectRef": novo_ti.get("ObjectID")})
                        ordem = sorted(lista, key=lambda x: int(_ref(objs, x).findtext("ClipTrackItem/TrackItem/Start") or 0))
                        for k, x in enumerate(ordem):
                            x.set("Index", str(k))
                        lista[:] = ordem
                        # o Track Matte Key no clipe
                        tm, _ = _clonar(molde.track_matte, proximo)
                        ids_comp = [int(_ref(objs, x).findtext("Component/ID") or 0) for x in cadeia.findall("ComponentChain/Components/Component")
                                    if _ref(objs, x) is not None]
                        _texto(tm[0], "Component/ID", max(ids_comp + [2]) + 1)
                        matte_p = next(p for p in tm[1:] if p.findtext("ParameterID") == "1")
                        sk = matte_p.findtext("StartKeyframe").split(",")
                        sk[1] = str(n_matte + 1)                             # Matte = a trilha do matte (1 = V1)
                        matte_p.find("StartKeyframe").text = ",".join(sk)
                        for el in tm:
                            raiz.append(el)
                            objs[el.get("ObjectID")] = el
                        comps = cadeia.find("ComponentChain/Components")
                        ET.SubElement(comps, "Component", {"Index": str(len(comps)), "ObjectRef": tm[0].get("ObjectID")})
                        notas.append((uid, inicio, "CONVERTIDO: máscara de objeto → Track Matte",
                                      f"O clipe {nome_clipe} tinha uma máscara de objeto (Premiere 2026), que o 2023 não tem. Ela virou "
                                      f"um vídeo de matte em V{n_matte + 1}{' (trilha criada para ele)' if criada else ''} ({nome}, na pasta '{os.path.basename(pasta_mattes)}') e o "
                                      "clipe ganhou o Track Matte Key (Matte Luma). A máscara não é mais editável: refina-se no matte "
                                      "ou refazendo a máscara à mão."))
                        cont["máscara de objeto → Track Matte"] = cont.get("máscara de objeto → Track Matte", 0) + 1
                        cont["quadros com máscara no matte"] = cont.get("quadros com máscara no matte", 0) + com
    return cont, notas


# ------------------------------------------------------------------------------------------------------------------------------
# Máscaras de FORMA do 26 (`AEMask2` Type 0 caminho convertido, 1 elipse, 2 retângulo, 3 caneta) → a máscara do 22/23
# (`AE.ADBE AEMask`, 15 parâmetros) — medido 2026-10-08: o "Caminho" (param 7) do 26 tem os MESMOS vértices do "Mask Path"
# (param 6) do 22/23, só a embalagem muda; o TRACKING do 26 (param 6 "Controlador": uma matriz 3×3 por quadro, em coordenadas
# de 0 a 1 do quadro) e o Transformar da própria máscara (params 9–12, 26, 27) são ASSADOS no caminho, um keyframe por quadro
# — que é como o 23 grava uma máscara rastreada. Molde: `lab/moldes/mascara-23.2.xml` (PRODUCAO-C 22.4 salvo pelo 23.2).

MOLDE_MASCARA_23 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moldes", "mascara-23.2.xml")


def _caminho_26(b: bytes) -> tuple[list, bytes]:
    """[(marca, (x, y, entrada x, y, saída x, y))] e o fim. Cabeçalho: u32 2, u32 1, 'V', u32 tamanho, u32 2, u32 n."""
    import struct
    n = struct.unpack_from("<I", b, 17)[0]
    vs = [(struct.unpack_from("<I", b, 21 + 28 * i)[0], struct.unpack_from("<6f", b, 25 + 28 * i)) for i in range(n)]
    return vs, b[21 + 28 * n:]


def _binary_hash(dados: bytes) -> str:
    """O atributo `BinaryHash` de um valor binário: o Premiere o grava em TODO valor base64 (262/262 em 3 projetos) e o 23.2
    recusa o projeto ("damaged") sem ele. Formato medido: 12 bytes + u32 BE (tamanho + 12). O 23.2 não confere os 12 bytes
    contra o conteúdo (a LUT embutida levou o do molde e abriu); são aleatórios aqui para não colidir na deduplicação."""
    b = uuid.uuid4().bytes[:12] + (len(dados) + 12).to_bytes(4, "big")
    h = b.hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def _caminho_23(vs: list) -> bytes:
    """O "Mask Path" do 22/23: '2cin', u32 2, u32 0, u32 n; por vértice u32 marca + 6 float32 + u32 1."""
    import struct
    out = bytearray(b"2cin" + struct.pack("<III", 2, 0, len(vs)))
    for marca, v in vs:
        out += struct.pack("<I6fI", marca, *v, 1)
    return bytes(out)


def _keyframes(po) -> list:
    out = []
    for x in (po.findtext("Keyframes") or "").split(";"):
        x = x.strip()
        if x:
            t, resto = x.split(",", 1)
            out.append((int(t), resto))
    return out


def _valor(po, t: int):
    """Valor do parâmetro no tempo `t` (interpolação linear entre keyframes; ponto 'x:y' vira tupla)."""
    def conv(s):
        s = s.split(",")[0]
        return tuple(float(v) for v in s.split(":")) if ":" in s else (float(s.rstrip(".") or 0) if s not in ("true", "false") else s == "true")
    if po is None:
        return None
    kfs = _keyframes(po)
    if not kfs:
        sk = po.findtext("StartKeyframe") or ""
        return conv(sk.split(",", 1)[1]) if "," in sk else None
    if t <= kfs[0][0]:
        return conv(kfs[0][1])
    for (t0, v0), (t1, v1) in zip(kfs, kfs[1:]):
        if t0 <= t <= t1:
            a, b = conv(v0), conv(v1)
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return tuple(x + (y - x) * f for x, y in zip(a, b)) if isinstance(a, tuple) else a + (b - a) * f
    return conv(kfs[-1][1])


def _caminho_em(po, t: int) -> list:
    kfs = _keyframes(po)
    def dec(v):
        return _caminho_26(base64.b64decode(v.split(",")[0] + "=" * (-len(v.split(",")[0]) % 4)))[0]
    if not kfs:
        v = re.sub(r"\s", "", po.findtext("StartKeyframeValue") or "")
        return dec(v) if v else []
    if t <= kfs[0][0]:
        return dec(kfs[0][1])
    for (t0, v0), (t1, v1) in zip(kfs, kfs[1:]):
        if t0 <= t <= t1:
            a, b = dec(v0), dec(v1)
            if len(a) != len(b):
                return a
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return [(ma, tuple(x + (y - x) * f for x, y in zip(va, vb))) for (ma, va), (_, vb) in zip(a, b)]
    return dec(kfs[-1][1])


def _matriz_em(po, t: int):
    """A matriz do tracking (Controlador) no tempo `t` — a do keyframe mais próximo (há um por quadro)."""
    import struct
    kfs = _keyframes(po) if po is not None else []
    if not kfs:
        return None
    tk, v = min(kfs, key=lambda kv: abs(kv[0] - t))
    b = base64.b64decode(v.split(",")[0] + "=" * (-len(v.split(",")[0]) % 4))
    return struct.unpack_from("<9f", b, 4)                         # coluna a coluna: a b 0 | c d 0 | tx ty 1


def _transformar(p, t: int, w: int, h: int):
    """O Transformar da própria máscara (posição, ancoragem, escala, dimensionar, rotação) como função de ponto."""
    import math
    pos = _valor(p.get("9"), t) or (0, 0)
    anc = _valor(p.get("10"), t) or pos
    esc = _valor(p.get("11"), t) or (1, 1)
    alt = (_valor(p.get("26"), t) or 100) / 100
    lar = (_valor(p.get("27"), t) or 100) / 100
    rot = math.radians(_valor(p.get("12"), t) or 0)
    sx, sy = esc[0] * lar, esc[1] * alt
    c, s = math.cos(rot), math.sin(rot)
    neutro = abs(pos[0] - anc[0]) < 1e-9 and abs(pos[1] - anc[1]) < 1e-9 and abs(sx - 1) < 1e-9 and abs(sy - 1) < 1e-9 and abs(rot) < 1e-12

    def f(x, y):
        dx, dy = (x - anc[0]) * w * sx, (y - anc[1]) * h * sy        # rotação em PIXELS
        return pos[0] + (c * dx - s * dy) / w, pos[1] + (s * dx + c * dy) / h
    return None if neutro else f


def _aplicar(vs: list, f) -> list:
    out = []
    for marca, v in vs:
        pts = [f(v[0], v[1]), f(v[2], v[3]), f(v[4], v[5])]
        out.append((marca, tuple(c for p in pts for c in p)))
    return out


def formas_para_mascara_antiga(raiz, so_tipos: tuple | None = None, max_quadros: int | None = None) -> tuple[dict, list]:
    """Troca cada `AEMask2` de forma (Type 0–3) pela `AE.ADBE AEMask` do 23, com o caminho por quadro. Devolve (contagem, notas)."""
    import xml.etree.ElementTree as ET
    objs = _objs(raiz)
    molde = ET.parse(MOLDE_MASCARA_23).getroot()
    proximo = [max((int(k) for k in objs if k and k.isdigit()), default=0) + 1]
    cont: dict[str, int] = {}
    notas: list = []
    pai_de = {sc.get("ObjectRef"): (comp, sc) for comp in raiz if comp.tag == "VideoFilterComponent"
              for sc in comp.findall("SubComponents/SubComponent")}
    for masc in [el for el in raiz if el.tag == "VideoFilterComponent" and el.findtext("MatchName") == "AE.ADBE AEMask2"]:
        tipo, _ = _tipo_e_ids(objs, masc)
        if tipo not in ("0", "1", "2", "3") or masc.get("ObjectID") not in pai_de or (so_tipos and tipo not in so_tipos):
            continue
        p = {}
        for x in masc.findall("Component/Params/Param"):
            o = _ref(objs, x)
            if o is not None:
                p[o.findtext("ParameterID")] = o
        cam, ctl = p.get("7"), p.get("6")
        if cam is None:
            continue
        w, h = 1920, 1080
        tempos = sorted({t for t, _ in _keyframes(ctl)} if ctl is not None and _keyframes(ctl) else
                        {t for t, _ in _keyframes(cam)} | {t for q in ("9", "10", "11", "12", "26", "27") if p.get(q) is not None
                                                           for t, _ in _keyframes(p[q])})
        if not tempos:
            tempos = [-91445760000000000]
        quadros = []
        for t in tempos:
            vs = _caminho_em(cam, t)
            tf = _transformar(p, t, w, h)
            if tf:
                vs = _aplicar(vs, tf)
            m = _matriz_em(ctl, t)
            if m:
                a, b, _, c, d, _, tx, ty, _ = m
                vs = _aplicar(vs, lambda x, y: (a * x + c * y + tx, b * x + d * y + ty))
            quadros.append((t, vs))
        if max_quadros:
            quadros = quadros[:max_quadros]
        # a máscara do 23, clonada do molde
        novos, _ = _clonar(list(molde), proximo)
        comp = novos[0]
        pn = {e.findtext("ParameterID"): e for e in novos[1:]}
        cam23 = pn["6"]
        # ⚠️ a ORDEM dos filhos importa (o 23.2 deu "project appears to be damaged" com os Keyframes depois do ParameterID):
        # o valor entra no lugar do que o molde tinha, logo depois do StartKeyframePosition
        pos = next((i for i, x in enumerate(cam23) if x.tag in ("StartKeyframeValue", "Keyframes")), None)
        for tag in ("StartKeyframeValue", "Keyframes"):
            x = cam23.find(tag)
            if x is not None:
                cam23.remove(x)
        if pos is None:
            pos = next((i + 1 for i, x in enumerate(cam23) if x.tag == "StartKeyframePosition"), len(cam23))
        # o 23.2 grava os DOIS: Keyframes e, logo depois, StartKeyframeValue (o caminho inicial) — sem este, "damaged"
        dados0 = _caminho_23(quadros[0][1])
        inicial = ET.Element("StartKeyframeValue", {"Encoding": "base64", "BinaryHash": _binary_hash(dados0)})
        inicial.text = base64.b64encode(dados0).decode()
        if len(quadros) == 1 and quadros[0][0] < 0:
            cam23.insert(pos, inicial)
        else:
            novo = ET.Element("Keyframes")
            novo.text = ";".join(f"{t},{base64.b64encode(_caminho_23(vs)).decode()}" for t, vs in quadros) + ";"
            cam23.insert(pos, novo)
            cam23.insert(pos + 1, inicial)
        for de, para in (("14", "7"), ("15", "8"), ("16", "9"), ("17", "10")):
            v = _valor(p.get(de), quadros[0][0]) if p.get(de) is not None else None
            if v is None or pn.get(para) is None:
                continue
            sk = pn[para].findtext("StartKeyframe").split(",")
            sk[1] = ("true" if v else "false") if isinstance(v, bool) else (repr(float(v)).rstrip("0") if float(v) != int(v) else f"{int(v)}.")
            pn[para].find("StartKeyframe").text = ",".join(sk)
        for e in novos:
            raiz.append(e)
        dono, sc = pai_de[masc.get("ObjectID")]
        sc.set("ObjectRef", comp.get("ObjectID"))
        for x in masc.findall("Component/Params/Param"):
            o = _ref(objs, x)
            if o is not None and o in list(raiz):
                raiz.remove(o)
        raiz.remove(masc)
        chave = {"0": "caminho", "1": "elipse", "2": "retângulo", "3": "caneta"}[tipo]
        cont[f"máscara ({chave}) → máscara do 23"] = cont.get(f"máscara ({chave}) → máscara do 23", 0) + 1
        if ctl is not None and _keyframes(ctl):
            cont["quadros de tracking assados no caminho"] = cont.get("quadros de tracking assados no caminho", 0) + len(quadros)
    return cont, notas
