"""B24_COR_MC no RESOLVE — levar o Color Correction do Media Composer para a página Color, EDITÁVEL, e medir na
MESMA carta (pedido do autor, 2026-11-20: controles editáveis com LUT de reserva; o Resolve primeiro).

Roda de FORA do Resolve (API externa, `resolve.conectar()`), num projeto DESCARTÁVEL (banco: uma grade montada que
derruba o Resolve fica salva no projeto). O caminho:

1. `preparar` — projeto "LAB COR RESOLVE" (23,976, 1080p), a carta importada, uma timeline com N cópias da carta
   (12 quadros cada; o quadro do meio de cada uma é o que se mede);
2. `bodies_do_projeto` — os `Body` das grades, lidos de uma CÓPIA do `Project.db` (só depois do `SaveProject`);
3. `aplicar` — um `.drx` mínimo com o `Body` montado → `ApplyGradeFromDRX` (página Edit: a paleta Curves nunca
   desenha a curva — a queda registrada no banco acontece aí);
4. `renderizar` + `medir` — ProRes 422 HQ, Y'CbCr de 8 bits no miolo de cada área (o medidor do MC).

Banco: `protocolos/drt-drp/estruturas.md` (o `Body`, os ids dos controles, a curva Custom = Bézier por trechos, o eixo
0–1 da curva = código 0,00649 a 1,02441) e `protocolos/avb/color-correction.md` (o lado do MC).
"""
from __future__ import annotations

import glob
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARTA = os.path.join(RAIZ, "saida", "base", "B24_COR_MC", "B24_CARTA_COR.mov")
TRABALHO = os.path.join(RAIZ, "saida", "bancadas", "resolve_cor")
PROJETO = "LAB COR RESOLVE"
PASTA_PM = "LABORATORIO"
QUADROS = 12            # por cópia da carta na timeline
MEIO = 6                # o quadro medido de cada cópia


def _motor():
    """O `pb_decode`/`pb_encode` e o zstd do motor do Conformar (o mesmo que escreve os `.drx` do produto)."""
    m = os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar", "motor")
    if m not in sys.path:
        sys.path.insert(0, m)
    import zstandard
    from tools.inspect_drp import pb_decode, pb_encode
    return zstandard, pb_decode, pb_encode


def projeto(resolve, nome: str = PROJETO):
    pm = resolve.GetProjectManager()
    pm.GotoRootFolder()
    if PASTA_PM not in pm.GetFolderListInCurrentFolder():
        pm.CreateFolder(PASTA_PM)
    pm.OpenFolder(PASTA_PM)
    atual = pm.GetCurrentProject()
    if atual and atual.GetName() == nome:
        return atual
    if nome in pm.GetProjectListInCurrentFolder():
        return pm.LoadProject(nome)
    p = pm.CreateProject(nome)
    for k, v in (("timelineFrameRate", "23.976"), ("timelineResolutionWidth", "1920"),
                 ("timelineResolutionHeight", "1080")):
        p.SetSetting(k, v)
    return p


def _carta(p):
    pool = p.GetMediaPool()
    raiz = pool.GetRootFolder()
    for c in raiz.GetClipList() or []:
        if c.GetClipProperty("File Name") == os.path.basename(CARTA):
            return c
    pool.SetCurrentFolder(raiz)
    return (pool.ImportMedia([CARTA]) or [None])[0]


def achar_timeline(p, nome: str):
    for i in range(1, p.GetTimelineCount() + 1):
        tl = p.GetTimelineByIndex(i)
        if tl.GetName() == nome:
            return tl
    return None


def preparar(resolve, nome_tl: str, n: int) -> list:
    """A timeline `nome_tl` com `n` cópias da carta (cria se não existir). Devolve os itens da V1, em ordem."""
    p = projeto(resolve)
    tl = achar_timeline(p, nome_tl)
    if tl is None:
        c = _carta(p)
        pool = p.GetMediaPool()
        tl = pool.CreateEmptyTimeline(nome_tl)
        p.SetCurrentTimeline(tl)
        pool.AppendToTimeline([{"mediaPoolItem": c, "startFrame": 0, "endFrame": QUADROS, "mediaType": 1}
                               for _ in range(n)])
    p.SetCurrentTimeline(tl)
    return sorted(tl.GetItemListInTrack("video", 1) or [], key=lambda it: it.GetStart())


def salvar(resolve) -> None:
    resolve.GetProjectManager().SaveProject()


