"""Bancada do Resolve para o B14/B16 (máscara): o `.prproj` do Premiere passa pelo De Lá Pra Cá (`prproj_para_drt`), entra no
Resolve aberto (scripting externo), o Fusion é montado pelo gêmeo Python do app e cada quadro sai num still com a agulha
CONFERIDA (o `SetCurrentTimecode` às vezes não pega — banco `drt-drp/estruturas.md`). A régua é a do `lab.mascara_b14`.

    python -m lab.bancadas.resolve_mascara_dlpc B14     (ou B16; o Resolve aberto num projeto de teste)

Precisa do app De Lá Pra Cá na família (achado subindo de pasta: `2 ATIVOS/_DeLaPraCa`) e do módulo de scripting do Resolve.
Grava `medida_resolve.json` ao lado do projeto da bancada do Premiere.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from .. import mascara_b14 as b14
from ..gerar import RAIZ


def _app() -> str:
    d = RAIZ
    for _ in range(4):
        cand = os.path.join(d, "2 ATIVOS", "_DeLaPraCa")
        if os.path.isdir(cand):
            return cand
        d = os.path.dirname(d)
    raise FileNotFoundError("app De Lá Pra Cá não achado subindo de pasta")


def _resolve():
    if os.name == "nt":
        os.environ.setdefault("RESOLVE_SCRIPT_API", r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
        os.environ.setdefault("RESOLVE_SCRIPT_LIB", r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll")
    else:
        os.environ.setdefault("RESOLVE_SCRIPT_API", "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting")
        os.environ.setdefault("RESOLVE_SCRIPT_LIB", "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so")
    sys.path.append(os.path.join(os.environ["RESOLVE_SCRIPT_API"], "Modules"))
    import DaVinciResolveScript as dvr                        # noqa: E402 — só existe com o Resolve instalado
    r = dvr.scriptapp("Resolve")
    if r is None:
        raise SystemExit("sem conexão com o Resolve (aberto, com um projeto?)")
    return r


CASOS = {
    "B14": {"trab": os.path.join(RAIZ, "saida", "bancadas", "premiere", "B14_MASCARA"), "projeto": "B14 MASCARA.prproj",
            "seq": "B14"},
    "B16": {"trab": os.path.join(RAIZ, "saida", "bancadas", "premiere", "B16_NEST_MASCARA"),
            "projeto": "B16 NEST MASCARA.prproj", "seq": "B16"},
}


def drt(caso: str) -> str:
    """O DRT pelo De Lá Pra Cá (o mesmo comando do produto, com o Python do app)."""
    c = CASOS[caso]
    app = _app()
    py = os.path.join(app, ".venv-win", "Scripts", "python.exe") if os.name == "nt" else os.path.join(app, ".venv", "bin", "python")
    saida = os.path.join(c["trab"], f"{caso}.drt")
    subprocess.run([py, "-m", "tools.prproj_para_drt", os.path.join(c["trab"], c["projeto"]), c["seq"], saida],
                   cwd=os.path.join(app, "motor"), check=True, capture_output=True,
                   env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return saida


def medir(caso: str, quadros: list[int]) -> list:
    """Importa o DRT, aplica o Fusion e devolve {quadro: caminho do still}."""
    c = CASOS[caso]
    sys.path.insert(0, os.path.join(_app(), "motor"))
    from drp.fusion_clipe import aplicar_relatorio            # noqa: E402 — o gêmeo Python do app
    arq_drt = drt(caso)
    rel = json.load(open(os.path.splitext(arq_drt)[0] + ".relatorio.json", encoding="utf-8"))
    r = _resolve()
    pr = r.GetProjectManager().GetCurrentProject()
    tl = pr.GetMediaPool().ImportTimelineFromFile(arq_drt, {"timelineName": f"{caso} " + time.strftime("%H%M%S"),
                                                            "importSourceClips": True})
    pr.SetCurrentTimeline(tl)
    res = aplicar_relatorio(tl, rel)
    print("fusion:", sum(1 for x in res if x.get("ok")), "de", len(res), flush=True)
    fps = round(float(tl.GetSetting("timelineFrameRate")))
    ini = tl.GetStartFrame()

    def tc(q):
        q += ini
        s = q // fps
        return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{q % fps:02d}"
    pasta = os.path.join(c["trab"], "resolve")
    os.makedirs(pasta, exist_ok=True)
    r.OpenPage("color")
    time.sleep(1)
    feitos = {}
    for q in quadros:
        for _ in range(8):
            tl.SetCurrentTimecode(tc(q))
            time.sleep(0.4)
            if tl.GetCurrentTimecode() == tc(q):
                break
        else:
            print("agulha não foi para", q)
            continue
        arq = os.path.join(pasta, f"r_{q:04d}.png")
        if os.path.exists(arq):
            os.remove(arq)
        time.sleep(0.4)
        pr.ExportCurrentFrameAsStill(arq)
        for _ in range(40):
            if os.path.exists(arq) and os.path.getsize(arq) > 0:
                feitos[q] = arq
                break
            time.sleep(0.25)
    r.OpenPage("edit")
    return feitos


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    caso = argv[0] if argv else "B16"
    if caso == "B16":
        from . import premiere_mascara_nest as bn
        from .. import mascara_b16 as m
        stills = medir(caso, list(range(m.inicio(len(m.PLANO)))))
        medida = bn.medir_arquivo(lambda q: b14.ler_quadro(stills[q])[2] if q in stills else None)
    else:
        from . import premiere_mascara as bb
        qs = [b14.inicio(i) + k for i, s in enumerate(b14.PLANO) for k in (range(s["quadros"]) if "anim" in s else [2])]
        stills = medir(caso, qs)
        medida = bb.medir_lista(lambda q: b14.ler_quadro(stills[q])[2] if q in stills else None, qs)
    with open(os.path.join(CASOS[caso]["trab"], "medida_resolve.json"), "w", encoding="utf-8") as f:
        json.dump(medida, f, ensure_ascii=False, indent=1)
    print(len(medida), "quadros medidos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
