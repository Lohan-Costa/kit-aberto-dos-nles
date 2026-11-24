"""B14 MÁSCARA — a máscara de OPACIDADE do Premiere medida com contorno CONHECIDO (pedido do autor, 2026-10-10: levar as
condições do caso real R04 PRODUCAO-C ao laboratório — `docs/condicoes-R04-we-speak-dance.md`).

Duas placas lisas que dizem o próprio quadro: FUNDO (azul-escuro, número embaixo à direita) na V1 e FRENTE (laranja, número
em cima à esquerda) na V2; a FRENTE_100 é a mesma placa a 100 qps (tempo real numa timeline de 23,976). A máscara da FRENTE
é um retângulo cuja borda DIREITA é uma reta vertical em `x` (fração da largura da fonte) — o resto do contorno fica fora
do quadro. Na faixa do meio da imagem não há texto: a mistura de cada coluna entre as duas cores É o alfa da máscara.

- `gerar(saida)`: a mídia (ffmpeg, ProRes 422) e o `verdade.json` com o PLANO (um segmento por variante).
- `aplicar(prproj_entrada, prproj_saida)`: põe as máscaras no projeto do 23.2, uma por clipe da V2, na ordem do plano,
  clonadas do molde salvo pelo próprio 23.2 (`moldes/mascara-23.2.xml`, o mesmo do `prproj_mascara`).
- `perfil(imagem, cor_fundo, cor_frente)`: o alfa por coluna; `borda(perfil)`: o meio (50 %) e a largura 10–90 % em px.

Só biblioteca padrão + ffmpeg (regra do laboratório); a leitura de imagens do `perfil` lê PPM cru que o ffmpeg escreve.
"""
from __future__ import annotations

import base64
import gzip
import json
import os
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET

from . import ffmpeg as ff
from . import video
from .prproj_mascara import MOLDE_MASCARA_23, _binary_hash, _caminho_23, _clonar

W, H = 1920, 1080
FPS = "24000/1001"
TPS = 254016000000
TICKS_QUADRO = TPS * 1001 // 24000            # um quadro de 23,976 em ticks (exato: 10594584000)
COR_FUNDO = (0x20, 0x20, 0x60)
COR_FRENTE = (0xB0, 0x40, 0x20)
FAIXA_Y = (400, 680)                          # a faixa sem texto onde se mede o alfa
MOLDE_OPACIDADE_23 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moldes", "opacidade-23.2.xml")

#: Os segmentos, na ordem da V2. `x` = a borda (fração da largura da fonte); `anim` = (x inicial, x final) com um
#: keyframe a cada `passo` quadros da timeline; `desigual` alterna 4 e 5 vértices entre keyframes (o LOU_7310 do R04).
PLANO = (
    [{"rotulo": f"F{f}", "clipe": "FRENTE", "quadros": 6, "x": 0.5, "feather": f, "expansao": 0} for f in
     (0, 10, 25, 50, 100, 201, 300, 500)]
    + [{"rotulo": f"E{e}", "clipe": "FRENTE", "quadros": 6, "x": 0.5, "feather": 0, "expansao": e} for e in (-16, 16, 50)]
    + [{"rotulo": "E16_F50", "clipe": "FRENTE", "quadros": 6, "x": 0.5, "feather": 50, "expansao": 16},
       {"rotulo": "Z200_F201", "clipe": "FRENTE", "quadros": 6, "x": 0.5, "feather": 201, "expansao": 0, "zoom": 200},
       {"rotulo": "Z200_F50", "clipe": "FRENTE", "quadros": 6, "x": 0.5, "feather": 50, "expansao": 0, "zoom": 200},
       {"rotulo": "ANIM", "clipe": "FRENTE", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0, "expansao": 0},
       {"rotulo": "ANIM_DESIGUAL", "clipe": "FRENTE", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "desigual": True,
        "feather": 0, "expansao": 0},
       {"rotulo": "ANIM_ESPARSO", "clipe": "FRENTE", "quadros": 12, "anim": (0.2, 0.8), "passo": 4, "feather": 0,
        "expansao": 0},
       {"rotulo": "ANIM_100", "clipe": "FRENTE_100", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0,
        "expansao": 0}]
)
CLIPES = {"FUNDO": {"cor": COR_FUNDO, "fps": FPS, "segundos": 12, "digitos": "baixo"},
          "FRENTE": {"cor": COR_FRENTE, "fps": FPS, "segundos": 6, "digitos": "cima"},
          "FRENTE_100": {"cor": COR_FRENTE, "fps": "100", "segundos": 6, "digitos": "cima"}}


