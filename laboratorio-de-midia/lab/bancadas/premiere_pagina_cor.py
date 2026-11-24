"""A PÁGINA COLOR do Premiere 2027 (27.0.0) — ler a árvore que ela grava no `.prproj` (pedido do autor, 2026-11-20).

A página Color grava uma árvore de `CompoundComponent` (classe `250b3605-8b7a-4687-bf33-f54e312a510e`) na cadeia do
clipe (e, a confirmar, da sequência): cada nó tem `CompoundComponentType` (o papel), `ComponentOwner/Components` → uma
`VideoComponentChain` com os filhos. A API vê só "Color Mode Effect" opaco — por isso o arquivo.

    py -m lab.bancadas.premiere_pagina_cor <projeto.prproj> [<anterior.prproj>]   # a árvore (e o que mudou)
"""
from __future__ import annotations

import json
import re
import sys

from .premiere_cor_mc import ler_xml

COMPOUND = "250b3605-8b7a-4687-bf33-f54e312a510e"
#: o papel de cada `CompoundComponentType` (o que já foi visto; o resto aparece como número)
TIPOS = {65537: "contêiner da página", 65541: "nível Clip", 65538: "camada Adjustment", 65539: "grupo Detail",
         65542: "grupo", 65543: "contêiner da SEQUÊNCIA (no VideoTrackGroup)", 65540: "Style"}


class Arvore:
    def __init__(self, xml: str):
        self.xml = xml
        self.obj = {m.group(2): (m.group(1), m.group(0)) for m in
                    re.finditer(r'<(\w+) ObjectID="(\d+)"[^>]*>.*?</\1>', xml, re.S)}
        self.uobj = {m.group(2): (m.group(1), m.group(0)) for m in
                     re.finditer(r'<(\w+) ObjectUID="([^"]+)"[^>]*>.*?</\1>', xml, re.S)}

    def _campo(self, corpo: str, nome: str) -> str | None:
        m = re.search(r"<%s>([^<]*)</%s>" % (nome, nome), corpo)
        return m.group(1) if m else None

    def _cadeia(self, oid: str) -> list[str]:
        _, corpo = self.obj.get(oid, ("", ""))
        return re.findall(r'<Component Index="\d+" ObjectRef="(\d+)"/>', corpo)

    def _params(self, corpo: str) -> dict:
        out = {}
        for ref in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', corpo):
            tipo, c = self.obj.get(ref, ("", ""))
            nome = self._campo(c, "Name") or ""
            pid = self._campo(c, "ParameterID")
            sk = self._campo(c, "StartKeyframe")
            val = sk.split(",")[1] if sk and "," in sk else None
            if val is None:
                v = re.search(r'<StartKeyframeValue[^>]*BinaryHash="([^"]+)"', c)
                val = "blob:" + v.group(1)[:8] if v else None
            kfs = self._campo(c, "Keyframes")
            out[f"{pid}:{nome.strip() or '?'}"] = val + (" [animado]" if kfs else "") if val is not None else None
        return out

    def no(self, oid: str) -> dict:
        tipo, corpo = self.obj[oid]
        if COMPOUND in corpo[:200]:
            t = int(self._campo(corpo, "CompoundComponentType") or 0)
            dono = re.search(r'<Components ObjectRef="(\d+)"/>', corpo)
            return {"compound": TIPOS.get(t, t), "tipo": t, "id": self._campo(corpo, "ID"),
                    "nome": self._campo(corpo, "InstanceName"), "desligado": self._campo(corpo, "Bypass"),
                    "filhos": [self.no(f) for f in (self._cadeia(dono.group(1)) if dono else [])]}
        return {"efeito": self._campo(corpo, "MatchName"), "nome": self._campo(corpo, "DisplayName") or
                self._campo(corpo, "InstanceName"), "desligado": self._campo(corpo, "Bypass"), "params": self._params(corpo)}

    def clipes(self) -> list[dict]:
        """Cada clipe de vídeo (início em ticks) com a sua árvore de componentes."""
        fora = []
        for m in re.finditer(r'<VideoClipTrackItem ObjectID="(\d+)"[^>]*>(.*?)</VideoClipTrackItem>', self.xml, re.S):
            ini = self._campo(m.group(2), "Start")
            comps = re.search(r'<Components ObjectRef="(\d+)"/>', m.group(2))
            fora.append({"item": m.group(1), "inicio": int(ini or 0),
                         "componentes": [self.no(c) for c in (self._cadeia(comps.group(1)) if comps else [])]})
        return sorted(fora, key=lambda c: c["inicio"])

    def compounds_soltos(self) -> list[dict]:
        """Todo CompoundComponent que NÃO está na cadeia de um clipe (sequência, grupos…) — para achar onde mais a
        página Color grava."""
        nos_clipes = set()

        def marcar(n):
            if "compound" in n:
                nos_clipes.add(n["id"])
        usados = set(re.findall(r'ObjectRef="(\d+)"', self.xml))
        fora = []
        for oid, (tipo, corpo) in self.obj.items():
            if COMPOUND in corpo[:200]:
                fora.append({"oid": oid, "tipo": int(self._campo(corpo, "CompoundComponentType") or 0),
                             "nome": self._campo(corpo, "InstanceName"), "referenciado": oid in usados})
        return fora


