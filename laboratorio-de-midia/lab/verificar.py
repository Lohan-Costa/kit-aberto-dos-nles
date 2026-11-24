"""Confere cada arquivo de um caso contra o `verdade.json` — antes de alguém confiar nele.

    python3 -m lab.verificar saida/base/B01_FORMATOS

Mede (não infere): ffprobe para codec, raster, taxa, quantidade de quadros e TC; o código de barras
do primeiro, do quadro do meio e do último; o tom de cada canal e onde caem as claques. Grava
`verificacao.json` ao lado da verdade e sai com 1 se algo não bateu.
"""
from __future__ import annotations

import json
import os
import sys
from fractions import Fraction

from . import ffmpeg, ler, tc

TOLERANCIA_CLAQUE_S = 0.0015


def codigo_esperado(esp: dict, k: int) -> list[int]:
    """[quadro no arquivo, rótulo do TC] que o quadro `k` do arquivo deve trazer no código de barras."""
    v = esp.get("video") or {}
    b = esp.get("base") or tc.base(tc.taxa(v.get("fps") or esp.get("fps")))
    return [k, tc.rotulo(esp["tc_inicio_quadros"] + k, b, bool(esp.get("drop_frame")))]


def claques_esperadas(esp: dict, janela: float) -> list[float]:
    cl = esp["claque"]
    if "instantes_s" in cl:
        return [round(x, 4) for x in cl["instantes_s"] if x < janela - 0.01]
    saida, t = [], cl["primeira_s"]            # verdade antiga (B01 de antes do drop-frame)
    while t < janela - 0.01:
        saida.append(round(t, 4))
        t += cl["periodo_s"]
    return saida


def inicio_da_janela_de_tom(esp: dict) -> float:
    """0,2 s depois da primeira claque: 0,1 s de tom puro (as claques distam ~1 s)."""
    cl = esp["claque"]
    inst = cl.get("instantes_s") or [cl.get("primeira_s", 0.0)]
    return (inst[0] if inst else 0.0) + 0.2


def _tc_do_arquivo(info: dict) -> str | None:
    """MXF OP-Atom do Avid guarda o TC na STREAM; OP-1a, mov e mp4 no FORMATO (banco:
    `protocolos/mxf/timecode.md`). Pedimos os dois e ficamos com o primeiro."""
    achados = [info.get("format", {}).get("tags", {}).get("timecode")]
    achados += [s.get("tags", {}).get("timecode") for s in info.get("streams", [])]
    return next((t for t in achados if t), None)


