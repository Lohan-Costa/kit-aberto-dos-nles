"""A MÁSCARA RETANGULAR com feather na Lumetri — a lei da borda, para traduzir o Gradient do Resolve (2026-11-20).

O autor pediu: o Gradient do Resolve (`drt-drp/estruturas.md` §A BORDA EM PX: rampa em S só para um lado, meio em
0,52·L) vira, no Premiere, um RETÂNGULO com feather na Lumetri. No 26.5/2027 a interface mudou ("Unassigned Masks"),
mas o arquivo é o mesmo: `AE.ADBE AEMask2` em `SubComponents` da Lumetri (o molde, salvo pelo 26.5.2 no Windows:
`saida/bancadas/premiere-26.5.2/B24_COR_MC/LAB MASCARA LUMETRI 26.prproj`, 35 parâmetros; o 26.0.2 grava 27).

Pela ponte do laboratório (`premiere.py`), no Premiere `ANO`:
1. `montar` — projeto novo, o quadro branco em N cópias de 12 quadros, uma Lumetri com Exposure −5 em cada;
2. `injetar` — com o projeto FECHADO, uma `Mask2` retangular em cada Lumetri (clone do molde: ids e BinaryHash novos);
   a aresta vertical em x = `BORDA` (fração do quadro), o retângulo saindo do quadro pelos outros três lados;
3. reabrir, exportar ProRes, medir o perfil da linha do meio (`perfil`).

    python -m lab.bancadas.premiere_mascara_lumetri rodar
"""
from __future__ import annotations

import base64
import gzip
import json
import os
import re
import struct
import subprocess
import sys

import numpy as np

from . import premiere as p
from . import premiere_cor_mc as pc

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRANCO = os.path.join(RAIZ, "saida", "bancadas", "resolve_cor", "BRANCO_1080.mov")
MOLDE = os.path.join(RAIZ, "saida", "bancadas", "premiere-26.5.2", "B24_COR_MC", "LAB MASCARA LUMETRI 26.prproj")
TRABALHO = os.path.join(RAIZ, "saida", "bancadas", "premiere_mascara_lumetri")
QUADROS, MEIO = 12, 6
BORDA = 0.5
# (feather px, expansion px) por clipe; o 1º sem máscara (a referência da Lumetri inteira)
VARIANTES = [None, (0, 0), (25, 0), (50, 0), (100, 0), (200, 0), (400, 0), (100, 100)]


def montar(nome: str, n: int) -> str:
    os.makedirs(TRABALHO, exist_ok=True)
    proj = os.path.join(TRABALHO, nome + ".prproj")
    if os.path.exists(proj):
        os.remove(proj)
    js = """(function(){
      var proj = %s, src = %s, N = %d, Q = %d;
      if (!app.newProject(proj)) return "newProject falhou";
      app.project.importFiles([src], true, app.project.rootItem, false);
      var it = null;
      for (var i = 0; i < app.project.rootItem.children.numItems; i++) {
        var c = app.project.rootItem.children[i]; if (c.name.indexOf("BRANCO_1080") == 0) it = c; }
      if (!it) return "sem o branco";
      var seq = app.project.createNewSequenceFromClips("COR", [it], app.project.rootItem);
      var v1 = seq.videoTracks[0];
      while (v1.clips.numItems) v1.clips[0].remove(false, false);
      var TQ = 10594584000;
      var tin = new Time(); tin.ticks = "0"; var tout = new Time(); tout.ticks = String(Q * TQ);
      it.setInPoint(tin, 4); it.setOutPoint(tout, 4);
      for (var k = 0; k < N; k++) { var tk = new Time(); tk.ticks = String(k * Q * TQ); v1.overwriteClip(it, tk); }
      app.enableQE();
      var qv = qe.project.getActiveSequence().getVideoTrackAt(0), clipes = [];
      for (var i = 0; i < qv.numItems; i++) if (qv.getItemAt(i).type == "Clip") clipes.push(qv.getItemAt(i));
      var ef = qe.project.getVideoEffectByName("Lumetri Color");
      for (var k = 0; k < N; k++) clipes[k].addVideoEffect(ef);
      var out = [];
      for (var k = 0; k < N; k++) {
        var ti = v1.clips[k], comp = null;
        for (var j = 0; j < ti.components.numItems; j++) if (ti.components[j].matchName == "AE.ADBE Lumetri") comp = ti.components[j];
        if (!comp) { out.push("sem lumetri " + k); continue; }
        for (var j = 0; j < comp.properties.numItems; j++)
          if (comp.properties[j].displayName == "Exposure") { comp.properties[j].setValue(-5, true); out.push(comp.properties[j].getValue()); break; }
      }
      app.project.save();
      return {clipes: v1.clips.numItems, exp: out, versao: app.version};
    })()""" % (pc._js(proj), pc._js(BRANCO), n, QUADROS)
    r = p.executar(js)
    print("montar:", r, flush=True)
    return proj


