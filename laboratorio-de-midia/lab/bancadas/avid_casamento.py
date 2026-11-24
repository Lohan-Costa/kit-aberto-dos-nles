"""BL08 no Media Composer (Mac, 25.12) — a MESMA montagem do Premiere (`premiere_casamento.MONTAGEM`, 18 planos) nos
dailies da BL08, AMA-linkados numa bin própria do projeto LAB BASELIGHT 2398; o AAF vai ao Baselight.

    (o MC aberto no projeto LAB BASELIGHT 2398)
    <conformar>/.venv/bin/python -m lab.bancadas.avid_casamento linkar|montar|exportar|ler
"""
from __future__ import annotations

import json
import os
import sys
import time
import unicodedata

from ..casamento import SAIDA
from .avid_baselight import ASSIST, RAIZ, _caminhos
from .premiere_casamento import MONTAGEM

PROJETO = "LAB BASELIGHT 2398"
BIN = "BL08 DAILIES"
BIN_ABS = os.path.join(os.path.expanduser("~"), "Documents", "Avid Projects", PROJETO, BIN + ".avb")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "avid_casamento")
#: v3 (2026-11-22): a montagem com os 20 planos (E19/E20 = P11/P12); a 1ª (18 planos) fica na bin; a "2" saiu com buracos (o serviço fora do ar no linkar) e não vale
SEQ = os.environ.get("BL08_SEQ", "BL08 CASAMENTO 3")
DUR = 48
FPS_TL = 24000 / 1001


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _urn(api: str) -> str:
    """O MobID da API do MC (`060a2b34…-000000-…`) na forma do pyavb (`urn:smpte:umid:` + 8 grupos de 8 hex)."""
    h = api.replace("-", "")
    return "urn:smpte:umid:" + ".".join(h[i:i + 8] for i in range(0, 64, 8))


def linkar() -> dict:
    _caminhos()
    from avid.acoes import Acoes
    from avid.mcapi import MediaComposer
    os.makedirs(TRAB, exist_ok=True)
    dailies = sorted({d for _e, d, _i, _n in MONTAGEM})
    arq = os.path.join(TRAB, "linkados.json")
    feitos = json.load(open(arq, encoding="utf-8")) if os.path.exists(arq) else {}
    dailies = [d for d in dailies if d not in feitos]     # 2ª rodada: só os novos (não duplicar masters na bin)
    with MediaComposer() as m:
        a = Acoes(m)
        try:
            a.criar_bin(BIN)
        except Exception as e:                # noqa: BLE001 — a bin já existe (2ª rodada)
            print("bin:", str(e)[:120], flush=True)
        for d in dailies:
            if not d.isascii():
                # ⛔ medido 2026-11-22 (MC 25.12 Mac): `LinkFile` com acento falha em NFC e em NFD (o MC lê o UTF-8 como
                # MacRoman: "CORACÃßAÃÉO_01.mov cannot be linked", ErrorType 66) — o plano vira BURACO na sequência
                feitos[d] = None
                print(f"  —   {d} → NÃO LINKA (acento; MC 25.12 Mac)", flush=True)
                continue
            t0 = time.time()
            feitos[d] = a.link_file(os.path.join(SAIDA, d), BIN + ".avb")
            print(f"{time.time() - t0:5.1f} s  {d} → {feitos[d]}", flush=True)
    with open(os.path.join(TRAB, "linkados.json"), "w", encoding="utf-8") as fh:
        json.dump(feitos, fh, indent=1, ensure_ascii=False)
    return feitos