def _db(nome: str = PROJETO) -> str:
    base = os.path.join(os.environ.get("APPDATA", ""), "Blackmagic Design", "DaVinci Resolve", "Support",
                        "Resolve Project Library", "Resolve Projects", "Users", "guest", "Projects")
    achados = glob.glob(os.path.join(base, "**", nome, "Project.db"), recursive=True)
    if not achados:
        raise FileNotFoundError(f"Project.db de {nome!r} em {base}")
    return max(achados, key=os.path.getmtime)


def bodies_do_projeto(nome: str = PROJETO) -> list[bytes]:
    """Os `Body` (descomprimidos) de todas as versões de grade do projeto, de uma CÓPIA do `Project.db`."""
    zstandard, _, _ = _motor()
    tmp = os.path.join(tempfile.gettempdir(), f"lab_cor_{uuid.uuid4().hex}.db")
    shutil.copy(_db(nome), tmp)
    try:
        c = sqlite3.connect(tmp)
        fora = []
        for (b,) in c.execute('select Body from "ListMgt::LmVersion"'):
            if b and b[0] == 0x81:
                fora.append(zstandard.ZstdDecompressor().decompress(b[1:], max_output_size=1 << 28))
        c.close()
        return fora
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def drx(body: bytes) -> str:
    zstandard, _, _ = _motor()
    blob = (b"\x81" + zstandard.ZstdCompressor().compress(body)).hex()
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<Gallery::GyStill DbId="{uuid.uuid4()}">\n <pClipFullVer>\n'
            f'  <ListMgt::LmVersion DbId="{uuid.uuid4()}">\n   <FieldsBlob/>\n   <Name/>\n'
            '   <HasCorrection>false</HasCorrection>\n   <VerType>0</VerType>\n   <ImplVersion>1</ImplVersion>\n'
            f'   <Body>{blob}</Body>\n  </ListMgt::LmVersion>\n </pClipFullVer>\n</Gallery::GyStill>\n')


def aplicar(tl, item, body: bytes, nome: str) -> bool:
    os.makedirs(os.path.join(TRABALHO, "drx"), exist_ok=True)
    caminho = os.path.join(TRABALHO, "drx", f"{nome}.drx")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(drx(body))
    pegar = getattr(item, "GetNodeGraph", None)
    g = pegar() if callable(pegar) else None
    m = getattr(g, "ApplyGradeFromDRX", None) if g is not None else None
    if callable(m) and m(caminho, 0):
        return True
    m = getattr(tl, "ApplyGradeFromDRX", None)
    return bool(callable(m) and m(caminho, 0, [item]))


def renderizar(resolve, nome_tl: str, nome_arquivo: str, ate_s: float = 300) -> str:
    """ProRes 422 HQ da timeline inteira, sem áudio; espera terminar. Devolve o caminho."""
    p = projeto(resolve)
    p.SetCurrentTimeline(achar_timeline(p, nome_tl))
    resolve.OpenPage("deliver")
    pasta = os.path.join(TRABALHO, "renders")
    os.makedirs(pasta, exist_ok=True)
    alvo = os.path.join(pasta, nome_arquivo + ".mov")
    if os.path.exists(alvo):
        os.remove(alvo)
    p.DeleteAllRenderJobs()
    p.SetCurrentRenderFormatAndCodec("mov", "ProRes422HQ")
    p.SetRenderSettings({"SelectAllFrames": True, "TargetDir": pasta, "CustomName": nome_arquivo,
                         "ExportVideo": True, "ExportAudio": False})
    job = p.AddRenderJob()
    p.StartRendering([job], isInteractiveMode=False)
    limite = time.time() + ate_s
    while p.IsRenderingInProgress() and time.time() < limite:
        time.sleep(1)
    st = p.GetRenderJobStatus(job)
    resolve.OpenPage("edit")
    if not os.path.exists(alvo):
        raise RuntimeError(f"render sem arquivo: {st}")
    return alvo


def medir(arquivo: str, n: int) -> list[dict]:
    """A medida de cada cópia da carta (o quadro do meio), na ordem da timeline."""
    from ..cor_b24_medir import medir as _medir
    return [_medir(arquivo, k * QUADROS + MEIO) for k in range(n)]


# ── o Body montado ────────────────────────────────────────────────────────────────────────────────────────────────────
#: ids dos controles (banco `drt-drp/estruturas.md`; Sat e Lum Mix conferidos no Body do SetCDL do 19.1.4, 2026-11-20)
SAT = 0x06000005
LUM_MIX = 0x8600000B
CURVA = {"R": 0x86000506, "G": 0x86000507, "B": 0x86000508, "Y": 0x86000509}
FLAG = {"R": 0x860000BD, "G": 0x860000BE, "B": 0x860000BF, "Y": 0x860000BB}
#: a ponta da lista da curva Custom: (−1024, −1024) na frente; a escala dos pontos é 0–1023 (banco)
SENTINELA = -1024.0
ESCALA = 1023.0


