"""Autora uma CÓPIA de uma sequência do Media Composer com o áudio separado por faixas (som direto / FX / trilha),
numa bin NOVA, sem tocar a original. Só troca clipes de trilha: posição, duração, fonte, volume/pan, mute e fades
ficam iguais (um crossfade entre um clipe que fica e um que sai vira fade-out + fade-in do mesmo tamanho).
Par estéreo (canal 1 e 2 do mesmo master) vai com L em trilha ÍMPAR e R em PAR.
A categoria de cada clipe vem do NOME do master/fonte, por expressões regulares que a pessoa ajusta ao projeto.

uso:
  python organizar_audio.py <bin original.avb> <bin destino.avb> --seq "<nome da sequência>" [--novo "<nome>"]
         [--direto 1-18] [--fx 19-24] [--trilha 25-] [--mus REGEX] [--efx REGEX]
Feche a bin no MC antes? Não precisa para LER; o destino é um arquivo NOVO (abrir com OpenBin depois).
Requer pyavb (testado com a versão do venv do kit em 2026-11-27)."""
import os, sys, re, argparse, avb
from avb import ioctx
from avb.mobid import MobID

# --- strings nulas (0xFFFF) preservadas: regra do banco (protocolos/avb/escrita.md) ---
class Nula(str): pass
_rs, _ws = ioctx.AVBIOContext.read_string, ioctx.AVBIOContext.write_string
def read_string(self, f, encoding='macroman'):
    pos = f.tell(); size = self.read_u16(f)
    if size >= 65535: return Nula("")
    f.seek(pos); return _rs(self, f, encoding)
def write_string(self, f, s, encoding='macroman'):
    if isinstance(s, Nula): self.write_u16(f, 0xFFFF); return
    return _ws(self, f, s, encoding)
ioctx.AVBIOContext.read_string, ioctx.AVBIOContext.write_string = read_string, write_string

# --- pyavb: ASPIPlugin.__init__(self, root) quebra o copy() (from_name chama __init__ sem argumentos) ---
from avb import trackgroups as _tg, core as _core
def _aspi_init(self, root=None):
    _core.AVBObject.__init__(self, root if root is not None else self.root); self.chunks = []
_tg.ASPIPlugin.__init__ = _aspi_init

ap = argparse.ArgumentParser()
ap.add_argument("orig"); ap.add_argument("dest")
ap.add_argument("--seq", required=True); ap.add_argument("--novo")
ap.add_argument("--direto", default="1-18"); ap.add_argument("--fx", default="19-24"); ap.add_argument("--trilha", default="25-")
ap.add_argument("--mus", default=r"BPM|\.mp3|soundtrack|_MUS_", help="regex: nome de master que é TRILHA")
ap.add_argument("--efx", default=r"_PSE_|\.aif|\.aiff|SFX|_FX_", help="regex: nome de master que é FX (o resto é som direto)")
a = ap.parse_args()
def faixa(t):
    i, _, f = t.partition("-"); return int(i), (int(f) if f else 10**6)
DIR_R, FX_R, MUS_R = faixa(a.direto), faixa(a.fx), faixa(a.trilha)
ORIG, DEST, SEQ = a.orig, a.dest, a.seq
NOVO_NOME = a.novo or SEQ + "_AUDIO_ORG"
FX_PARES = [(i, i + 1) for i in range(FX_R[0], FX_R[1], 2)]
assert not os.path.exists(DEST), "bin de destino já existe"
TMP = DEST + ".tmp_autoria"
MUS = re.compile(a.mus, re.I)
FX = re.compile(a.efx, re.I)
dentro = lambda n, r: r[0] <= n <= r[1]

def nome(c): return type(c).__name__
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
def info(c):
    sc = first_sc(c); nomes = []; cur = sc
    for _ in range(6):
        if cur is None: break
        m = cur.mob
        if m is None: break
        nomes.append(m.name or "")
        if m.mob_type == "SourceMob": break
        tr = [t for t in m.tracks if t.index == cur.track_id]
        cur = first_sc(tr[0].component) if tr else None
    s = " ".join(nomes)
    cat = "TRILHA" if MUS.search(s) else ("FX" if FX.search(s) else "DIRETO")
    na = len([t for t in sc.mob.tracks if t.component.media_kind == "sound"]) if sc and sc.mob else 0
    return cat, (sc.track_id if sc else None), na, s

