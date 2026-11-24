"""Mede no Premiere 2026 (Mac, pela ponte) como ele converte cada LOG de câmera para Rec.709 e para ACEScct, e grava a LUT
(.cube 17³) que o rebaixamento para o 2023 embute numa Lumetri (`prproj_downgrade.COR_LOG` / `lut_embutida`).

Método (o do S-Log3, provado no 23.2 em 2026-10-07): a CARTA — 17³ = 4913 quadrados de 20 px, 96 por linha, valores n/16 com o
vermelho variando mais rápido, ProRes 4444 12 bits (`saida/bancadas/slog3/carta_cru.mov`) — é importada uma vez POR LOG, o
espaço de cor do clipe é sobrescrito com aquele log, uma sequência é criada a partir dele (Rec.709, e outra em ACEScct) e o
quadro de 1 s é exportado. O centro de cada quadrado é o valor de saída daquele nó da LUT. O nome que vai na tabela é o que o
26 GRAVA no projeto (`OverriddenColorSpace` → `colorProfileName`), lido do .prproj salvo — não o do menu.

    python3 -m lab.bancadas.carta_log [medir] [luts] [17|33]      (padrão: 33 — a 17³ erra nos logs íngremes)
"""
from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARTA = os.path.join(RAIZ, "saida", "bancadas", "slog3", "carta_cru.mov")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "logs")
MOLDES = os.path.join(RAIZ, "lab", "moldes")
VERSAO = "26.0.2"

LOGS = ["Apple Log/Rec. 2020", "ARRI LogC3/Wide Gamut3", "ARRI LogC4/Wide Gamut4", "Canon Log/Cinema Gamut",
        "Canon Log2/Cinema Gamut", "Canon Log3/Cinema Gamut", "DJI D-Log/D-Gamut", "Fuji F-Log/Rec. 2020",
        "Fuji F-Log2/Rec. 2020", "Leica L-Log/Rec. 2020", "Nikon N-Log/Rec2020", "Panasonic V-Log/V-Gamut",
        "Red Log3G10/Wide Gamut", "Sony S-Log/S-Gamut", "Sony S-Log2/S-Gamut", "Sony S-Log3/S-Gamut3",
        "Sony S-Log3/S-Gamut3.Cine"]


POR_QUADRO = 96 * 54            # quadrados de 20 px num quadro 1920×1080