def _f32(v: float) -> bytes:
    import struct
    return struct.pack("<f", float(v))


def _campo(f: int, v) -> dict:
    if isinstance(v, int):
        return {"field": f, "wire": 0, "value": v}
    if isinstance(v, float):
        return {"field": f, "wire": 5, "value": _f32(v)}
    return {"field": f, "wire": 2, "value": v}


def _msg(*pares) -> list[dict]:
    return [_campo(f, v) for f, v in pares]


def p_f32(pid: int, v: float) -> dict:
    return _campo(3, _msg((1, pid), (2, _msg((1, float(v))))))


def p_int(pid: int, n: int) -> dict:
    return _campo(3, _msg((1, pid), (2, _msg((2, int(n))))))


def p_curva(pid: int, lista: list[tuple[float, float]]) -> dict:
    """`{1: id, 2: {8: {1: ponto, 1: ponto, …}}}` — UM campo 8 com os pontos repetidos no campo 1 (lido da curva feita
    na UI do 19.1.4, 2026-11-20; um campo 8 POR ponto derrubou o Resolve no `ApplyGradeFromDRX`). Ponto = `{1: x, 2: y}`
    em f32 na escala 0–1023, o ZERO omitido (o (0, 0) vai vazio, como o Resolve grava), a sentinela na frente."""
    pts = [(SENTINELA, SENTINELA)] + [(x * ESCALA, y * ESCALA) for x, y in lista]
    ponto = [_campo(1, [_campo(k, float(v)) for k, v in ((1, x), (2, y)) if v != 0.0]) for x, y in pts]
    return _campo(3, _msg((1, pid), (2, _msg((8, ponto)))))


def curvas_rgb(lista: list[tuple[float, float]], canais: str = "RGB") -> list[dict]:
    """A MESMA lista Bézier (P0 a a P1 a a P2 …, em 0–1) nas curvas dos `canais`, o flag = 2 × pontos do meio, e a
    Lum Mix 0 (sem ela as curvas R/G/B preservam a luma — banco)."""
    meio = (len(lista) - 4) // 3
    assert len(lista) == 4 + 3 * meio, f"lista Bézier com {len(lista)} pontos (tem de ser 4 + 3k)"
    out = []
    for c in canais:
        out += [p_curva(CURVA[c], lista), p_int(FLAG[c], 2 * meio)]
    return out + [p_f32(LUM_MIX, 0.0)]


def no(nid: int, params: list[dict], rotulo: str | None = None) -> dict:
    """Um nó (campo 7 do grafo), na forma do Body do SetCDL do 19.1.4 (x = 190 + 270·(n−1), y 180); rótulo = campo 6."""
    campos = [(1, nid), (2, nid)] + ([(6, rotulo.encode("utf-8"))] if rotulo else []) + [
        (4, 190 + 270 * (nid - 1)), (5, 180), (7, 1), (8, 44),
        (9, _msg((1, _msg((1, 1), (3, 1), (6, _msg((2, _msg((1, 1)) + params)))))) + _msg((2, bytes.fromhex("0304050612")))),
        (10, bytes.fromhex("0a0a08818080800c12021002"))]
    return _campo(7, _msg(*campos))


def body(nos: list[dict]) -> bytes:
    """O grafo em SÉRIE: entrada → nó 1 → … → saída (banco: ligação `{1: de, 3: para, 5: 64, 6: 64, 7: nº}`)."""
    _, _, enc = _motor()
    n = len(nos)
    res = _msg((1, 1920), (2, 1080), (3, 1.0), (4, 1920), (5, 1080), (6, 1.0), (7, 1920), (8, 1080), (9, 4294967295))
    g = _msg((1, n), (2, 1), (3, res)) + list(nos)
    for k in range(1, n):
        g.append(_campo(8, _msg((1, k), (3, k + 1), (5, 64), (6, 64), (7, k))))
    g.append(_campo(9, _msg((1, 1), (2, 80), (3, _msg((1, 1), (2, 64), (3, 1), (4, 1))))))
    g.append(_campo(10, _msg((1, 2), (2, 64), (3, _msg((1, n + 1), (2, 64), (3, 2), (4, n))))))
    return bytes(enc([_campo(1, g)]))


# ── a curva do MC na curva Custom do Resolve ──────────────────────────────────────────────────────────────────────────
#: o eixo da curva Custom: 0–1 da curva = valor C0 + W·u da imagem (banco, 2026-10-11, rampa de cinza 8 bits)
EIXO_C0, EIXO_W = 0.00649, 1.01792


