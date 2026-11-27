"""Confere uma sequência reorganizada (organizar_audio.py) contra a original, lendo as .avb com o pyavb.
- vídeo idêntico; mesmos clipes de áudio (posição, duração, fonte, início, canal) em qualquer trilha;
- mute de cada clipe igual (Selector com a alternativa selecionada vazia = clipe mutado);
- duração de cada trilha igual; os fades que mudaram (deve ser só crossfade desfeito em fade-out + fade-in);
- com --pan-centro A-B: todo clipe dessas trilhas com pan DEFINIDO no centro (pan_set=True, pan=16384).
Leia CÓPIAS das bins (o MC regrava a .avb aberta; uma biblioteca preguiçosa não pode dividir o arquivo com ele).

uso: python conferir_audio.py <orig.avb> <SEQ> <nova.avb> <SEQ_NOVA> [--pan-centro 1-18]"""
import sys, argparse, collections, avb

PAN_CENTRO = 16384   # medido: o Mixer em modo Clip grava MID como pan=16384 (MC 24.12.6, macOS)

def nome(c): return type(c).__name__
def itens(seqc):
    out = []; p = 0
    for i, c in enumerate(seqc.components):
        if nome(c) == "TransitionEffect": p -= c.length; continue
        out.append((i, p, c)); p += c.length
    return out
def first_sc(c, d=0):
    if c is None or d > 12: return None
    k = nome(c)
    if k == "SourceClip": return c
    if k == "Sequence":
        for x in c.components:
            r = first_sc(x, d + 1)
            if r: return r
        return None
    if k == "Selector":
        for i in [c.selected] + [i for i in range(len(c.tracks)) if i != c.selected]:
            r = first_sc(getattr(c.tracks[i], "component", None), d + 1)
            if r: return r
        return None
    for t in getattr(c, "tracks", None) or []:
        if getattr(t, "component", None) is not None:
            r = first_sc(t.component, d + 1)
            if r: return r
    return None
def mutado(c, d=0):
    if nome(c) == "Selector":
        sel = getattr(c.tracks[c.selected], "component", None)
        return sel is None or nome(sel) == "Filler"
    if nome(c) == "PanVolumeEffect" and d < 4:
        for t in c.tracks:
            if getattr(t, "component", None) is not None: return mutado(t.component, d + 1)
    return False
def pans(c):
    if nome(c) == "PanVolumeEffect": yield c
    for t in getattr(c, "tracks", None) or []:
        if getattr(t, "component", None) is not None: yield from pans(t.component)

def ler(arq, seq):
    f = avb.open(arq)
    s = [m for m in f.content.mobs if m.mob_type == "CompositionMob" and m.name == seq]
    assert len(s) == 1, (arq, seq, len(s))
    out = {}
    for t in s[0].tracks:
        k = t.component.media_kind
        if k not in ("sound", "picture") or nome(t.component) != "Sequence": continue
        L = []
        for i, p, c in itens(t.component):
            if nome(c) == "Filler": continue
            sc = first_sc(c)
            L.append(dict(chave=(p, c.length, str(sc.mob_id) if sc else None, sc.start_time if sc else None,
                                 sc.track_id if sc else None),
                          mut=mutado(c), pans=[(x.pan_set, x.pan) for x in pans(c)], comp=c,
                          trilha=t.index, kind=k))
        tot = sum(-x.length if nome(x) == "TransitionEffect" else x.length for x in t.component.components)
        out[(k, t.index)] = (L, tot)
    return out

ap = argparse.ArgumentParser()
ap.add_argument("orig"); ap.add_argument("seq"); ap.add_argument("nova"); ap.add_argument("seq_nova")
ap.add_argument("--pan-centro")
a = ap.parse_args()
A, B = ler(a.orig, a.seq), ler(a.nova, a.seq_nova)
ok = True
def diz(cond, txt):
    global ok; ok &= bool(cond); print(("OK  " if cond else "FALHA ") + txt)
diz(sorted(A) == sorted(B), "mesmas trilhas")
diz(all([x["chave"] for x in A[k][0]] == [x["chave"] for x in B[k][0]] for k in A if k[0] == "picture"), "vídeo idêntico")
ca = collections.Counter(x["chave"] for k in A if k[0] == "sound" for x in A[k][0])
cb = collections.Counter(x["chave"] for k in B if k[0] == "sound" for x in B[k][0])
diz(ca == cb, f"mesmos clipes de áudio ({sum(ca.values())} × {sum(cb.values())})")
ma = {x["chave"]: x["mut"] for k in A if k[0] == "sound" for x in A[k][0]}
mb = {x["chave"]: x["mut"] for k in B if k[0] == "sound" for x in B[k][0]}
diz(ma == mb, f"mute igual em cada clipe ({sum(ma.values())} mutados)")
diz(all(A[k][1] == B[k][1] for k in A), "duração de cada trilha igual")
mov = collections.Counter((x["trilha"], y["trilha"]) for k in A if k[0] == "sound" for x in A[k][0]
                          for kk in B if kk[0] == "sound" for y in B[kk][0] if x["chave"] == y["chave"] and x["trilha"] != y["trilha"])
print("clipes que trocaram de trilha:", sum(mov.values()), dict(sorted(mov.items())))
if a.pan_centro:
    i, _, f = a.pan_centro.partition("-"); i, f = int(i), int(f or 10**6)
    sem = [(x["trilha"], x["chave"][0]) for k in B if k[0] == "sound" and i <= k[1] <= f for x in B[k][0]
           if not any(ps and pv == PAN_CENTRO for ps, pv in x["pans"])]
    n = sum(len(B[k][0]) for k in B if k[0] == "sound" and i <= k[1] <= f)
    diz(not sem, f"pan centro definido em A{i}–A{f if f < 10**6 else ''}: {n - len(sem)}/{n}")
    if sem: print("   sem pan centro (trilha, posição):", sem[:20])
sys.exit(0 if ok else 1)
