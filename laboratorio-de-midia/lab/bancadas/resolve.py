"""Bancada do DaVinci Resolve — roda DENTRO do Resolve (MCP do Resolve ou `fuscript`/API externa).

Recebe o objeto `resolve` e só usa a API dele + biblioteca padrão. Grava tudo o que o Resolve disse num
json (`resolve.json`), os stills e os renders numa pasta de trabalho; quem confere é `conferir.py`.

Armadilhas que o banco já sabia (`plugins/resolve-scripting/api-scripting.md`) e que este código aplica:
- a taxa do projeto vai ANTES de importar (fracionária só pelo projeto);
- `ExportCurrentFrameAsStill` só funciona na página Color;
- `SetCurrentTimecode` às vezes não pega (logo depois de trocar de página, ou sem motivo): repetir até o
  `GetCurrentTimecode` bater, e esperar antes do still (1 em 230 saiu com o quadro anterior sem pausa);
- `SetCurrentFolder` é estado global: a importação cai na pasta corrente;
- o render só de áudio não gera arquivo: render com vídeo e áudio.

Uso pelo MCP (`run_script_unsafe`), em passos de menos de 60 s:
    import sys, importlib; sys.dont_write_bytecode = True; sys.path.insert(0, LAB); importlib.invalidate_caches()
    from lab.bancadas import resolve as b
    b.preparar(resolve, CASO, TRABALHO, "LAB B01 FORMATOS")   # projeto, import, timelines
    b.stills(resolve, TRABALHO)                                # quadros 0 / meio / último de cada timeline
    b.renderizar(resolve, TRABALHO)                            # enfileira e começa; depois b.esperar_render
"""
from __future__ import annotations

import json
import os
import time

from .. import tc as _tc

PROPRIEDADES = ("Type", "File Name", "Start TC", "End TC", "Frames", "FPS", "Resolution", "Video Codec",
                "Bit Depth", "Field Dominance", "Format", "Audio Ch", "Audio Codec", "Audio Bit Depth",
                "Sample Rate", "Drop frame", "Duration", "Data Level", "Input Color Space", "Reel Name", "Start")


def conectar():
    """O Resolve aberto, pela API de script EXTERNA (sem o MCP): roda de qualquer Python 3 desta máquina e
    não tem o limite de 60 s por chamada. Medido 2026-10-06 (Mac, Studio 21.1, Python 3.9 do sistema):
    conecta em ~0 s. Precisa de Preferências → Sistema → Geral → "External scripting using: Local".
    Caminhos (banco, matriz de plataforma §G3): o módulo `DaVinciResolveScript.py` e a `fusionscript`."""
    import sys
    if sys.platform == "darwin":
        api = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
        lib = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
    elif os.name == "nt":
        api = os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                           "Blackmagic Design", "DaVinci Resolve", "Support", "Developer", "Scripting")
        lib = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"
    else:
        api = "/opt/resolve/Developer/Scripting"
        lib = "/opt/resolve/libs/Fusion/fusionscript.so"
    os.environ.setdefault("RESOLVE_SCRIPT_API", api)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", lib)
    modulos = os.path.join(api, "Modules")
    if modulos not in sys.path:
        sys.path.append(modulos)
    import DaVinciResolveScript as dvr
    r = dvr.scriptapp("Resolve")
    if not r:
        raise RuntimeError("Resolve não respondeu: está aberto, e com 'External scripting using: Local'?")
    return r


def _ler(trabalho: str) -> dict:
    caminho = os.path.join(trabalho, "resolve.json")
    if os.path.isfile(caminho):
        with open(caminho, encoding="utf-8") as fh:      # o Python do MCP abre em ASCII sem isto (banco)
            return json.load(fh)
    return {}


