from arvore import *
import numpy as np
def acha(fs, caminho):
    for f in fs:
        if f["field"] == caminho[0] and isinstance(f["value"], list):
            if len(caminho) == 1: yield f["value"]
            else: yield from acha(f["value"], caminho[1:])
def entradas(d):
    """[(campo1, {id: valor-bruto})] das entradas por quadro do nó."""
    fs = pb_decode(d)
    out = []
    for no in acha(fs, [3, 9, 1, 6, 2]):
        for lista in acha(no, [4]):
            for e in [f for f in lista if f["field"] == 1]:
                q = next((x["value"] for x in e["value"] if x["field"] == 1), 0)
                ps = {}
                for p in [x for x in e["value"] if x["field"] == 2]:
                    pid = next(x["value"] for x in p["value"] if x["field"] == 1)
                    val = next(x["value"] for x in p["value"] if x["field"] == 2)
                    ps[pid] = val
                out.append((q, ps))
    return out
if __name__ == "__main__":
    d = dec(body_do_xml(sys.argv[1])[0])
    E = entradas(d)
    print(len(E), "entradas; campos", sorted({hex(k) for _, ps in E for k in ps}))
    for q, ps in E[:4] + E[60:62] + E[-2:]:
        b = ps[0x10300015][0]["value"]
        w = struct.unpack("<20f", b); i = struct.unpack("<20I", b)
        print(q, [hex(x) for x in i[:10]], np.round(w[10:], 5))
