"""BL09 — ATUALIZAR CORTE no Baselight: o que a cor da v1 vira quando a montagem v2 chega (etapa 5 da proposta
"Baselight no app", Ciclo Assist, 2026-11-22).

Roda no Python da FilmLight (tem o `flapi`):
    "/Library/Application Support/FilmLight/python/3.12-v7-venv/bin/python" atualizar_corte.py preparar
    … atualizar_corte.py v1          # conform da v1 + a "cor do colorista" (um CDL que IDENTIFICA cada plano)
    … atualizar_corte.py v2 <via>    # a v2 numa scene NOVA, com a cor levada pela via (copygrades|multipaste|ciclo)
    … atualizar_corte.py ler <scene> # plano a plano: arquivo, trecho de fonte, qual cor da v1 está nele

A mídia: seis originais LIMPOS do BL08 (23,976, nomes e TCs únicos), copiados para `saida/baselight/BL09_ATUALIZAR/
ORIGINAIS` (cada caso é uma ilha). A identidade da cor: o slope R do CDL = 1 + k/100, com k o número do plano na v1.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import quote

AQUI = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
BL08 = os.path.join(LAB, "saida", "baselight", "BL08_CASAMENTO", "ORIGINAIS")
SAIDA = os.path.join(LAB, "saida", "baselight", "BL09_ATUALIZAR")
ORIG = os.path.join(SAIDA, "ORIGINAIS")
BIN = next(iter(sorted(__import__("glob").glob("/Applications/Baselight/*/Baselight-*.app/Contents/bin"))), "")
HOST, JOB = "localhost", "LAB_BL09_ATUALIZAR"

#: nome → (caminho no BL08, TC de início, quadros)
MIDIA = {
    "B001C007": ("DIA01/B001/B001C007.mov", "13:00:00:00", 288),
    "B001C008": ("DIA01/B001/B001C008.mov", "13:10:00:00", 288),
    "A001C008": ("DIA01/A003/A001C008.mov", "14:00:00:00", 240),
    "C001C003": ("DIA02/C001/C001C003.mov", "17:00:00:00", 240),
    "C001C004": ("DIA02/C001/C001C004.mov", "17:10:00:00", 240),
    "A006C001": ("DIA02/A006/A006C001.mov", "20:00:00:00", 288),
}

#: a montagem v1: (id, arquivo, in, duração) — o id é o k da cor
V1 = [
    ("S1", "B001C007", 48, 48),
    ("S2", "A001C008", 24, 48),
    ("S3", "C001C003", 60, 48),
    ("S4", "B001C008", 100, 48),
    ("S5", "A006C001", 30, 48),
    ("S6", "B001C007", 150, 48),
    ("S7", "A001C008", 120, 48),
]
#: a v2, com UMA mudança de cada tipo, e o que DEVERIA chegar de cor em cada plano (None = nenhuma: plano novo/trocado)
V2 = [
    ("N1", "A006C001", 200, 36, None, "NOVO no início — mesmo arquivo do S5 (retirado), outro trecho"),
    ("S1", "B001C007", 48, 48, "S1", "igual (só andou: algo entrou antes)"),
    ("S7", "A001C008", 120, 48, "S7", "MOVIDO (era o último)"),
    ("S2", "A001C008", 24, 48, "S2", "igual — duas camadas de cor"),
    ("S3", "C001C004", 60, 48, None, "TAKE TROCADO (C001C003 → C001C004)"),
    ("S4", "B001C008", 112, 30, "S4", "APARADO (cabeça +12, cauda −6)"),
    ("S6", "B001C007", 138, 60, "S6", "ESTENDIDO (cabeça −12) — mesmo arquivo do S1, outro trecho"),
]
K = {s[0]: i + 1 for i, s in enumerate(V1)}
#: a v1 em que o COLORISTA dividiu o S4 em dois (cores diferentes: S4 e "S4b", k = 8) — a v2 apara esse plano
V1_DIVIDIDA = [p for p in V1 if p[0] != "S4"]
V1_DIVIDIDA[3:3] = [("S4", "B001C008", 100, 24), ("S4b", "B001C008", 124, 24)]
K["S4b"] = 8


def tc_q(tc: str) -> int:
    h, m, s, f = (int(x) for x in re.split("[:;]", tc))
    return ((h * 60 + m) * 60 + s) * 24 + f


def bl(ferramenta: str, *args: str, entrada: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([os.path.join(BIN, ferramenta), *args], capture_output=True, text=True, input=entrada,
                          timeout=1800)


def scenes() -> list[str]:
    pre = f"{HOST}:{JOB}:"
    return [l[len(pre):] for l in bl("bl-lsscenes", "-q", f"{HOST}:{JOB}").stdout.splitlines() if l.startswith(pre)]


# ── o xmeml (o mínimo que o bl-conform lê bem: <duration> e <timecode> no <file>, BL08) ─────────────────────────────

RATE = "<rate><timebase>24</timebase><ntsc>TRUE</ntsc></rate>"


def _file(nome: str, fid: str, vistos: set) -> str:
    if fid in vistos:
        return f'<file id="{fid}"/>'
    vistos.add(fid)
    _, tc, dur = MIDIA[nome]
    url = "file://localhost" + quote(os.path.join(ORIG, nome + ".mov"))
    return (f'<file id="{fid}"><name>{nome}.mov</name><pathurl>{url}</pathurl>{RATE}<duration>{dur}</duration>'
            f'<timecode>{RATE}<string>{tc}</string><frame>{tc_q(tc)}</frame><displayformat>NDF</displayformat>'
            f'<reel><name>{nome}</name></reel></timecode><media><video><samplecharacteristics>{RATE}<width>1920</width>'
            f'<height>1080</height></samplecharacteristics></video></media></file>')


def xmeml(nome: str, planos: list[tuple]) -> str:
    vistos: set = set()
    itens, t = [], 0
    for i, p in enumerate(planos, 1):
        arq, ini, dur = p[1], p[2], p[3]
        itens.append(f'<clipitem id="clipitem-{i}"><name>{arq}.mov</name><enabled>TRUE</enabled>'
                     f'<duration>{MIDIA[arq][2]}</duration>{RATE}<start>{t}</start><end>{t + dur}</end>'
                     f'<in>{ini}</in><out>{ini + dur}</out>{_file(arq, "file-" + arq, vistos)}</clipitem>')
        t += dur
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="sequence-1">'
            f'<duration>{t}</duration>{RATE}<name>{nome}</name><timecode>{RATE}<string>01:00:00:00</string>'
            f'<frame>{tc_q("01:00:00:00")}</frame><displayformat>NDF</displayformat></timecode><media><video><format>'
            f'<samplecharacteristics>{RATE}<width>1920</width><height>1080</height></samplecharacteristics></format>'
            f'<track>{"".join(itens)}</track></video></media></sequence></xmeml>\n')


def preparar() -> None:
    os.makedirs(ORIG, exist_ok=True)
    for nome, (rel, _, _) in MIDIA.items():
        d = os.path.join(ORIG, nome + ".mov")
        if not os.path.exists(d):
            shutil.copy2(os.path.join(BL08, rel), d)
    for nome, planos in (("BL09 V1", V1), ("BL09 V2", V2)):
        with open(os.path.join(SAIDA, nome.replace(" ", "_") + ".xml"), "w", encoding="utf-8") as fh:
            fh.write(xmeml(nome, planos))
    verdade = {"caso": "BL09 atualizar corte", "v1": [dict(zip(("id", "arquivo", "in", "dur"), p)) | {"k": K[p[0]]}
                                                      for p in V1],
               "v2": [dict(zip(("id", "arquivo", "in", "dur", "cor_esperada", "mudanca"), p)) for p in V2]}
    with open(os.path.join(SAIDA, "verdade.json"), "w", encoding="utf-8") as fh:
        json.dump(verdade, fh, ensure_ascii=False, indent=1)
    print("preparado:", SAIDA)


def conformar(xml: str, scene: str, *extra: str) -> str:
    if JOB not in bl("bl-lsjobs", "-q", HOST).stdout:
        bl("bl-mkjob", f"{HOST}:{JOB}")
    r = bl("bl-conform", "--edlname", os.path.join(SAIDA, xml), "--destscene", f"{HOST}:{JOB}:{scene}",
           "--fps", "23.976", "--space", "Video_Full", "--multiples", "--Filter", "Filename",
           "--src", f"dir={ORIG}", *extra)
    log = (r.stdout + r.stderr).strip()
    if scene not in scenes():
        raise SystemExit("não conformou:\n" + log[-1500:])
    return log


# ── a FLAPI ──────────────────────────────────────────────────────────────────────────────────────────────────────────

def _abrir(scene: str, leitura: bool = False):
    import flapi
    c = flapi.Connection(HOST)
    c.connect()
    s = c.Scene.open_scene(c.Scene.parse_path(f"{HOST}:{JOB}:{scene}"), {flapi.OPENFLAG_READ_ONLY} if leitura else set())
    s.wait_until_open()
    return flapi, c, s


def _cdl(k: int) -> list[float]:
    return [1 + k / 100, 1.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]


def colorir_v1(scene: str, planos: list = V1) -> None:
    """O colorista: um CDL por plano (slope R = 1 + k/100); o S2 ganha uma 2ª camada (slope G = 1.5); um marker no S4."""
    flapi, c, s = _abrir(scene)
    try:
        s.start_delta("BL09: a cor do colorista")
        infos = list(s.get_shot_ids())
        for (pid, *_), info in zip(planos, infos):
            sh = s.get_shot(info.ShotId)
            sh.insert_cdl_layer(_cdl(K[pid]))
            if pid == "S2":
                sh.insert_cdl_layer([1.0, 1.5, 1.0, 0, 0, 0, 1, 1, 1, 1])
            if pid == "S4":
                cats = s.get_mark_categories()
                s.add_mark(info.StartFrame + 10, cats[0], "colorista: conferir o céu")
            sh.release()
        s.end_delta()
        s.save_scene()
    finally:
        s.close_scene()
        c.close()


_NUM = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?")


_CDL = re.compile(r"GR_CDLGradeRop \S+ (?:\S+ ){4}((?:f [0-9a-f]{16} ){10})")


def _hex(h: str) -> float:
    import struct
    return struct.unpack(">d", bytes.fromhex(h))[0]


def cores_do_plano(sh) -> list[str]:
    """As camadas CDL do plano, lidas do BLG (base64 → 8 bytes de cabeçalho → zlib → texto): "S2" (slope R = 1 + k/100)
    e "+G1.5" (a 2ª camada do S2). Ordem do BLG."""
    import base64
    import zlib
    p = sh.get_blg_payload() or ""
    try:
        txt = zlib.decompress(base64.b64decode(p)[8:]).decode("utf-8", "replace")
    except Exception as e:
        return [f"?{e}"]
    out = []
    for m in _CDL.finditer(txt):
        v = [_hex(x) for x in m.group(1).split()[1::2]]
        if abs(v[1] - 1.5) < 1e-6:
            out.append("+G1.5")
            continue
        k = round((v[0] - 1) * 100)
        out.append(next((pid for pid, kk in K.items() if kk == k), f"k{k}") if k else "neutro")
    return out


def ler(scene: str) -> list[dict]:
    flapi, c, s = _abrir(scene, leitura=True)
    out = []
    try:
        for info in s.get_shot_ids():
            sh = s.get_shot(info.ShotId)
            try:
                sd = sh.get_sequence_descriptor()
                out.append({"inicio": info.StartFrame, "fim": info.EndFrame,
                            "arquivo": os.path.basename(sd.get_full_filename_with_F()) if sd else None,
                            "src": [sh.get_src_start_frame(), sh.get_src_end_frame()],
                            "src_tc": str(sh.get_src_start_timecode()), "blg": cores_do_plano(sh)})
            finally:
                sh.release()
        marks = [(s.get_mark(i).get_record_frame(), s.get_mark(i).get_note_text()) for i in s.get_mark_ids()]
    finally:
        s.close_scene()
        c.close()
    return out, marks


def via_multipaste(scene: str, match: list[str], qualidade: str = "ExactMatch", origem: str = "BL09 V1") -> int:
    """A cor da v1 levada à scene nova pelo Multi-Paste do Baselight (Source = MultipleScenes, a v1)."""
    flapi, c, s = _abrir(scene)
    try:
        ms = flapi.MultiPasteSettings(
            Source="MultipleScenes", SourceScenes=[f"{HOST}:{JOB}:{origem}"], MatchBy=match, MatchQuality=qualidade,
            PasteGrades=1, LayerZeroBehaviour="StackOnly", SourceShots="CopyAll", DestShots="OverwriteAll",
            DetectGradeChanges=0, PasteLocation="Above", MaintainTracks=1, PasteMetadata=0, PasteGroups=0)
        mp = c.MultiPaste.create()
        s.start_delta("Multi-Paste da v1")
        try:
            n = mp.multi_paste(s, ms, [i.ShotId for i in s.get_shot_ids()])
        except flapi.FLAPIException as e:
            s.cancel_delta()
            print("  multi-paste RECUSOU:", e)
            n = -1
        else:
            s.end_delta()
        s.save_scene()
        for item in (mp.get_log() or [])[:40]:
            print("  log:", getattr(item, "__dict__", item))
        return n
    finally:
        s.close_scene()
        c.close()


def via_ciclo(scene: str, origem: str = "BL09 V1") -> list:
    """A cor da v1 levada plano a plano pelo BLG, decidida pela comparação do CICLO: o plano da v2 herda a cor do plano
    da v1 com o MESMO arquivo e trecho de fonte em comum (o take trocado não herda; o retirado não vai)."""
    flapi, c, s1 = _abrir(origem, leitura=True)
    v1 = []
    try:
        for info in s1.get_shot_ids():
            sh = s1.get_shot(info.ShotId)
            sd = sh.get_sequence_descriptor()
            v1.append({"arquivo": os.path.basename(sd.get_full_filename_with_F()),
                       "src": (sh.get_src_start_frame(), sh.get_src_end_frame()),
                       "blg": sh.get_blg_payload(), "res": sh.get_blg_resources()})
            sh.release()
    finally:
        s1.close_scene()
        c.close()
    flapi, c, s = _abrir(scene)
    feito = []
    try:
        s.start_delta("Ciclo Assist: a cor da v1 (atualizar corte)")
        for info in s.get_shot_ids():
            sh = s.get_shot(info.ShotId)
            sd = sh.get_sequence_descriptor()
            arq = os.path.basename(sd.get_full_filename_with_F())
            a, b = sh.get_src_start_frame(), sh.get_src_end_frame()
            cand = [o for o in v1 if o["arquivo"] == arq and min(b, o["src"][1]) - max(a, o["src"][0]) > 0]
            # o de MAIOR trecho em comum; empate = ninguém (vai para o editor)
            comum = lambda o: min(b, o["src"][1]) - max(a, o["src"][0])  # noqa: E731
            cand.sort(key=lambda o: -comum(o))
            if len(cand) > 1:
                feito.append((info.StartFrame, arq, "AVISO: cobre %d planos da v1 (%s)" % (
                    len(cand), ", ".join(f"{o['src'][0]}-{o['src'][1]}:{comum(o)}q" for o in cand))))
            if cand and (len(cand) == 1 or comum(cand[0]) != comum(cand[1])):
                sh.apply_blg_payload(cand[0]["blg"], cand[0]["res"])
                feito.append((info.StartFrame, arq, "copiada"))
            else:
                feito.append((info.StartFrame, arq, "sem cor"))
            sh.release()
        s.end_delta()
        s.save_scene()
    finally:
        s.close_scene()
        c.close()
    return feito


def conferir(scene: str) -> dict:
    """A v2 lida × o esperado da verdade: placar por plano (a cor certa, a errada, a que faltou ou sobrou)."""
    planos, marks = ler(scene)
    linhas, certo = [], 0
    for (pid, arq, ini, dur, esperada, mud), p in zip(V2, planos):
        tem = [x for x in p["blg"] if x != "+G1.5"]
        ok = (tem == [esperada]) if esperada else (tem == [])
        if pid == "S2" and esperada:
            ok = ok and "+G1.5" in p["blg"]
        certo += ok
        linhas.append({"plano": pid, "mudanca": mud, "arquivo_ok": p["arquivo"] == arq + ".mov",
                       "src": p["src"], "esperada": esperada, "chegou": p["blg"], "ok": ok})
    sobra = planos[len(V2):]
    return {"scene": scene, "certos": certo, "de": len(V2), "planos": linhas,
            "sobra_depois_da_v2": [{"inicio": p["inicio"], "fim": p["fim"], "arquivo": p["arquivo"], "cor": p["blg"]}
                                   for p in sobra], "marks": marks}


def main(argv: list[str]) -> int:
    cmd = argv[0]
    if cmd == "preparar":
        preparar()
    elif cmd == "v1":
        if "BL09 V1" not in scenes():
            print(conformar("BL09_V1.xml", "BL09 V1")[-600:])
            colorir_v1("BL09 V1")
        print("v1 pronta")
    elif cmd == "v1-dividida":
        with open(os.path.join(SAIDA, "BL09_V1_DIVIDIDA.xml"), "w", encoding="utf-8") as fh:
            fh.write(xmeml("BL09 V1 dividida", V1_DIVIDIDA))
        if "BL09 V1 dividida" not in scenes():
            conformar("BL09_V1_DIVIDIDA.xml", "BL09 V1 dividida")
            colorir_v1("BL09 V1 dividida", V1_DIVIDIDA)
        print("v1 dividida pronta")
    elif cmd == "v2-dividida":
        via = argv[1]
        scene = f"BL09 V2 dividida {via}"
        if scene not in scenes():
            conformar("BL09_V2.xml", scene)
        if via == "multipaste":
            print("multi-paste:", via_multipaste(scene, ["Filename", "Timecode"], origem="BL09 V1 dividida"))
        else:
            print(via_ciclo(scene, origem="BL09 V1 dividida"))
    elif cmd == "v2":
        via = argv[1]
        scene = f"BL09 V2 {via}"
        if scene not in scenes():
            conformar("BL09_V2.xml", scene)
        if via.startswith("multipaste"):
            match = {"multipaste": ["Filename", "Timecode"], "multipaste-nome": ["Filename", "AlwaysMatch"],
                     "multipaste-quadro": ["Filename", "FrameNumber"]}[via]
            print("multi-paste:", via_multipaste(scene, match), "planos")
        elif via == "ciclo":
            print(via_ciclo(scene))
    elif cmd == "conferir":
        r = conferir(argv[1])
        with open(os.path.join(SAIDA, "conferencia_" + argv[1].replace(" ", "_") + ".json"), "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)
        print(f"{r['scene']}: {r['certos']} de {r['de']}")
        for l in r["planos"]:
            print(f"  {'ok ' if l['ok'] else 'ERR'} {l['plano']:3} {l['mudanca'][:40]:40} esperada={l['esperada']} chegou={l['chegou']}")
        print("  sobra:", r["sobra_depois_da_v2"], "marks:", r["marks"])
    elif cmd == "ler":
        planos, marks = ler(argv[1])
        print(json.dumps({"planos": planos, "marks": marks}, ensure_ascii=False, indent=1)[:int(argv[2]) if len(argv) > 2 else None])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
