"""Mede cada máscara do autor contra a máscara perfeita do B10: IoU, quanto da pessoa ficou de fora e quanto de fundo
entrou. Clipes 1–5: a máscara é o ALFA do frame exportado (máscara na Opacidade). Clipe 6 (máscara na Lumetri): a máscara
é onde a cor mudou em relação à fonte."""
import json, os, subprocess, sys
sys.path.insert(0, "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia")
from lab.ffmpeg import achar
FF = achar("ffmpeg")
LAB = "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia"
OUT = LAB + "/saida/bancadas/roto26/frames"
B10 = LAB + "/saida/base/B10_ROTO"
W, H = 1920, 1080
NOMES = {1: "objeto (Opacidade)", 2: "retângulo + tracking", 3: "elipse + tracking", 4: "caneta + tracking",
         5: "caneta com keyframes", 6: "objeto (Lumetri)"}


def cru(args):
    return subprocess.run([FF, "-v", "error"] + args + ["-f", "rawvideo", "-"], capture_output=True, check=True).stdout


def quadro_video(arq, q, fmt):
    return cru(["-i", arq, "-vf", f"select=eq(n\\,{q}),format={fmt}", "-fps_mode", "passthrough", "-frames:v", "1"])


fr = json.load(open(OUT + "/frames.json"))["frames"]
res = {}
for f in fr:
    if not f["ok"]:
        continue
    c, q = f["clipe"], f["quadro_fonte"]
    perf = quadro_video(B10 + "/B10_ROTO_MASCARA_MOV-PRORES.mov", q, "gray")
    P = [b >= 126 for b in perf]
    png = OUT + "/" + f["png"]
    if c <= 5:
        a = cru(["-i", png, "-vf", "alphaextract,format=gray"])
        M = [b >= 128 for b in a]
    else:
        orig = quadro_video(B10 + "/B10_ROTO_MOV-PRORES.mov", q, "rgb24")
        got = cru(["-i", png, "-vf", "format=rgb24"])
        M = [max(abs(orig[i] - got[i]), abs(orig[i + 1] - got[i + 1]), abs(orig[i + 2] - got[i + 2])) > 10 for i in range(0, len(orig), 3)]
    inter = sum(1 for p, m in zip(P, M) if p and m)
    uniao = sum(1 for p, m in zip(P, M) if p or m)
    np_, nm = sum(P), sum(M)
    if np_ == 0:
        continue
    res.setdefault(c, []).append({"q": q, "iou": inter / uniao if uniao else 1.0, "fora": 1 - inter / np_, "sobra": (nm - inter) / np_})
resumo = {}
for c, l in sorted(res.items()):
    media = lambda k: sum(x[k] for x in l) / len(l)
    pior = min(l, key=lambda x: x["iou"])
    resumo[c] = {"mascara": NOMES[c], "frames": len(l), "iou_medio": round(media("iou"), 3), "pessoa_fora_%": round(100 * media("fora"), 1),
                 "fundo_dentro_%": round(100 * media("sobra"), 1), "pior_quadro": pior["q"], "pior_iou": round(pior["iou"], 3)}
    print(f"{c} {NOMES[c]:26s} IoU médio {resumo[c]['iou_medio']:.3f}  pessoa fora {resumo[c]['pessoa_fora_%']:5.1f}%  "
          f"fundo dentro {resumo[c]['fundo_dentro_%']:6.1f}%  pior q{pior['q']} IoU {pior['iou']:.3f}")
json.dump({"resumo": resumo, "por_quadro": res}, open(OUT + "/iou.json", "w"), indent=1)
