"""Leva a transcrição das fotos do Effect Editor (`transcricao_paineis.json`, uma por PAINEL distinto) para o
`catalogo.json`, uma entrada por effect_id — as 25 categorias além da Image (2026-10-12).

Painel = o md5 da foto abaixo da linha do título (o título muda, o resto não: os 59 wipes de borda têm UM painel).
Efeito → fotos: `saida/bancadas/avid/efeitos/catalogo_<CAT>.json` (a rodada da bancada); efeito → effect_id:
`LAB_EF_<CAT>.json` (a aplicação, mesma ordem dos clipes). Rodar no `laboratorio-de-midia`:
`py -m lab.bancadas.avid.effect_editor.montar_catalogo`.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os

from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "..", "..", "..", "..", "saida", "bancadas", "avid", "efeitos")


def painel(foto: str) -> str:
    im = Image.open(os.path.join(AQUI, foto)).convert("L")
    return hashlib.md5(im.crop((0, 45, 370, im.size[1] - 50)).tobytes()).hexdigest()[:8]


def main() -> None:
    trans = json.load(open(os.path.join(AQUI, "transcricao_paineis.json"), encoding="utf-8"))
    cat_path = os.path.join(AQUI, "catalogo.json")
    catalogo = json.load(open(cat_path, encoding="utf-8"))
    faltam, novos = [], 0
    for f in sorted(glob.glob(os.path.join(SAIDA, "catalogo_*.json"))):
        cat = os.path.basename(f)[len("catalogo_"):-len(".json")]
        if cat.startswith("IMAGE"):
            continue
        rodada = json.load(open(f, encoding="utf-8"))
        aplicados = json.load(open(os.path.join(SAIDA, f"LAB_EF_{cat}.json"), encoding="utf-8"))["clipes"]
        for item in rodada["clipes"]:
            ap = aplicados[item["clipe"]]
            fotos = [os.path.basename(p) for p in item.get("fotos", [])]
            chave = "+".join(painel(p) for p in fotos)
            if chave not in trans:
                faltam.append((cat, item["nome"], chave))
                continue
            t = trans[chave]
            entrada = {"nome": item["nome"], "categoria": ap.get("_EFFECT_PLUGIN_CLASS"), "tipo": ap.get("_EFFECT_PLUGIN_TYPE"),
                       "fotos": fotos, "painel": chave, "grupos": t["grupos"]}
            if t.get("nota"):
                entrada["nota"] = t["nota"]
            catalogo[ap["effect_id"]] = entrada
            novos += 1
    json.dump(catalogo, open(cat_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{novos} efeitos gravados; sem transcrição: {faltam}")


if __name__ == "__main__":
    main()