def verificar_arquivo(pasta: str, esp: dict) -> list[dict]:
    res = []

    def conf(nome, esperado, medido, ok=None):
        res.append({"conferencia": nome, "esperado": esperado, "medido": medido,
                    "ok": (esperado == medido) if ok is None else ok})

    caminho = os.path.join(pasta, esp["arquivo"])
    if not os.path.isfile(caminho):
        conf("existe", True, False)
        return res
    info = ffmpeg.sondar(caminho, contar_pacotes=True)
    vids = [s for s in info["streams"] if s["codec_type"] == "video"]
    auds = [s for s in info["streams"] if s["codec_type"] == "audio"]

    if esp["tc_inicio"] and esp["perfil"] != "wav-bwf":
        conf("timecode", esp["tc_inicio"], _tc_do_arquivo(info))

    v = esp.get("video")
    if v:
        if not vids:
            conf("tem vídeo", True, False)
        else:
            s = vids[0]
            w, h = v["raster"]
            fps = tc.taxa(v["fps"])
            conf("codec de vídeo", v["codec"], s["codec_name"])
            conf("raster", [w, h], [s["width"], s["height"]])
            conf("pix_fmt", v["pix_fmt"], s.get("pix_fmt"))
            if "sar" in v:
                conf("proporção do pixel (SAR)", v["sar"], s.get("sample_aspect_ratio") or "1:1")
            conf("taxa (avg_frame_rate)", f"{fps.numerator}/{fps.denominator}", s.get("avg_frame_rate"))
            # a armadilha do MPEG-2 OP-Atom do Avid: r_frame_rate pela metade (banco, 2026-09-17)
            conf("r_frame_rate = avg_frame_rate", True, s.get("r_frame_rate") == s.get("avg_frame_rate"))
            conf("quadros", v["quadros"], int(s.get("nb_read_packets", -1)))
            ultimo = v["quadros"] - 1
            pos = sorted({0, ultimo // 2, ultimo})
            try:
                quadros = ler.quadros_cinza(caminho, pos, w, h)
            except RuntimeError as e:
                conf("ler os quadros " + ", ".join(map(str, pos)), True, str(e), False)
                quadros = {}
            for i in pos:
                if i in quadros:
                    n, t = ler.ler_faixas(quadros[i], w, h)
                    conf(f"código do quadro {i}", codigo_esperado(esp, i), [n, t])

    if esp["perfil"] == "wav-bwf":
        conf("time_reference (BWF)", str(esp["time_reference"]),
             info.get("format", {}).get("tags", {}).get("time_reference"))

    conf("trilhas de áudio", len(esp["audio"]), len(auds))
    duracao = float(info["format"].get("duration", 0))
    for k, trilha in enumerate(esp["audio"][: len(auds)]):
        s = auds[k]
        conf(f"A{k + 1} codec", trilha["codec"], s["codec_name"])
        conf(f"A{k + 1} canais", len(trilha["canais"]), int(s["channels"]))
        conf(f"A{k + 1} amostragem", trilha["amostragem"], int(s["sample_rate"]))
        # tom: 0,1 s longe de qualquer claque (a 20% do período depois da primeira)
        inicio = inicio_da_janela_de_tom(esp)
        canais, sr = ler.amostras(caminho, k, inicio, 0.1)
        for c, esp_c in enumerate(trilha["canais"][: len(canais)]):
            hz, amp = ler.identificar_tom(canais[c], sr)
            conf(f"A{k + 1} canal {c + 1} tom (Hz)", esp_c["hz"], hz)
        # claques nos primeiros ~2,5 s (ou no arquivo inteiro, se for mais curto)
        janela = min(duracao, 2.5)
        canais, sr = ler.amostras(caminho, k, 0.0, janela)
        esperadas = claques_esperadas(esp, janela)
        for c, esp_c in enumerate(trilha["canais"][: len(canais)]):
            if esp_c["hz"] is None:
                conf(f"A{k + 1} canal {c + 1} claques", [], ler.claques(canais[c], sr))
                continue
            achadas = [round(x, 4) for x in ler.claques(canais[c], sr)]
            ok = len(achadas) == len(esperadas) and all(abs(a - e) <= TOLERANCIA_CLAQUE_S
                                                        for a, e in zip(achadas, esperadas))
            conf(f"A{k + 1} canal {c + 1} claques (s)", esperadas, achadas, ok)

    if esp["perfil"] == "mxf-opatom":
        # não é falha: é o que a bancada do MC vai medir (o MC agrupa por material_package_umid)
        res.append({"conferencia": "material_package_umid (registro)", "esperado": None, "ok": True,
                    "medido": info.get("format", {}).get("tags", {}).get("material_package_umid")})
    return res


def verificar(pasta: str) -> dict:
    with open(os.path.join(pasta, "verdade.json"), encoding="utf-8") as fh:
        verdade = json.load(fh)
    relatorio = {"caso": verdade["caso"], "ffmpeg": ffmpeg.versao()[0], "plataforma": sys.platform,
                 "arquivos": []}
    for esp in verdade["arquivos"]:
        try:
            r = verificar_arquivo(pasta, esp)
        except Exception as e:      # um arquivo ilegível é FALHA no relatório, não fim da conferência
            r = [{"conferencia": "ler o arquivo", "esperado": True, "medido": f"{type(e).__name__}: {e}", "ok": False}]
        relatorio["arquivos"].append({"arquivo": esp["arquivo"], "ok": all(x["ok"] for x in r), "conferencias": r})
    relatorio["ok"] = all(a["ok"] for a in relatorio["arquivos"])
    return relatorio


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("uso: python3 -m lab.verificar <pasta do caso>", file=sys.stderr)
        return 2
    pasta = argv[0]
    rel = verificar(pasta)
    with open(os.path.join(pasta, "verificacao.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rel, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    for a in rel["arquivos"]:
        n_ok = sum(x["ok"] for x in a["conferencias"])
        print(f"{'OK   ' if a['ok'] else 'FALHA'} {a['arquivo']}  ({n_ok}/{len(a['conferencias'])})")
        for x in a["conferencias"]:
            if not x["ok"]:
                print(f"        ✗ {x['conferencia']}: esperado {x['esperado']!r}, medido {x['medido']!r}")
    print("TUDO CONFERE" if rel["ok"] else "HÁ DIFERENÇAS — ver verificacao.json")
    return 0 if rel["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
