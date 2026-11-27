"""Esqueleto do contorno do relato (item 1): monta uma timeline com o SRT no lugar certo.

Uso: python3 legenda_na_timeline.py NOME_DA_TL CAMINHO.srt NOME_DO_CLIPE_DE_VIDEO NOME_DO_CLIPE_DE_AUDIO
Cria uma timeline NOVA no projeto aberto (não mexe nas existentes). Começa em 01:00:00:00.
ATENÇÃO: é o esqueleto do que rodou, reescrito sem nada do trabalho; NESTA forma não foi executado.
Pressupõe que os clipes de vídeo e áudio já estejam no Media Pool (pasta raiz) e entrem inteiros.
"""
import os
import sys

sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
import DaVinciResolveScript as dvr  # noqa: E402


def achar(pasta, nome):
    for c in pasta.GetClipList():
        if c.GetName() == nome:
            return c
    raise SystemExit("clipe não achado: " + nome)


nome_tl, srt, nome_v, nome_a = sys.argv[1:5]
resolve = dvr.scriptapp("Resolve")
proj = resolve.GetProjectManager().GetCurrentProject()
mp = proj.GetMediaPool()
raiz = mp.GetRootFolder()

tl = mp.CreateEmptyTimeline(nome_tl)
tl.SetStartTimecode("01:00:00:00")
inicio = tl.GetStartFrame()

# 1) o SRT PRIMEIRO: numa timeline vazia ele cai no início + o 1º evento (o lugar certo)
item_srt = mp.ImportMedia([srt])[0]
mp.AppendToTimeline([{"mediaPoolItem": item_srt}])

# 2) depois vídeo e áudio com recordFrame (endFrame é EXCLUSIVO)
v = achar(raiz, nome_v)
a = achar(raiz, nome_a)
nv = int(v.GetClipProperty("Frames"))
na = int(a.GetClipProperty("Frames"))
mp.AppendToTimeline([
    {"mediaPoolItem": v, "startFrame": 0, "endFrame": nv, "recordFrame": inicio, "trackIndex": 1, "mediaType": 1},
    {"mediaPoolItem": a, "startFrame": 0, "endFrame": na, "recordFrame": inicio, "trackIndex": 1, "mediaType": 2},
])
print("legendas:", len(tl.GetItemListInTrack("subtitle", 1)))

# 3) sair sem passar pelos finalizadores (item 7: evita o SIGSEGV da thread RemoteApp)
sys.stdout.flush()
os._exit(0)
