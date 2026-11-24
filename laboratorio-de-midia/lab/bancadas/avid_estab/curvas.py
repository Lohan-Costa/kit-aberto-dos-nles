import sys
import avb
from avb.parameter_uuids import PARAMETER_UUIDS

def pts(pc):
    out = []
    for cp in pc.control_points:
        off = cp.offset
        out.append((off[0] / off[1], cp.value))
    return out

with avb.open(sys.argv[1]) as f:
    o = f.read_object(int(sys.argv[2]))
    td = list(o.property_data["trackman"].data_slots.tracker_data)[0]
    print("settings", bytes(td.settings).hex(), bytes(td.settings))
    for i, pc in enumerate(list(td.clips) + [td.clip5, td.clip6]):
        p = pts(pc)
        vs = [v for _q, v in p]
        print(f"clip {i}: n={len(p)} q {p[0][0]:.0f}..{p[-1][0]:.0f} interp={pc.interp_kind} vt={pc.value_type} "
              f"min={min(vs):.5f} max={max(vs):.5f} 1os={[round(v,5) for v in vs[:4]]}")
    print("--- parâmetros do efeito")
    for p in o.property_data.get("param_list") or []:
        pd = p.property_data
        nome = PARAMETER_UUIDS.get(str(pd.get("uuid")), str(pd.get("uuid"))[:13])
        ct = pd.get("control_track")
        n = len(ct.control_points) if ct is not None and hasattr(ct, "control_points") else 0
        print(f"  {nome}: {pd.get('value')!r:.40} kf={n}")
    print("--- keyframes (EffectParamList)")
    kl = o.property_data.get("keyframes")
    print("  ", {k: getattr(kl, k, None) for k in ("orig_length", "window_offset", "keyframe_size")})
    for ep in kl.parameters:
        print("   ", {k: (bytes(v).hex()[:80] if isinstance(v, (bytes, bytearray)) else v) for k, v in
                      ((pd.name, getattr(ep, pd.name, None)) for pd in getattr(type(ep), "propertydefs", []))})
