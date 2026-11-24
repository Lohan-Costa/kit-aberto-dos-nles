import sys
import avb
from avb.parameter_uuids import PARAMETER_UUIDS

def props(o):
    out = {}
    for pd in getattr(type(o), "propertydefs", []) or []:
        try:
            out[pd.name] = getattr(o, pd.name)
        except Exception:
            pass
    if not out:
        out = dict(getattr(o, "property_data", {}) or {})
    return out

def desc(v):
    if isinstance(v, (bytes, bytearray)):
        return f"<bytes {len(v)}> {bytes(v[:64]).hex()}"
    if isinstance(v, (list, tuple)) and len(v) > 6 and not hasattr(v[0], "propertydefs"):
        return f"<{len(v)}> {repr(list(v[:6]))[:200]}"
    return repr(v)[:160]

def anda(o, ind=0, prof=0):
    if prof > 8:
        return
    for k, v in props(o).items():
        if (hasattr(v, "propertydefs") or hasattr(v, "property_data")) and type(v).__name__ != "AVBRefList":
            print(" " * ind + f"{k}: <{type(v).__name__}>")
            anda(v, ind + 4, prof + 1)
        elif isinstance(v, (list, tuple)) or type(v).__name__ in ("AVBRefList", "AVBObjectRef"):
            try:
                itens = list(v)
            except TypeError:
                itens = [v]
            if itens and (hasattr(itens[0], "propertydefs") or hasattr(itens[0], "property_data")):
                print(" " * ind + f"{k}: [{len(itens)} × {type(itens[0]).__name__}]")
                for i, x in enumerate(itens[:int(sys.argv[3]) if len(sys.argv) > 3 else 3]):
                    print(" " * (ind + 2) + f"[{i}]")
                    anda(x, ind + 6, prof + 1)
            else:
                print(" " * ind + f"{k}: {desc(v)}")
        else:
            print(" " * ind + f"{k}: {desc(v)}")

with avb.open(sys.argv[1]) as f:
    alvo = int(sys.argv[2])
    o = f.read_object(alvo)
    print(type(o).__name__, o.property_data.get("effect_id"))
    anda(o.property_data["trackman"])