def montar() -> dict:
    """Grava a sequência na bin (fechada no MC, a dança do banco) e reabre. O in de cada plano em quadros da TIMELINE
    (23,976), como o Premiere; os masters de outra taxa (o P7, 29,97) vão conferidos no AAF exportado."""
    _caminhos()
    if ASSIST not in sys.path:
        sys.path.insert(0, ASSIST)
    import avb
    from avid.mcapi import MediaComposer
    from cicloassist.avid import timeline as T
    with open(os.path.join(TRAB, "linkados.json"), encoding="utf-8") as fh:
        linkados = json.load(fh)
    with MediaComposer() as m:
        try:
            m.fechar_bin(BIN_ABS)
        except Exception:                    # noqa: BLE001 — bin já fechada responde erro (normal)
            pass
        with avb.open(BIN_ABS) as f:
            masters = {str(mm.mob_id): mm for mm in f.content.mobs if mm.mob_type == "MasterMob"}
            taxa = None
            entradas = []
            um = _urn(next(v for v in linkados.values() if v))
            for ev, d, ins, _nota in MONTAGEM:
                if not linkados.get(d):          # não linkado (acento): BURACO do mesmo tamanho (entrada sem trilhas)
                    entradas.append(T.Entrada(mob_id=um, duracao=DUR, trilhas=(), start_time=0))
                    continue
                mm = masters[_urn(linkados[d])]
                taxa = taxa or mm.edit_rate
                trilhas = tuple(sorted((t.media_kind, t.index) for t in mm.tracks if t.media_kind in ("picture", "sound")))
                entradas.append(T.Entrada(mob_id=str(mm.mob_id), duracao=DUR, trilhas=trilhas,
                                          start_time=int(ins * FPS_TL)))
            taxas = {d: float(masters[_urn(linkados[d])].edit_rate) for _e, d, _i, _n in MONTAGEM if linkados.get(d)}
        T.acrescentar_timeline(BIN_ABS, SEQ, entradas, taxa, drop_frame=False)
        m.abrir_bin(BIN_ABS)
        fim, achada = time.time() + 120, {}
        while time.time() < fim and not achada:
            achada = {it.name: it.mob_id for it in m.itens_de(BIN_ABS, flags=("AllTypes",)) if it.name == SEQ}
            time.sleep(2)
    print(achada, {k: v for k, v in taxas.items() if abs(v - FPS_TL) > 0.01})
    with open(os.path.join(TRAB, "sequencia.json"), "w", encoding="utf-8") as fh:
        json.dump(achada, fh, indent=1)
    return achada


def exportar() -> str:
    _caminhos()
    from avid.mcapi import MediaComposer
    from relink import exportar_aaf
    with open(os.path.join(TRAB, "sequencia.json"), encoding="utf-8") as fh:
        mob = json.load(fh)[SEQ]
    with MediaComposer() as m:
        aaf = exportar_aaf(m, mob, os.path.join(TRAB, "aaf_do_mc"), SEQ.replace(" ", "_"))
    print(aaf)
    return aaf


def ler() -> list:
    """O AAF exportado pelo leitor do Conformar: nome, in na fonte e duração de cada segmento de imagem."""
    _caminhos()
    from aaf.parser import parse_aaf
    p = parse_aaf(os.path.join(TRAB, "aaf_do_mc", SEQ.replace(" ", "_") + ".aaf"))
    out = []
    for s in p["segments"]:
        if s.get("is_audio") or s.get("is_gap"):
            continue
        mr = s.get("media_ref") or {}
        out.append({k: s.get(k) for k in ("clip_name", "source_start_frames", "duration_frames", "track")}
                   | {"tape": mr.get("tape_name"), "caminho": mr.get("local_path"), "tc": mr.get("source_tc_start")})
    for x in out:
        print(x)
    return out


def vidref() -> str:
    """O vid ref da sequência pelo próprio MC (preset do laboratório DNxHR LB 23,976 + `ExportFile`), como a BL02: o que
    o MC MOSTRA em cada plano — a verdade para os planos de fonte de outra taxa (P3, P7)."""
    from .avid_baselight import vidref as _vr, VIDREF
    import lab.bancadas.avid_baselight as AB
    seqs = json.load(open(os.path.join(TRAB, "sequencia.json"), encoding="utf-8"))
    arq = os.path.join(AB.TRABALHO, "sequencias.json")
    todas = json.load(open(arq, encoding="utf-8")) if os.path.exists(arq) else {}
    todas.update(seqs)
    with open(arq, "w", encoding="utf-8") as fh:
        json.dump(todas, fh, indent=1)
    return _vr(SEQ)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"linkar": linkar, "montar": montar, "exportar": exportar, "ler": ler, "vidref": vidref}[sys.argv[1]]()
