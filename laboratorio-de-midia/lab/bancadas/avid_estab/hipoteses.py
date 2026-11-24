import json
import numpy as np
import avb
B = r"%USERPROFILE%\Documents\Avid Projects\DLPC LAB ESTABILIZADOR\DLPC LAB ESTABILIZADOR Bin.avb"
with avb.open(B) as f:
    td = list(f.read_object(130).property_data["trackman"].data_slots.tracker_data)[0]
    px = np.array([cp.value for cp in list(td.clips)[0].control_points]) * 1920
    py = np.array([cp.value for cp in list(td.clips)[1].control_points]) * 1080
M = json.load(open("render_medido.json"))
ux = np.array([m["ux"] for m in M]); uy = np.array([m["uy"] for m in M])
def rel(nome, hx, hy):
    for eixo, u, h in (("x", ux, hx), ("y", uy, hy)):
        k, c = np.polyfit(h, u, 1); r = np.corrcoef(h, u)[0, 1]
        print(f"{nome:28s} {eixo}: corr {r:+.4f} u = {k:+.3f}·h {c:+.2f}  rms {np.std(u - (k*h + c)):.2f}  (sem ajuste: rms {np.sqrt(np.mean((u-h)**2)):.2f})")
rel("trava no quadro 0", px[0] - px, py[0] - py)
rel("trava na média", px.mean() - px, py.mean() - py)
for jan in (3, 5, 9, 15, 25, 49):
    kern = np.ones(jan) / jan
    sx = np.convolve(np.pad(px, jan // 2, mode="edge"), kern, "valid"); sy = np.convolve(np.pad(py, jan // 2, mode="edge"), kern, "valid")
    rel(f"suaviza média móvel {jan}", sx - px, sy - py)
print("u: média", ux.mean().round(2), uy.mean().round(2), "faixa", ux.min().round(1), ux.max().round(1))
