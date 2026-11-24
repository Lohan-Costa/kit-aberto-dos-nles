"""BL09, o render da cor de OUTRA TAXA voltando PELO MEDIA COMPOSER VIVO (Ciclo Assist, 2026-11-23): os renders de
`outra_taxa.py` (A002C001 de 29,97 DF e B001C005 de 59,94, renderizados pelo Baselight a 23,976 com o TC de fonte no
contador cru do `tmcd`, base do ORIGINAL) + o B001C007 normal, LINKADOS no MC, montados numa sequência, o AAF exportado
pelo MC e o caminho do painel do De Lá Pra Cá com o Baselight (relink pelas pastas dos originais do BL08 → destino
baselight). A pergunta: o MC lê o TC híbrido do render como o casador espera (o trecho do original no quadro certo)?

    (o MC aberto no projeto LAB BASELIGHT 2398; a interface do Baselight FECHADA)
    <assist>/.venv/bin/python mc_outra_taxa.py linkar | montar | exportar | ler
    (o MC fechado ou aberto)
    <assist>/.venv/bin/python mc_outra_taxa.py produto
A verdade (o quadro de fonte do ORIGINAL no in do plano): B001C007 47 · A002C001 364 · B001C005 128 (`outra_taxa.py`).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import atualizar_corte as B  # noqa: E402
import mc_render as MR  # noqa: E402  (os caminhos do Assist no sys.path)
import outra_taxa as OT  # noqa: E402

PROJETO = MR.PROJETO
BIN = "BL09 MC OUTRA TAXA"
BIN_ABS = os.path.join(os.path.expanduser("~"), "Documents", "Avid Projects", PROJETO, BIN + ".avb")
TRAB = os.path.join(B.SAIDA, "mc_outra_taxa")
SEQ = "BL09 OUTRA TAXA MC"
AAF = os.path.join(TRAB, "aaf_do_mc", SEQ.replace(" ", "_") + ".aaf")
#: (arquivo, in no arquivo em quadros dele (23,976), duração) — os mesmos planos do xmeml de `outra_taxa.py`
PLANOS = [(arq, ini, dur) for arq, _tc, _q, ini, dur, _reel in OT.PLANOS]


def linkar() -> dict:
    from avid.acoes import Acoes
    from avid.mcapi import MediaComposer
    os.makedirs(TRAB, exist_ok=True)
    arq = os.path.join(TRAB, "linkados.json")
    feitos = json.load(open(arq, encoding="utf-8")) if os.path.exists(arq) else {}
    with MediaComposer() as m:
        a = Acoes(m)
        try:
            a.criar_bin(BIN)
        except Exception as e:                # noqa: BLE001 — a bin já existe (2ª rodada)
            print("bin:", str(e)[:120], flush=True)
        for caminho, _i, _d in PLANOS:
            n = os.path.basename(caminho)
            if feitos.get(n):
                continue
            t0 = time.time()
            feitos[n] = a.link_file(caminho, BIN + ".avb")
            print(f"{time.time() - t0:5.1f} s  {n} → {feitos[n]}", flush=True)
    with open(arq, "w", encoding="utf-8") as fh:
        json.dump(feitos, fh, indent=1)
    return feitos


def montar() -> dict:
    import avb
    from avid.mcapi import MediaComposer
    from cicloassist.avid import timeline as T
    linkados = json.load(open(os.path.join(TRAB, "linkados.json"), encoding="utf-8"))
    with MediaComposer() as m:
        try:
            m.fechar_bin(BIN_ABS)
        except Exception:                    # noqa: BLE001 — bin já fechada responde erro (normal)
            pass
        with avb.open(BIN_ABS) as f:
            masters = {str(mm.mob_id): mm for mm in f.content.mobs if mm.mob_type == "MasterMob"}
            entradas, taxa = [], None
            for caminho, ins, dur in PLANOS:
                mm = masters[MR._urn(linkados[os.path.basename(caminho)])]
                print(os.path.basename(caminho), "edit rate", mm.edit_rate, flush=True)
                taxa = taxa or mm.edit_rate
                trilhas = tuple(sorted((t.media_kind, t.index) for t in mm.tracks if t.media_kind in ("picture", "sound")))
                entradas.append(T.Entrada(mob_id=str(mm.mob_id), duracao=dur, trilhas=trilhas, start_time=ins))
        T.acrescentar_timeline(BIN_ABS, SEQ, entradas, taxa, drop_frame=False)
        m.abrir_bin(BIN_ABS)
        fim, achada = time.time() + 120, {}
        while time.time() < fim and not achada:
            achada = {it.name: it.mob_id for it in m.itens_de(BIN_ABS, flags=("AllTypes",)) if it.name == SEQ}
            time.sleep(2)
    print(achada)
    with open(os.path.join(TRAB, "sequencia.json"), "w", encoding="utf-8") as fh:
        json.dump(achada, fh, indent=1)
    return achada


def exportar() -> str:
    from avid.mcapi import MediaComposer
    from relink import exportar_aaf
    mob = json.load(open(os.path.join(TRAB, "sequencia.json"), encoding="utf-8"))[SEQ]
    with MediaComposer() as m:
        aaf = exportar_aaf(m, mob, os.path.dirname(AAF), SEQ.replace(" ", "_"))
    print(aaf)
    return aaf


def ler() -> list:
    from aaf.parser import parse_aaf
    out = []
    for s in parse_aaf(AAF)["segments"]:
        if s.get("is_audio") or s.get("is_gap"):
            continue
        mr = s.get("media_ref") or {}
        out.append({k: s.get(k) for k in ("clip_name", "source_start_frames", "duration_frames", "timeline_tc_in")}
                   | {"tape": mr.get("tape_name"), "caminho": mr.get("local_path"), "tc": mr.get("source_tc_start")})
    for x in out:
        print(x)
    return out


def produto(base: str = "BL09 outra taxa MC") -> dict:
    """O painel, sem o HTTP: o AAF avulso → o casamento dos masters com os originais (`relink.preparar`, rota carta) →
    `preparar_avulso` (destino baselight). Depois o `bl-shots`: o quadro de fonte de cada plano × a verdade."""
    import relink
    import sessao_receber as SR
    rec = SR.SessaoReceber()
    aberto = rec.abrir(AAF)
    t = relink.Trabalho(rota="carta", carta=SR._carta_do_aaf(AAF), pastas=[OT.ORIG08], sequence=aberto.get("nome") or "")
    relink.preparar(t)
    for c in t.casamentos:
        print(f" casador: {c.master.nome:16} → {c.metodo:11} {os.path.basename(c.arquivo or c.sugestao or ''):14}"
              f" {c.confianca:.2f} {'REVISAR ' if c.precisa_de_revisao else ''}{c.motivo[:120]}")
    r = rec.preparar_avulso(aberto["chave"], "", t.decididos(), [OT.ORIG08],
                            sinais={"destino": "baselight", "job": OT.JOB, "scene": base, "markers": True})
    bl = r["baselight"]
    print(f"scene {bl['scene']}: {bl['planos']} planos {bl['contagem']}; nos originais {r.get('nos_originais')}")
    for x in bl.get("problemas", []):
        print("  problema:", x)
    saida = subprocess.run([os.path.join(B.BIN, "bl-shots"), "-inputrange", "-outputrange",
                            f"{B.HOST}:{OT.JOB}:{bl['scene']}"], capture_output=True, text=True).stdout
    certos = 0
    for linha in saida.splitlines():
        a, _b, _c, _d, arq = linha.split("\t", 4)
        nome = os.path.basename(arq.strip().strip('"'))
        ok = OT.VERDADE.get(nome) == int(a)
        certos += ok
        print(f"  {nome:14} fonte {a:>4} (verdade {OT.VERDADE.get(nome)}) {'✓' if ok else '✗'}")
    print(f"no ponto: {certos}/{len(OT.VERDADE)}")
    with open(os.path.join(TRAB, f"produto_{bl['scene'].replace(' ', '_').replace('·', '')}.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"casamentos": [c.to_dict() for c in t.casamentos], "resultado": r}, fh, indent=1,
                  ensure_ascii=False, default=str)
    return r


if __name__ == "__main__":
    cmd, *resto = sys.argv[1:]
    {"linkar": linkar, "montar": montar, "exportar": exportar, "ler": ler, "produto": produto}[cmd](*resto)