def _tangentes(xs, ys) -> list[float]:
    """As da curva do MC: Catmull-Rom (secante dos vizinhos); nas pontas, a secante do segmento (`cor_curva.catmull`)."""
    n = len(xs)
    if n == 2:
        s = (ys[1] - ys[0]) / (xs[1] - xs[0])
        return [s, s]
    return ([(ys[1] - ys[0]) / (xs[1] - xs[0])]
            + [(ys[i + 1] - ys[i - 1]) / (xs[i + 1] - xs[i - 1]) for i in range(1, n - 1)]
            + [(ys[-1] - ys[-2]) / (xs[-1] - xs[-2])])


def _mc(xs, ys, ms, t: float, j: int | None):
    """Valor e derivada da curva do MC em t, no trecho j (None = fora das pontas: plana)."""
    if j is None:
        return (ys[0] if t <= xs[0] else ys[-1]), 0.0
    h = xs[j + 1] - xs[j]
    s = (t - xs[j]) / h
    v = ((2 * s**3 - 3 * s**2 + 1) * ys[j] + (s**3 - 2 * s**2 + s) * h * ms[j]
         + (-2 * s**3 + 3 * s**2) * ys[j + 1] + (s**3 - s**2) * h * ms[j + 1])
    d = ((6 * s * s - 6 * s) * ys[j] + (3 * s * s - 4 * s + 1) * h * ms[j]
         + (-6 * s * s + 6 * s) * ys[j + 1] + (3 * s * s - 2 * s) * h * ms[j + 1]) / h
    return v, d


def curva_do_mc(pontos: list[tuple[float, float]], c0: float = EIXO_C0, w: float = EIXO_W) -> list[tuple[float, float]]:
    """A curva Master do MC (pontos em t = código/255, Catmull-Rom, plana fora das pontas) como lista Bézier da curva
    Custom do Resolve, no eixo dele: u tal que o valor da imagem é v = C0 + W·u, e v = (código − 16)/219 na mídia de
    faixa de vídeo. A troca é AFIM nos dois eixos: cada intervalo entre os nós (cortado em u = 0 e 1) é UMA cúbica —
    plana ou um trecho da Hermite — e vira um trecho Bézier EXATO pelas derivadas de cada lado."""
    P = sorted((float(x), float(y)) for x, y in pontos)
    xs, ys = [x for x, _ in P], [y for _, y in P]
    ms = _tangentes(xs, ys)
    a, b = 219 * w / 255, (16 + 219 * c0) / 255          # t = a·u + b
    k = 255 / 219 / w                                     # dy_u/dy_t

    def yu(y):
        return ((255 * y - 16) / 219 - c0) / w

    quebras = sorted({0.0, 1.0} | {(x - b) / a for x in xs if 0 < (x - b) / a < 1})
    lista = []
    for p, q in zip(quebras, quebras[1:]):
        tm = a * (p + q) / 2 + b
        j = next((i for i in range(len(xs) - 1) if xs[i] <= tm <= xs[i + 1]), None)
        v0, d0 = _mc(xs, ys, ms, a * p + b, j)
        v1, d1 = _mc(xs, ys, ms, a * q + b, j)
        y0, y1, m0, m1 = yu(v0), yu(v1), d0 * a * k, d1 * a * k
        h = q - p
        if not lista:
            lista.append((p, y0))
        lista += [(p + h / 3, y0 + m0 * h / 3), (q - h / 3, y1 - m1 * h / 3), (q, y1)]
    return lista


def avaliar_bezier(lista: list[tuple[float, float]], u):
    """A curva Custom como Bézier cúbica por trechos (plana fora): y(u) — para conferir a tradução no papel."""
    import numpy as np
    u = np.atleast_1d(np.asarray(u, float))
    out = np.empty_like(u)
    for k, uu in enumerate(u):
        if uu <= lista[0][0] or uu >= lista[-1][0]:
            out[k] = lista[0][1] if uu <= lista[0][0] else lista[-1][1]
            continue
        for i in range(0, len(lista) - 3, 3):
            p0, p1, p2, p3 = lista[i:i + 4]
            if p0[0] <= uu <= p3[0]:
                lo, hi = 0.0, 1.0
                for _ in range(60):
                    s = (lo + hi) / 2
                    x = (1 - s) ** 3 * p0[0] + 3 * (1 - s) ** 2 * s * p1[0] + 3 * (1 - s) * s * s * p2[0] + s ** 3 * p3[0]
                    lo, hi = (s, hi) if x < uu else (lo, s)
                s = (lo + hi) / 2
                out[k] = (1 - s) ** 3 * p0[1] + 3 * (1 - s) ** 2 * s * p1[1] + 3 * (1 - s) * s * s * p2[1] + s ** 3 * p3[1]
                break
    return out