def inicio(i: int) -> int:
    """Quadro da timeline em que começa o segmento `i`."""
    return sum(s["quadros"] for s in PLANO[:i])


def x_em(seg: dict, k: int) -> float:
    """A borda (fração da largura da fonte) no quadro `k` do segmento — a VERDADE do contorno."""
    if "anim" not in seg:
        return seg["x"]
    a, b = seg["anim"]
    n = seg["quadros"] - 1
    return a + (b - a) * k / n


def _hex(c: tuple) -> str:
    return "0x%02X%02X%02X" % c


def _filtro(nome: str, c: dict) -> str:
    alt, larg = 120, 66
    y = 40 if c["digitos"] == "cima" else H - 40 - alt
    x0 = 40 if c["digitos"] == "cima" else W - 40 - 5 * (larg + 18)
    partes = []
    for i in range(5):                        # 5 algarismos do número do quadro no ARQUIVO
        partes += video._digito(x0 + (4 - i) * (larg + 18), y, larg, alt, f"mod(floor(n/{10 ** i}),10)")
    partes += video._texto(nome, x0, y + alt + 20 if c["digitos"] == "cima" else y - 60, 5)
    return ",".join(partes)


def gerar(saida: str) -> dict:
    os.makedirs(saida, exist_ok=True)
    exe = ff.achar("ffmpeg")
    arquivos = {}
    for nome, c in CLIPES.items():
        arq = os.path.join(saida, f"B14_{nome}.mov")
        subprocess.run([exe, "-v", "error", "-y", "-f", "lavfi", "-i",
                        f"color=c={_hex(c['cor'])}:s={W}x{H}:r={c['fps']}:d={c['segundos']}",
                        "-vf", _filtro(nome, c), "-c:v", "prores_ks", "-profile:v", "2", "-pix_fmt", "yuv422p10le",
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", arq], check=True)
        arquivos[nome] = os.path.basename(arq)
    verdade = {"caso": "B14_MASCARA", "raster": [W, H], "fps_timeline": FPS, "cor_fundo": COR_FUNDO,
               "cor_frente": COR_FRENTE, "faixa_y": FAIXA_Y, "arquivos": arquivos,
               "segmentos": [dict(s, inicio=inicio(i), x_por_quadro=[x_em(s, k) for k in range(s["quadros"])])
                             for i, s in enumerate(PLANO)]}
    with open(os.path.join(saida, "verdade.json"), "w", encoding="utf-8") as f:
        json.dump(verdade, f, ensure_ascii=False, indent=1)
    return verdade


# ── o contorno no formato do 23.2 ────────────────────────────────────────────────────────────────────────────────────
def contorno(x: float, desigual: bool = False) -> list:
    """Retângulo com a borda direita em `x`; o resto fora do quadro. Vértices de CANTO (marca 0, alças = o vértice).
    `desigual`: um 5º vértice no meio da borda (na própria reta: a forma é a mesma, a contagem não)."""
    pts = [(-0.2, -0.2), (x, -0.2)] + ([(x, 0.5)] if desigual else []) + [(x, 1.2), (-0.2, 1.2)]
    return [(0, (px, py, px, py, px, py)) for px, py in pts]


def _b64(vs: list) -> tuple[str, str]:
    d = _caminho_23(vs)
    return base64.b64encode(d).decode(), _binary_hash(d)


def _numero(v: float) -> str:
    return f"{int(v)}." if float(v) == int(v) else repr(float(v))


def _mascara(seg: dict, proximo: list) -> list:
    """Os elementos de UMA máscara do 23.2 (componente + 15 parâmetros) para o segmento."""
    molde = ET.parse(MOLDE_MASCARA_23).getroot()
    novos, _ = _clonar(list(molde), proximo)
    pn = {e.findtext("ParameterID"): e for e in novos[1:]}
    cam = pn["6"]
    pos = next(i for i, x in enumerate(cam) if x.tag in ("StartKeyframeValue", "Keyframes"))
    for tag in ("StartKeyframeValue", "Keyframes"):
        x = cam.find(tag)
        if x is not None:
            cam.remove(x)
    fps_m = 100.0 if seg["clipe"] == "FRENTE_100" else 24000 / 1001
    if "anim" in seg:
        kfs = []
        for k in range(0, seg["quadros"], seg["passo"]):
            # tempo da MÍDIA do clipe (in = 0), em ticks: o instante do quadro k da timeline (tempo real)
            # `vel`: quantos quadros da mídia do alvo passam por quadro da timeline (velocidade do clipe ou do nest)
            t = seg.get("t0_ticks", 0) + round(k * seg.get("vel", 1) * TICKS_QUADRO)
            b, _ = _b64(contorno(x_em(seg, k), seg.get("desigual") and k % 2 == 1))
            kfs.append(f"{t},{b}")
        el = ET.Element("Keyframes")
        el.text = ";".join(kfs) + ";"
        cam.insert(pos, el)
        pos += 1
        _ = fps_m
    b, h = _b64(contorno(x_em(seg, 0)))
    ini = ET.Element("StartKeyframeValue", {"Encoding": "base64", "BinaryHash": h})
    ini.text = b
    cam.insert(pos, ini)
    for pid, v in (("7", seg["feather"]), ("9", seg["expansao"])):
        sk = pn[pid].findtext("StartKeyframe").split(",")
        sk[1] = _numero(v)
        pn[pid].find("StartKeyframe").text = ",".join(sk)
    return novos


def _b14(itens: list) -> list:
    """Os alvos do B14: os clipes da FRENTE, pela ordem no tempo = a ordem do PLANO."""
    itens = sorted([i for i in itens if (i["nome"] or "").startswith("B14_FRENTE")], key=lambda i: i["start"])
    if len(itens) != len(PLANO):
        raise ValueError(f"{len(itens)} clipes da FRENTE no projeto, o plano tem {len(PLANO)}")
    for i, seg in zip(itens, PLANO):
        if i["nome"] != f"B14_{seg['clipe']}.mov":
            raise ValueError(f"o clipe em {i['start']} é {i['nome']}, o plano pede {seg['clipe']}")
    return list(zip(itens, PLANO))


def aplicar(entrada: str, saida: str, alvos=_b14) -> list:
    """Uma máscara por clipe-alvo. `alvos(itens)` recebe os `VideoClipTrackItem` de TODAS as sequências como
    `{start, nome (o do SubClip), …}` e devolve [(item, segmento)] — no B14, a FRENTE pela ordem; no B16, pelo nome
    dado ao clipe. O segmento é o do `PLANO` (com `t0_ticks`: o tempo da mídia do clipe no 1º quadro). Devolve
    [(rótulo, início ticks)]."""
    texto = gzip.open(entrada, "rb").read().decode("utf-8")
    raiz = ET.fromstring(texto)
    por_id: dict = {}
    for el in raiz:
        por_id.setdefault(el.get("ObjectID") or el.get("ObjectUID"), []).append(el)

    def ref(el, tag):
        for o in por_id.get(el.get("ObjectRef") or el.get("ObjectURef"), []):
            if o.tag == tag:
                return o
        return None
    itens = []
    for ti in [e for e in raiz if e.tag == "VideoClipTrackItem"]:
        sub = ref(ti.find("ClipTrackItem/SubClip"), "SubClip")
        nome = sub.findtext("Name") if sub is not None else ""
        cadeia = ref(ti.find("ClipTrackItem/ComponentOwner/Components"), "VideoComponentChain")
        opac = None
        for c in cadeia.findall("ComponentChain/Components/Component"):
            o = ref(c, "VideoFilterComponent")
            if o is not None and o.findtext("MatchName") == "AE.ADBE Opacity":
                opac = o
        itens.append({"start": int(ti.findtext("ClipTrackItem/TrackItem/Start")), "nome": nome, "opac": opac,
                      "cadeia": cadeia})
    escolhidos = alvos(itens)
    proximo = [max((int(k) for k in por_id if k and k.isdigit()), default=0) + 1]
    mexidos: list = []

    def opacidade(cadeia):
        """A Opacity no padrão o 23.2 NÃO grava (`DefaultOpacity` = true na cadeia, nenhum componente; mexer no valor pela
        API não muda isso — medido 2026-10-10). Para pendurar a máscara: o componente clonado do molde (tirado de um
        projeto salvo pelo 23.2, o R04) entra na lista da cadeia e as duas marcas de padrão saem."""
        novos, _ = _clonar(list(ET.parse(MOLDE_OPACIDADE_23).getroot()), proximo)
        cc = cadeia.find("ComponentChain")
        lista = cc.find("Components")
        if lista is None:
            lista = ET.Element("Components", {"Version": "1"})
            cc.insert(list(cc).index(cc.find("Node")) + 1 if cc.find("Node") is not None else 0, lista)
        ET.SubElement(lista, "Component", {"Index": str(len(lista)), "ObjectRef": novos[0].get("ObjectID")})
        for tag in ("DefaultOpacity", "DefaultOpacityComponentID"):
            x = cadeia.find(tag)
            if x is not None:
                cadeia.remove(x)
        for e in novos:
            raiz.append(e)
        mexidos.extend([cadeia] + novos)
        return novos[0]
    feitos = []
    for item, seg in escolhidos:
        start = item["start"]
        opac = item["opac"] if item["opac"] is not None else opacidade(item["cadeia"])
        novos = _mascara(seg, proximo)
        subs = opac.find("SubComponents")
        if subs is None:
            subs = ET.Element("SubComponents", {"Version": "1"})
            opac.insert(list(opac).index(opac.find("MatchName")), subs)
        ET.SubElement(subs, "SubComponent", {"Index": str(len(subs)), "ObjectRef": novos[0].get("ObjectID")})
        for e in novos:
            raiz.append(e)
        mexidos.extend([opac] + novos)
        feitos.append((seg["rotulo"], start))
    # cada objeto numa linha com um TAB, como o Premiere grava: o `ET` deixa o 1º acrescentado colado ao "\n" anterior e
    # um leitor que indexa por "\n\t<Tag ObjectID" (o do De Lá Pra Cá) não o enxergava (2026-10-10)
    for e in mexidos:
        _indentar(e, 1)
    filhos = list(raiz)
    raiz.text = "\n\t"
    for i, e in enumerate(filhos):
        e.tail = "\n\t" if i < len(filhos) - 1 else "\n"
    from .bancadas.premiere_relink import _gravar_prproj      # o cabeçalho gzip que o Premiere escreve
    # e as tags vazias como o Premiere: `<X .../>`, sem o espaço que o `ET` põe antes da barra
    xml = ET.tostring(raiz, encoding="unicode").replace(" />", "/>")
    _gravar_prproj(saida, '<?xml version="1.0" encoding="UTF-8" ?>\n' + xml)
    return feitos


def _indentar(el, nivel: int) -> None:
    """Indentação do Premiere (um TAB por nível) num elemento que se mexeu: o indexador do De Lá Pra Cá acha o FIM de um
    objeto por "\\n\\t</Tag>" — sem isto, tirar o último filho de uma cadeia (o `DefaultOpacity`) a escondia. Folhas mantêm
    o texto."""
    filhos = list(el)
    if not filhos:
        return
    el.text = "\n" + "\t" * (nivel + 1)
    for i, f in enumerate(filhos):
        _indentar(f, nivel + 1)
        f.tail = "\n" + "\t" * (nivel + 1 if i < len(filhos) - 1 else nivel)


# ── a medida ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def ler_quadro(arquivo: str, quadro: int | None = None) -> tuple[int, int, bytes]:
    """RGB 8 bits de um quadro (de um vídeo, pelo índice) ou de uma imagem, pelo ffmpeg (sem bibliotecas)."""
    exe = ff.achar("ffmpeg")
    cmd = [exe, "-v", "error", "-i", arquivo]
    if quadro is not None:
        cmd += ["-vf", f"select=eq(n\\,{quadro})", "-vsync", "0"]
    cmd += ["-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-"]
    dados = subprocess.run(cmd, capture_output=True, check=True).stdout
    if len(dados) != W * H * 3:
        raise ValueError(f"{arquivo} quadro {quadro}: {len(dados)} bytes")
    return W, H, dados


def perfil(rgb: bytes, fundo=COR_FUNDO, frente=COR_FRENTE, faixa=FAIXA_Y) -> list[float]:
    """Alfa por coluna (0 = só o FUNDO, 1 = só a FRENTE): a projeção de cada pixel na reta fundo → frente, média na faixa."""
    d = [b - a for a, b in zip(fundo, frente)]
    dd = sum(v * v for v in d)
    soma = [0.0] * W
    for y in range(faixa[0], faixa[1], 4):
        base = y * W * 3
        for x in range(W):
            i = base + 3 * x
            soma[x] += ((rgb[i] - fundo[0]) * d[0] + (rgb[i + 1] - fundo[1]) * d[1] + (rgb[i + 2] - fundo[2]) * d[2]) / dd
    n = len(range(faixa[0], faixa[1], 4))
    return [s / n for s in soma]


def borda(p: list[float]) -> dict:
    """O meio (coluna onde o alfa cruza 0,5, interpolada) e a largura 10–90 % da transição (a 1ª descida da esquerda)."""
    def cruza(nivel):
        for x in range(1, len(p)):
            if p[x - 1] >= nivel > p[x]:
                return x - 1 + (p[x - 1] - nivel) / (p[x - 1] - p[x])
        return None
    m, a, b = cruza(0.5), cruza(0.9), cruza(0.1)
    return {"meio": m, "largura_10_90": (b - a) if a is not None and b is not None else None,
            "a90": a, "a10": b, "alfa_esq": sum(p[20:60]) / 40, "alfa_dir": sum(p[-60:-20]) / 40}


_DIGITOS = {frozenset(s for s, ds in video._SEGMENTOS.items() if d in ds): d for d in range(10)}


def numero_da_placa(rgb: bytes, digitos: str = "cima", x0: int | None = None, y0: int | None = None,
                    larg: int = 66, alt: int = 120, passo: int = 84) -> int | None:
    """O número do quadro que a placa mostra (5 algarismos de 7 segmentos do `_filtro`), lido no centro de cada segmento:
    aceso = claro (o branco do algarismo × o laranja/azul da placa). None quando um algarismo não se lê (máscara por cima,
    escala, outra placa)."""
    x0 = (40 if digitos == "cima" else W - 40 - 5 * passo) if x0 is None else x0
    y0 = (40 if digitos == "cima" else H - 40 - alt) if y0 is None else y0
    k = max(2, round(larg * 0.2))
    meia = alt // 2
    v = meia - k - k // 2
    n = 0
    for i in range(5):
        x = x0 + (4 - i) * passo
        geo = {"a": (x + k, y0, larg - 2 * k, k), "b": (x + larg - k, y0 + k, k, v), "c": (x + larg - k, y0 + meia + k // 2, k, v),
               "d": (x + k, y0 + alt - k, larg - 2 * k, k), "e": (x, y0 + meia + k // 2, k, v), "f": (x, y0 + k, k, v),
               "g": (x + k, y0 + meia - k // 2, larg - 2 * k, k)}
        acesos = set()
        for s, (gx, gy, gw, gh) in geo.items():
            cx, cy = gx + gw // 2, gy + gh // 2
            j = (cy * W + cx) * 3
            if min(rgb[j], rgb[j + 1], rgb[j + 2]) > 200:
                acesos.add(s)
        d = _DIGITOS.get(frozenset(acesos))
        if d is None:
            return None
        n += d * 10 ** i
    return n


def main(argv=None) -> int:
    import argparse
    from .gerar import RAIZ
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=os.path.join(RAIZ, "saida", "base", "B14_MASCARA"))
    a = ap.parse_args(argv)
    v = gerar(a.saida)
    print(json.dumps(v["arquivos"]), len(v["segmentos"]), "segmentos,", inicio(len(PLANO)), "quadros")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
