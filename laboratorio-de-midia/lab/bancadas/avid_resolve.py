"""O passo 4 da bancada do Media Composer (desenho aprovado em 2026-10-11): o DRT que o De Lá Pra Cá fez da sequência
do Avid entra num projeto do LABORATÓRIO no Resolve (um por taxa; a taxa fracionária só entra pelo projeto, antes do
import — banco), é renderizado e volta para a comparação quadro a quadro contra a referência exportada pelo MC."""
from __future__ import annotations

import os
import time

from . import resolve as R
from . import vigia_windows as V

PASTA_PM = "LABORATORIO"
PRESET_RENDER = "FCP - Final Cut Pro 7"
FOTOS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "saida", "bancadas", "resolve", "vigia")


def projeto(r, nome: str, fps: str, drop_frame: bool = False):
    """Abre (ou cria) o projeto `nome` na pasta LABORATORIO com a taxa `fps` — nada de SaveProject no "Untitled
    Project" (abre a caixa de salvar); o vigia fotografa e para em diálogo desconhecido."""
    pm = r.GetProjectManager()
    pm.GotoRootFolder()
    if PASTA_PM not in (pm.GetFolderListInCurrentFolder() or []):
        pm.CreateFolder(PASTA_PM)
    pm.OpenFolder(PASTA_PM)
    atual = pm.GetCurrentProject()
    if not (atual and atual.GetName() == nome):
        V.vigiar(lambda: pm.LoadProject(nome) or pm.CreateProject(nome), FOTOS, imagem=V.RESOLVE)
        time.sleep(2)
    pr = r.GetProjectManager().GetCurrentProject()
    if pr is None or pr.GetName() != nome:
        raise RuntimeError(f"o projeto {nome!r} não abriu")
    if pr.GetTimelineCount() == 0:
        pr.SetSetting("timelineFrameRate", fps)
        pr.SetSetting("timelineDropFrameTimecode", "1" if drop_frame else "0")
    lida = pr.GetSetting("timelineFrameRate")
    if abs(float(lida) - float(fps)) > 1e-6:             # o Resolve devolve "24.0" para "24"
        raise RuntimeError(f"o projeto {nome!r} está a {lida}, não {fps}")
    return pr


def limpar_pool(pr) -> None:
    """O projeto do laboratório começa VAZIO a cada import. ⚠️ Medido 2026-10-11 (Resolve 19.0.0b Windows): com um item
    de mesmo nome já no pool, o `ImportTimelineFromFile` REAPROVEITA o item de VÍDEO (com o caminho antigo, que já não
    existia: render "could not be decoded") e ignora o caminho do DRT; os de áudio ele criou novos, no caminho do DRT."""
    mp = pr.GetMediaPool()
    tls = [pr.GetTimelineByIndex(i) for i in range(1, pr.GetTimelineCount() + 1)]
    if tls:
        mp.DeleteTimelines(tls)
    raiz = mp.GetRootFolder()
    subs = raiz.GetSubFolderList() or []
    if subs:
        mp.DeleteFolders(subs)
    clips = raiz.GetClipList() or []
    if clips:
        mp.DeleteClips(clips)
    sobra = len(raiz.GetClipList() or []) + len(raiz.GetSubFolderList() or []) + pr.GetTimelineCount()
    if sobra:
        raise RuntimeError(f"o pool do projeto {pr.GetName()!r} não esvaziou ({sobra} itens)")


def importar_e_renderizar(drt: str, nome: str, nome_projeto: str, fps: str, pasta_render: str,
                          drop_frame: bool = False) -> str:
    r = R.conectar()
    pr = projeto(r, nome_projeto, fps, drop_frame)
    limpar_pool(pr)
    tl = V.vigiar(lambda: pr.GetMediaPool().ImportTimelineFromFile(drt, {"timelineName": nome,
                                                                       "importSourceClips": True}),
                  FOTOS, imagem=V.RESOLVE)
    if not tl:
        raise RuntimeError(f"o Resolve recusou o DRT {drt}")
    pr.SetCurrentTimeline(tl)
    os.makedirs(pasta_render, exist_ok=True)
    alvo = os.path.join(pasta_render, nome + ".mov")
    if os.path.exists(alvo):
        os.remove(alvo)
    r.OpenPage("deliver")
    time.sleep(1)
    # ⚠️ No Resolve 19 do Windows `SetCurrentRenderFormatAndCodec` devolve False (banco, 2026-10-10) e mexer no áudio
    # pelo SetRenderSettings DESLIGA o áudio do trabalho (IsExportAudio False, render mudo — medido 2026-10-11). O preset
    # de FÁBRICA "FCP - Final Cut Pro 7" já é QuickTime sem compressão (RGB 10-bit) com áudio: carregá-lo e só apontar
    # destino, nome e o modo de um arquivo só.
    if not pr.LoadRenderPreset(PRESET_RENDER):
        raise RuntimeError(f"o preset de render {PRESET_RENDER!r} não carregou")
    pr.SetCurrentRenderMode(1)                          # o preset do FCP 7 é clipe a clipe + XML; 1 = um arquivo só
    pr.SetRenderSettings({"SelectAllFrames": True, "TargetDir": pasta_render, "CustomName": nome})
    job = pr.AddRenderJob()
    trabalho = next(x for x in pr.GetRenderJobList() if x["JobId"] == job)
    if not trabalho.get("IsExportAudio"):
        pr.DeleteRenderJob(job)
        raise RuntimeError(f"o trabalho de render saiu sem áudio: {trabalho}")
    pr.StartRendering(job)
    fim = time.time() + 900
    while pr.IsRenderingInProgress():
        if time.time() > fim:
            pr.StopRendering()
            raise V.Travado(f"render de {nome!r} passou de 15 min", V.foto_da_tela(FOTOS, "render"))
        time.sleep(3)
    estado = pr.GetRenderJobStatus(job)
    pr.DeleteRenderJob(job)
    r.OpenPage("edit")
    if estado.get("JobStatus") != "Complete":
        raise RuntimeError(f"render: {estado}")
    import glob
    for xml in glob.glob(os.path.join(pasta_render, nome + ".*.xml")):  # o preset do FCP 7 deixa o XML ao lado
        os.remove(xml)
    return alvo
