"""B24_COR_MC no Premiere: DUAS Lumetris no mesmo clipe — a ordem do ARQUIVO é a ordem do RENDER? (autor, 2026-11-20)

No par ProcAmp + Lumetri o arquivo diz "Lumetri → ProcAmp" e o pixel é Sat → curva (`cor_b24_premiere_ordem.py`). Aqui
duas Lumetris, cada uma com uma curva RGB (blocos R/G/B do param 39) que NÃO comuta com a outra:
  A = afunda os meios (0,0) (0,5, 0,22) (1,1)        B = levanta o preto e baixa o branco (0, 0,2) (1, 0,85)
Clipes: neutro · só A · só B (validam o modelo da curva: spline natural em u = (código − 16)/219, plana fora) ·
[A no índice 0, B no 1] · [B no 0, A no 1]. Previsão: compor na ordem do arquivo (0 depois 1) e na inversa.

    python lab/cor_b24_premiere_duas_lumetri.py "LAB COR PREMIERE 2 LUMETRI"   (Premiere aberto, ponte do laboratório)
"""
import base64
import json
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from lab import cor_b24_modelo as M
from lab.bancadas import premiere_cor_mc as pc
from lab.cor_curva import natural, linear

A = [(0.0, 0.0), (0.5, 0.22), (1.0, 1.0)]
B = [(0.0, 0.2), (1.0, 0.85)]
L = ["Lumetri Color", {}]
#: (nome, nº de Lumetris, curvas por índice da cadeia NO ARQUIVO)
CASOS = [("neutro", 0, []), ("só A", 1, [A]), ("só B", 1, [B]), ("arquivo A,B", 2, [A, B]), ("arquivo B,A", 2, [B, A])]
BLOCOS = (1, 2, 3)


def lumetris_por_clipe(xml: str) -> list[list[str]]:
    """Os ObjectID das Lumetris de cada clipe da V1, NA ORDEM DA CADEIA do arquivo; clipes na ordem do tempo."""
    out = []
    for m in re.finditer(r'<VideoClipTrackItem ObjectID="\d+"[^>]*>(.*?)</VideoClipTrackItem>', xml, re.S):
        ini = re.search(r"<Start>(-?\d+)</Start>", m.group(1))
        comps = re.search(r'<Components ObjectRef="(\d+)"/>', m.group(1))
        cad = pc._obj(xml, comps.group(1)) if comps else None
        lums = [ref for ref in re.findall(r'<Component Index="\d+" ObjectRef="(\d+)"/>', cad.group(0) if cad else "")
                if "<MatchName>AE.ADBE Lumetri</MatchName>" in (pc._obj(xml, ref).group(0) if pc._obj(xml, ref) else "")]
        out.append((int(ini.group(1)) if ini else 0, lums))
    return [x for _, x in sorted(out)]


def escrever(proj: str) -> list[int]:
    """A curva de cada Lumetri (pelo índice na cadeia) nos blocos R/G/B. Desfaz a deduplicação antes (como a bancada)."""
    xml = pc.ler_xml(proj)
    conteudo = dict(re.findall(r'BinaryHash="([^"]+)">([^<]+)<', xml))
    xml = re.sub(r'<(\w+) Encoding="base64" BinaryHash="([^"]+)"/>',
                 lambda m: '<%s Encoding="base64" BinaryHash="%s">%s</%s>' % (m.group(1), m.group(2), conteudo[m.group(2)], m.group(1))
                 if m.group(2) in conteudo else m.group(0), xml)
    por_clipe = lumetris_por_clipe(xml)
    contagem = []
    for (_, n, curvas), lums in zip(CASOS, por_clipe):
        contagem.append(len(lums))
        assert len(lums) == n, f"esperava {n} Lumetris, achei {len(lums)}"
        for lum, pts in zip(lums, curvas):
            c = pc._obj(xml, lum)
            for ref in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', c.group(0)):
                m = pc._obj(xml, ref)
                if not m or "<ParameterID>39</ParameterID>" not in m.group(0):
                    continue
                v = re.search(r'<StartKeyframeValue Encoding="base64" BinaryHash="([^"]+)">([^<]*)</StartKeyframeValue>', m.group(0))
                velho = base64.b64decode(v.group(2).strip())
                blob = bytearray(velho)
                for bl in BLOCOS:
                    blob[bl * 520:(bl + 1) * 520] = pc._bloco(pts, struct.unpack("<I", velho[bl * 520:bl * 520 + 4])[0])
                blob = bytes(blob)
                novo = '<StartKeyframeValue Encoding="base64" BinaryHash="%s">%s</StartKeyframeValue>' % (
                    pc._hash(len(blob)), base64.b64encode(blob).decode())
                corpo = m.group(0)[:v.start()] + novo + m.group(0)[v.end():]
                xml = xml[:m.start()] + corpo + xml[m.end():]
    pc.gravar_xml(proj, xml)
    return contagem


def curva_fn(pts):
    f = natural(pts) if len(pts) > 2 else linear(pts)
    return lambda c: 16 + 219 * float(f(np.clip((c - 16) / 219, 0, 1)))


def prever(curvas, y, cb, cr):
    rgb = M.para_rgb(y, cb, cr)
    for pts in curvas:
        f = curva_fn(pts)
        rgb = [f(c) for c in rgb]
    return M.de_rgb(*rgb)


def erro(base, m, curvas, areas):
    dentro = []
    for a in areas:
        q = prever(curvas, *base[a])
        if all(15.5 <= c <= 235.5 for c in M.para_rgb(*base[a])):
            dentro.append(max(abs(x - y) for x, y in zip([M.cortar(c) for c in q], m[a])))
    return [round(float(np.mean(dentro)), 2), round(float(np.max(dentro)), 2), len(dentro)]


def main(nome: str) -> None:
    v = pc.p.executar("app.version")
    pc.TRABALHO = os.path.join(pc.RAIZ, "saida", "bancadas", f"premiere-{v}", "B24_COR_MC")
    ano = {"27": "2027", "26": "2026", "25": "2025", "23": "2023"}.get(v.split(".")[0], "2026")
    print("Premiere", v, "→", pc.TRABALHO, flush=True)
    try:
        pc.fechar_projeto()
    except Exception:  # noqa: BLE001
        pass
    r = pc.montar_efeitos(nome, [[L] * n for _, n, _ in CASOS])
    proj = r["projeto"]
    pc.fechar_projeto()
    print("Lumetris por clipe:", escrever(proj), flush=True)
    pc.abrir_projeto(proj)
    arq = pc.exportar(proj, ano)
    med = pc.medir(arq, len(CASOS))
    base = med[0]
    areas = [a for a in base if not a.startswith("_")]
    resumo = []
    for (nome_c, n, curvas), m in list(zip(CASOS, med))[1:]:
        res = {"caso": nome_c, "na ordem do arquivo (0→1)": erro(base, m, curvas, areas)}
        if n == 2:
            res["na ordem INVERSA (1→0)"] = erro(base, m, list(reversed(curvas)), areas)
        resumo.append(res)
        print(json.dumps(res, ensure_ascii=False), flush=True)
    json.dump({"casos": [c[0] for c in CASOS], "medidas": med, "resumo": resumo},
              open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "LAB COR PREMIERE 2 LUMETRI")