def _gravar(trabalho: str, dados: dict) -> None:
    os.makedirs(trabalho, exist_ok=True)
    with open(os.path.join(trabalho, "resolve.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def _arquivos_do_caso(caso: str, variante: str | None = None) -> list[str]:
    with open(os.path.join(caso, "verdade.json"), encoding="utf-8") as fh:
        verdade = json.load(fh)
    return [os.path.join(caso, a["arquivo"]) for a in verdade["arquivos"]
            if variante is None or a.get("variante") == variante]


def _pasta(pool, raiz, nome):
    for p in raiz.GetSubFolderList():
        if p.GetName() == nome:
            return p
    return pool.AddSubFolder(raiz, nome)


def _todos_os_clipes(pasta) -> list:
    itens = list(pasta.GetClipList())
    for sub in pasta.GetSubFolderList():
        itens += _todos_os_clipes(sub)
    return itens


def _trilhas(tl) -> dict:
    out = {}
    for tipo in ("video", "audio"):
        lista = []
        for i in range(1, tl.GetTrackCount(tipo) + 1):
            itens = []
            for it in tl.GetItemListInTrack(tipo, i) or []:
                d = {"nome": it.GetName(), "inicio": it.GetStart(), "duracao": it.GetDuration(),
                     "entrada_na_fonte": it.GetSourceStartFrame() if hasattr(it, "GetSourceStartFrame") else None}
                if tipo == "audio":
                    try:
                        d["mapa_de_canais"] = json.loads(it.GetSourceAudioChannelMapping() or "null")
                    except ValueError:
                        d["mapa_de_canais"] = it.GetSourceAudioChannelMapping()
                itens.append(d)
            lista.append({"trilha": i, "subtipo": tl.GetTrackSubType(tipo, i) if tipo == "audio" else None,
                          "itens": itens})
        out[tipo] = lista
    return out


def preparar(resolve, caso: str, trabalho: str, nome_projeto: str, pasta_pm: str = "LABORATORIO",
             fps: str = "25", raster=(1920, 1080), drop_frame: bool = False, variante: str | None = None,
             timeline_no_tc_do_clipe: bool = True, timelines_de_audio: bool = False,
             rasters: bool = False) -> dict:
    """Projeto (um por taxa: a taxa fracionária só entra pelo projeto, antes de importar — banco), import
    dos arquivos do caso (ou só os da `variante`), uma timeline por clipe com vídeo."""
    pm = resolve.GetProjectManager()
    pm.GotoRootFolder()
    if pasta_pm not in pm.GetFolderListInCurrentFolder():
        pm.CreateFolder(pasta_pm)
    pm.OpenFolder(pasta_pm)
    atual = pm.GetCurrentProject()
    if atual and atual.GetName() == nome_projeto:
        projeto = atual
    elif nome_projeto in pm.GetProjectListInCurrentFolder():
        projeto = pm.LoadProject(nome_projeto)
    else:
        projeto = pm.CreateProject(nome_projeto)
    ajustes = {k: projeto.SetSetting(k, v) for k, v in (
        ("timelineFrameRate", fps), ("timelineResolutionWidth", str(raster[0])),
        ("timelineResolutionHeight", str(raster[1])), ("timelineDropFrameTimecode", "1" if drop_frame else "0"))}
    ajustes["lidos"] = {k: projeto.GetSetting(k) for k in ("timelineFrameRate", "timelineDropFrameTimecode")}

    pool = projeto.GetMediaPool()
    raiz = pool.GetRootFolder()
    pasta = _pasta(pool, raiz, os.path.basename(caso.rstrip("/\\")))
    if not pasta.GetClipList():
        pool.SetCurrentFolder(pasta)
        importados = pool.ImportMedia(_arquivos_do_caso(caso, variante)) or []
    else:
        importados = []
    clipes = [c for c in _todos_os_clipes(pasta) if c.GetClipProperty("Type") != "Timeline"]
    info_pool = []
    for c in clipes:
        props = c.GetClipProperty()
        d = {k: props.get(k) for k in PROPRIEDADES + ("PAR",)}
        d["File Path"] = props.get("File Path")
        try:
            d["mapa_de_audio"] = json.loads(c.GetAudioMapping() or "null")
        except ValueError:
            d["mapa_de_audio"] = c.GetAudioMapping()
        info_pool.append(d)

    # uma timeline por clipe com vídeo, com o nome do arquivo
    timelines = []
    pool.SetCurrentFolder(pasta)
    existentes = {projeto.GetTimelineByIndex(i).GetName(): projeto.GetTimelineByIndex(i)
                  for i in range(1, projeto.GetTimelineCount() + 1)}
    pedidos = []
    for c in clipes:
        tipo = c.GetClipProperty("Type") or ""
        if "Video" in tipo:
            if rasters:
                # B05: a timeline NATIVA (do tamanho de exibição do clipe) e a do projeto (HD), onde o
                # clipe é ajustado ("scale entire image to fit")
                pedidos += [(c, "TL NATIVA " + c.GetClipProperty("File Name"), "nativa"),
                            (c, "TL HD " + c.GetClipProperty("File Name"), "hd")]
            else:
                pedidos.append((c, "TL " + c.GetClipProperty("File Name"), None))
        elif timelines_de_audio and tipo == "Audio":
            pedidos.append((c, "TL " + c.GetClipProperty("File Name"), "audio"))
    for c, nome, modo in pedidos:
        tl = existentes.get(nome) or pool.CreateTimelineFromClips(nome, [{"mediaPoolItem": c}])
        if not tl:
            timelines.append({"nome": nome, "erro": "CreateTimelineFromClips devolveu None"})
            continue
        if timeline_no_tc_do_clipe:
            # a timeline nasce em 00:00:00:00 nesta instalação; no TC do clipe, a régua repete o relógio
            # da fonte e a agulha pedida por TC atravessa o que o clipe atravessa (o minuto do drop-frame)
            tl.SetStartTimecode(c.GetClipProperty("Start TC"))
        if modo == "nativa":
            larg, alt = (int(x) for x in c.GetClipProperty("Resolution").split("x"))
            par = c.GetClipProperty("PAR") or "Square"
            if par not in ("Square", "1.0", "1"):
                try:
                    larg = round(larg * float(par.split(":")[0]) / float(par.split(":")[1])) if ":" in par else round(larg * float(par))
                except ValueError:
                    pass
            tl.SetSetting("useCustomSettings", "1")
            tl.SetSetting("timelineResolutionWidth", str(larg))
            tl.SetSetting("timelineResolutionHeight", str(alt))
        timelines.append({"nome": nome, "clipe": c.GetClipProperty("File Name"), "modo": modo,
                          "resolucao": [tl.GetSetting("timelineResolutionWidth"), tl.GetSetting("timelineResolutionHeight")],
                          "inicio_tc": tl.GetStartTimecode(), "inicio_quadro": tl.GetStartFrame(),
                          "fim_quadro": tl.GetEndFrame(), "fps": tl.GetSetting("timelineFrameRate"),
                          "trilhas": _trilhas(tl)})
    pm.SaveProject()
    dados = {"resolve": resolve.GetVersionString(), "produto": resolve.GetProductName(),
             "fps": fps, "base": _tc.base(_tc.taxa(fps)), "drop_frame": drop_frame, "variante": variante,
             "projeto": projeto.GetName(), "pasta_no_project_manager": pasta_pm, "ajustes": ajustes,
             "importados_agora": len(importados), "pool": info_pool, "timelines": timelines}
    _gravar(trabalho, {**_ler(trabalho), **dados})
    return {"pool": len(info_pool), "timelines": [t["nome"] for t in timelines]}


def _achar_timeline(projeto, nome):
    for i in range(1, projeto.GetTimelineCount() + 1):
        tl = projeto.GetTimelineByIndex(i)
        if tl.GetName() == nome:
            return tl
    return None


def stills(resolve, trabalho: str, base: int | None = None, so: list[str] | None = None, pausa: float = 0.6) -> dict:
    """Quadros 0, meio e último de cada timeline (posição na TIMELINE) → `stills/<timeline>_<k>.png`."""
    projeto = resolve.GetProjectManager().GetCurrentProject()
    dados = _ler(trabalho)
    resolve.OpenPage("color")
    time.sleep(1.0)
    pasta = os.path.join(trabalho, "stills")
    os.makedirs(pasta, exist_ok=True)
    feitos = dados.get("stills", {})
    base = base or dados.get("base", 25)
    df = bool(dados.get("drop_frame"))
    mesmo = lambda a, b: (a or "").replace(";", ":") == (b or "").replace(";", ":")
    for t in dados["timelines"]:
        if "erro" in t or t.get("modo") in ("audio", "sem_stills") or (so and t["nome"] not in so):
            continue
        tl = _achar_timeline(projeto, t["nome"])
        projeto.SetCurrentTimeline(tl)
        time.sleep(0.5)
        dur = t["fim_quadro"] - t["inicio_quadro"]
        inicio = _tc.tc_para_quadros(t["inicio_tc"], base, df)
        lista = []
        # além de início/meio/fim, o quadro antes e o da primeira virada de segundo de TC (no B02, a do minuto)
        virada = next((k for k in range(1, dur) if _tc.rotulo(inicio + k, base, df) // base
                       != _tc.rotulo(inicio + k - 1, base, df) // base), None)
        extras = {virada - 1, virada} if virada else set()
        # e a virada da meia-noite, se houver (o rótulo volta a 00)
        meia_noite = next((k for k in range(1, dur) if _tc.rotulo(inicio + k, base, df)
                           < _tc.rotulo(inicio + k - 1, base, df)), None)
        if meia_noite:
            extras |= {meia_noite - 1, meia_noite}
        for k in sorted({0, (dur - 1) // 2, dur - 1} | extras):
            alvo = _tc.quadros_para_tc(inicio + k, base, df)
            formas = [alvo]
            if _tc.rotulo(inicio + k, base, df) < _tc.rotulo(inicio, base, df):
                # passou da meia-noite: o relógio do arquivo volta a 00, mas a régua pode seguir em 24:…
                formas.append(f"{int(alvo[:2]) + 24:02d}{alvo[2:]}")
            pegou, forma = False, None
            for f in formas:
                for _ in range(4):
                    tl.SetCurrentTimecode(f)
                    time.sleep(0.2)
                    if mesmo(tl.GetCurrentTimecode(), f):
                        pegou, forma = True, f
                        break
                if pegou:
                    break
            time.sleep(pausa)
            arq = os.path.join(pasta, f"{t['nome']}_{k:04d}.png")
            ok = projeto.ExportCurrentFrameAsStill(arq)
            lista.append({"posicao_na_timeline": k, "tc_pedido": alvo, "forma_que_pegou": forma,
                          "tc_na_agulha": tl.GetCurrentTimecode(),
                          "agulha_pegou": pegou, "exportou": bool(ok), "arquivo": os.path.relpath(arq, trabalho)})
        feitos[t["nome"]] = lista
    dados["stills"] = feitos
    _gravar(trabalho, dados)
    return {n: [s["agulha_pegou"] and s["exportou"] for s in l] for n, l in feitos.items()}


def renderizar(resolve, trabalho: str, so: list[str] | None = None) -> dict:
    """Enfileira um render ProRes 422 + PCM 24 bits/48 kHz de cada timeline e começa. Não espera."""
    projeto = resolve.GetProjectManager().GetCurrentProject()
    dados = _ler(trabalho)
    resolve.OpenPage("deliver")
    pasta = os.path.join(trabalho, "renders")
    os.makedirs(pasta, exist_ok=True)
    jobs = []
    for t in dados["timelines"]:
        if "erro" in t or (so and t["nome"] not in so):
            continue
        tl = _achar_timeline(projeto, t["nome"])
        projeto.SetCurrentTimeline(tl)
        projeto.SetCurrentRenderFormatAndCodec("mov", "ProRes422")
        nome = t["nome"].replace("TL ", "RENDER ").rsplit(".", 1)[0]
        ok = projeto.SetRenderSettings({"SelectAllFrames": True, "TargetDir": pasta, "CustomName": nome,
                                        "ExportVideo": True, "ExportAudio": True, "AudioCodec": "lpcm",
                                        "AudioBitDepth": 24, "AudioSampleRate": 48000})
        job = projeto.AddRenderJob()
        jobs.append({"timeline": t["nome"], "arquivo": f"renders/{nome}.mov", "ajustes_aceitos": ok, "job": job})
    ids = [j["job"] for j in jobs if j["job"]]
    comecou = projeto.StartRendering(ids, isInteractiveMode=False) if ids else False
    # junta com os renders de antes (uma variante renderizada depois não apaga a fila anterior)
    feitos = [j for j in dados.get("renders", {}).get("jobs", []) if j["timeline"] not in {x["timeline"] for x in jobs}]
    dados["renders"] = {"comecou": bool(comecou), "jobs": feitos + jobs}
    _gravar(trabalho, dados)
    return dados["renders"]


def esperar_render(resolve, trabalho: str, ate_s: float = 50) -> dict:
    projeto = resolve.GetProjectManager().GetCurrentProject()
    limite = time.time() + ate_s
    while projeto.IsRenderingInProgress() and time.time() < limite:
        time.sleep(1)
    dados = _ler(trabalho)
    for j in dados.get("renders", {}).get("jobs", []):
        if j.get("job"):
            j["status"] = projeto.GetRenderJobStatus(j["job"])
    _gravar(trabalho, dados)
    return {"rodando": bool(projeto.IsRenderingInProgress()),
            "status": [j.get("status") for j in dados.get("renders", {}).get("jobs", [])]}


def timeline_com_mapa(resolve, trabalho: str, arquivo: str, nome: str, mapa: dict) -> dict:
    """Variante: troca o mapa de áudio do clipe no pool (`SetAudioMapping`), cria uma timeline com ele e
    DEVOLVE o mapa original ao clipe (as timelines de antes não mudam). Ex.: o XDCAM de 8 mono com os
    canais 1–2 como par estéreo."""
    projeto = resolve.GetProjectManager().GetCurrentProject()
    pool = projeto.GetMediaPool()
    dados = _ler(trabalho)
    clipe = next(c for c in _todos_os_clipes(pool.GetRootFolder()) if c.GetClipProperty("File Name") == arquivo)
    original = clipe.GetAudioMapping()
    aceitou = clipe.SetAudioMapping(json.dumps(mapa))
    aplicado = json.loads(clipe.GetAudioMapping() or "null")
    tl = _achar_timeline(projeto, nome) or pool.CreateTimelineFromClips(nome, [{"mediaPoolItem": clipe}])
    devolveu = clipe.SetAudioMapping(original)
    reg = {"nome": nome, "clipe": arquivo, "variante": {"mapa_pedido": mapa, "aceitou": bool(aceitou),
                                                         "mapa_no_pool": aplicado, "mapa_devolvido": bool(devolveu)},
           "inicio_tc": tl.GetStartTimecode(), "inicio_quadro": tl.GetStartFrame(), "fim_quadro": tl.GetEndFrame(),
           "fps": tl.GetSetting("timelineFrameRate"), "trilhas": _trilhas(tl)}
    dados["timelines"] = [t for t in dados["timelines"] if t["nome"] != nome] + [reg]
    _gravar(trabalho, dados)
    resolve.GetProjectManager().SaveProject()
    return {"aceitou": bool(aceitou), "mapa_no_pool": aplicado,
            "trilhas_audio": [(a["subtipo"], [i.get("mapa_de_canais") for i in a["itens"]]) for a in reg["trilhas"]["audio"]]}


def rodada(resolve, caso: str, trabalho: str, nome_projeto: str, fps: str, drop_frame: bool = False,
           variante: str | None = None, render: bool = True, **kw) -> dict:
    """Uma rodada inteira num projeto: preparar → stills → render → esperar (um projeto não troca no meio
    de um render). Cabe numa chamada do MCP (< 60 s) para um par de clipes de 10 s."""
    p = preparar(resolve, caso, trabalho, nome_projeto, fps=fps, drop_frame=drop_frame, variante=variante, **kw)
    s = stills(resolve, trabalho)
    e = None
    if render:
        renderizar(resolve, trabalho)
        e = esperar_render(resolve, trabalho, 25)
    return {"timelines": p["timelines"], "stills_ok": all(all(v) for v in s.values()), "render": e}


def sync_por_tc(resolve, trabalho: str, video: str, som: str) -> dict:
    """B06: (1) `AutoSyncAudio` por TIMECODE entre o clipe de vídeo e o BWF → timeline do vídeo sincronizado;
    (2) à mão: timeline vazia no TC do som, o vídeo e o BWF postos cada um no SEU TC (`recordFrame`)."""
    projeto = resolve.GetProjectManager().GetCurrentProject()
    pool = projeto.GetMediaPool()
    dados = _ler(trabalho)
    clipes = {c.GetClipProperty("File Name"): c for c in _todos_os_clipes(pool.GetRootFolder())}
    v, s = clipes[video], clipes[som]
    base = dados.get("base", 25)
    reg = {}
    ajustes = {resolve.AUDIO_SYNC_MODE: resolve.AUDIO_SYNC_TIMECODE,
               resolve.AUDIO_SYNC_CHANNEL_NUMBER: resolve.AUDIO_SYNC_CHANNEL_AUTOMATIC,
               resolve.AUDIO_SYNC_RETAIN_EMBEDDED_AUDIO: True,
               resolve.AUDIO_SYNC_RETAIN_VIDEO_METADATA: False}
    reg["autosync"] = bool(pool.AutoSyncAudio([v, s], ajustes))
    reg["synced_audio"] = v.GetClipProperty("Synced Audio")
    try:
        reg["mapa_do_video_depois"] = json.loads(v.GetAudioMapping() or "null")
    except ValueError:
        reg["mapa_do_video_depois"] = v.GetAudioMapping()
    nomes = {}
    existentes = {projeto.GetTimelineByIndex(i).GetName() for i in range(1, projeto.GetTimelineCount() + 1)}
    nome = "TL SYNC AUTOMATICO POR TC"
    if nome not in existentes:
        tl = pool.CreateTimelineFromClips(nome, [{"mediaPoolItem": v}])
        tl.SetStartTimecode(v.GetClipProperty("Start TC"))
    nomes["auto"] = nome
    nome = "TL SYNC MANUAL POR TC"
    if nome not in existentes:
        tl = pool.CreateEmptyTimeline(nome)
        tl.SetStartTimecode(s.GetClipProperty("Start TC"))
        projeto.SetCurrentTimeline(tl)
        ini = tl.GetStartFrame()
        q_v = _tc.tc_para_quadros(v.GetClipProperty("Start TC"), base)
        q_s = _tc.tc_para_quadros(s.GetClipProperty("Start TC"), base)
        # a câmera PRIMEIRO (V1 + A1) e o som direto numa trilha PRÓPRIA do tamanho dele: no mesmo A1, o
        # AppendToTimeline apara em silêncio o que vem depois (medido 2026-10-06: o áudio da câmera entrou
        # com 100 dos 250 quadros, atrás do BWF — a armadilha do banco, §7)
        reg["manual_append"] = [bool(pool.AppendToTimeline([{"mediaPoolItem": v, "recordFrame": ini + (q_v - q_s)}]))]
        tipo = {1: "mono", 2: "stereo"}.get(int(s.GetClipProperty("Audio Ch") or 2), f"adaptive{s.GetClipProperty('Audio Ch')}")
        tl.AddTrack("audio", tipo)
        faixa = tl.GetTrackCount("audio")
        reg["manual_trilha_do_som"] = [faixa, tipo]
        reg["manual_append"].append(bool(pool.AppendToTimeline(
            [{"mediaPoolItem": s, "recordFrame": ini, "trackIndex": faixa, "mediaType": 2}])))
    nomes["manual"] = nome
    for chave, nome in nomes.items():
        tl = _achar_timeline(projeto, nome)
        dados["timelines"] = [t for t in dados["timelines"] if t["nome"] != nome] + [{
            "nome": nome, "clipe": video, "modo": "sem_stills", "sync": chave,
            "inicio_tc": tl.GetStartTimecode(), "inicio_quadro": tl.GetStartFrame(), "fim_quadro": tl.GetEndFrame(),
            "fps": tl.GetSetting("timelineFrameRate"), "trilhas": _trilhas(tl)}]
    dados["sync"] = reg
    _gravar(trabalho, dados)
    resolve.GetProjectManager().SaveProject()
    return {**reg, "timelines": {k: [(a["subtipo"], [(i["nome"], i["inicio"], i["duracao"]) for i in a["itens"]])
                                      for a in next(t for t in dados["timelines"] if t["nome"] == n)["trilhas"]["audio"]]
                                 for k, n in nomes.items()}}