def _so_mudou(a, b, cam=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            out += _so_mudou(a.get(k), b.get(k), f"{cam}/{k}")
    elif isinstance(a, list) and isinstance(b, list):
        for i in range(max(len(a), len(b))):
            out += _so_mudou(a[i] if i < len(a) else None, b[i] if i < len(b) else None, f"{cam}[{i}]")
    elif a != b:
        out.append((cam, a, b))
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    sys.stdout.reconfigure(encoding="utf-8")
    b = Arvore(ler_xml(argv[0]))
    if len(argv) > 1:
        a = Arvore(ler_xml(argv[1]))
        for cam, va, vb in _so_mudou(a.clipes(), b.clipes()):
            print(cam, ":", json.dumps(va, ensure_ascii=False)[:200], "→", json.dumps(vb, ensure_ascii=False)[:300])
        print("compounds:", b.compounds_soltos())
        return 0
    print(json.dumps({"clipes": b.clipes(), "compounds": b.compounds_soltos()}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def escrever(xml: str, clipe: int, caminho: list[str], efeito: str, param: str, valor: str) -> str:
    """Troca o valor inicial de `param` (nome) do `efeito` (matchName) no `clipe` (índice na ordem do tempo), dentro do
    nó da página cujo caminho de nomes/tipos é `caminho` (ex.: ["nível Clip", "Adjust 1"] ou ["Group 01", "Adjust 2"])."""
    a = Arvore(xml)
    itens = sorted(((int(a._campo(m.group(2), "Start") or 0), m.group(2)) for m in
                    re.finditer(r'<VideoClipTrackItem ObjectID="(\d+)"[^>]*>(.*?)</VideoClipTrackItem>', xml, re.S)))
    comps = re.search(r'<Components ObjectRef="(\d+)"/>', itens[clipe][1])

    def achar(oids, resto):
        for oid in oids:
            _, corpo = a.obj[oid]
            if COMPOUND in corpo[:200]:
                t = int(a._campo(corpo, "CompoundComponentType") or 0)
                rot = {a._campo(corpo, "InstanceName"), TIPOS.get(t), str(t)}
                dono = re.search(r'<Components ObjectRef="(\d+)"/>', corpo)
                filhos = a._cadeia(dono.group(1)) if dono else []
                if resto and resto[0] in rot:
                    r = achar(filhos, resto[1:])
                    if r:
                        return r
                elif not resto or resto[0] not in rot:
                    r = achar(filhos, resto) if t in (65537, 65539) else None
                    if r:
                        return r
            elif not resto and a._campo(corpo, "MatchName") == efeito:
                for ref in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', corpo):
                    if (a._campo(a.obj[ref][1], "Name") or "").strip() == param:
                        return ref
        return None
    ref = achar(a._cadeia(comps.group(1)), list(caminho))
    if not ref:
        raise KeyError((clipe, caminho, efeito, param))
    tipo, corpo = a.obj[ref]
    novo = re.sub(r"<StartKeyframe>([^,<]*),[^,<]*", lambda m: "<StartKeyframe>%s,%s" % (m.group(1), valor), corpo, 1)
    return xml.replace(corpo, novo, 1)


def clonar_pagina(xml: str, de: int, para: list[int]) -> str:
    """Copia a árvore da página Color (o `CompoundComponent` 65537 e tudo o que ele alcança por ObjectRef) do clipe `de`
    para os clipes `para` (índices na ordem do tempo), com ObjectIDs NOVOS, e a pendura na cadeia de cada um."""
    a = Arvore(xml)
    itens = sorted(((int(a._campo(m.group(2), "Start") or 0), m.group(2)) for m in
                    re.finditer(r'<VideoClipTrackItem ObjectID="(\d+)"[^>]*>(.*?)</VideoClipTrackItem>', xml, re.S)))
    cad = lambda k: re.search(r'<Components ObjectRef="(\d+)"/>', itens[k][1]).group(1)
    raiz = next(o for o in a._cadeia(cad(de)) if COMPOUND in a.obj[o][1][:200])
    alc, fila = [], [raiz]
    while fila:
        o = fila.pop()
        if o in alc or o not in a.obj:
            continue
        alc.append(o)
        fila += re.findall(r'ObjectRef="(\d+)"', a.obj[o][1])
    proximo = max(int(o) for o in a.obj) + 1
    novos = []
    for k in para:
        mapa = {o: str(proximo + i) for i, o in enumerate(alc)}
        proximo += len(alc)
        for o in alc:
            corpo = a.obj[o][1]
            corpo = re.sub(r'ObjectID="(\d+)"', lambda m: 'ObjectID="%s"' % mapa.get(m.group(1), m.group(1)), corpo, 1)
            corpo = re.sub(r'ObjectRef="(\d+)"', lambda m: 'ObjectRef="%s"' % mapa.get(m.group(1), m.group(1)), corpo)
            novos.append(corpo)
        c = cad(k)
        tipo, corpo_c = a.obj[c]
        if "<Components Version" in corpo_c:
            n = len(re.findall(r'<Component Index=', corpo_c))
            corpo_n = corpo_c.replace("</Components>", '\t<Component Index="%d" ObjectRef="%s"/>\n\t\t\t</Components>' % (n, mapa[raiz]), 1)
        else:
            corpo_n = corpo_c.replace("<ComponentChain Version=\"3\">", '<ComponentChain Version="3">\n\t\t\t<Components Version="1">\n\t\t\t\t<Component Index="0" ObjectRef="%s"/>\n\t\t\t</Components>' % mapa[raiz], 1)
        xml = xml.replace(corpo_c, corpo_n, 1)
    fim = xml.rfind("</PremiereData>")
    return xml[:fim] + "\n".join("\t" + n for n in novos) + "\n" + xml[fim:]


# ── o MODELO dos controles da página Color (Color And Contrast), medido na carta B24 — Premiere 27.0.0, 2026-11-20 ───
# v = o valor de VÍDEO de cada canal R'G'B' ((código − 16)/219); "linear" = v² (a gama 2 que o Exposure e o Pivot usam).
W709 = (0.2126, 0.7152, 0.0722)


def exposure(rgb, E):
    """Ganho 2^(E/2) em cada canal (pivô no preto) — = Gain do MC com G = 100·2^(E/2) %. `confirmado` (0,08 código)."""
    return [c * 2 ** (E / 2) for c in rgb]


def contrast(rgb, C, P=-3.0):
    """Potência sobre a LUMINÂNCIA linear (gama 2, Rec.709), o RGB escalado pela mesma razão (a cor fica):
    pivô Pv = √(0,18·2^P) em v; expoente γ = C até 1 e 3C − 2 acima. `confirmado` nos cinzas (≤ 0,1) e nas cores sem
    estouro (0,15–0,29); com C > 1 e pivô baixo os canais passam de 1 e o tratamento disso é `pendente`."""
    g = C if C <= 1 else 3 * C - 2
    pv = (0.18 * 2 ** P) ** 0.5
    lin = [max(c, 0.0) ** 2 for c in rgb]
    y = sum(w * c for w, c in zip(W709, lin))
    if y <= 0:
        return list(rgb)
    yv = y ** 0.5
    k = (pv * (yv / pv) ** g) ** 2 / y
    return [(c * k) ** 0.5 for c in lin]


#: Temperature/Tint = ganho CONSTANTE por canal R'G'B' (o mesmo em todo nível de cinza) — tabela medida (`confirmado`
#: como ganho por canal; a lei entre os pontos `pendente`: interpolar).
TEMPERATURA = {-100: (0.807, 1.003, 1.410), -50: None, -25: (0.915, 1.006, 1.170), 0: (1, 1, 1), 25: (1.045, 0.995, 0.916),
               100: (1.231, 0.954, 0.632)}
TINT = {-100: (0.007, 1.158, 0.827), -25: (0.856, 1.043, 0.956), 0: (1, 1, 1), 25: (1.215, 0.918, 1.071), 100: (1.761, 0.570, 1.291)}


# ── ⭐ O MODELO EXATO (2026-11-20, REA): a ordem e as contas do kernel `ColorAndContrastKernel` (fonte OpenCL que o
# Premiere 27 distribui em `PTX\CL\ColorAndContrast.clz` — ZIP com o texto em XOR 0x2B) + os valores que o HOST manda ao
# kernel (Frida no `cuMemcpyHtoD` do CUDA, a struct de 952 bytes). Conferido na carta B24: 29 casos, 0,09–1,25 código
# de média. Aqui só as FÓRMULAS (a fonte da Adobe não entra no repositório).
#: Temperature/Tint → a matriz `mColorShiftMatrix` (3×3, Rec.709 linear) que o host manda, lida pelo Frida por valor.
MATRIZ_COLOR_SHIFT = {
    ("Temperature", -100): (0.86643, -0.16635, -0.04262, 0.00768, 1.01541, -0.01808, 0.02091, 0.07884, 1.85955),
    ("Temperature", -25): (0.93994, -0.08196, -0.01671, 0.00385, 1.01382, -0.00651, 0.00792, 0.02907, 1.32003),
    ("Temperature", 25): (1.03311, 0.04904, 0.00789, -0.00234, 0.98867, 0.00272, -0.00357, -0.01259, 0.85937),
    ("Temperature", 100): (1.17781, 0.28755, 0.03411, -0.01393, 0.91592, 0.00918, -0.01417, -0.04606, 0.46905),
    ("Tint", -100): (0.67568, -0.65865, -0.0163, 0.03292, 1.28238, 0.01348, -0.00188, -0.0355, 0.72366),
    ("Tint", -25): (0.9147, -0.17323, -0.00429, 0.00866, 1.07427, 0.00354, -0.00049, -0.00934, 0.92732),
    ("Tint", 25): (1.15097, 0.30661, 0.00759, -0.01533, 0.86855, -0.00627, 0.00087, 0.01652, 1.12864),
    ("Tint", 100): (1.65936, 1.33909, 0.03315, -0.06694, 0.42591, -0.0274, 0.00382, 0.07217, 1.56182)}


def do_host(nome: str, valor: float) -> float:
    """O valor da UI/arquivo → o que o kernel recebe (Frida): Contrast e Saturation iguais até 1; acima, 3C − 2 e
    1 + 1,75·(S − 1). Os outros, iguais. Black leva junto rolloff 0,18, offset máx. 0,01 e saturação do black 0,5."""
    if nome == "Contrast" and valor > 1:
        return 3 * valor - 2
    if nome == "Saturation" and valor > 1:
        return 1 + 1.75 * (valor - 1)
    return valor


def color_and_contrast(rgb_v, p: dict, matriz=None):
    """O Color And Contrast GLOBAL num pixel: `rgb_v` = R'G'B' de VÍDEO ((código − 16)/219), `p` = os valores do
    arquivo (Exposure, Contrast, Pivot, Black, Saturation), `matriz` = a de Temperature/Tint (9 números) ou None.
    Linear = v² (a sequência medida; o espaço de trabalho manda — `pendente` em outras). Ordem do kernel: Exposure →
    Contrast/Pivot → Black → matriz de cor → Saturation. Sem corte: quem grava corta cada canal em v ≈ 1,09 (254,75)."""
    import numpy as np
    W = np.array(W709)
    x = np.sign(rgb_v) * np.abs(np.asarray(rgb_v, float)) ** 2
    x = x * 2 ** p.get("Exposure", 0.0)
    c, piv = do_host("Contrast", p.get("Contrast", 1.0)), p.get("Pivot", -3.0)
    if c != 1:
        x = x * max(abs((x @ W) / (0.18 * 2 ** piv)), 1e-8) ** (c - 1)
    b = p.get("Black", 0.0)
    if b:
        mx = float(x.max()); rol = 0.18
        if mx <= 0:
            sl = 0.5
        elif mx <= rol / 2:
            sl = 1 - 0.5 * (mx * 2 / rol) ** 2
        elif mx <= rol:
            sl = 0.5 * (1 - (mx * 2 / rol - 1)) ** 2
        else:
            sl = 0.0
        off = 0.01 * b * sl
        bs = 0.5 * min(max(mx, 0.0) / 0.01, 1.0)
        x = x + off if mx == 0 else bs * x * (off + mx) / mx + (1 - bs) * (off + x)
    if matriz is None and (p.get("Temperature") or p.get("Tint")):
        matriz = matriz_temperatura_tint(p.get("Temperature", 0.0), p.get("Tint", 0.0))
    if matriz is not None:
        x = np.array(matriz, float).reshape(3, 3) @ x
    s = do_host("Saturation", p.get("Saturation", 1.0))
    if s != 1:
        y = np.abs(x) @ W
        o = x * s + (1 - s) * (x.max() + x.min()) / 2
        x = o * np.clip(max(1e-8, y) / max(1e-8, np.abs(o) @ W), 1 / 1.5, 2.5)
    return np.sign(x) * np.abs(x) ** 0.5


# ── Temperature/Tint → a matriz (lei, REA + Frida, 38 matrizes lidas; 2026-11-20) ──────────────────────────────────────
# A matriz é uma ADAPTAÇÃO BRADFORD (Y preservado) do branco D65 para um branco de destino, em Rec.709 linear;
# Temperature e Tint se combinam pelo PRODUTO das duas matrizes (escalas diagonais no mesmo espaço Bradford: comutam).
#   Temperature: o branco anda no LOCUS DA LUZ DO DIA (iluminantes D da CIE), log2(CCT) reta por lado:
#     T ≥ 0: CCT = 6487,6 K · 2^(−0,0083875·T)   T < 0: CCT = 6453,3 K · 2^(−0,022085·T)    (erro ≤ 0,3 / 1,0 código)
#   Tint: o branco anda em RETA no plano CIE 1960 uv a partir do D65, ângulo −17,56° (magenta, Tint > 0) / 162,44°
#     (verde), 0,001155 (Tint > 0) e 0,000681 (Tint < 0) por unidade.
_M709_XYZ = ((0.4124, 0.3576, 0.1805), (0.2126, 0.7152, 0.0722), (0.0193, 0.1192, 0.9505))
_BRADFORD = ((0.8951, 0.2664, -0.1614), (-0.7502, 1.7135, 0.0367), (0.0389, -0.0685, 1.0296))


def _bradford_d65_para(w_xyz):
    import numpy as np
    T, B = np.array(_M709_XYZ), np.array(_BRADFORD)
    d65 = T @ np.ones(3)
    g = (B @ np.asarray(w_xyz, float)) / (B @ d65)
    return np.linalg.inv(T) @ np.linalg.inv(B) @ np.diag(g) @ B @ T


def _branco_temperatura(t: float):
    import numpy as np
    cct = 6487.6 * 2 ** (-0.0083875 * t) if t >= 0 else 6453.3 * 2 ** (-0.022085 * t)
    if cct <= 7000:
        x = -4.6070e9 / cct ** 3 + 2.9678e6 / cct ** 2 + 0.09911e3 / cct + 0.244063
    else:
        x = -2.0064e9 / cct ** 3 + 1.9018e6 / cct ** 2 + 0.24748e3 / cct + 0.237040
    y = -3.0 * x * x + 2.870 * x - 0.275
    return np.array([x / y, 1.0, (1 - x - y) / y])


def _branco_tint(ti: float):
    import math
    import numpy as np
    d65 = np.array(_M709_XYZ) @ np.ones(3)
    den = d65[0] + 15 * d65[1] + 3 * d65[2]
    u, v = 4 * d65[0] / den, 6 * d65[1] / den
    passo = 0.001155 if ti >= 0 else 0.000681
    a = math.radians(-17.56)
    u, v = u + ti * passo * math.cos(a), v + ti * passo * math.sin(a)
    x, y = 3 * u / (2 * u - 8 * v + 4), 2 * v / (2 * u - 8 * v + 4)
    return np.array([x / y, 1.0, (1 - x - y) / y])


def matriz_temperatura_tint(temperatura: float = 0.0, tint: float = 0.0):
    """A `mColorShiftMatrix` que o Premiere 27 manda ao kernel para (Temperature, Tint) — 3×3 em Rec.709 linear."""
    import numpy as np
    m = np.eye(3)
    if temperatura:
        m = _bradford_d65_para(_branco_temperatura(temperatura)) @ m
    if tint:
        m = _bradford_d65_para(_branco_tint(tint)) @ m
    return m
