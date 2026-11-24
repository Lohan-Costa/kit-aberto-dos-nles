"""A página Color do Premiere 2027: o módulo FILM COLOR pelo pixel (pedido do autor, 2026-11-20).

O Film Color (`AE.ADBE Color Film`) não processa pixel: o kernel `ColorFilmKernel` (fonte em `PTX\\CL\\ColorFilm.clz`)
MODIFICA uma LUT 3D — a do estoque Negativo_Print, que é a `.cube` do próprio Premiere em `LUTs\\FilmEmulation`
(capturada pelo Frida no `cuMemcpyHtoDAsync_v2`: idêntica byte a byte à `Fuji ETERNA 250_Fuji 3510.cube` com
Negative 0 / Print 0). Aqui: o Film Color PADRÃO sozinho na Style da sequência (sai a Vignette da Style e a
"Sequence Adjust 1"), contra as hipóteses de como a LUT é aplicada ao sinal.

    python lab/premiere27_film_color.py [<estoque.cube>]     (Premiere 2027 aberto, ponte do laboratório)
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from lab import cor_b24_modelo as M
from lab.bancadas import premiere_cor_mc as pc
from lab.bancadas import premiere_pagina_cor as pg
from lab.premiere27_ordem_camadas import PASTA

ORIGEM = os.path.join(PASTA, "LAB COR 27 STYLE C.prproj")
DESTINO = os.path.join(PASTA, "LAB COR 27 FILM PIXEL.prproj")
BASE = os.path.join(PASTA, "LAB COR 27 CAMADAS_medidas.json")
ESTOQUES = r"C:\Program Files\Adobe\Adobe Premiere Pro 2027\LUTs\FilmEmulation"
CUBE = os.path.join(ESTOQUES, "Fuji ETERNA 250_Fuji 3510.cube")


def ler_cube(caminho: str) -> np.ndarray:
    """→ tabela [b][g][r][3] (o .cube anda com o R mais rápido)."""
    n, v = 0, []
    for linha in open(caminho, encoding="utf-8", errors="replace"):
        p = linha.split()
        if p[:1] == ["LUT_3D_SIZE"]:
            n = int(p[1])
        elif len(p) == 3 and p[0][:1] in "0123456789-.":
            v.append([float(x) for x in p])
    return np.array(v).reshape(n, n, n, 3)


def trilinear(t: np.ndarray, rgb) -> np.ndarray:
    n = t.shape[0]
    x = np.clip(np.asarray(rgb, float), 0, 1) * (n - 1)
    i = np.minimum(x.astype(int), n - 2)
    f = x - i
    out = np.zeros(3)
    for dr in (0, 1):
        for dg in (0, 1):
            for db in (0, 1):
                w = (f[0] if dr else 1 - f[0]) * (f[1] if dg else 1 - f[1]) * (f[2] if db else 1 - f[2])
                out += w * t[i[2] + db, i[1] + dg, i[0] + dr]
    return out


def tetraedrica(t: np.ndarray, rgb) -> np.ndarray:
    n = t.shape[0]
    x = np.clip(np.asarray(rgb, float), 0, 1) * (n - 1)
    i = np.minimum(x.astype(int), n - 2)
    fr, fg, fb = x - i
    c = lambda r, g, b: t[i[2] + b, i[1] + g, i[0] + r]
    c000, c111 = c(0, 0, 0), c(1, 1, 1)
    if fr > fg:
        if fg > fb:
            return c000 + fr * (c(1, 0, 0) - c000) + fg * (c(1, 1, 0) - c(1, 0, 0)) + fb * (c111 - c(1, 1, 0))
        if fr > fb:
            return c000 + fr * (c(1, 0, 0) - c000) + fb * (c(1, 0, 1) - c(1, 0, 0)) + fg * (c111 - c(1, 0, 1))
        return c000 + fb * (c(0, 0, 1) - c000) + fr * (c(1, 0, 1) - c(0, 0, 1)) + fg * (c111 - c(1, 0, 1))
    if fb > fg:
        return c000 + fb * (c(0, 0, 1) - c000) + fg * (c(0, 1, 1) - c(0, 0, 1)) + fr * (c111 - c(0, 1, 1))
    if fb > fr:
        return c000 + fg * (c(0, 1, 0) - c000) + fb * (c(0, 1, 1) - c(0, 1, 0)) + fr * (c111 - c(0, 1, 1))
    return c000 + fg * (c(0, 1, 0) - c000) + fr * (c(1, 1, 0) - c(0, 1, 0)) + fb * (c111 - c(1, 1, 0))


def _tirar_da_cadeia(xml: str, a: "pg.Arvore", dono: str, ref: str) -> str:
    """Tira o componente `ref` da cadeia `dono` e renumera os índices."""
    corpo = a.obj[dono][1]
    refs = [r for r in a._cadeia(dono) if r != ref]
    novo = re.sub(r'(<Components Version="1">).*?(</Components>)',
                  lambda m: m.group(1) + "".join('\n\t\t\t\t<Component Index="%d" ObjectRef="%s"/>' % (i, r)
                                                 for i, r in enumerate(refs)) + "\n\t\t\t" + m.group(2),
                  corpo, count=1, flags=re.S)
    return xml.replace(corpo, novo, 1)


def gerar() -> None:
    xml = pc.ler_xml(ORIGEM)
    a = pg.Arvore(xml)
    achar = lambda txt: next(o for o, (_, c) in a.obj.items() if txt in c)
    estilo = achar("<InstanceName>Sequence Style 1</InstanceName>")
    cad_estilo = re.search(r'<Components ObjectRef="(\d+)"/>', a.obj[estilo][1]).group(1)
    vinheta = next(f for f in a._cadeia(cad_estilo) if "AE.Impact_Vignette_FX" in a.obj[f][1])
    xml = _tirar_da_cadeia(xml, a, cad_estilo, vinheta)
    ajuste = achar("<InstanceName>Sequence Adjust 1</InstanceName>")
    cont = next(o for o, (_, c) in a.obj.items() if "<CompoundComponentType>65543" in c)
    cad_cont = re.search(r'<Components ObjectRef="(\d+)"/>', a.obj[cont][1]).group(1)
    xml = _tirar_da_cadeia(xml, a, cad_cont, ajuste)
    pc.gravar_xml(DESTINO, xml)
    b = pg.Arvore(xml)
    print("sequência:", [n.get("efeito") or n.get("nome") for n in b.no(cont)["filhos"]],
          "· Style:", [n.get("efeito") or n.get("compound") for n in b.no(estilo)["filhos"]], flush=True)


def main() -> None:
    cube = sys.argv[1] if len(sys.argv) > 1 else CUBE
    gerar()
    print("Premiere", pc.p.executar("app.version"), flush=True)
    pc.fechar_projeto()
    pc.abrir_projeto(DESTINO)
    arq = pc.exportar(DESTINO, "2027")
    med = pc.medir(arq, 1)[0]
    base = json.load(open(BASE, encoding="utf-8"))["medidas"][0]
    t = ler_cube(cube)
    lin = lambda v: np.where(v < 0.081, v / 4.5, ((v + 0.099) / 1.099) ** (1 / 0.45))
    hipoteses = {
        "cube no sinal (trilinear)": lambda v: trilinear(t, v),
        "cube no sinal (tetraédrica)": lambda v: tetraedrica(t, v),
        "LUT linear gravada (709 inversa)": lambda v: lin(trilinear(t, v)),
        "nada": lambda v: np.asarray(v),
    }
    resumo = {}
    for nome, f in hipoteses.items():
        erros = []
        for x in (k for k in base if not k.startswith("_")):
            v = [(c - 16) / 219 for c in M.para_rgb(*base[x])]
            q = M.de_rgb(*[16 + 219 * float(c) for c in f(np.array(v))])
            if all(16 <= c <= 235 for c in M.para_rgb(*q)):
                erros.append(max(abs(a - b) for a, b in zip([M.cortar(c) for c in q], med[x])))
        resumo[nome] = [round(float(np.mean(erros)), 2), round(float(np.max(erros)), 2), len(erros)]
        print(nome, resumo[nome], flush=True)
    json.dump({"cube": cube, "medida": med, "resumo": resumo},
              open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
