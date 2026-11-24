"""A correção que o MC aplicou: para cada quadro k, a transformação de semelhança tremido_k → render_k (features AKAZE +
estimateAffinePartial2D) → escala s, rotação, e o deslocamento u no espaço da FONTE (antes do zoom em torno do centro)."""
import json, subprocess, sys
import numpy as np, cv2
sys.path.insert(0, r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia")
from lab import ffmpeg as ff
W, H = 1920, 1080
TREM = sys.argv[3] if len(sys.argv) > 3 else r"D:\PROGRAMAS COM CLAUDE\laboratorio-de-midia\saida\base\B19_ESTABILIZADOR\B19_TREMIDO.mov"
REND = "D:/PROGRAMAS COM CLAUDE/laboratorio-de-midia/saida/bancadas/avid/estab_mc/B19_MC_ESTAB" + (sys.argv[1] if len(sys.argv) > 1 else "") + ".mxf"
exe = ff.achar("ffmpeg")
def leitor(arq):
    p = subprocess.Popen([exe, "-v", "error", "-i", arq, "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H)
        if len(b) < W * H:
            return
        yield np.frombuffer(b, np.uint8).reshape(H, W)
S = float(sys.argv[2]) / 100 if len(sys.argv) > 2 else 1.0604091292619704   # DVE_SCALE_X_U (Auto-Zoom)
c = np.array([W / 2, H / 2])
# R(p) = S·(p + u − c) + c  ⇒  desfazer o zoom: R'(q) = R(S·(q − c) + c) = T(q + u)
Z = np.float32([[S, 0, c[0] - S * c[0]], [0, S, c[1] - S * c[1]]])
jan = cv2.createHanningWindow((W, H), cv2.CV_32F)
fora = []
for k, (a, b) in enumerate(zip(leitor(TREM), leitor(REND))):
    rb = cv2.warpAffine(b.astype(np.float32), Z, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
    (dx, dy), resp = cv2.phaseCorrelate(a.astype(np.float32), rb, jan)
    # phaseCorrelate devolve o deslocamento de a para rb: rb(q) = a(q − d) ⇒ T(q + u) = T(q − d) ⇒ u = −d
    fora.append({"k": k, "ux": -dx, "uy": -dy, "resp": resp})
    if k % 24 == 0:
        print(fora[-1], flush=True)
json.dump(fora, open("render_medido" + (sys.argv[1] if len(sys.argv) > 1 else "") + ".json", "w"))
print("quadros", len(fora))
