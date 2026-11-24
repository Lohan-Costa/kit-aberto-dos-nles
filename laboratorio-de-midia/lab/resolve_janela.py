"""A POWER WINDOW do Resolve — o que cada número do `Body` quer dizer EM PIXELS (pedido do autor, 2026-11-20: traduzir
a Vignette da página Color do Premiere 2027 por uma janela circular; mapear as janelas, muito usadas na cor).

Os ids (lidos de gestos pilotados na paleta Window do 19.1.4, um campo por vez; banco `drt-drp/estruturas.md`):
  0x08500006 Size (50 → 1; < 50: 0,002 + 0,01996·S; ≥ 50: 1 + 0,08·(S − 50)) · 0x08500004 Aspect ((50 − A)/50)
  0x0850000B Pan / 0x0850000C Tilt ((P − 50)·81,92) · 0x08500001 Rotate (−graus/180) · 0x08500012 Opacity (0–1)
  0x08500005 Soft 1 (UI × 16) · 0x88500008 = 2 (circular) · 0x88500009 = 2 (invertida) · 0x8850000D = 288 ·
  0x88500010 = matriz identidade {10: {1: 1, 5: 1, 9: 1}}.

Aqui: um quadro BRANCO, a janela INVERTIDA e o Gain mestre 0 no nó ⇒ o render É a máscara (branco dentro, preto
fora). Mede o centro, o raio horizontal e vertical a 50 % e a largura da borda (10–90 %) em cada caso.

    python lab/resolve_janela.py            (Resolve aberto no LAB COR RESOLVE, venv com zstandard + numpy)
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np

from lab.bancadas import resolve as R
from lab.bancadas import resolve_cor as C

BRANCO = os.path.join(C.TRABALHO, "BRANCO_1080.mov")
TL = "MASCARA"
SIZE, ASPECT, PAN, TILT, ROT, OPAC, SOFT1 = 0x08500006, 0x08500004, 0x0850000B, 0x0850000C, 0x08500001, 0x08500012, 0x08500005
TIPO, INVERTIDA = 0x88500008, 0x88500009
GAIN = 0x06000020
PADRAO = {"size": 50, "aspect": 50, "pan": 50, "tilt": 50, "rot": 0, "soft": 2.0652}
CASOS = [("padrão", {}), ("Size 30", {"size": 30}), ("Aspect 30", {"aspect": 30}), ("Pan 45", {"pan": 45}),
         ("Tilt 45", {"tilt": 45}), ("Soft 10", {"soft": 10}), ("Soft 0", {"soft": 0}), ("Size 80", {"size": 80}),
         ("Pan 55", {"pan": 55}), ("Aspect 70", {"aspect": 70}), ("Soft 5", {"soft": 5}), ("Size 40", {"size": 40})]


def tamanho(s: float) -> float:
    return 0.002 + 0.01996 * s if s < 50 else 1 + 0.08 * (s - 50)


def params_janela(ui: dict, invertida: bool = True) -> list[dict]:
    u = dict(PADRAO, **ui)
    ps = [C.p_f32(ROT, -u["rot"] / 180), C.p_f32(ASPECT, (50 - u["aspect"]) / 50), C.p_f32(SOFT1, u["soft"] * 16),
          C.p_f32(SIZE, tamanho(u["size"])), C.p_f32(PAN, (u["pan"] - 50) * 81.92),
          C.p_f32(TILT, (u["tilt"] - 50) * 81.92), C.p_int(TIPO, 2)]
    if invertida:
        ps.append(C.p_int(INVERTIDA, 2))
    ps += [C.p_f32(0x8850000D, 288.0), C.p_f32(0x8850000E, 0.0), C.p_f32(0x8850000F, 0.0),
           C._campo(3, C._msg((1, 0x88500010), (2, C._msg((10, C._msg((1, 1.0), (5, 1.0), (9, 1.0)))))))]
    return ps


def no_com_janela(nid: int, janela: list[dict], cor: list[dict]) -> dict:
    """O nó de `resolve_cor.no` com DOIS correctors no campo 9 (lido do nó que a UI gravou, 19.1.4): cada `9.1` é um
    corrector, `9.1.1` o TIPO — 1 = Primaries (Gain, Sat, curvas…), 4 = Window. A cor dentro do corrector da janela é
    ignorada calada (o Gain 0 ali não escureceu nada)."""
    def corretor(tipo, params):
        return (1, C._msg((1, tipo), (3, 1), (6, C._msg((2, C._msg((1, 1)) + params)))))
    campos = [(1, nid), (2, nid), (4, 190 + 270 * (nid - 1)), (5, 180), (7, 1), (8, 44),
              (9, C._msg(corretor(1, cor), corretor(4, janela)) + C._msg((2, bytes.fromhex("0304050612")))),
              (10, bytes.fromhex("0a0a08818080800c12021002"))]
    return C._campo(7, C._msg(*campos))


def gerar_branco() -> None:
    if not os.path.exists(BRANCO):
        os.makedirs(os.path.dirname(BRANCO), exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "color=c=white:s=1920x1080:r=24000/1001:d=1", "-c:v", "prores_ks", "-profile:v", "3",
                        "-pix_fmt", "yuv422p10le", BRANCO], check=True)


def quadro(arquivo: str, n: int) -> np.ndarray:
    """O quadro n como Y' de 8 bits normalizado (0 = 16, 1 = 235)."""
    cru = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", arquivo, "-vf", f"select=eq(n\\,{n})", "-vframes", "1",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return (np.frombuffer(cru, np.uint8).reshape(1080, 1920).astype(float) - 16) / 219