# ── a máscara no XML ─────────────────────────────────────────────────────────────────────────────────────────────────
def caminho(vertices: list[tuple[float, float]]) -> bytes:
    """O `Path` (param 7) de um contorno de CANTOS: o cabeçalho do molde (21 bytes, o nº de vértices no 17), 28 bytes
    por vértice (u32 0 = canto + vértice + alça de entrada + alça de saída, f32 0–1 do quadro da fonte, Y para baixo)
    e o byte 01 do fim (fechado)."""
    cab = bytes.fromhex("020000000100000056790000" "00" "02000000")
    corpo = b"".join(struct.pack("<I6f", 0, x, y, x, y, x, y) for x, y in vertices)
    return cab + struct.pack("<I", len(vertices)) + corpo + b"\x01"


def _conteudos(xml: str) -> dict:
    return dict(re.findall(r'BinaryHash="([^"]+)">([^<]+)<', xml))


def _molde() -> tuple[str, list[str], dict]:
    xml = pc.ler_xml(MOLDE)
    m = re.search(r'<VideoFilterComponent ObjectID="(\d+)"[^>]*>(?:(?!</VideoFilterComponent>).)*?<DisplayName>Mask2'
                  r'</DisplayName>\s*<InstanceName>.*?</VideoFilterComponent>', xml, re.S)
    comp = m.group(0)
    params = [pc._obj(xml, r).group(0) for r in re.findall(r'<Param Index="\d+" ObjectRef="(\d+)"/>', comp)]
    return comp, params, _conteudos(xml)


def _binarios_novos(trecho: str, conteudos: dict) -> str:
    """Cada valor binário do clone com o SEU conteúdo e um BinaryHash novo (o vazio deduplicado ficaria órfão)."""
    def troca(mm):
        tag, h, corpo = mm.group(1), mm.group(2), mm.group(3)
        dados = (corpo or conteudos.get(h, "")).strip()
        n = len(base64.b64decode(dados)) if dados else 0
        return '<%s Encoding="base64" BinaryHash="%s">%s</%s>' % (tag, pc._hash(n), dados, tag)
    return re.sub(r'<(\w+) Encoding="base64" BinaryHash="([^"]+)"(?:/>|>([^<]*)</\1>)', troca, trecho)


def _param(params: list[str], nome: str | None = None, pid: int | None = None) -> int:
    for i, t in enumerate(params):
        if pid is not None and f"<ParameterID>{pid}</ParameterID>" in t:
            return i
        if nome is not None and f"<Name>{nome}</Name>" in t:
            return i
    raise KeyError(nome or pid)


def _valor(t: str, v: float) -> str:
    return re.sub(r"<StartKeyframe>(-?\d+),[^,]*,", lambda m: f"<StartKeyframe>{m.group(1)},{v!r},", t, count=1)