def itens(seqc):
    """lista (i, pos, comp) dos componentes não-transição"""
    out = []; p = 0
    for i, c in enumerate(seqc.components):
        if nome(c) == "TransitionEffect": p -= c.length; continue
        out.append((i, p, c)); p += c.length
    return out
def total(seqc): return sum(-c.length if nome(c) == "TransitionEffect" else c.length for c in seqc.components)

def reconstruir(seqc, comps, f_modelo):
    """grava a lista na sequência: tira transições entre dois vazios e junta vazios vizinhos"""
    mudou = True
    while mudou:
        mudou = False
        for i in range(1, len(comps) - 1):
            if nome(comps[i]) == "TransitionEffect" and nome(comps[i-1]) == "Filler" and nome(comps[i+1]) == "Filler":
                a, t, b = comps[i-1], comps[i], comps[i+1]
                a.length = a.length - t.length + b.length
                comps = comps[:i] + comps[i+2:]; mudou = True; break
        for i in range(len(comps) - 1):
            if nome(comps[i]) == "Filler" and nome(comps[i+1]) == "Filler":
                comps[i].length += comps[i+1].length; comps = comps[:i+1] + comps[i+2:]; mudou = True; break
    while len(seqc.components): seqc.components.pop()
    for c in comps: seqc.components.append(c)