def _PRODUCAO-A(perfil: np.ndarray, nivel: float) -> tuple[float, float]:
    """As duas posições (subpixel) em que o perfil cruza `nivel`, a da esquerda e a da direita."""
    acima = np.where(perfil >= nivel)[0]
    if len(acima) == 0:
        return float("nan"), float("nan")
    a, b = acima[0], acima[-1]
    def interp(i, j):
        return i + (nivel - perfil[i]) / (perfil[j] - perfil[i]) * (j - i) if perfil[j] != perfil[i] else float(i)
    esq = interp(a - 1, a) if a > 0 else float(a)
    dir_ = interp(b, b + 1) if b + 1 < len(perfil) else float(b)
    return esq, dir_


def medir_mascara(m: np.ndarray) -> dict:
    total = m.clip(0, 1).sum()
    if total < 1:
        return {"vazia": True}
    ys, xs = np.mgrid[0:1080, 0:1920]
    cx, cy = float((xs * m.clip(0, 1)).sum() / total), float((ys * m.clip(0, 1)).sum() / total)
    lin, col = m[int(round(cy))], m[:, int(round(cx))]
    out = {"centro": [round(cx, 1), round(cy, 1)], "max": round(float(m.max()), 3), "min": round(float(m.min()), 3)}
    for nome, perfil in (("h", lin), ("v", col)):
        e50, d50 = _PRODUCAO-A(perfil, 0.5)
        e10, d10 = _PRODUCAO-A(perfil, 0.1)
        e90, d90 = _PRODUCAO-A(perfil, 0.9)
        out[f"raio_{nome}"] = round((d50 - e50) / 2, 1)
        out[f"borda_{nome}"] = round(((e90 - e10) + (d10 - d90)) / 2, 1)     # 10 → 90 %
    return out


def main() -> None:
    gerar_branco()
    r = R.conectar()
    p = C.projeto(r)
    pool = p.GetMediaPool()
    clipe = next((c for c in pool.GetRootFolder().GetClipList() or []
                  if c.GetClipProperty("File Name") == os.path.basename(BRANCO)), None)
    if clipe is None:
        pool.SetCurrentFolder(pool.GetRootFolder())
        clipe = pool.ImportMedia([BRANCO])[0]
    tl = C.achar_timeline(p, TL)
    if tl is not None and len(tl.GetItemListInTrack("video", 1) or []) != len(CASOS):
        p.GetMediaPool().DeleteTimelines([tl])
        tl = None
    if tl is None:
        tl = pool.CreateEmptyTimeline(TL)
        p.SetCurrentTimeline(tl)
        pool.AppendToTimeline([{"mediaPoolItem": clipe, "startFrame": 0, "endFrame": C.QUADROS, "mediaType": 1}
                               for _ in CASOS])
    p.SetCurrentTimeline(tl)
    r.OpenPage("color")
    itens = sorted(tl.GetItemListInTrack("video", 1) or [], key=lambda it: it.GetStart())
    for (nome, ui), it in zip(CASOS, itens):
        b = C.body([no_com_janela(1, params_janela(ui), [C.p_f32(GAIN, 0.0)])])
        print(nome, "aplicado" if C.aplicar(tl, it, b, "janela_" + nome.replace(" ", "_")) else "FALHOU", flush=True)
    C.salvar(r)
    arq = C.renderizar(r, TL, "MASCARA")
    medidas = []
    for k, (nome, ui) in enumerate(CASOS):
        m = medir_mascara(quadro(arq, k * C.QUADROS + C.MEIO))
        medidas.append({"caso": nome, "ui": ui, **m})
        print(json.dumps(medidas[-1], ensure_ascii=False), flush=True)
    json.dump(medidas, open(arq.replace(".mov", "_medidas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