def injetar(proj: str, variantes: list) -> dict:
    comp, params, conteudos = _molde()
    xml = pc.ler_xml(proj)
    prox = max(int(x) for x in re.findall(r'ObjectID="(\d+)"', xml)) + 1
    lum = pc.lumetri_por_clipe(xml)
    blocos, feito = [], {}
    ret = [(-1.0, -1.0), (BORDA, -1.0), (BORDA, 2.0), (-1.0, 2.0)]   # a aresta direita em x = BORDA
    for k, var in enumerate(variantes):
        if var is None or lum[k] is None:
            continue
        feather, expansao = var[0], var[1]
        contorno = var[2] if len(var) > 2 else ret
        ids = list(range(prox, prox + len(params) + 1))
        prox += len(params) + 1
        novos = []
        for i, t in enumerate(params):
            t = re.sub(r'ObjectID="\d+"', f'ObjectID="{ids[i + 1]}"', t, count=1)
            novos.append(t)
        ip = _param(params, "Path")
        novos[ip] = re.sub(r'(<StartKeyframeValue Encoding="base64" BinaryHash=")[^"]+"(?:/>|>[^<]*</StartKeyframeValue>)',
                           lambda m: '<StartKeyframeValue Encoding="base64" BinaryHash="x">%s</StartKeyframeValue>'
                           % base64.b64encode(caminho(contorno)).decode(), novos[ip])
        novos[_param(params, "Feather")] = _valor(novos[_param(params, "Feather")], float(feather))
        novos[_param(params, "Expansion")] = _valor(novos[_param(params, "Expansion")], float(expansao))
        c = re.sub(r'ObjectID="\d+"', f'ObjectID="{ids[0]}"', comp, count=1)
        refs = iter(ids[1:])
        c = re.sub(r'(<Param Index="\d+" ObjectRef=")\d+("/>)', lambda m: m.group(1) + str(next(refs)) + m.group(2), c)
        blocos.append(_binarios_novos(c, conteudos))
        blocos += [_binarios_novos(t, conteudos) for t in novos]
        # pendura na Lumetri do clipe k
        m = pc._obj(xml, lum[k])
        corpo = m.group(0)
        sub = f'<SubComponents Version="1">\n\t\t\t<SubComponent Index="0" ObjectRef="{ids[0]}"/>\n\t\t</SubComponents>\n\t\t'
        corpo = corpo.replace("<MatchName>AE.ADBE Lumetri</MatchName>", sub + "<MatchName>AE.ADBE Lumetri</MatchName>", 1)
        xml = xml[:m.start()] + corpo + xml[m.end():]
        feito[k] = {"mascara": ids[0], "feather": feather, "expansao": expansao}
    # os valores deduplicados do próprio projeto ficam como estão; os blocos novos entram antes do fecho
    fim = xml.rfind("</PremiereData>")
    xml = xml[:fim] + "\n".join(blocos) + "\n" + xml[fim:]
    pc.gravar_xml(proj, xml)
    return feito


# ── a medida ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def quadro(arquivo: str, n: int) -> np.ndarray:
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", arquivo, "-vf", f"select=eq(n\\,{n})", "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "gray16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(b, np.uint16).reshape(1080, 1920).astype(float) / 65535


def perfil(arquivo: str, k: int, ref_escuro: float, ref_claro: float) -> dict:
    """A linha do meio do clipe k normalizada: 1 = escurecido (dentro da máscara), 0 = branco."""
    lin = quadro(arquivo, k * QUADROS + MEIO)[500:580].mean(0)
    s = (ref_claro - lin) / (ref_claro - ref_escuro)
    def onde(nivel):
        i = np.where(s < nivel)[0]
        return float(i[0]) if len(i) else None
    return {"s": [round(float(x), 4) for x in s], "x90": onde(0.9), "x50": onde(0.5), "x10": onde(0.1)}


