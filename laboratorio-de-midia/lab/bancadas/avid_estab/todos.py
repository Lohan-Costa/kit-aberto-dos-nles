import sys
import avb
with avb.open(sys.argv[1]) as f:
    vistos = set()
    for i in range(len(f.object_positions)):
        try:
            o = f.read_object(i)
        except Exception:
            continue
        if type(o).__name__ != "TrackEffect" or "STABIL" not in str(o.property_data.get("effect_id", "")).upper():
            continue
        tm = o.property_data.get("trackman")
        tds = list(tm.data_slots.tracker_data) if tm else []
        chave = tuple(round(c.value, 6) for td in tds for c in list(td.clips[0].control_points)[:3])
        marca = "(repetido)" if chave in vistos else ""
        vistos.add(chave)
        for td in tds:
            nome = bytes(td.settings)[21:28]
            c0 = list(td.clips[0].control_points)
            print(f"obj {i} len={o.property_data.get('length')} pontos={len(tds)} '{nome.decode(errors='replace')}' "
                  f"n={len(c0)} offset_tracking={getattr(td,'offset_tracking',None)} smoothing={getattr(td,'smoothing',None)} "
                  f"jitter={getattr(td,'jitter_removal',None)} filtro={getattr(td,'filter_amount',None)} "
                  f"precomp={'sim' if o.property_data.get('precomputed') else 'não'} {marca}")
