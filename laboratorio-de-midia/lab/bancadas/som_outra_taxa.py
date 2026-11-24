"""O SOM de uma fonte de OUTRA TAXA no DRT (Ciclo Assist, 2026-11-23): o A002C001 do BL08 (29,97 DF, bipe de 400 Hz a cada
segundo de TC) posto do quadro 364 numa timeline de 23,976 — o `<In>` = 364 × 0,8 = 291,2. O DRT nativo do Resolve
21.1 grava `291|<fração>` no vídeo E no áudio; o writer do Conformar gravava o áudio inteiro (291 = 8,3 ms antes).

    <assist>/.venv/bin/python som_outra_taxa.py drt          # os dois DRTs: o do writer (fração) e o "antigo" (291)
    (o Resolve importa e renderiza o som: `ImportTimelineFromFile` + render WAV — pela API, ver o diário)
    <assist>/.venv/bin/python som_outra_taxa.py medir <render.wav> [<render.wav> …]

A verdade: o 1º bipe da fonte depois do quadro 364 (12,14548 s) — no render ele cai em bipe − 364/29,97.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
p = AQUI
while not os.path.isdir(os.path.join(p, "2 ATIVOS")):
    p = os.path.dirname(p)
CONFORMAR = os.path.join(p, "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar")
LAB = os.path.abspath(os.path.join(AQUI, "..", ".."))
ORIG = os.path.join(LAB, "saida", "baselight", "BL08_CASAMENTO", "ORIGINAIS", "DIA02", "A004", "A002C001.mov")
TRAB = os.path.join(LAB, "saida", "baselight", "BL09_ATUALIZAR", "som_outra_taxa")
FPS_TL, FPS_F, Q, DUR = 24000 / 1001, 30000 / 1001, 364, 76


def _seg(audio: bool) -> dict:
    return {"timeline_tc_in": "00:00:00:00", "timeline_tc_out": "00:00:03:04", "duration_frames": DUR,
            "source_start_frames": Q, "source_fps": FPS_F, "clip_name": "A002C001", "track": 1, "is_gap": False,
            "is_transition": False, "is_effect": False, "is_audio": audio, "speed_ratio": FPS_TL / FPS_F,
            "conform_ratio": 1.0, "relative_speed": 1.0, "motion_class": "native", "effects": [], "disabled": False,
            "media_ref": {"local_path": ORIG, "descriptor_type": "prproj", "source_fps": FPS_F}}


def drt() -> None:
    sys.path.insert(0, os.path.join(CONFORMAR, "motor"))
    from drp.writer import build_drt
    os.makedirs(TRAB, exist_ok=True)
    novo = os.path.join(TRAB, "WRITER_FRACAO.drt")
    build_drt([_seg(False), _seg(True)], [{"segment_index": 0, "matched_path": ORIG},
                                          {"segment_index": 1, "matched_path": ORIG}], novo,
              timeline_name="WRITER FRACAO", timeline_fps=FPS_TL, timeline_start_frames=0, timeline_size=(1920, 1080))
    # o "antigo": o mesmo DRT com o In do ÁUDIO inteiro (o writer de antes)
    antigo = os.path.join(TRAB, "WRITER_INTEIRO.drt")
    with zipfile.ZipFile(novo) as zi, zipfile.ZipFile(antigo, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in zi.namelist():
            b = zi.read(n)
            if "SeqContainer" in n:
                t = b.decode("utf-8")
                t = re.sub(r"(<Sm2TiAudioClip\b.*?<In>)291\|[0-9a-f]{16}(</In>)", r"\g<1>291\2", t, flags=re.S)
                t = t.replace("WRITER FRACAO", "WRITER INTEIRO")
                b = t.encode("utf-8")
            elif n.endswith(".xml"):
                b = b.replace(b"WRITER FRACAO", b"WRITER INTEIRO")
            zo.writestr(n, b)
    for f in (novo, antigo):
        with zipfile.ZipFile(f) as z:
            txt = "".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if "SeqContainer" in n)
        print(os.path.basename(f), "vídeo In", re.findall(r"<Sm2TiVideoClip\b.*?<In>([^<]*)</In>", txt, re.S),
              "áudio In", re.findall(r"<Sm2TiAudioClip\b.*?<In>([^<]*)</In>", txt, re.S))


def _som(arq: str, ss: float = 0.0, t: float | None = None):
    import numpy as np
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss:.6f}", "-i", arq] + (["-t", f"{t:.6f}"] if t else []) + \
          ["-ac", "1", "-ar", "48000", "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def _inicio_do_bipe(a, depois: int = 0, limiar: float = 0.5) -> float:
    """A amostra em que o próximo bipe COMEÇA depois de `depois` (limiar 0,5: o bipe chega a 0,9; o tom de canal do lab fica em 0,14): o envelope (|x| máximo em 0,5 ms) estava abaixo do
    limiar por pelo menos 20 ms e passa dele — a borda de SUBIDA (um bipe dura mais de 100 ms)."""
    import numpy as np
    w = 24
    x = np.abs(a[depois:depois + (len(a) - depois) // w * w]).reshape(-1, w).max(1)
    acima = x > limiar
    quieto = 40                                         # 40 × 0,5 ms = 20 ms abaixo antes da subida
    for k in range(quieto, len(acima)):
        if acima[k] and not acima[k - quieto:k].any():
            bloco = np.abs(a[depois + k * w: depois + (k + 1) * w])
            return depois + k * w + int(np.argmax(bloco > limiar))
    raise ValueError("nenhum bipe depois do ponto")


def medir(*renders: str) -> None:
    a = _som(ORIG)
    ini = Q / FPS_F                                    # 12,14548 s: o quadro 364 da fonte
    # o bipe SEGUINTE ao do começo (o 1º cai a menos de 1 ms do início do plano: colado na borda)
    b = _inicio_do_bipe(a, depois=int(ini * 48000)) / 48000
    alvo = b - ini
    print(f"fonte: o 1º bipe depois do quadro {Q} em {b:.5f} s ⇒ no render em {alvo * 1000:.2f} ms")
    for r in renders:
        x = _som(r)
        t = _inicio_do_bipe(x, depois=0) / 48000
        print(f"{os.path.basename(r):28} bipe em {t * 1000:8.2f} ms · erro {(t - alvo) * 1000:+6.2f} ms "
              f"({(t - alvo) * FPS_TL:+.3f} quadro da timeline)")


if __name__ == "__main__":
    cmd, *resto = sys.argv[1:]
    {"drt": drt, "medir": medir}[cmd](*resto)