def gradient_para_retangulo(linha_y: float, soft_l: float, w: int = 1920, h: int = 1080) -> tuple:
    """O Gradient do Resolve SEM rotação (escurece o lado de CIMA da linha horizontal em y px, Soft 1 = L px, o `…0B`)
    → (feather, expansion, contorno): a aresta a 0,53·L abaixo da linha (o meio da rampa em S do Gradient), feather
    0,60·L (a largura 10–90 % do Gradient é 0,56·L; a do Premiere, 0,935·feather; as rampas têm a mesma forma em S,
    ≤ 0,034 normalizadas)."""
    aresta = (linha_y + 0.53 * soft_l) / h
    return (0.60 * soft_l, 0, [(-1.0, -1.0), (2.0, -1.0), (2.0, aresta), (-1.0, aresta)])


def conferir_gradient(ano: str = "2027") -> dict:
    """Ponta a ponta: o caso "Gradient Soft 2" (L = 200, linha em y 538,5) medido no Resolve
    (`saida/bancadas/resolve_cor/renders/JANELAS_BORDA_5.npy`) contra o retângulo traduzido no Premiere."""
    g = gradient_para_retangulo(538.5, 200.0)
    variantes = [None, g, (0, 0, g[2])]
    p.esperar_ponte()
    proj = montar("GRADIENT PARA RETANGULO " + ano, len(variantes))
    pc.fechar_projeto()
    injetar(proj, variantes)
    pc.abrir_projeto(proj)
    mov = pc.exportar(proj, ano)
    escuro = float(quadro(mov, MEIO).mean())
    q = quadro(mov, QUADROS + MEIO)
    branco = float(q[1000:1070].mean())
    premiere = ((branco - q) / (branco - escuro)).clip(0, 1)
    resolve = np.load(os.path.join(RAIZ, "saida", "bancadas", "resolve_cor", "renders", "JANELAS_BORDA_5.npy"))
    dif = np.abs(premiere - resolve)[:, 200:1720]
    col_p, col_r = premiere[:, 960], resolve[:, 960]
    res = {"ano": ano, "render": mov, "feather": g[0], "aresta_y": g[2][2][1] * 1080,
           "dif_media": round(float(dif.mean()), 4), "dif_max": round(float(dif.max()), 4),
           "dif_p99": round(float(np.percentile(dif, 99)), 4),
           "coluna": {"y": list(range(300, 760, 20)), "premiere": [round(float(col_p[y]), 3) for y in range(300, 760, 20)],
                      "resolve": [round(float(col_r[y]), 3) for y in range(300, 760, 20)]}}
    with open(os.path.join(TRABALHO, f"gradient_{ano}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False), flush=True)
    return res


def rodar(ano: str = "2027") -> dict:
    p.instalar()
    p.reabrir_premiere(ano)
    p.esperar_ponte()
    proj = montar("MASCARA LUMETRI " + ano, len(VARIANTES))
    pc.fechar_projeto()
    feito = injetar(proj, VARIANTES)
    pc.abrir_projeto(proj)
    mov = pc.exportar(proj, ano)
    claro = float(quadro(mov, 0 * QUADROS + MEIO)[500:580].mean())   # o 1º clipe: Lumetri sem máscara (escuro inteiro)
    # a referência do branco: o canto direito de um clipe com máscara (fora do retângulo)
    branco = float(quadro(mov, 1 * QUADROS + MEIO)[500:580, 1700:1900].mean())
    res = {"ano": ano, "projeto": proj, "render": mov, "escuro": claro, "branco": branco, "clipes": {}}
    for k, var in enumerate(VARIANTES):
        if var is None:
            continue
        pf = perfil(mov, k, claro, branco)
        res["clipes"][str(var)] = {**feito.get(k, {}), "x90": pf["x90"], "x50": pf["x50"], "x10": pf["x10"],
                                   "s": pf["s"][700:1300]}
        print(var, pf["x90"], pf["x50"], pf["x10"], flush=True)
    with open(os.path.join(TRABALHO, f"medidas_{ano}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["rodar"]:
        rodar(*(sys.argv[2:3] or []))
    elif sys.argv[1:2] == ["gradient"]:
        conferir_gradient(*(sys.argv[2:3] or []))
