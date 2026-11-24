"""Bancada DERIVA no Resolve (Windows, API externa + piloto) — pacote `receitas/deriva/` (autor, 2026-10-30).

    py -m lab.bancadas.resolve_deriva preparar D03_PULLUP_1000PPM      (projeto, import, as duas timelines)
    py -m lab.bancadas.resolve_deriva corrigir D03_PULLUP_1000PPM      (pilotado: Change Clip Speed na A2)
    py -m lab.bancadas.resolve_deriva renderizar D03_PULLUP_1000PPM    (só a A2 de cada timeline)
    py -m lab.bancadas.resolve_deriva medir D03_PULLUP_1000PPM         (régua × verdade → resultados/)

As timelines (projeto `LAB DERIVA <Dnn>` na pasta LABORATORIO do Project Manager):
- `TL SEM CORRECAO` — V1/A1 a câmera inteira; A2 (mono) o som direto pelo TC (o editor sincronizou no começo).
- `TL CORRIGIDA` — a mesma, com a A2 na velocidade que a RÉGUA mediu nos arquivos (não a da verdade: é o que o app
  faria), digitada no Change Clip Speed com 6 casas e SEM Pitch Correction.
O render leva só a A2 (A1 desligada pelo `SetTrackEnable`); a régua compara o render com o som guia ORIGINAL da
câmera: como o vídeo/A1 começam no quadro 0 da timeline, o tempo do render = o tempo do arquivo da câmera.

⛔ A API do Resolve 19 não escreve velocidade (o `GetProperty` do áudio vem vazio; não há setter) — por isso o piloto.
⛔ O Change Clip Speed é modal e FECHA se o foco sair do Resolve (`devolver_ao_terminal` no meio = diálogo perdido e
   a digitação na timeline, 2026-10-30): o gesto inteiro vai num comando só.
"""
from __future__ import annotations

import json
import os
import sys
import time

from . import resolve as b
from .. import tc as _tc

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PILOTO = os.path.join(os.path.dirname(RAIZ), "piloto")


def _caso(nome: str) -> tuple[str, dict]:
    pasta = os.path.join(RAIZ, "saida", "deriva", nome)
    with open(os.path.join(pasta, "verdade.json"), encoding="utf-8") as fh:
        return pasta, json.load(fh)


def _trab(nome: str) -> str:
    t = os.path.join(RAIZ, "saida", "bancadas", "resolve_deriva", nome)
    os.makedirs(os.path.join(t, "fotos"), exist_ok=True)
    return t


