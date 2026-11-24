# ⚠️ REGISTRO HISTÓRICO — script de UMA rodada, na máquina do autor: os caminhos abaixo são os do SSD de trabalho
# dele e não existem noutra máquina. O que se mediu está registrado no banco (bancodedadosnles). Para repetir,
# peça ao Claude para adaptar: achar o laboratório SUBINDO de pasta e gerar a mídia por uma receita
# (skill ciclo-laboratorio) — nunca com o material de uma produção.
"""Compara ref-2026 (Mac) × win-2023 (Windows) frame a frame com o PSNR do ffmpeg (inf = idêntico)."""
import json, os, re, subprocess, sys
B = "/Volumes/_transfer/LABORATORIO - TESTE PREMIERE 2023/LAB 26 PARA 23"
sys.path.insert(0, "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia")
from lab.ffmpeg import achar


def ffmpeg():
    return achar("ffmpeg")


def psnr(a, b):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", a, "-i", b, "-lavfi", "[0:v]format=rgb24[x];[1:v]format=rgb24[y];[x][y]psnr", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"average:(\S+)", r.stderr)
    if not m:
        t = re.search(r"(Input #1.*|Error.*|Invalid.*)", r.stderr)
        return None, (t.group(1)[:120] if t else r.stderr[-200:])
    v = m.group(1)
    return (float("inf") if v == "inf" else float(v)), ""


tot = {}
CASOS = sys.argv[1:]
for caso in sorted(os.listdir(os.path.join(B, "ref-2026"))):
    if CASOS and caso not in CASOS:
        continue
    pr = os.path.join(B, "ref-2026", caso)
    if not os.path.isdir(pr):
        continue
    linhas = []
    for f in sorted(os.listdir(pr)):
        if not f.endswith(".png") or f.startswith("._"):
            continue
        w = os.path.join(B, "win-2023", caso, f)
        if not os.path.exists(w):
            linhas.append((f, None, "FALTA no Windows")); continue
        v, err = psnr(os.path.join(pr, f), w)
        linhas.append((f, v, err))
    tot[caso] = linhas
    ok = sum(1 for _, v, _ in linhas if v is not None and v >= 40)
    print(f"\n== {caso}: {ok}/{len(linhas)} frames com PSNR >= 40 dB (inf = idêntico)")
    for f, v, err in linhas:
        if v is None or v < 40:
            print(f"   {f:45s} {'%.1f dB' % v if v is not None else ''} {err}")
if not CASOS:
  json.dump({c: [(f, v if v != float('inf') else 'inf', e) for f, v, e in l] for c, l in tot.items()},
          open(os.path.join(B, "comparacao-lab26.json"), "w"), indent=1)
