"""BL08 pelo CÓDIGO DO PRODUTO (Conformar `motor/baselight/`): decisão do casador → `entrega.reescrever` → `bl-conform` →
`bl-shots` → `conferencia.conferir` (arquivo + 1º e último quadro visível).

    <conformar>/.venv/bin/python -m lab.bancadas.baselight_produto [scene_extra …]     # a montagem do Premiere
    <conformar>/.venv/bin/python -m lab.bancadas.baselight_produto mc                  # a do MC: xmeml lido do AAF

O lado do MC (2026-11-22): `baselight/do_aaf.escrever` gera o xmeml da leitura do AAF (com os dailies), e daí em diante é
a MESMA entrega do Premiere, com as decisões do casador do AAF (`papel-mc.json`).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unicodedata

from ..casamento import SAIDA
from .avid_baselight import CONFORMAR, RAIZ
from .baselight_casamento import BL, JOB, TRAB, conformar

XML_PR = os.path.join(RAIZ, "saida", "bancadas", "premiere_casamento", "BL08_CASAMENTO.xml")
PAPEL = os.path.join(RAIZ, "saida", "bancadas", "casamento_papel", "papel-nfc.json")


def xml_do_mc() -> str:
    """O xmeml da montagem do MC, lido do AAF (`baselight/do_aaf`)."""
    sys.path.insert(0, os.path.join(CONFORMAR, "motor"))
    from .avid_baselight import _caminhos
    _caminhos()
    from aaf.parser import parse_aaf
    from baselight import do_aaf
    from media.matcher import _daily_do_segmento
    from prproj.originais import sondar
    from .baselight_casamento_mc import AAF
    saida = os.path.join(TRAB, "BL08_MC_DO_AAF.xml")
    r = do_aaf.escrever(parse_aaf(AAF), saida, sondar, _daily_do_segmento)
    print("xmeml do AAF:", r, flush=True)
    return saida


def main(extras: list[str], xml: str = XML_PR, papel: str = PAPEL, scene: str = "BL08_PRODUTO") -> dict:
    sys.path.insert(0, os.path.join(CONFORMAR, "motor"))
    from baselight import conferencia as C, entrega as E
    from prproj.originais import sondar
    with open(papel, encoding="utf-8") as fh:
        linhas = json.load(fh)["linhas"]
    decisao = {}
    for x in linhas:
        daily = os.path.join(SAIDA, x["daily"])
        if x["original"]:
            o = os.path.join(SAIDA, x["original"])
            decisao[daily] = E.descrever(o, sondar(E.como_o_disco_lista(o)), fps_sequencia=24000 / 1001)
        else:
            decisao[daily] = None
    saida = os.path.join(TRAB, scene + ".xml")
    feitos = E.reescrever(xml, saida, decisao, os.path.join(SAIDA, "OFFLINE"))
    esperados = E.esperado(saida)
    log = conformar(scene, ["--multiples", "--Filter", "Filename"], xml=saida)
    print(scene, "|", log.splitlines()[-1] if log else "", flush=True)
    out = {}
    for sc in [scene, *extras]:
        r = subprocess.run([os.path.join(BL, "bl-shots"), f"localhost:{JOB}:{sc}", "-inputrange", "-outputrange"],
                           capture_output=True, text=True, timeout=120)
        res = C.conferir(C.ler_bl_shots(r.stdout), esperados)
        trocas = C.linhas_de_troca(res) if sc == scene else []
        if trocas:                       # a correção do produto: só o plano errado, pela faixa na fonte
            t = subprocess.run([os.path.join(BL, "bl-shots"), f"localhost:{JOB}:{sc}", "-replace", "-undomessage",
                                "Ciclo Assist: casamento"], input="\n".join(trocas) + "\n", capture_output=True,
                               text=True, timeout=300)
            print(f"   troca ({len(trocas)}):", (t.stdout + t.stderr).strip().splitlines()[-2:], flush=True)
            r = subprocess.run([os.path.join(BL, "bl-shots"), f"localhost:{JOB}:{sc}", "-inputrange", "-outputrange"],
                               capture_output=True, text=True, timeout=120)
            res = C.conferir(C.ler_bl_shots(r.stdout), esperados)
        cont = {}
        for x in res:
            cont[x["estado"]] = cont.get(x["estado"], 0) + 1
        print(f"== {sc}: {cont}")
        for x in res:
            if x["estado"] != "ok":
                print(f"   q{x['inicio']:4} {x['estado']:20} {C.motivo(x)[:150]}")
        out[sc] = res
    with open(os.path.join(TRAB, ("produto" if scene == "BL08_PRODUTO" else scene.lower()) + ".json"), "w",
              encoding="utf-8") as fh:
        json.dump({"reescrito": feitos, "resultado": out}, fh, indent=1, ensure_ascii=False)
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["mc"]:
        from .baselight_casamento_mc import PAPEL_MC
        main(sys.argv[2:], xml=xml_do_mc(), papel=PAPEL_MC, scene="BL08_MC_PRODUTO")
    else:
        main(sys.argv[1:])