def _estado(nome: str) -> dict:
    f = os.path.join(_trab(nome), "resolve.json")
    if os.path.isfile(f):
        with open(f, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _gravar(nome: str, e: dict) -> None:
    with open(os.path.join(_trab(nome), "resolve.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(e, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def _projeto(r, nome: str, fps: str, criar: bool = True):
    pm = r.GetProjectManager()
    atual = pm.GetCurrentProject()
    alvo = "LAB DERIVA " + nome.split("_")[0]
    if atual and atual.GetName() == alvo:
        return atual
    pm.GotoRootFolder()
    if "LABORATORIO" not in (pm.GetFolderListInCurrentFolder() or []):
        pm.CreateFolder("LABORATORIO")
    pm.OpenFolder("LABORATORIO")
    p = pm.LoadProject(alvo)
    if not p and criar:
        p = pm.CreateProject(alvo)
        p.SetSetting("timelineFrameRate", fps)            # a taxa ANTES de importar (banco)
    return p


def _timeline(p, nome):
    for i in range(1, p.GetTimelineCount() + 1):
        t = p.GetTimelineByIndex(i)
        if t.GetName() == nome:
            return t
    return None


def preparar(nome: str) -> dict:
    pasta, v = _caso(nome)
    r = b.conectar()
    fps = {"29.97": "29.97", "23.976": "23.976"}.get(v["fps"], v["fps"])
    p = _projeto(r, nome, fps)
    mp = p.GetMediaPool()
    cam_v = next(a for a in v["arquivos"] if a["papel"] == "camera")
    som_v = next(a for a in v["arquivos"] if a["papel"] == "som")
    clipes = {c.GetName(): c for c in mp.GetRootFolder().GetClipList()}
    falta = [os.path.join(pasta, a["arquivo"]) for a in (cam_v, som_v) if a["arquivo"] not in clipes]
    if falta:
        mp.ImportMedia(falta)
        clipes = {c.GetName(): c for c in mp.GetRootFolder().GetClipList()}
    cam, som = clipes[cam_v["arquivo"]], clipes[som_v["arquivo"]]
    # ⛔ numa sessão do Resolve que já tinha aberto/apagado projetos e renderizado, o AppendToTimeline passou a pôr SÓ
    # o vídeo (A1/A2 vazias; o append só de áudio devolvia o item e a trilha seguia vazia) — no D05, 2026-10-30.
    # Fechar e reabrir o Resolve resolveu. Por isso a checagem logo abaixo (timeline sem áudio = refazer).
    taxa = _tc.taxa(v["fps"])
    base = _tc.base(taxa)
    # o som começa ANTES da câmera: entra aparado na cabeça, pelo TC (quadros da timeline)
    cabeca = _tc.tc_para_quadros(cam.GetClipProperty("Start TC"), base) - _tc.tc_para_quadros(
        som.GetClipProperty("Start TC"), base)
    n_cam = int(cam.GetClipProperty("Frames"))
    e = {**_estado(nome), "caso": nome, "versao": r.GetVersionString(), "fps": v["fps"], "cabeca_do_som_quadros": cabeca,
         "start_tc": {"camera": cam.GetClipProperty("Start TC"), "som": som.GetClipProperty("Start TC")},
         "timelines": {}}
    tl = _timeline(p, "TL SEM CORRECAO")
    if tl and not tl.GetItemListInTrack("audio", 1):
        mp.DeleteTimelines([t for t in (tl, _timeline(p, "TL CORRIGIDA")) if t])
        tl = None
    if not tl:
        tl = mp.CreateEmptyTimeline("TL SEM CORRECAO")
        p.SetCurrentTimeline(tl)
        s0 = tl.GetStartFrame()
        mp.AppendToTimeline([{"mediaPoolItem": cam, "startFrame": 0, "endFrame": n_cam - 1, "trackIndex": 1,
                              "recordFrame": s0}])
        tl.AddTrack("audio", "mono")
        mp.AppendToTimeline([{"mediaPoolItem": som, "startFrame": cabeca, "endFrame": cabeca + n_cam - 1,
                              "trackIndex": 2, "mediaType": 2, "recordFrame": s0}])
    if not _timeline(p, "TL CORRIGIDA"):
        p.SetCurrentTimeline(tl)
        d = tl.DuplicateTimeline("TL CORRIGIDA")
    for n in ("TL SEM CORRECAO", "TL CORRIGIDA"):
        t = _timeline(p, n)
        e["timelines"][n] = {"audio": [[(i.GetName(), i.GetStart(), i.GetEnd(), i.GetLeftOffset())
                                        for i in (t.GetItemListInTrack("audio", k) or [])] for k in (1, 2)]}
    r.GetProjectManager().SaveProject()
    _gravar(nome, e)
    return e


def medir_arquivos(nome: str) -> dict:
    """A régua nos ARQUIVOS (câmera × som direto) — o número que o app digitaria."""
    from .. import medir_deriva
    pasta, v = _caso(nome)
    cam = next(a for a in v["arquivos"] if a["papel"] == "camera")
    som = next(a for a in v["arquivos"] if a["papel"] == "som")
    m = medir_deriva.medir(os.path.join(pasta, cam["arquivo"]), os.path.join(pasta, som["arquivo"]))
    m["verdade_ppm"] = v["deriva_ppm"]
    m["erro_ppm"] = round(m["deriva_ppm"] - v["deriva_ppm"], 3)
    e = _estado(nome)
    e["regua_nos_arquivos"] = {k: m[k] for k in m if k != "pontos"}
    _gravar(nome, e)
    return e["regua_nos_arquivos"]


#: posições no Change Clip Speed, relativas ao canto do diálogo (medidas 2026-10-30, 19.1.4, 1920×1080 escala 100 %)
SPEED, PITCH, CHANGE = (261, 127), (412, 239), (506, 389)
#: os cadeados de V1 e A1 no cabeçalho da timeline da página Edit (mesma medição)
CADEADOS = ((707, 865), (707, 905))


def _rect(h):
    import ctypes
    from ctypes import wintypes
    rc = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(h, ctypes.byref(rc))
    return rc.left, rc.top, rc.right, rc.bottom


def corrigir(nome: str, x_clipe: int, y_a2: int, velocidade_pct: str | None = None) -> dict:
    """Pilotado, 1ª metade: V1/A1 TRAVADAS pela API (senão o clique leva a A1 junto: "Multiple Clips", 2026-10-30),
    seleciona o clipe da A2 em (x_clipe, y_a2) — medidos numa foto DESTA abertura —, abre o Change Clip Speed (R) e
    digita a velocidade no campo Speed (clicado pela posição relativa ao diálogo). Foto `2_digitado` (+ recorte):
    LER antes do `confirmar`."""
    sys.path.insert(0, PILOTO)
    from piloto import maos, olhos
    from PIL import Image
    e = _estado(nome)
    vel = velocidade_pct or f"{e['regua_nos_arquivos']['velocidade_de_correcao'] * 100:.6f}"
    fotos = os.path.join(_trab(nome), "fotos")
    r = b.conectar()
    p = _projeto(r, nome, "", criar=False)
    tl = _timeline(p, "TL CORRIGIDA")
    p.SetCurrentTimeline(tl)
    tl.SetTrackLock("video", 1, True)
    tl.SetTrackLock("audio", 1, True)
    r.OpenPage("edit")
    time.sleep(1.5)
    h = olhos.janela_principal("Resolve.exe")
    reg = {"velocidade_digitada": vel, "fotos": []}
    maos.frente(h)
    time.sleep(0.4)
    maos.clicar(x_clipe, y_a2)
    time.sleep(0.6)
    reg["fotos"].append(os.path.basename(olhos.foto_da_tela(fotos, "1_selecionado")))
    maos.tecla(ord("R"))
    time.sleep(1.5)
    ds = [d for d in olhos.dialogos("Resolve.exe") if d["titulo"] == "Edit Speed Change"]
    if not ds:
        reg["fotos"].append(os.path.basename(olhos.foto_da_tela(fotos, "1b_sem_dialogo")))
        raise RuntimeError("o Change Clip Speed não abriu")
    d = ds[0]["hwnd"]
    L, T, R_, B = _rect(d)
    maos.frente(d)
    time.sleep(0.3)
    maos.clicar(L + SPEED[0], T + SPEED[1])
    time.sleep(0.3)
    maos.tecla(ord("A"), maos.CTRL)
    time.sleep(0.2)
    maos.digitar_em(d, vel)
    time.sleep(0.3)
    maos.tecla(maos.TAB)
    time.sleep(0.8)
    f = olhos.foto_da_tela(fotos, "2_digitado")
    Image.open(f).crop((L, T, R_, B)).save(f.replace(".png", "_c.png"))
    reg["fotos"].append(os.path.basename(f))
    reg["retangulo_dialogo"] = [L, T, R_, B]
    _gravar(nome, {**e, "correcao": reg})
    return reg


def confirmar(nome: str, desmarcar_pitch: bool = True) -> dict:
    """2ª metade, depois de LER a foto 2_digitado: desmarca o Pitch Correction (vem MARCADO por padrão), Change, e
    destrava V1/A1 pelos CADEADOS da interface — ⛔ o `SetTrackLock(False)` da API devolve True e NÃO destrava
    (19.1.4), e com a trilha travada o `SetTrackEnable` também não faz nada, calado: o render da A2 levaria a A1."""
    sys.path.insert(0, PILOTO)
    from piloto import maos, olhos
    from PIL import Image
    e = _estado(nome)
    fotos = os.path.join(_trab(nome), "fotos")
    ds = [d for d in olhos.dialogos("Resolve.exe") if d["titulo"] == "Edit Speed Change"]
    if not ds:
        raise RuntimeError("o diálogo não está mais aberto")
    d = ds[0]["hwnd"]
    L, T, R_, B = _rect(d)
    try:
        maos.frente(d)
        time.sleep(0.3)
        if desmarcar_pitch:
            maos.clicar(L + PITCH[0], T + PITCH[1])
            time.sleep(0.5)
            f = olhos.foto_da_tela(fotos, "3_sem_pitch")
            Image.open(f).crop((L, T, R_, B)).save(f.replace(".png", "_c.png"))
            e["correcao"]["fotos"].append(os.path.basename(f))
        maos.clicar(L + CHANGE[0], T + CHANGE[1])
        time.sleep(1.2)
        e["correcao"]["dialogo_fechou"] = not [x for x in olhos.dialogos("Resolve.exe")]
        h = olhos.janela_principal("Resolve.exe")
        maos.frente(h)
        time.sleep(0.4)
        for x, y in CADEADOS:
            maos.clicar(x, y)
            time.sleep(0.5)
        f = olhos.foto_da_tela(fotos, "4_aplicado_destravado")
        Image.open(f).crop((600, 840, 900, 960)).save(f.replace(".png", "_c.png"))
        e["correcao"]["fotos"].append(os.path.basename(f))
    finally:
        e["correcao"]["terminal"] = maos.devolver_ao_terminal()
    r = b.conectar()
    tl = r.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    e["correcao"]["travas_depois"] = [tl.GetIsTrackLocked("video", 1), tl.GetIsTrackLocked("audio", 1)]
    r.GetProjectManager().SaveProject()
    _gravar(nome, e)
    return e["correcao"]


def renderizar(nome: str, so: list[str] | None = None, prazo: float = 1800) -> dict:
    r = b.conectar()
    p = _projeto(r, nome, "", criar=False)
    e = _estado(nome)
    pasta = os.path.join(_trab(nome), "renders")
    os.makedirs(pasta, exist_ok=True)
    e.setdefault("renders", {})
    for n in so or ("TL SEM CORRECAO", "TL CORRIGIDA"):
        tl = _timeline(p, n)
        p.SetCurrentTimeline(tl)
        if tl.GetIsTrackLocked("audio", 1):
            raise RuntimeError(f"{n}: A1 travada — o SetTrackEnable não pegaria (destrave pelos cadeados)")
        tl.SetTrackEnable("audio", 1, False)
        p.DeleteAllRenderJobs()
        p.SetCurrentRenderFormatAndCodec("mov", "ProRes422")  # ProRes 422 a 640×360: leve
        saida = n.replace("TL ", "RENDER ").replace(" ", "_") + "_A2"
        # ⛔ no raster da MÍDIA (640×360), não no da timeline (1920×1080): o ProRes HD de 30 min deu 13 GB e o Resolve
        # CAIU no meio (notebook, D05, 2026-10-30). O que se mede é o som; a imagem só existe porque o render só de
        # áudio não gera arquivo (banco).
        ok = p.SetRenderSettings({"SelectAllFrames": True, "TargetDir": pasta, "CustomName": saida,
                                  "ExportVideo": True, "ExportAudio": True, "AudioCodec": "lpcm",
                                  "AudioBitDepth": 24, "AudioSampleRate": 48000,
                                  "FormatWidth": 640, "FormatHeight": 360})
        j = p.AddRenderJob()
        t0 = time.time()
        p.StartRendering([j], isInteractiveMode=False)
        while p.IsRenderingInProgress() and time.time() - t0 < prazo:
            time.sleep(3)
        st = p.GetRenderJobStatus(j)
        tl.SetTrackEnable("audio", 1, True)
        e["renders"][n] = {"arquivo": f"renders/{saida}.mov", "ajustes": ok, "status": st,
                           "s": round(time.time() - t0, 1)}
        _gravar(nome, e)
    r.GetProjectManager().SaveProject()
    return e["renders"]


def medir(nome: str) -> dict:
    from .. import medir_deriva
    pasta, v = _caso(nome)
    e = _estado(nome)
    cam = os.path.join(pasta, next(a for a in v["arquivos"] if a["papel"] == "camera")["arquivo"])
    e["medicoes"] = {}
    for n, rd in e.get("renders", {}).items():
        m = medir_deriva.medir(cam, os.path.join(_trab(nome), rd["arquivo"]))
        e["medicoes"][n] = {k: m[k] for k in m if k != "pontos"}
        e["medicoes"][n]["pontos"] = m["pontos"]
    e["verdade"] = {k: v[k] for k in ("deriva_ppm", "velocidade_de_correcao_pct", "atraso_no_fim_ms",
                                      "atraso_no_fim_quadros")}
    _gravar(nome, e)
    destino = os.path.join(RAIZ, "resultados", nome)
    os.makedirs(destino, exist_ok=True)
    with open(os.path.join(destino, f"resolve-{e.get('versao', '?')}-{sys.platform}.json"), "w", encoding="utf-8",
              newline="\n") as fh:
        json.dump({k: e[k] for k in e if k != "timelines"}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return {n: {k: m[k] for k in ("deriva_ppm", "atraso_no_inicio_ms", "atraso_no_fim_ms", "variacao_ms",
                                  "residuo_max_ms")} for n, m in e["medicoes"].items()}


if __name__ == "__main__":
    passo, nome, *resto = sys.argv[1:]
    f = {"preparar": preparar, "regua": medir_arquivos, "renderizar": renderizar, "medir": medir}.get(passo)
    if passo == "corrigir":
        out = corrigir(nome, int(resto[0]), int(resto[1]), *(resto[2:3]))
    elif passo == "confirmar":
        out = confirmar(nome)
    else:
        out = f(nome)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