def gerar_carta(n: int, destino: str) -> int:
    """A carta n³ como vídeo ProRes 4444 12 bits faixa de vídeo (o mesmo caminho da 17³ provada): quadrados de 20 px, 96 por
    linha, nó i = (r, g, b) = (i % n, i // n % n, i // n²) / (n − 1), em ceil(n³ / 5184) quadros. Devolve o nº de quadros."""
    import array
    total = n ** 3
    quadros = -(-total // POR_QUADRO)
    from lab import ffmpeg
    cmd = [ffmpeg.achar("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", "1920x1080", "-r", "25",
           "-i", "-", "-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuv444p12le", "-color_range", "tv",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", destino]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for q in range(quadros + 2):                                   # 2 quadros a mais: nenhuma exportação cai no fim
        img = array.array("H", bytes(1920 * 1080 * 6))
        for k in range(POR_QUADRO):
            i = q * POR_QUADRO + k
            if q >= quadros or i >= total:
                break
            r, g, b = (round((i % n) * 65535 / (n - 1)), round((i // n % n) * 65535 / (n - 1)), round((i // n // n) * 65535 / (n - 1)))
            x0, y0 = (k % 96) * 20, (k // 96) * 20
            linha = array.array("H", [r, g, b] * 20)
            for y in range(y0, y0 + 20):
                o = (y * 1920 + x0) * 3
                img[o:o + 60] = linha
        pr.stdin.write(img.tobytes())
    pr.stdin.close()
    if pr.wait():
        raise RuntimeError("ffmpeg não gravou a carta")
    return quadros


def slug(nome: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")


def medir(logs: list[str] = LOGS, n: int = 33) -> dict:
    from lab.bancadas import premiere as p, premiere_projeto as pp
    trab = _trab(n)
    os.makedirs(trab, exist_ok=True)
    J = json.dumps
    cru = os.path.join(trab, f"carta{n}_cru.mov")
    if not os.path.exists(cru):
        gerar_carta(n, cru)
    nq = -(-n ** 3 // POR_QUADRO)
    arqs = {"CRU": cru}
    for nome in logs:
        a = os.path.join(trab, f"carta_{slug(nome)}.mov")
        if not os.path.exists(a):
            shutil.copy(cru, a)
        arqs[nome] = a
    if not p._premiere_vivo():
        p.abrir_premiere("2026")
    p.esperar_ponte(300)
    p.executar("""(function(){ var a=''; try { a = app.project.path; } catch (e) {} if (a) app.project.closeDocument(0, 0); return a; })()""")
    proj = os.path.join(trab, "LOGS 2026.prproj")
    if os.path.exists(proj):
        os.remove(proj)
    p.executar("app.newProject(%s)" % J(proj), timeout=120)
    time.sleep(3)
    p.executar(pp._JS + "app.project.importFiles(%s, true, app.project.rootItem, false)" % J(list(arqs.values())), timeout=300)
    feitos = {}
    for nome, arq in arqs.items():
        if nome == "CRU":
            ok = "sem override"
        else:
            ok = p.executar(pp._JS + """(function(){ var c = _lab_midia(%s), l = c.getOverrideColorSpaceList, alvo = null;
              for (var i = 0; i < l.length; i++) if (l[i].name == %s) alvo = l[i];
              if (!alvo) return 'sem ' + %s; c.setOverrideColorSpace(alvo); return c.isColorManagedMedia(); })()""" % (J(arq), J(nome), J(nome)))
        feitos[nome] = {"override": ok}
        for esp in (("709",) if nome == "CRU" else ("709", "ACEScct")):
            seq = f"{slug(nome)} {esp}"
            p.executar(pp._JS + """(function(){ var c = _lab_midia(%s);
              var s = app.project.createNewSequenceFromClips(%s, [c], app.project.rootItem); s.name = %s;
              if (%s) { var st = s.getSettings(), l = st.workingColorSpaceList, a = null;
                for (var i = 0; i < l.length; i++) if (l[i].name == "ACEScct") a = l[i]; st.workingColorSpace = a; s.setSettings(st); }
              return s.name; })()""" % (J(arq), J(seq), J(seq), "true" if esp == "ACEScct" else "false"), timeout=120)
            bons = 0
            for q in range(nq):
                alvo = os.path.join(trab, f"{seq.replace(' ', '_')}_q{q}")
                if os.path.exists(alvo + ".png"):
                    os.remove(alvo + ".png")
                p.executar("""(function(){ var q=null; for (var i=0;i<app.project.sequences.numSequences;i++) if (app.project.sequences[i].name==%s) q=app.project.sequences[i];
                  app.project.openSequence(q.sequenceID); var s=app.project.activeSequence; s.setPlayerPosition(%s);
                  app.enableQE(); var qs=qe.project.getActiveSequence(); return qs.exportFramePNG(qs.CTI.timecode, %s); })()""" % (J(seq), J(str(q * 10160640000)), J(alvo)), timeout=120)
                t = time.time()
                while (not os.path.exists(alvo + ".png") or os.path.getsize(alvo + ".png") == 0) and time.time() - t < 30:
                    time.sleep(0.3)
                bons += os.path.exists(alvo + ".png")
            feitos[nome][esp] = f"{bons}/{nq}"
        print(nome, feitos[nome], flush=True)
    p.executar("app.project.save()", timeout=120)
    time.sleep(3)
    p.executar("app.project.closeDocument(0, 0)", timeout=60)
    # o nome que o 26 GRAVA para cada log (a chave do COR_LOG)
    with open(proj, "rb") as fh:
        xml = gzip.decompress(fh.read()).decode("utf-8")
    gravados = sorted(set(json.loads(m).get("baseColorProfile", {}).get("colorProfileName", "")
                          for m in re.findall(r"<OverriddenColorSpace>([^<]+)</OverriddenColorSpace>", xml) if m.strip() not in ("{}", "")))
    with open(os.path.join(trab, "medicao.json"), "w", encoding="utf-8") as fh:
        json.dump({"versao": VERSAO, "n": n, "feitos": feitos, "nomes_gravados": gravados}, fh, ensure_ascii=False, indent=1)
    return {"feitos": feitos, "nomes_gravados": gravados}


def _trab(n: int) -> str:
    return TRAB if n == 17 else TRAB + str(n)


def _quadrados(prefixo: str, n: int = 17) -> list:
    """Os n³ valores de saída (0–1), do centro (8×8) de cada quadrado, dos PNG `<prefixo>_q<k>.png` (17³: um `<prefixo>.png`)."""
    import array
    w, out, total = 1920, [], n ** 3
    k = 0
    while len(out) < total:
        png = prefixo + ".png" if (n == 17 and os.path.exists(prefixo + ".png")) else f"{prefixo}_q{k}.png"
        b = subprocess.run(["ffmpeg", "-v", "error", "-i", png, "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"], capture_output=True, check=True).stdout
        a = array.array("H")
        a.frombytes(b)
        for i in range(min(POR_QUADRO, total - len(out))):
            cx, cy = (i % 96) * 20 + 6, (i // 96) * 20 + 6
            soma = [0, 0, 0]
            for y in range(cy, cy + 8):
                base = (y * w + cx) * 3
                for x in range(8):
                    for c in range(3):
                        soma[c] += a[base + x * 3 + c]
            out.append([v / 64 / 65535 for v in soma])
        k += 1
    return out


def luts(n: int = 33) -> dict:
    """Uma .cube n³ por log e espaço, a partir dos PNG medidos. Devolve {nome: {"": arq709, "ACEScct": arqACES}}."""
    tabela, trab = {}, _trab(n)
    sufixo = "" if n == 17 else f"-{n}"
    for nome in LOGS:
        por = {}
        for esp, chave in (("709", ""), ("ACEScct", "ACEScct")):
            prefixo = os.path.join(trab, f"{slug(nome)}_{esp}")
            if not (os.path.exists(prefixo + ".png") or os.path.exists(prefixo + "_q0.png")):
                continue
            vals = _quadrados(prefixo, n)
            arq = f"{slug(nome)}-{'rec709' if esp == '709' else 'acescct'}-{VERSAO}{sufixo}.cube"
            with open(os.path.join(MOLDES, arq), "w", encoding="utf-8") as fh:
                fh.write(f'TITLE "{nome} para {"Rec.709" if esp == "709" else "ACEScct"} como o Premiere {VERSAO} converte"\n')
                fh.write(f"# medida: carta {n}^3 (ProRes 4444 12 bits, faixa de video) no {VERSAO} Mac (laboratorio-de-midia, carta_log.py)\n")
                fh.write(f"LUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n")
                for r, g, b in vals:
                    fh.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
            por[chave] = arq
        tabela[nome] = por
    return tabela


if __name__ == "__main__":
    passos = [a for a in sys.argv[1:] if not a.isdigit()] or ["medir", "luts"]
    n = int(next((a for a in sys.argv[1:] if a.isdigit()), "33"))
    if "medir" in passos:
        print(json.dumps(medir(n=n), ensure_ascii=False, indent=1))
    if "luts" in passos:
        print(json.dumps(luts(n), ensure_ascii=False, indent=1))
