"""Ler a grade de um projeto REAL do Resolve, sem tocar no projeto: o inventário de correctors, ids e OFX por timeline.

Uso (o Resolve pode estar aberto; lê o que está salvo em disco):
    python lab/resolve_grades_reais.py "PRODUCAO-H" --saida grades.json [--timeline NOME ...]

Copia o `Project.db` do banco de disco (Mac ou Windows) para uma pasta temporária e lê de lá. Cada item da timeline:
os nós, e em cada nó os CORRECTORS (o tipo em `9.1.1`: 1 Primaries, 2 HSL, 3/4/5/6/18 janelas, 9 Key, 15 NR) com os
parâmetros `{id: valor}`, e os OFX do campo 10 (plugin + parâmetros fora do padrão). As seis janelas-fantasma de todo nó
(só o parâmetro de matriz) ficam de fora do resumo. Banco: `protocolos/drt-drp/estruturas.md` §"Uma grade REAL".
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import shutil
import sqlite3
import struct
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOTOR = os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar", "motor")
FANTASMAS = {"0x88300031", "0x8870001E", "0x88500010", "0x88B00012", "0x88D00014", "0x88F0000D"}


def _pb():
    if MOTOR not in sys.path:
        sys.path.insert(0, MOTOR)
    import zstandard
    from tools.inspect_drp import pb_decode
    return zstandard, pb_decode


def achar_db(nome: str) -> str:
    bases = [
        os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Resolve Project Library"),
        os.path.join(os.environ.get("APPDATA", ""), "Blackmagic Design", "DaVinci Resolve", "Support",
                     "Resolve Project Library"),
    ]
    achados = [a for b in bases for a in glob.glob(os.path.join(glob.escape(b), "**", glob.escape(nome), "Project.db"),
                                                  recursive=True)]
    if not achados:
        raise FileNotFoundError(f"Project.db de {nome!r}")
    return max(achados, key=os.path.getmtime)


def _f(m, n):
    return [x for x in m if x["field"] == n]


def _val(p):
    v = p.get("value")
    if isinstance(v, (bytes, bytearray)):
        if p["wire"] == 5 and len(v) == 4:
            return round(struct.unpack("<f", v)[0], 6)
        if p["wire"] == 1 and len(v) == 8:
            return struct.unpack("<d", v)[0]
        try:
            return v.decode("utf-8")
        except UnicodeDecodeError:
            return v.hex()[:80]
    if isinstance(v, list):
        return {str(x["field"]): _val(x) for x in v} if len(v) < 12 else f"<{len(v)} campos>"
    return v


class Leitor:
    def __init__(self, db: str):
        self.zstd, self.pb_decode = _pb()
        self.tmp = os.path.join(tempfile.mkdtemp(prefix="grades_"), "Project.db")
        shutil.copy(db, self.tmp)
        self.c = sqlite3.connect(self.tmp)

    def body(self, vid):
        r = self.c.execute('select Body from "ListMgt::LmVersion" where "ListMgt::LmVersion_id"=?', (vid,)).fetchone()
        if not r or not r[0]:
            return None
        b = r[0]
        return self.zstd.ZstdDecompressor().decompress(b[1:], max_output_size=1 << 28) if b[0] == 0x81 else b

    def ativa(self, vt):
        r = self.c.execute('select pActive from "ListMgt::LmVersionTable" where "ListMgt::LmVersionTable_id"=?',
                           (vt,)).fetchone() if vt else None
        return r[0] if r else None

    def _ofx(self, m10):
        out = []
        for e in _f(m10, 1):
            em = e["value"]
            if not isinstance(em, list) or not _f(em, 2) or not isinstance(_f(em, 2)[0]["value"], list):
                continue
            for o in _f(_f(em, 2)[0]["value"], 21):
                om = o["value"]
                if not isinstance(om, list):
                    continue
                params = {}
                for p in _f(om, 5):
                    pm = p["value"]
                    if isinstance(pm, list) and _f(pm, 1):
                        params[_val(_f(pm, 1)[0])] = _val(_f(pm, 2)[0]) if _f(pm, 2) else None
                out.append({"plugin": _val(_f(om, 2)[0]) if _f(om, 2) else None, "params": params})
        return out

    def nos(self, b):
        g = _f(self.pb_decode(b), 1)
        if not g or not isinstance(g[0]["value"], list):
            return [], []
        g = g[0]["value"]
        nos = []
        for nd in _f(g, 7):
            m = nd["value"]
            info = {"id": _f(m, 1)[0]["value"] if _f(m, 1) else None,
                    "rotulo": _val(_f(m, 6)[0]) if _f(m, 6) else "", "correctors": [], "ofx": []}
            for p9 in _f(m, 9):
                for cor in _f(p9["value"], 1) if isinstance(p9["value"], list) else []:
                    cm = cor["value"]
                    if not isinstance(cm, list):
                        continue
                    params = {}
                    for s6 in _f(cm, 6):
                        for s2 in _f(s6["value"], 2) if isinstance(s6["value"], list) else []:
                            for pr in _f(s2["value"], 3) if isinstance(s2["value"], list) else []:
                                pm = pr["value"]
                                if isinstance(pm, list) and _f(pm, 1):
                                    params["0x%08X" % _f(pm, 1)[0]["value"]] = _val(_f(pm, 2)[0]) if _f(pm, 2) else None
                    info["correctors"].append({"tipo": _f(cm, 1)[0]["value"] if _f(cm, 1) else None,
                                               "fantasma": set(params) <= FANTASMAS, "params": params})
            for m10 in _f(m, 10):
                if isinstance(m10["value"], list):
                    info["ofx"] += self._ofx(m10["value"])
            nos.append(info)
        ligs = [{str(x["field"]): x["value"] for x in l["value"]} for l in _f(g, 8) if isinstance(l["value"], list)]
        return nos, ligs

    def timelines(self, filtro=None):
        res = {}
        seqs = self.c.execute('select s.Sm2Sequence_id, s.pLmVerTable, t.Name from Sm2Sequence s '
                              'join Sm2Timeline t on s.Sm2Timeline_id=t.Sm2Timeline_id').fetchall()
        for seq, svt, nome in seqs:
            if filtro and nome not in filtro:
                continue
            itens = []
            for iid, inome, start, dur, vt in self.c.execute(
                    'select i.Sm2TiItem_id, i.Name, i.Start, i.Duration, i.pLmVerTable from Sm2TiItem i '
                    'join Sm2TiTrack t on i.Sm2TiTrack_id=t.Sm2TiTrack_id '
                    "where t.Sequence=? and t.Type=0 and i.DbType='Sm2TiVideoClip'", (seq,)).fetchall():
                b = self.body(self.ativa(vt))
                nos, ligs = self.nos(b) if b else ([], [])
                itens.append({"item": iid, "nome": inome, "start": start, "dur": dur, "nos": nos, "ligacoes": ligs})
            b = self.body(self.ativa(svt))
            res[nome] = {"itens": itens, "grade_timeline": self.nos(b)[0] if b else []}
        return res


def resumo(tl: dict) -> dict:
    tipos, ids, ofx = collections.Counter(), collections.defaultdict(collections.Counter), collections.Counter()
    for it in tl["itens"]:
        for n in it["nos"]:
            for c in n["correctors"]:
                if c["fantasma"]:
                    continue
                tipos[c["tipo"]] += 1
                for k in c["params"]:
                    ids[c["tipo"]][k] += 1
            for o in n["ofx"]:
                ofx[(o["plugin"], tuple(sorted(o["params"])))] += 1
    return {"itens": len(tl["itens"]), "nos": sum(len(i["nos"]) for i in tl["itens"]),
            "correctors": dict(tipos), "ids": {t: dict(c) for t, c in ids.items()},
            "ofx": [{"plugin": p, "params": list(k), "n": n} for (p, k), n in ofx.items()]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--saida")
    ap.add_argument("--timeline", nargs="*")
    a = ap.parse_args()
    tls = Leitor(achar_db(a.projeto)).timelines(a.timeline)
    if a.saida:
        with open(a.saida, "w", encoding="utf-8") as fh:
            json.dump(tls, fh, ensure_ascii=False, indent=1, default=str)
    for nome, tl in tls.items():
        print(nome, json.dumps(resumo(tl), ensure_ascii=False, default=str)[:600])


if __name__ == "__main__":
    main()
