"""Bancada B22_RAMPAS no Premiere (Windows) — a ORIGEM sintética das rampas para os testes entre NLEs (autor, 2026-10-12:
"um segmento começar em curva e depois fixar em um valor linear"; "começa normal, acelera/desacelera no meio, e depois
volta a um valor constante"; mapear quando a curva começa e termina).

    py -m lab.bancadas.premiere_rampas            (Premiere 2023 aberto com a ponte no ar; o MC FECHADO)
    py -m lab.bancadas.premiere_rampas medir      (só lê o render já feito)

Três clipes da placa B02 23,976 (o número do quadro em código de barras), 48 quadros cada, numa sequência de 23,976:
  A — 1,2× → transição suave (influência 50 %) nos quadros 12–30 → 1,9× constante (in 0)
  B — 2× → transição para 0,6× nos quadros 8–28 → 0,6×; o IN cai DENTRO da transição (14): o clipe "começa em curva"
  C — 50 % constante (`PlaybackSpeed` 0,5) com `TimeInterpolationType 2` (a hipótese do banco: Optical Flow)
Monta pela API, salva, fecha, escreve o Time Remapping no XML (o formato do R04: `ticks, fonte s, tipo, …`; tipo 6
canto, 7 → 8 transição com a influência nos campos 4 e 6), reabre, renderiza (ProRes 4444) e lê cada quadro.
"""
from __future__ import annotations

import gzip
import math
import json
import os
import re
import struct
import subprocess
import sys
import time

from . import premiere as p
from . import premiere_relink as r
from ..gerar import RAIZ

PLACA = os.path.join(RAIZ, "saida", "base", "B02_TAXAS", "B02_2398_MOV-PRORES.mov")
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", "B22_RAMPAS")
PROJETO = os.path.join(TRAB, "B22 RAMPAS.prproj")
RENDER = os.path.join(TRAB, "renders", "B22_RENDER.mov")
ANO = "2023"
J = p._js
TPS = 254016000000
Q = 1001 / 24000
TPF = 10594584000                                  # ticks por quadro de 23,976
N = 48
NL = chr(10)
MIDIA_S = 240 * Q                                  # a placa: 240 quadros


def _caso_A():
    s7 = 1.2 * 12 * Q
    s8 = s7 + 18 * Q * (1.2 + 1.9) / 2
    return [(0, 0.0, "6"), (12 * Q, s7, "7", (0.5, 0.5)), (30 * Q, s8, "8"),
            (30 * Q + (MIDIA_S - s8) / 1.9, MIDIA_S, "6")], 0


def _caso_B():
    s7 = 2 * 8 * Q
    s8 = s7 + 20 * Q * (2 + 0.6) / 2
    return [(0, 0.0, "6"), (8 * Q, s7, "7", (0.5, 0.5)), (28 * Q, s8, "8"),
            (28 * Q + (MIDIA_S - s8) / 0.6, MIDIA_S, "6")], 14


CASOS = {"RAMPA_A": _caso_A, "RAMPA_B": _caso_B, "RAMPA_C": None}


def _kf_texto(pts) -> str:
    out = []
    for pt in pts:
        t, s, tp = pt[:3]
        if tp == "7":
            i1, i2 = pt[3]
            cauda = f"7,0,{i1 * 100:g},0.0001,{i2 * 100:g},0"
        else:
            cauda = f"{tp},0,0,0,0,0"
        out.append(f"{round(t * TPS)},{s:.24f},{cauda}")
    return ";".join(out) + ";"


def esperado() -> dict:
    """Por clipe: a posição EXATA da fonte (em quadros) em cada quadro k da timeline, pelo `_remap_fonte` de produção."""
    sys.path.insert(0, os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar", "motor"))  # o De Lá Pra Cá virou o Conformar
    from prproj.leitura import _remap_fonte
    out = {}
    for nome, f in CASOS.items():
        if f is None:
            out[nome] = [k * 0.5 for k in range(N)]
            continue
        curva, inq = f()
        out[nome] = [_remap_fonte(curva, (inq + k) * Q) / Q for k in range(N)]
    return out


# ── abrir/fechar no Windows (a bancada só tinha o macOS) ──
def abrir() -> dict:
    subprocess.Popen([p._app(ANO)], close_fds=True)
    return p.esperar_ponte(300)


def rodando() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Adobe Premiere Pro.exe"], capture_output=True,
                         text=True).stdout
    return "Adobe Premiere Pro.exe" in out


