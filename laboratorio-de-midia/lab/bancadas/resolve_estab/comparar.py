from comum import *
import subprocess, numpy as np, cv2, sys
W, H = 1920, 1080
def quadro(arq, k):
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-vf", f"select=eq(n\\,{k})", "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.uint8).reshape(H, W).astype(np.float32)
def corr(a, b, m=60):
    a, b = a[m:-m, m:-m], b[m:-m, m:-m]
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
KS = (30, 40, 72, 100, 108)
for var in sys.argv[1:]:
    linha = []
    for k in (KS if var == "M" else (5, 20, 40, 72, 100, 130)):
        ref = quadro(REND, k)
        img = cv2.imread(AQUI + f"/quadros_{var}/{k:03d}.png", cv2.IMREAD_GRAYSCALE).astype(np.float32) if var != "T" else quadro(TREM, k)
        if img.shape != ref.shape: img = cv2.resize(img, (W, H))
        (dx, dy), _ = cv2.phaseCorrelate(ref, img)
        linha.append(f"{k}:{corr(ref, img):.3f}({dx:+.1f},{dy:+.1f})")
    print(var, " ".join(linha))