with avb.open(ORIG) as fo:
    novo = avb.open()
    seq_orig = None
    for m in fo.content.mobs:
        if m.name == SEQ and m.mob_type == "CompositionMob": seq_orig = m
        novo.content.add_mob(m.copy(novo)).user_placed = False
    assert seq_orig is not None
    seq = seq_orig.copy(novo); seq.mob_id = MobID.new(); seq.name = NOVO_NOME
    novo.content.add_mob(seq).user_placed = True
    A = {t.index: t.component for t in seq.tracks if t.component.media_kind == "sound"}
    TOT = {n: total(s) for n, s in A.items()}
    f_modelo = next(c for s in A.values() for c in s.components if nome(c) == "Filler")
    def filler(n):
        f = f_modelo.copy(novo); f.length = n; return f

    # 1) recolher o que muda de trilha: (trilha, pos, comp, trans_antes, trans_depois, cat, canal, n canais)
    mover = []
    for n, s in sorted(A.items()):
        for i, p, c in itens(s):
            if nome(c) == "Filler": continue
            cat, ch, na, txt = info(c)
            certo = {"DIRETO": dentro(n, DIR_R), "FX": dentro(n, FX_R), "TRILHA": dentro(n, MUS_R)}[cat]
            par_ok = not (na >= 2 and ch in (1, 2) and (ch == 1) != (n % 2 == 1))
            if cat == "DIRETO" or (certo and par_ok): continue
            ta = s.components[i-1] if i > 0 and nome(s.components[i-1]) == "TransitionEffect" else None
            td = s.components[i+1] if i + 1 < len(s.components) and nome(s.components[i+1]) == "TransitionEffect" else None
            mover.append(dict(n=n, pos=p, c=c, ta=ta, td=td, cat=cat, ch=ch, na=na, txt=txt))
    # 2) tirar das trilhas de origem: o clipe vira vazio do mesmo tamanho (as transições ficam como fade do vizinho)
    for n in sorted({x["n"] for x in mover}):
        s = A[n]; comps = list(s.components)
        for x in mover:
            if x["n"] == n:
                comps[comps.index(x["c"])] = filler(x["c"].length)
        reconstruir(s, comps, f_modelo)
    # 3) ocupação atual de cada trilha (com a folga das transições)
    def ocup(n):
        out = []
        s = A[n]; comps = list(s.components)
        for i, p, c in itens(s):
            if nome(c) == "Filler": continue
            ta = comps[i-1].length if i > 0 and nome(comps[i-1]) == "TransitionEffect" else 0
            td = comps[i+1].length if i + 1 < len(comps) and nome(comps[i+1]) == "TransitionEffect" else 0
            out.append((p - ta, p + c.length + td))
        return out
    OC = {n: ocup(n) for n in A}
    def livre(n, a, b): return all(b <= x or a >= y for x, y in OC[n])
    # 4) agrupar em pares L/R (mesmo nome de master, canais 1 e 2, início a até 3 quadros)
    eventos = []; usados = set()
    mover.sort(key=lambda x: (x["pos"], x["n"]))
    for k, x in enumerate(mover):
        if k in usados: continue
        usados.add(k); par = None
        if x["na"] >= 2 and x["ch"] in (1, 2):
            for j in range(k + 1, len(mover)):
                y = mover[j]
                if j not in usados and y["txt"] == x["txt"] and abs(y["pos"] - x["pos"]) <= 3 and {x["ch"], y["ch"]} == {1, 2}:
                    par = y; usados.add(j); break
        L, R = (x, par) if (par is None or x["ch"] == 1) else (par, x)
        eventos.append((L, R))
    def ext(x): return (x["pos"] - (x["ta"].length if x["ta"] else 0), x["pos"] + x["c"].length + (x["td"].length if x["td"] else 0))
    # 5) escolher destino: FX → pares da faixa de FX; trilha → pares da faixa de trilha (ímpar/par)
    destino = []
    for L, R in eventos:
        cands = FX_PARES if L["cat"] == "FX" else [(i, i + 1) for i in range(MUS_R[0], min(MUS_R[1], max(A)) + 1, 2) if i + 1 in A]
        ok = None
        for a, b in cands:
            if livre(a, *ext(L)) and (R is None or livre(b, *ext(R))): ok = (a, b); break
        assert ok, ("não coube", L["txt"], L["pos"])
        OC[ok[0]].append(ext(L))
        if R: OC[ok[1]].append(ext(R))
        destino.append((L, ok[0]));
        if R: destino.append((R, ok[1]))
    # 6) inserir nas trilhas de destino: só corta o vazio onde o clipe entra; o resto da trilha não é remontado
    def inserir(n, p, ta, c, td):
        s = A[n]; comps = list(s.components)
        t0 = ta.length if ta else 0; t1 = td.length if td else 0
        for i, fp, f in itens(s):
            if nome(f) != "Filler" or not (fp <= p and p + c.length <= fp + f.length): continue
            tb = comps[i-1].length if i > 0 and nome(comps[i-1]) == "TransitionEffect" else 0
            tf = comps[i+1].length if i + 1 < len(comps) and nome(comps[i+1]) == "TransitionEffect" else 0
            F1 = p - fp + t0; F2 = fp + f.length - (p + c.length) + t1
            assert (F1 == 0 and t0 == 0 and tb == 0) or F1 >= t0 + tb, ("sem espaço antes", n, p, F1)
            assert (F2 == 0 and t1 == 0 and tf == 0) or F2 >= t1 + tf, ("sem espaço depois", n, p, F2)
            bloco = ([filler(F1)] if F1 else []) + ([ta] if ta else []) + [c] + ([td] if td else []) + ([filler(F2)] if F2 else [])
            reconstruir(s, comps[:i] + bloco + comps[i+1:], f_modelo); return
        raise AssertionError(("nenhum vazio contém o clipe", n, p))
    for x, d in destino:
        inserir(d, x["pos"], x["ta"].copy(novo) if x["ta"] else None, x["c"], x["td"].copy(novo) if x["td"] else None)
    for n, s in A.items():
        assert total(s) == TOT[n], ("duração mudou", n, total(s), TOT[n])
    for x, d in destino:
        print(f"A{x['n']:>2} → A{d:<2} {x['pos']:>6} {x['c'].length:>5} ch{x['ch']}/{x['na']} {x['cat']:6} {x['txt'][:50]}")
    novo.write(TMP)
os.replace(TMP, DEST); print("gravado", DEST, os.path.getsize(DEST))