def fechar(ate_s: float = 120) -> bool:
    try:
        p.executar("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } "
                   "catch (e) {} app.quit(); return true; })()", timeout=20)
    except Exception:                                # noqa: BLE001 — a ponte cai junto com o app
        pass
    fim = time.time() + ate_s
    while time.time() < fim:
        if not rodando():
            return True
        time.sleep(2)
    return False


def x(codigo: str, timeout: float = 600):
    r.TRAB = TRAB
    return r.x(codigo, timeout)


def montar() -> list:
    os.makedirs(TRAB, exist_ok=True)
    x("(function(){ try { if (app.project && app.project.path) app.project.closeDocument(0, 0); } catch (e) {} return true; })()")
    if os.path.exists(PROJETO):
        os.remove(PROJETO)
    x("app.newProject(%s)" % J(PROJETO))
    x("app.project.importFiles(%s, true, app.project.rootItem, false)" % J([PLACA]))
    return x(r"""(function(){
      var it = _lab_itens(app.project.rootItem), pl = null; for (var i = 0; i < it.length; i++) if (it[i].name == "B02_2398_MOV-PRORES.mov") pl = it[i];
      var s = app.project.createNewSequenceFromClips("B22", [pl], app.project.rootItem); s.name = "B22";
      while (s.videoTracks[0].clips.numItems) s.videoTracks[0].clips[0].remove(false, false);
      for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false);
      var nomes = %(nomes)s, o = [];
      for (var i = 0; i < nomes.length; i++) {
        var ti = new Time(), to = new Time(); ti.ticks = "0"; to.ticks = String(200 * %(tpf)d);
        pl.setInPoint(ti, 4); pl.setOutPoint(to, 4);
        var q = new Time(); q.ticks = String(i * %(n)d * %(tpf)d);
        s.videoTracks[0].overwriteClip(pl, q);
        var c = s.videoTracks[0].clips, alvo = null;
        for (var j = 0; j < c.numItems; j++) if (Math.abs(c[j].start.ticks - i * %(n)d * %(tpf)d) < %(tpf)d / 2) alvo = c[j];
        var fim = new Time(); fim.ticks = String((i + 1) * %(n)d * %(tpf)d); alvo.end = fim;
        alvo.name = nomes[i];
        o.push(alvo.name + "@" + Math.round(alvo.start.ticks / %(tpf)d) + "+" + Math.round((alvo.end.ticks - alvo.start.ticks) / %(tpf)d));
      }
      for (var a = 0; a < s.audioTracks.numTracks; a++) while (s.audioTracks[a].clips.numItems) s.audioTracks[a].clips[0].remove(false, false);
      app.project.save();
      return o;
    })()""" % {"nomes": json.dumps(list(CASOS)), "n": N, "tpf": TPF})


def _bloco(t: str, tag: str, oid: str) -> str:
    return re.search(r'\n\t<%s ObjectID="%s"[^>]*>.*?\n\t</%s>' % (tag, oid, tag), t, re.S).group(0)


def _objetos_remap(tid: int, pid: int, kf: str) -> str:
    """Os dois objetos do Time Remapping como o Premiere 23.2 grava (copiados do R04 PRODUCAO-C)."""
    linhas = [f'\t<TimeComponentParam ObjectID="{pid}" ClassID="278ae1f9-ab7b-4dff-a53c-21029a399a9d" Version="8">',
              "\t\t<Name>Speed</Name>", "\t\t<IsTimeVarying>true</IsTimeVarying>", "\t\t<IsLocked>false</IsLocked>",
              "\t\t<DiscontinuousInterpolate>false</DiscontinuousInterpolate>",
              "\t\t<ParameterControlType>21</ParameterControlType>", "\t\t<LowerBound>0</LowerBound>",
              f"\t\t<UpperBound>{MIDIA_S!r}</UpperBound>",
              "\t\t<StartKeyframe>-91445760000000000,0.000000000000000000000000,0,0,0,0,0,0</StartKeyframe>",
              f"\t\t<Keyframes>{kf}</Keyframes>", "\t\t<CurrentValue>0</CurrentValue>",
              "\t\t<RangeLocked>false</RangeLocked>", "\t\t<ParameterID>-1</ParameterID>",
              "\t</TimeComponentParam>",
              f'\t<TimeRemapping ObjectID="{tid}" ClassID="ace5148e-9c9b-40ed-9f82-64cb67308464" Version="2">',
              f'\t\t<Keyframes ObjectRef="{pid}"/>', "\t</TimeRemapping>"]
    return "".join(NL + l for l in linhas)


