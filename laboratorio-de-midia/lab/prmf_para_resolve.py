"""A máscara de OBJETO do Premiere (.prmf) → Magic Mask da página COLOR do DaVinci Resolve, sem o Resolve rastrear nada.

Com o Resolve ABERTO no projeto e na timeline do clipe:

    python3 -m lab.prmf_para_resolve "<projeto> Masks"/*.prmf --clipe "NOME DO CLIPE NA TIMELINE"

O que acontece (receita do banco, `protocolos/drt-drp/magic-mask.md` §7):
1. pela API: o nó AI Magic Mask entra no clipe (copiado de um molde, `lab/moldes/resolve/no_magic_mask_color.drt`) e o
   projeto é salvo;
2. o Resolve vai para um projeto TEMPORÁRIO (o banco do seu projeto fica fechado);
3. cópia de segurança do `Project.db` em `~/Movies/prmf_para_resolve/copias/`; o banco é marcado "em dia" (`resolve_mascara`);
4. a máscara do Premiere é escrita no cache do Resolve, um `.dvcc` por quadro;
5. o seu projeto reabre e o temporário é apagado.

⚠️ Os traços do nó são os do molde: se o colorista mandar rastrear de novo, o Resolve refaz por cima com eles.
O cache conta quadros da MÍDIA, só a faixa do clipe (clipe aparado: medido 2026-10-08).
⏳ Pendente: velocidade alterada, Windows/Resolve 19, banco em rede.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from . import prmf, resolve_mascara as rm

TEMPORARIO = "_prmf_para_resolve (temporário)"


def conectar():
    """O objeto `resolve` pela API externa (Resolve Studio aberto)."""
    if sys.platform != "darwin":
        raise RuntimeError("medido só no macOS (Windows: pendente)")
    mods = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
    os.environ.setdefault("RESOLVE_SCRIPT_API", os.path.dirname(mods))
    os.environ.setdefault("RESOLVE_SCRIPT_LIB",
                          "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so")
    if mods not in sys.path:
        sys.path.append(mods)
    import DaVinciResolveScript as drs  # noqa: E402  (vem com o Resolve)
    r = drs.scriptapp("Resolve")
    if not r:
        raise RuntimeError("não conectou ao Resolve — ele está aberto? (Preferências > Sistema > Geral > Scripting externo)")
    return r


def mascaras(arquivos: list[str], fps: float, largura: int, altura: int) -> dict[int, bytes]:
    """{quadro da mídia: máscara largura×altura 0/255}, juntando as passadas do Premiere (união)."""
    if (largura, altura) != (1920, 1080):
        raise ValueError("o leitor do .prmf amplia para 1920×1080 — outras resoluções: pendente")
    limiar = bytes(255 if v >= 128 else 0 for v in range(256))
    out: dict[int, bytes] = {}
    for arq in arquivos:
        for q in prmf.ler(arq):
            if not (q["caixa"] and (q["tam"] or 0) > 16):
                continue
            n = round(q["segundos"] * fps)
            a = bytes(prmf.alfa_quadro_inteiro(q, largura, altura)).translate(limiar)
            if n in out:                                           # duas passadas no mesmo quadro: a união
                a = (int.from_bytes(out[n], "big") | int.from_bytes(a, "big")).to_bytes(len(a), "big")
            out[n] = a
    return out


def _achar_clipe(timeline, nome: str):
    for tr in range(1, timeline.GetTrackCount("video") + 1):
        for it in timeline.GetItemListInTrack("video", tr) or []:
            if it.GetName() == nome:
                return it
    raise LookupError(f"clipe '{nome}' não está na timeline '{timeline.GetName()}'")


def _por_no_magic_mask(resolve, projeto, alvo) -> None:
    """Copia o nó AI Magic Mask do molde para o clipe e tira do projeto o que o molde trouxe."""
    mp = projeto.GetMediaPool()
    antes = {c.GetUniqueId() for c in mp.GetRootFolder().GetClipList()}
    tl_atual = projeto.GetCurrentTimeline()
    molde = mp.ImportTimelineFromFile(rm.MOLDE_NO)
    if not molde:
        raise RuntimeError("o Resolve não importou o molde do nó")
    origem = molde.GetItemListInTrack("video", 1)[0]
    ok = origem.CopyGrades([alvo])
    projeto.SetCurrentTimeline(tl_atual)
    mp.DeleteTimelines([molde])
    novos = [c for c in mp.GetRootFolder().GetClipList() if c.GetUniqueId() not in antes]
    if novos:
        mp.DeleteClips(novos)
    if not ok:
        raise RuntimeError("CopyGrades falhou")
    ferramentas = alvo.GetNodeGraph().GetToolsInNode(1) or []
    if "AI Magic Mask" not in ferramentas:
        raise RuntimeError(f"o nó não chegou ao clipe (ferramentas: {ferramentas})")


def aplicar(resolve, arquivos: list[str], clipe: str, cache_raiz: str | None = None, sem_no: bool = False) -> dict:
    pm = resolve.GetProjectManager()
    if pm.GetCurrentDatabase().get("DbType") != "Disk":
        raise RuntimeError("só banco LOCAL em disco (rede/nuvem: pendente)")
    projeto = pm.GetCurrentProject()
    nome, pid = projeto.GetName(), projeto.GetUniqueId()
    tl = projeto.GetCurrentTimeline()
    alvo = _achar_clipe(tl, clipe)
    fps = float(tl.GetSetting("timelineFrameRate"))
    largura, altura = int(projeto.GetSetting("timelineResolutionWidth")), int(projeto.GetSetting("timelineResolutionHeight"))
    # o cache conta QUADROS DA MÍDIA e só a faixa que o clipe usa (medido: clipe 50→298 gera 0000000050…0000000298)
    primeiro = int(alvo.GetSourceStartFrame())
    ultimo = primeiro + int(alvo.GetDuration()) - 1
    m = mascaras(arquivos, fps, largura, altura)
    if not sem_no:
        _por_no_magic_mask(resolve, projeto, alvo)
    item_id, tl_id = alvo.GetUniqueId(), tl.GetUniqueId()
    cache = projeto.GetSetting("perfCacheClipsLocation") or cache_raiz or os.path.expanduser("~/Movies/CacheClip")
    if not pm.SaveProject():
        raise RuntimeError("o Resolve não salvou o projeto")
    # o banco do projeto só se edita com o projeto FECHADO
    if TEMPORARIO in pm.GetProjectListInCurrentFolder():
        pm.DeleteProject(TEMPORARIO)
    if not pm.CreateProject(TEMPORARIO):
        raise RuntimeError("não deu para abrir o projeto temporário")
    try:
        db = rm.achar_banco(pid)
        seq, ver = rm.ids_do_caminho(db, tl_id, item_id)
        info = rm.marcar_em_dia(db, item_id, primeiro, ultimo, os.path.expanduser("~/Movies/prmf_para_resolve/copias"))
        pasta = os.path.join(cache, pid, "AlgoCache", "1000", seq, item_id, ver, "1", "0")
        os.makedirs(pasta, exist_ok=True)
        vazio = bytes(largura * altura)
        for n in range(primeiro, ultimo + 1):
            with open(os.path.join(pasta, f"{n:010d}.dvcc"), "wb") as fh:
                fh.write(rm.dvcc(m.get(n, vazio), largura, altura, n, fps))
    finally:
        if not pm.LoadProject(nome):
            raise RuntimeError(f"não reabriu o projeto '{nome}' — abra-o no Project Manager")
        pm.DeleteProject(TEMPORARIO)
    projeto = pm.GetCurrentProject()
    projeto.SetCurrentTimeline(next(projeto.GetTimelineByIndex(i) for i in range(1, projeto.GetTimelineCount() + 1)
                                    if projeto.GetTimelineByIndex(i).GetUniqueId() == tl_id))
    return {"projeto": nome, "clipe": clipe, "faixa": (primeiro, ultimo),
            "com_mascara": sum(1 for n in m if primeiro <= n <= ultimo), "cache": pasta, **info}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prmf", nargs="+", help="os .prmf da máscara (pasta '<projeto> Masks' do Premiere)")
    ap.add_argument("--clipe", required=True, help="nome do clipe na timeline aberta no Resolve")
    ap.add_argument("--sem-no", action="store_true", help="o clipe já tem o nó AI Magic Mask (não copiar o do molde)")
    a = ap.parse_args(argv)
    t = time.time()
    r = aplicar(conectar(), a.prmf, a.clipe, sem_no=a.sem_no)
    print(f"✅ {r['com_mascara']} quadros com máscara no clipe '{r['clipe']}' ({time.time() - t:.0f} s). "
          f"Cópia do banco: {r['copia']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
