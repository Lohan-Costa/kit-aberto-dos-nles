"""BL08, o lado do MC: o casador do Conformar para AAF (`media/matcher.match_segments`) no papel, o AAF do caminho B
(os Locators reescritos pelo `aaf/writer.relink_aaf` do Conformar) e o caminho C (`baselight_casamento.caminho_c`).

    <conformar>/.venv/bin/python -m lab.bancadas.baselight_casamento_mc papel     # decisões → papel-mc.json + AAF B
    python3 -m lab.bancadas.baselight_casamento_mc a|c                            # (python do sistema) Baselight

As regras do autor moram DENTRO do casador desde 2026-11-22: empate sai sem caminho (OFFLINE com marker) a não ser que
a imagem do daily confirme um candidato; cópias idênticas valem como uma (P9); o reel do daily é critério (P4).
"""
from __future__ import annotations

import filecmp
import json
import os
import sys
import unicodedata

from ..casamento import SAIDA
from .avid_baselight import RAIZ

#: o AAF da montagem v3 (20 planos, com P11/P12); a 1ª (18 planos) é `BL08_CASAMENTO.aaf`
AAF = os.path.join(RAIZ, "saida", "bancadas", "avid_casamento", "aaf_do_mc",
                   os.environ.get("BL08_AAF", "BL08_CASAMENTO_3.aaf"))
TRAB = os.path.join(RAIZ, "saida", "bancadas", "baselight_casamento")
AAF_B = os.path.join(TRAB, "BL08_CASAMENTO_MC_B.aaf")
PAPEL_MC = os.path.join(RAIZ, "saida", "bancadas", "casamento_papel", "papel-mc.json")
OFFLINE = os.path.join(SAIDA, "OFFLINE")


def _nfc(s):
    return unicodedata.normalize("NFC", s or "")


def papel() -> dict:
    from .avid_baselight import _caminhos
    _caminhos()
    from aaf.parser import parse_aaf
    from aaf.writer import build_url_map, relink_aaf
    from media.indexer import index_folder
    from media.matcher import match_segments
    p = parse_aaf(AAF)
    r = match_segments(p["segments"], index_folder([os.path.join(SAIDA, "ORIGINAIS")]))
    linhas, por = [], {x["segment_index"]: x for x in r["results"]}
    for i, s in enumerate(p["segments"]):
        if s.get("is_audio") or s.get("is_gap") or i not in por:
            continue
        x = por[i]
        lp = (s.get("media_ref") or {}).get("local_path") or ""
        daily = _nfc(lp.split("BL08_CASAMENTO/", 1)[-1])
        cands = [c.get("path") if isinstance(c, dict) else c for c in (x.get("candidates") or [])]
        estado = ("ambiguo" if x.get("ambiguous") else "original" if x.get("matched_path") else "sem_original")
        if x.get("matched_path") and x.get("imagem"):
            estado = "confirmado_pela_imagem"
        if x.get("match_method") == "reel":
            estado = "original_pelo_reel"
        mesmos = [c for c in cands if c and x.get("matched_path")
                  and os.path.basename(c) == os.path.basename(x["matched_path"])]
        if len(set(mesmos)) > 1 and all(filecmp.cmp(mesmos[0], c, shallow=False) for c in mesmos[1:]):
            estado = "copias_identicas"
        if not x.get("matched_path"):
            x["matched_path"] = os.path.join(OFFLINE, "OFFLINE_CICLO__" + os.path.basename(lp))
            x["match_method"] = "manual"
            original = None
        else:
            original = os.path.relpath(_nfc(x["matched_path"]), _nfc(SAIDA))
        linhas.append({"daily": daily, "original": original, "estado": estado, "metodo": x.get("match_method"),
                       "candidatos": sorted({os.path.relpath(_nfc(c), _nfc(SAIDA)) for c in cands if c
                                             and os.path.basename(c).lower().split(".")[0] ==
                                             os.path.basename(lp).lower().split(".")[0]})})
    url_map = build_url_map(p["segments"], list(por.values()))
    rel = relink_aaf(AAF, AAF_B, url_map)
    certo = {}
    with open(os.path.join(RAIZ, "saida", "bancadas", "premiere_casamento", "montagem.json"), encoding="utf-8") as fh:
        for e in json.load(fh)["eventos"]:
            certo[_nfc(e["daily"])] = e["original_certo"]
    placar = {"certo": 0, "alerta": 0, "errado": 0}
    vistos = set()
    for l in linhas:
        if l["daily"] in vistos:
            continue
        vistos.add(l["daily"])
        esperado = _nfc(certo.get(l["daily"]))
        # sequência de imagens (P10): a verdade diz `A003C001.%07d.dpx`; o casador devolve um quadro dela
        mesma_seq = ("%0" in esperado and l["original"]
                     and os.path.dirname(l["original"]) == os.path.dirname(esperado))
        ok = l["original"] == esperado or mesma_seq or (l["estado"] == "copias_identicas" and l["original"])
        nota = "certo" if ok else ("alerta" if not l["original"] else "errado")
        l["nota"] = nota
        placar[nota] += 1
        print(f"  {nota:7} {l['daily']:42} → {l['original'] or '-'}  [{l['estado']}]")
    os.makedirs(os.path.dirname(PAPEL_MC), exist_ok=True)
    with open(PAPEL_MC, "w", encoding="utf-8") as fh:
        json.dump({"placar": placar, "linhas": linhas, "religar": {k: rel[k] for k in ("updated_count", "skipped_count", "error_count")}},
                  fh, indent=1, ensure_ascii=False)
    print("placar (dailies distintos):", placar, "| religar:", {k: rel[k] for k in ("updated_count", "skipped_count", "error_count")})
    return placar


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "papel":
        papel()
    elif sys.argv[1] == "c":
        from . import baselight_casamento as B
        B.caminho_c(edl=AAF_B, papel=PAPEL_MC, scene="BL08_MC_C")
