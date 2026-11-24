import json
import numpy as np
import avb
from scipy.ndimage import gaussian_filter1d, uniform_filter1d
import os
B = os.environ.get("BIN_AVB", r"%USERPROFILE%\Documents\Avid Projects\DLPC LAB ESTABILIZADOR\DLPC LAB ESTABILIZADOR Bin.avb")
with avb.open(B) as f:
    td = list(f.read_object(int(os.environ.get("OBJ", "130"))).property_data["trackman"].data_slots.tracker_data)[0]
    px = np.array([cp.value for cp in list(td.clips)[0].control_points]) * 1920
    py = np.array([cp.value for cp in list(td.clips)[1].control_points]) * 1080
import sys
M = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "render_medido.json"))
u = np.array([[m["ux"], m["uy"]] for m in M]); p = np.stack([px, py], 1)
def nota(sm, nome, modos=("nearest", "reflect", "mirror")):
    out = []
    for modo in modos:
        s = np.stack([sm(px, modo), sm(py, modo)], 1)
        h = p - s
        off = (u - h).mean(0)
        rms = np.sqrt(((u - h - off) ** 2).mean(0))
        out.append((rms.mean(), modo, rms.round(2), off.round(2)))
    return min(out)[0], nome, min(out)
res = []
for w in range(15, 301, 2):
    res.append(nota(lambda x, m, w=w: uniform_filter1d(x, w, mode=m), f"média {w}"))
for sg in np.arange(4, 80, 1.0):
    res.append(nota(lambda x, m, sg=sg: gaussian_filter1d(x, sg, mode=m), f"gauss σ{sg:.0f}"))
def expo(x, a):
    f = np.empty_like(x); f[0] = x[0]
    for i in range(1, len(x)): f[i] = a * f[i-1] + (1 - a) * x[i]
    b = np.empty_like(x); b[-1] = f[-1]
    for i in range(len(x) - 2, -1, -1): b[i] = a * b[i+1] + (1 - a) * f[i]
    return b
for a in np.arange(0.5, 0.99, 0.01):
    res.append(nota(lambda x, m, a=a: expo(x, a), f"exp ida-volta {a:.2f}", modos=("-",)))
for r in sorted(res)[:10]:
    print(f"{r[0]:.3f}  {r[1]:22s} modo={r[2][1]} rms={r[2][2]} desvio={r[2][3]}")
