"""A ORDEM dos efeitos que o Conformar leva ao FUSION (desfoque, Basic 3D) — o Premiere aplica do último índice do
arquivo para o primeiro também neles? (autor, 2026-11-20; a regra foi medida na cor: `cor_b24_premiere_duas_lumetri.py`)

Gaussian Blur (Blurriness 40) + Basic 3D (Swivel 65°) na carta B24, nas duas ordens de chamada do QE; a cadeia lida do
arquivo salvo. O Swivel comprime a imagem na horizontal (cos 65° ≈ 0,42): desfocar ANTES de girar comprime o desfoque
junto (borda vertical mais NÍTIDA); girar antes e desfocar depois deixa o desfoque inteiro. Métrica: o percentil 99 do
|gradiente horizontal| da luma no quadro do meio de cada cópia (maior = mais nítido). Controles: só o Blur, só o Basic 3D.

    python lab/premiere_ordem_fusion.py "LAB ORDEM FUSION"      (Premiere aberto, ponte do laboratório)
"""
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from lab.bancadas import premiere_cor_mc as pc

BLUR = ["Gaussian Blur (Legacy)", {"Blurriness": 40}]
B3D = ["Basic 3D", {"Swivel": 65}]
CASOS = [("neutro", []), ("só blur", [BLUR]), ("só basic3d", [B3D]),
         ("chamada blur,b3d", [BLUR, B3D]), ("chamada b3d,blur", [B3D, BLUR])]
ALVOS = ("AE.ADBE Gaussian Blur 2", "AE.ADBE Basic 3D")


def cadeias(proj: str) -> list[list[str]]:
    xml = pc.ler_xml(proj)
    out = []
    for m in re.finditer(r'<VideoClipTrackItem ObjectID="\d+"[^>]*>(.*?)</VideoClipTrackItem>', xml, re.S):
        ini = re.search(r"<Start>(-?\d+)</Start>", m.group(1))
        comps = re.search(r'<Components ObjectRef="(\d+)"/>', m.group(1))
        cad = pc._obj(xml, comps.group(1)) if comps else None
        nomes = []
        for ref in re.findall(r'<Component Index="\d+" ObjectRef="(\d+)"/>', cad.group(0) if cad else ""):
            c = pc._obj(xml, ref)
            mn = re.search(r"<MatchName>([^<]+)</MatchName>", c.group(0)) if c else None
            if mn and not mn.group(1).endswith(("Motion", "Opacity")):
                nomes.append(mn.group(1))
        out.append((int(ini.group(1)) if ini else 0, nomes))
    return [n for _, n in sorted(out)]


def luma(arq: str, quadro: int) -> np.ndarray:
    cru = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-vf", f"select=eq(n\\,{quadro})", "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(cru, np.uint8).reshape(1080, 1920).astype(float)


def nitidez(img: np.ndarray) -> float:
    g = np.abs(np.diff(img[200:880, :], axis=1))
    g = g[g > 2]                                   # tira o liso (e o preto em volta da imagem girada)
    return round(float(np.percentile(g, 99)), 2) if g.size else 0.0


def main(nome: str) -> None:
    v = pc.p.executar("app.version")
    pc.TRABALHO = os.path.join(pc.RAIZ, "saida", "bancadas", f"premiere-{v}", "ORDEM_FUSION")
    ano = {"27": "2027", "26": "2026", "25": "2025", "23": "2023"}.get(v.split(".")[0], "2026")
    print("Premiere", v, "→", pc.TRABALHO, flush=True)
    try:
        pc.fechar_projeto()
    except Exception:  # noqa: BLE001
        pass
    r = pc.montar_efeitos(nome, [c[1] for c in CASOS])
    print("valores:", json.dumps(r["resposta"], ensure_ascii=False)[:800], flush=True)
    proj = r["projeto"]
    cads = cadeias(proj)
    print("cadeias no arquivo:", cads, flush=True)
    arq = pc.exportar(proj, ano)
    res = []
    for k, ((nome_c, _), cad) in enumerate(zip(CASOS, cads)):
        n = nitidez(luma(arq, k * pc.QUADROS + pc.MEIO))
        res.append({"caso": nome_c, "arquivo": [c.replace("AE.ADBE ", "") for c in cad], "nitidez p99": n})
        print(json.dumps(res[-1], ensure_ascii=False), flush=True)
    json.dump(res, open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "LAB ORDEM FUSION")
