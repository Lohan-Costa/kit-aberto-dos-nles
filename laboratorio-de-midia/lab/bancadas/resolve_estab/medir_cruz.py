from comum import *
import json, subprocess, numpy as np, cv2, glob
import estabilizacao as E
from aaf.leitura import ler_timeline_aaf
TR = sys.argv[1]; IN = int(sys.argv[2]); SEG = int(sys.argv[3])   # trilha, In da mídia (DRT), índice do segmento
pasta = AQUI + f"/cruz_V{TR}"; info = json.load(open(pasta + "/info.json"))
W, H = 960, 540
def cinza(img): return cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (W, H), interpolation=cv2.INTER_AREA).astype(np.float32)
saida = [cinza(cv2.imread(f)) for f in sorted(glob.glob(pasta + "/0*.png"))]
j0, n = info["j0"], info["n"]
b = subprocess.run(["ffmpeg", "-v", "error", "-i", info["arquivo"], "-vf",
                    f"select=between(n\\,{IN + j0}\\,{IN + j0 + n - 1}),scale={W}:{H}", "-vsync", "0",
                    "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fonte = [np.frombuffer(b[i*W*H:(i+1)*W*H], np.uint8).reshape(H, W).astype(np.float32) for i in range(len(b)//(W*H))]
print("quadros", len(saida), len(fonte))
ROI = (slice(40, 340), slice(560, 940)) if len(sys.argv) > 4 else (slice(0, H), slice(0, W))
h, w = ROI[0].stop - ROI[0].start, ROI[1].stop - ROI[1].start
jan = cv2.createHanningWindow((w, h), cv2.CV_32F)
def trilha(fr):
    return np.array([cv2.phaseCorrelate(np.ascontiguousarray(fr[0][ROI]), np.ascontiguousarray(f[ROI]), jan)[0] for f in fr])
ts, to = trilha(fonte), trilha(saida)
L = ler_timeline_aaf("/Volumes/SSD/MIDIAS DE TESTES/1 PRODUCOES/PRODUCAO-A/PRODA_RELINKER_ALTA.aaf")
d = E.dados_do_segmento(L["segments"][SEG]); u = np.array(E.correcao(d))[j0:j0+n] * [W, H]
z = d["zoom"]
# previsto: a saída = zoom( fonte deslocada de −u ) → o conteúdo anda (s − (u − u0))·z
prev = (ts - (u - u[0])) * z
def tremor(t): 
    from estabilizacao import _gauss_nearest
    g = np.stack([_gauss_nearest(list(t[:, 0]), 6), _gauss_nearest(list(t[:, 1]), 6)], 1)
    return np.sqrt(((t - g) ** 2).mean(0))
print("tremor (rms px a 960, acima do suavizado σ6): fonte", tremor(ts).round(2), "saída", tremor(to).round(2))
print("saída × previsto pela conta do Avid: rms", np.sqrt(((to - prev) ** 2).mean(0)).round(2), "px; corr x/y",
      np.corrcoef(to[:, 0], prev[:, 0])[0, 1].round(3), np.corrcoef(to[:, 1], prev[:, 1])[0, 1].round(3))
print("se fosse o sinal trocado: rms", np.sqrt(((to - (ts + (u - u[0])) * z) ** 2).mean(0)).round(2))