def forcar() -> list:
    """O Time Remapping (A, B) e a velocidade constante com interpolação (C) no XML; In/Out no tempo do CLIPE."""
    x("app.project.save()")
    x("app.project.closeDocument(0, 0)")
    t = gzip.open(PROJETO, "rb").read().decode("utf-8")
    proximo = max(int(i) for i in re.findall(r'ObjectID="(\d+)"', t)) + 1
    feitos = []
    for nome, f in CASOS.items():
        achou = None
        for mm in re.finditer(r'\n\t<VideoClipTrackItem ObjectID="(\d+)"[^>]*>.*?\n\t</VideoClipTrackItem>', t, re.S):
            sc = re.search(r'<SubClip ObjectRef="(\d+)"/>', mm.group(0)).group(1)
            sb = _bloco(t, "SubClip", sc)
            if re.search(r"<Name>([^<]*)</Name>", sb).group(1) == nome:
                achou = (mm.group(0), sb)
                break
        if achou is None:
            raise RuntimeError(f"clipe {nome} não achado no XML")
        cid = re.search(r'<Clip ObjectRef="(\d+)"/>', achou[1]).group(1)
        bloco = _bloco(t, "VideoClip", cid)
        novo = bloco
        if f is None:                                              # C: 50 % constante, interpolação 2
            v32 = struct.unpack("f", struct.pack("f", 0.5))[0]
            novo = re.sub(r"\n\t\t\t<PlaybackSpeed>[^<]*</PlaybackSpeed>", "", novo)
            novo = novo.replace("<InPoint>", f"<PlaybackSpeed>{v32!r}</PlaybackSpeed>{NL}\t\t\t<InPoint>", 1)
            novo = re.sub(r"<InPoint>-?\d+</InPoint>", "<InPoint>0</InPoint>", novo, count=1)
            novo = re.sub(r"<OutPoint>-?\d+</OutPoint>", f"<OutPoint>{round(N * TPF * v32)}</OutPoint>", novo, count=1)
            novo = re.sub(r"\n\t\t<TimeInterpolationType>[^<]*</TimeInterpolationType>", "", novo)
            novo = novo.replace(f"{NL}\t\t</Clip>", f"{NL}\t\t</Clip>{NL}\t\t<TimeInterpolationType>2</TimeInterpolationType>", 1)
            t = t.replace(bloco, novo, 1)
            feitos.append((nome, "PlaybackSpeed 0.5 + TimeInterpolationType 2"))
            continue
        curva, inq = f()
        kf = _kf_texto(curva)
        objs = ""
        m = re.search(r'<TimeRemapping ObjectRef="(\d+)"/>', bloco)
        if m:                                                      # já tem: troca as Keyframes do parâmetro
            tr = _bloco(t, "TimeRemapping", m.group(1))
            pid = re.search(r'<Keyframes ObjectRef="(\d+)"/>', tr).group(1)
            par = _bloco(t, "TimeComponentParam", pid)
            par2 = re.sub(r"<Keyframes>[^<]*</Keyframes>", f"<Keyframes>{kf}</Keyframes>", par)
            if "<Keyframes>" not in par2:
                par2 = par2.replace("</StartKeyframe>", f"</StartKeyframe>{NL}\t\t<Keyframes>{kf}</Keyframes>", 1)
            par2 = re.sub(r"<IsTimeVarying>[^<]*</IsTimeVarying>", "<IsTimeVarying>true</IsTimeVarying>", par2)
            t = t.replace(par, par2, 1)
        else:                                                      # não tem: os dois objetos, como no R04
            tid, pid = proximo, proximo + 1
            proximo += 2
            objs = _objetos_remap(tid, pid, kf)
            novo = novo.replace("<ClipID>", f'<TimeRemapping ObjectRef="{tid}"/>{NL}\t\t\t<ClipID>', 1)
        novo = re.sub(r"<InPoint>-?\d+</InPoint>", f"<InPoint>{inq * TPF}</InPoint>", novo, count=1)
        novo = re.sub(r"<OutPoint>-?\d+</OutPoint>", f"<OutPoint>{(inq + N) * TPF}</OutPoint>", novo, count=1)
        novo = re.sub(r"\n\t\t\t<PlaybackSpeed>[^<]*</PlaybackSpeed>", "", novo)
        t = t.replace(bloco, objs + novo, 1)
        feitos.append((nome, kf))
    r._gravar_prproj(PROJETO, t)
    x("app.openDocument(%s, true, true, true)" % J(PROJETO), timeout=300)
    return feitos


