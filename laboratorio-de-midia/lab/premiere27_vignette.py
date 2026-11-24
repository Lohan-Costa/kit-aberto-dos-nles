"""A página Color do Premiere 2027: o módulo VIGNETTE (`AE.Impact_Vignette_FX`, plugin FilmImpact) pelo pixel — o perfil
da vinheta num quadro BRANCO, para traduzi-la por uma Power Window circular no Resolve (pedido do autor, 2026-11-20).

Do `LAB COR 27 STYLE C`: a Style da sequência fica SÓ com a Vignette (padrão: Vignette 100, Width/Height 80, Scale 100,
Roundness 100, Feather 50, Softness 20, Chromatic Aberration 20, Opacity/Master 100); sai a "Sequence Adjust 1". O
quadro branco (o mesmo do Resolve, `resolve_janela.BRANCO`) entra por cima do 1º clipe da V1 pela ponte.

    python lab/premiere27_vignette.py      (Premiere 2027 aberto, ponte do laboratório)
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from lab.bancadas import premiere_cor_mc as pc
from lab.bancadas import premiere_pagina_cor as pg
from lab.premiere27_film_color import _tirar_da_cadeia
from lab.premiere27_ordem_camadas import PASTA
from lab.resolve_janela import BRANCO, medir_mascara, quadro

ORIGEM = os.path.join(PASTA, "LAB COR 27 STYLE C.prproj")
DESTINO = os.path.join(PASTA, "LAB COR 27 VIGNETTE PIXEL.prproj")


def gerar(valores: dict | None = None) -> str:
    """O projeto com só a Vignette na Style da sequência; `valores` = {nome do param: valor} escritos nela."""
    xml = pc.ler_xml(ORIGEM)
    a = pg.Arvore(xml)
    achar = lambda txt: next(o for o, (_, c) in a.obj.items() if txt in c)
    estilo = achar("<InstanceName>Sequence Style 1</InstanceName>")
    cad = re.search(r'<Components ObjectRef="(\d+)"/>', a.obj[estilo][1]).group(1)
    vinheta = next(f for f in a._cadeia(cad) if "AE.Impact_Vignette_FX" in a.obj[f][1])
    corpo = a.obj[cad][1]
    novo = re.sub(r'(<Components Version="1">).*?(</Components>)',
                  lambda m: m.group(1) + '\n\t\t\t\t<Component Index="0" ObjectRef="%s"/>\n\t\t\t' % vinheta
                  + m.group(2), corpo, count=1, flags=re.S)
    xml = xml.replace(corpo, novo, 1)
    cont = next(o for o, (_, c) in a.obj.items() if "<CompoundComponentType>65543" in c)
    cad_cont = re.search(r'<Components ObjectRef="(\d+)"/>', a.obj[cont][1]).group(1)
    xml = _tirar_da_cadeia(xml, a, cad_cont, achar("<InstanceName>Sequence Adjust 1</InstanceName>"))
    for nome, v in (valores or {}).items():
        for ref in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', a.obj[vinheta][1]):
            c = a.obj[ref][1]
            if (a._campo(c, "Name") or "").strip() == nome:
                xml = xml.replace(c, re.sub(r"<StartKeyframe>([^,<]*),[^,<]*",
                                            lambda m: "<StartKeyframe>%s,%s" % (m.group(1), v), c, 1), 1)
                break
        else:
            raise KeyError(nome)
    destino = DESTINO if not valores else DESTINO.replace(".prproj", " " + " ".join(
        f"{k}{v}" for k, v in valores.items()) + ".prproj")
    pc.gravar_xml(destino, xml)
    return destino


_BRANCO_NA_V1 = r"""(function(arq){
  var s = null;
  for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].name == "COR") s = app.project.sequences[i];
  app.project.openSequence(s.sequenceID);
  app.project.importFiles([arq], true, app.project.rootItem, false);
  var it = null, r = app.project.rootItem;
  for (var j = 0; j < r.children.numItems; j++) if (r.children[j].name.indexOf("BRANCO_1080") == 0) it = r.children[j];
  var t = new Time(); t.seconds = 0;
  s.videoTracks[0].overwriteClip(it, t.seconds);
  app.project.save();
  return s.videoTracks[0].clips[0].name; })(%s)"""


def medir_projeto(destino: str) -> dict:
    pc.fechar_projeto()
    pc.abrir_projeto(destino)
    print("V1[0]:", pc.p.executar(_BRANCO_NA_V1 % json.dumps(BRANCO), timeout=120), flush=True)
    arq = pc.exportar(destino, "2027")
    m = quadro(arq, 6)
    out = medir_mascara(m.clip(0, None) / max(m.max(), 1e-9))
    out["perfil_h"] = [round(float(x), 4) for x in m[540, ::8]]          # a linha do meio, de 8 em 8 px
    out["perfil_v"] = [round(float(x), 4) for x in m[::8, 960]]
    out["canto"] = [round(float(m[4, 4]), 4), round(float(m[540, 4]), 4), round(float(m[4, 960]), 4)]
    out["max_abs"] = round(float(m.max()), 4)
    np.save(arq.replace(".mov", "_q6.npy"), m)
    return out


def main() -> None:
    casos = [None] + [json.loads(a) for a in sys.argv[1:]]
    for v in casos:
        destino = gerar(v)
        res = medir_projeto(destino)
        print(json.dumps({"valores": v, **{k: res[k] for k in res if not k.startswith("perfil")}}, ensure_ascii=False),
              flush=True)
        json.dump(res, open(destino.replace(".prproj", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