def conferir() -> list:
    return x(r"""(function(){ var s = null;
      for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].name == "B22") s = app.project.sequences[i];
      var c = s.videoTracks[0].clips, o = [];
      for (var j = 0; j < c.numItems; j++) o.push([c[j].name, c[j].getSpeed(), c[j].inPoint.ticks, c[j].outPoint.ticks,
        Math.round(c[j].start.ticks / %d), Math.round(c[j].end.ticks / %d)]);
      return o; })()""" % (TPF, TPF))


def renderizar() -> str:
    os.makedirs(os.path.dirname(RENDER), exist_ok=True)
    if os.path.exists(RENDER):
        os.remove(RENDER)
    pre = os.path.join(os.path.dirname(p.preset_prores(ANO)), "Match Source - Apple ProRes 4444.epr")
    print(x(r"""(function(){ var s = null;
      for (var i = 0; i < app.project.sequences.numSequences; i++) if (app.project.sequences[i].name == "B22") s = app.project.sequences[i];
      app.project.openSequence(s.sequenceID);
      return app.project.activeSequence.exportAsMediaDirect(%s, %s, 0); })()""" % (J(RENDER), J(pre)), timeout=900))
    return RENDER


def medir(arq: str = RENDER) -> dict:
    import math
    from lab import ler
    from . import avid_taxas_render as TR
    W, H = 1920, 1080
    g = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, check=True).stdout
    esp = esperado()
    out = {}
    for i, nome in enumerate(CASOS):
        linhas = []
        for k in range(N):
            n = i * N + k
            cz = g[n * W * H:(n + 1) * W * H]
            if len(cz) < W * H:
                break
            pos = esp[nome][k]
            linhas.append({"k": k, "lido": ler.ler_faixas(cz, W, H)[0], "posicao": round(pos, 4),
                           "piso": math.floor(pos + 1e-6), "perto": round(pos),
                           "mistura": round(TR.mistura(cz, 880, 520, 330, 70), 4)})
        out[nome] = {"piso": sum(l["lido"] == l["piso"] for l in linhas),
                     "perto": sum(l["lido"] == l["perto"] for l in linhas),
                     "ilegivel": sum(l["lido"] is None for l in linhas), "n": len(linhas),
                     "mistura_max": max((l["mistura"] for l in linhas), default=None), "quadros": linhas}
    with open(os.path.join(TRAB, "medida.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] != "medir":
        p.esperar_ponte(120)
        print(montar())
        print(forcar())
        print(conferir())
        renderizar()
    res = medir()
    for nome, v in res.items():
        print(nome, {k: v[k] for k in ("piso", "perto", "ilegivel", "n", "mistura_max")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ── o sentido AVID → PREMIERE: o escritor a partir das POSIÇÕES por quadro (o modelo neutro) ──
DE_AVID = os.path.join(TRAB, "B22 DE AVID.prproj")


def de_posicoes(pos: list[float], render=None, tol: float = 1e-6) -> dict:
    """O segmento traduzido pela regra do autor: velocidade constante → `PlaybackSpeed` (FluidMotion em câmera lenta →
    Optical Flow); com curva → Time Remapping com cantos (tipo 6) só onde a velocidade muda — dentro da curva isso dá um
    keyframe por quadro, no trecho constante só as pontas. `pos` em quadros da fonte (a mesma taxa da timeline)."""
    d = [b - a for a, b in zip(pos, pos[1:])]
    if all(abs(x - d[0]) < tol for x in d):
        return {"speed": d[0], "in_q": pos[0], "interp": 2 if (render == 6 and d[0] < 1) else None}
    n = len(pos)
    kfs = [0] + [k for k in range(1, n - 1) if abs(d[k] - d[k - 1]) >= tol] + [n - 1]
    # ⛔ a curva começa em (0, 0) a 100 % e o plano anda `s0` para a frente (InPoint = s0), como no R04: com o 1º
    # keyframe em (0; 15,56) o Premiere mostrou o quadro 0 da mídia no 1º quadro do clipe (B22 Resolve → Premiere).
    # ⚠️ e o deslocamento é INTEIRO: o Premiere encaixa o InPoint na grade (B18) — com 15,564 o plano andou meio quadro
    # (35/48). O trecho (0, 0) → (I, pos0) fica antes do In e não aparece.
    s0 = math.ceil(pos[0] - 1e-9) if pos[0] > 1e-9 else 0
    pts = [(k * Q + s0 * Q, pos[k] * Q, "6") for k in kfs] + [((n + s0) * Q, (pos[-1] + d[-1]) * Q, "6")]
    if s0:
        pts = [(0.0, 0.0, "6")] + pts
    return {"remap": pts, "keyframes": len(pts), "in_q": s0}


def montar_de(nomes: list[str], projeto: str) -> list:
    global PROJETO
    PROJETO = projeto
    antes = dict(CASOS)
    CASOS.clear()
    CASOS.update({n: None for n in nomes})
    try:
        return montar()
    finally:
        CASOS.clear()
        CASOS.update(antes)


def forcar_de(traduzidos: dict, projeto: str) -> list:
    """Como `forcar`, para os segmentos traduzidos (`de_posicoes`)."""
    x("app.project.save()")
    x("app.project.closeDocument(0, 0)")
    t = gzip.open(projeto, "rb").read().decode("utf-8")
    proximo = max(int(i) for i in re.findall(r'ObjectID="(\d+)"', t)) + 1
    feitos = []
    for nome, tr in traduzidos.items():
        achou = None
        for mm in re.finditer(r'\n\t<VideoClipTrackItem ObjectID="(\d+)"[^>]*>.*?\n\t</VideoClipTrackItem>', t, re.S):
            sb = _bloco(t, "SubClip", re.search(r'<SubClip ObjectRef="(\d+)"/>', mm.group(0)).group(1))
            if re.search(r"<Name>([^<]*)</Name>", sb).group(1) == nome:
                achou = sb
                break
        bloco = _bloco(t, "VideoClip", re.search(r'<Clip ObjectRef="(\d+)"/>', achou).group(1))
        novo, objs = bloco, ""
        novo = re.sub(r"\n\t\t\t<PlaybackSpeed>[^<]*</PlaybackSpeed>", "", novo)
        if "speed" in tr:
            v32 = struct.unpack("f", struct.pack("f", tr["speed"]))[0]
            ini = round(tr["in_q"] * TPF)
            novo = novo.replace("<InPoint>", f"<PlaybackSpeed>{v32!r}</PlaybackSpeed>{NL}\t\t\t<InPoint>", 1)
            novo = re.sub(r"<InPoint>-?\d+</InPoint>", f"<InPoint>{ini}</InPoint>", novo, count=1)
            novo = re.sub(r"<OutPoint>-?\d+</OutPoint>", f"<OutPoint>{round(ini + N * TPF * v32)}</OutPoint>", novo, count=1)
            if tr.get("interp") is not None:
                novo = novo.replace(f"{NL}\t\t</Clip>", f"{NL}\t\t</Clip>{NL}\t\t<TimeInterpolationType>{tr['interp']}"
                                    f"</TimeInterpolationType>", 1)
            feitos.append((nome, f"PlaybackSpeed {v32:.4f}, interp {tr.get('interp')}"))
        else:
            kf = _kf_texto(tr["remap"])
            tid, pid = proximo, proximo + 1
            proximo += 2
            if re.search(r'<TimeRemapping ObjectRef="(\d+)"/>', novo):
                raise RuntimeError(f"{nome}: o clipe já tem TimeRemapping (caso não previsto)")
            objs = _objetos_remap(tid, pid, kf)
            novo = novo.replace("<ClipID>", f'<TimeRemapping ObjectRef="{tid}"/>{NL}\t\t\t<ClipID>', 1)
            ini = round(tr.get("in_q", 0) * TPF)
            novo = re.sub(r"<InPoint>-?\d+</InPoint>", f"<InPoint>{ini}</InPoint>", novo, count=1)
            novo = re.sub(r"<OutPoint>-?\d+</OutPoint>", f"<OutPoint>{ini + N * TPF}</OutPoint>", novo, count=1)
            feitos.append((nome, f"Time Remapping, {tr['keyframes']} keyframes"))
        t = t.replace(bloco, objs + novo, 1)
    r._gravar_prproj(projeto, t)
    x("app.openDocument(%s, true, true, true)" % J(projeto), timeout=300)
    return feitos


def rodada_de_avid(origem_json: str) -> dict:
    """Lê as posições que o leitor do Avid tirou da bin, monta o projeto, escreve, renderiza e compara com o render do
    MC, quadro a quadro (número lido + diferença de pixel na caixa do número)."""
    global RENDER
    dados = json.load(open(origem_json, encoding="utf-8"))
    nomes = ["RAMPA_A", "RAMPA_B", "RAMPA_C"]
    trad = {n: de_posicoes(s["pos"], s["render"]) for n, s in zip(nomes, dados["segmentos"])}
    print(montar_de(nomes, DE_AVID))
    print(forcar_de(trad, DE_AVID))
    print(conferir())
    RENDER = os.path.join(TRAB, "renders", "B22_DE_AVID.mov")
    renderizar()
    return comparar(dados["arquivo"], RENDER, nomes)


def comparar(arq_a: str, arq_b: str, nomes: list[str]) -> dict:
    from lab import ler
    W, H = 1920, 1080

    def quadros(arq):
        g = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-map", "0:v:0", "-frames:v", "144", "-f", "rawvideo",
                            "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        return [g[n * W * H:(n + 1) * W * H] for n in range(len(g) // (W * H))]
    a, b = quadros(arq_a), quadros(arq_b)
    caixa = [(y * W + x) for y in range(520, 590, 2) for x in range(880, 1210, 2)]
    out = {}
    for i, nome in enumerate(nomes):
        linhas = []
        for k in range(N):
            n = i * N + k
            la, lb = ler.ler_faixas(a[n], W, H)[0], ler.ler_faixas(b[n], W, H)[0]
            linhas.append((k, la, lb, round(sum(abs(a[n][q] - b[n][q]) for q in caixa) / len(caixa), 2)))
        out[nome] = {"mesmo_numero": sum(l[1] == l[2] for l in linhas), "dif_max": max(l[3] for l in linhas),
                     "linhas": linhas}
    with open(os.path.join(TRAB, "avid_x_premiere_de_avid.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=0)
    return {k: {x: v[x] for x in ("mesmo_numero", "dif_max")} for k, v in out.items()}


def rodada_de(origem_json: str, rotulo: str) -> dict:
    """`rodada_de_avid` para QUALQUER origem (as posições no mesmo formato): projeto e render com o `rotulo`."""
    global RENDER
    dados = json.load(open(origem_json, encoding="utf-8"))
    nomes = ["RAMPA_A", "RAMPA_B", "RAMPA_C"]
    projeto = os.path.join(TRAB, f"B22 DE {rotulo}.prproj")
    trad = {n: de_posicoes(s["pos"], s["render"]) for n, s in zip(nomes, dados["segmentos"])}
    print(montar_de(nomes, projeto))
    print(forcar_de(trad, projeto))
    print(conferir())
    RENDER = os.path.join(TRAB, "renders", f"B22_DE_{rotulo}.mov")
    renderizar()
    return comparar(dados["arquivo"], RENDER, nomes)
