"""BL08 — a mídia do laboratório de CASAMENTO no Baselight (pegadinhas P1–P10).

Plano: `2 ATIVOS/_CICLO ASSIST/docs/plano/2026-11-22-lab-casamento-baselight.md`. Receita:
`receitas/baselight/BL08_CASAMENTO.json` — `originais` (cada um no CAMINHO exato da pegadinha, com o reel = nome do
clipe, cópias idênticas, ou uma sequência DPX) e `dailies` (o proxy que o editor monta: outro nome, outra taxa,
reel vazio/trocado, TC rotulado NDF).

    python3 -m lab.casamento gerar        # mídia + verdade.json (~3 GB, alguns minutos)
    python3 -m lab.casamento verificar    # ffprobe + código de barras de cada arquivo → verificacao.json

A identidade de cada original no quadro é a COR da câmera + o código (quadro, TC) + o take em texto; em todo par
confundível as câmeras diferem (o render do Baselight denuncia a troca pela cor média do fundo).
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import shutil
import sys
import tempfile
import unicodedata
from fractions import Fraction

from . import audio, convertido, ffmpeg, formatos, ler, tc, video
from .gerar import RAIZ, _filtro_audio

RECEITA = os.path.join(RAIZ, "receitas", "baselight", "BL08_CASAMENTO.json")
SAIDA = os.path.join(RAIZ, "saida", "baselight", "BL08_CASAMENTO")


def _receita() -> dict:
    with open(RECEITA, encoding="utf-8") as fh:
        return json.load(fh)


def _gerar_mov(r: dict, o: dict, destino: str, avisar=print) -> dict:
    """O original em ProRes 422 (o perfil `mov-prores` do laboratório) com o reel = nome do clipe."""
    fps = tc.taxa(o["fps"])
    b = tc.base(fps)
    df = bool(o.get("drop_frame"))
    quadros = int(round(Fraction(str(o["segundos"])) * fps))
    amostras = int(Fraction(quadros) / fps * audio.AMOSTRAGEM)
    w, h = o.get("raster") or r["raster"]
    tc_q = tc.tc_para_quadros(o["tc_inicio"], b, df)
    claques = audio.instantes_claque(tc_q, b, df, fps, quadros)
    nome = os.path.basename(o["arquivo"]).split(".")[0]
    arq = formatos.arquivos("mov-prores", nome, w, h, o["fps"], r["canais"], o["tc_inicio"], 0)[0]
    taxa_txt = o["fps"].replace(".", ",") + (" DF" if df else "")
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", nome) if not unicodedata.combining(c))
    linhas = [f"{o['rotulo']} · {sem_acento} · {o['pegadinha']}", f"{taxa_txt} FPS · {w}×{h}"]
    partes = [video.filtro(w=w, h=h, fps=fps, quadros=quadros, tc_inicio_q=tc_q, base=b, camera=o["camera"],
                           take=o["take"], linhas=linhas, pix_fmt=arq.pix_fmt, df=df)]
    mapas = ["-map", "[v]"]
    for i, trilha in enumerate(arq.trilhas):
        partes.append(_filtro_audio(trilha, f"a{i}", r["fonte"], amostras, claques))
        mapas += ["-map", f"[a{i}]"]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(";\n".join(partes))
        script = fh.name
    reel = o.get("reel", nome)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    args = [ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y", *ffmpeg.opcao_script_de_filtro(script),
            *mapas, *arq.args_video, "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            *arq.args_audio, *arq.args_saida, *(["-metadata:s:v:0", f"reel_name={reel}"] if reel else []), destino]
    avisar(f"gerando {o['rotulo']} {o['arquivo']}")
    try:
        ffmpeg.rodar(args)
    finally:
        os.unlink(script)
    return {"rotulo": o["rotulo"], "pegadinha": o["pegadinha"], "arquivo": o["arquivo"], "camera": o["camera"],
            "take": o["take"], "fps": o["fps"], "base": b, "drop_frame": df, "quadros": quadros, "raster": [w, h],
            "tc_inicio": o["tc_inicio"], "tc_inicio_quadros": tc_q, "reel": reel or None,
            "cor_camera": video.CORES_CAMERA[o["camera"]]}


def _dpx(mov: str, padrao: str, primeiro: int, avisar=print) -> None:
    """A sequência DPX 10 bits (um arquivo por quadro), numerada a partir do RÓTULO do TC do 1º quadro."""
    os.makedirs(os.path.dirname(padrao), exist_ok=True)
    avisar(f"DPX {os.path.basename(padrao)} a partir de {primeiro}")
    ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-i", mov, "-map", "0:v:0",
                  "-c:v", "dpx", "-pix_fmt", "gbrp10le", "-start_number", str(primeiro), padrao])


def gerar(avisar=print) -> str:
    r = _receita()
    os.makedirs(SAIDA, exist_ok=True)
    verdade = {"caso": r["caso"], "pergunta": r["pergunta"], "nota": r["nota"],
               "receita": "receitas/baselight/BL08_CASAMENTO.json", "gerado_em": datetime.date.today().isoformat(),
               "ffmpeg": ffmpeg.versao()[0], "plataforma": sys.platform, "originais": [], "dailies": []}
    fonte_do_daily: dict[str, tuple[str, dict]] = {}
    temporarios = []
    for o in r["originais"]:
        destino = os.path.join(SAIDA, o["arquivo"])
        if o.get("sequencia") == "dpx":
            mov = os.path.join(SAIDA, "_temporario", os.path.basename(destino).split(".")[0] + ".mov")
            e = _gerar_mov(r, o, mov, avisar)
            primeiro = tc.rotulo(e["tc_inicio_quadros"], e["base"], e["drop_frame"])
            for velho in glob.glob(os.path.join(os.path.dirname(destino), "*.dpx")):
                os.remove(velho)
            _dpx(mov, destino, primeiro, avisar)
            e.update(sequencia="dpx", primeiro_numero=primeiro, reel=None)
            temporarios.append(mov)
        else:
            e = _gerar_mov(r, o, destino, avisar)
            mov = destino
            for c in o.get("copias", []):
                d = os.path.join(SAIDA, c)
                os.makedirs(os.path.dirname(d), exist_ok=True)
                avisar(f"copiando para {c}")
                shutil.copyfile(destino, d)
            e["copias"] = o.get("copias", [])
        verdade["originais"].append(e)
        fonte_do_daily[o["rotulo"]] = (mov, e)

    base_daily = r["daily"]
    for d in r["dailies"]:
        mov, e = fonte_do_daily[d["de"]]
        conv = {"raster": base_daily["raster"], "modo": base_daily["modo"]}
        if d.get("fps"):
            conv["fps"] = d["fps"]
        if "reel" in d:
            conv["reel"] = d["reel"]
        elif e.get("reel"):
            conv["reel"] = e["reel"]
        elif e.get("sequencia"):
            conv["reel"] = os.path.basename(e["arquivo"]).split(".")[0]
        tc_inicio = e["tc_inicio"].replace(";", ":") if d.get("tc_ndf") else e["tc_inicio"]
        if d.get("tc"):                    # P11/P12: a conversão com OUTRO TC (zerado, ou um TC que o original não tem)
            tc_inicio = d["tc"]
        w, h = e["raster"]
        x = convertido.gerar(mov, os.path.join(SAIDA, d["arquivo"]), conv, w, h, None, tc_inicio, avisar,
                             trilhas=1, fps_original=e["fps"])
        fps_d = d.get("fps") or e["fps"]
        quadros_d = int(round(Fraction(e["quadros"]) / tc.taxa(e["fps"]) * tc.taxa(fps_d)))
        verdade["dailies"].append({
            "arquivo": d["arquivo"], "de": d["de"], "pegadinha": e["pegadinha"], "nota": d.get("nota"),
            "fps": fps_d, "quadros": quadros_d, "raster": base_daily["raster"], "tc_inicio": x["tc_inicio"],
            "drop_frame": ";" in x["tc_inicio"], "reel": conv.get("reel") or None,
            "original_certo": e["arquivo"]})
    for t in temporarios:
        os.remove(t)
    shutil.rmtree(os.path.join(SAIDA, "_temporario"), ignore_errors=True)
    with open(os.path.join(SAIDA, "verdade.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(verdade, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return SAIDA


# ── conferência ───────────────────────────────────────────────────────────────────────────────────────────

def _quadros_da_sequencia(padrao: str, primeiro: int, indices: list[int], w: int, h: int) -> dict[int, bytes]:
    sel = "+".join(f"eq(n\\,{i})" for i in sorted(set(indices)))
    bruto = ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-start_number", str(primeiro),
                          "-i", padrao, "-vf", f"select={sel}", "-fps_mode", "passthrough", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-s", f"{w}x{h}", "-"], binario=True)
    tam = w * h
    return {i: bruto[k * tam:(k + 1) * tam] for k, i in enumerate(sorted(set(indices)))}


def _tags(info: dict) -> dict:
    t = dict(info.get("format", {}).get("tags", {}))
    for s in info.get("streams", []):
        for k, v in (s.get("tags") or {}).items():
            t.setdefault(k, v)
    return t


def _conferir_mov(caminho: str, fps: str, quadros: int, raster: list, tc_inicio: str, reel, codigos: dict) -> list:
    res = []

    def conf(nome, esperado, medido):
        res.append({"conferencia": nome, "esperado": esperado, "medido": medido, "ok": esperado == medido})

    if not os.path.isfile(caminho):
        conf("existe", True, False)
        return res
    info = ffmpeg.sondar(caminho, contar_pacotes=True)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    f = tc.taxa(fps)
    t = _tags(info)
    conf("raster", raster, [v["width"], v["height"]])
    conf("taxa", f"{f.numerator}/{f.denominator}", v.get("avg_frame_rate"))
    conf("quadros", quadros, int(v.get("nb_read_packets", -1)))
    conf("timecode", tc_inicio, t.get("timecode"))
    conf("reel", reel, t.get("reel_name"))
    w, h = raster
    lidos = ler.quadros_cinza(caminho, list(codigos), w, h)
    for k, esperado in codigos.items():
        medido = list(ler.ler_faixas(lidos[k], w, h))
        if esperado and isinstance(esperado[0], list):      # várias respostas aceitas (daily de outra taxa)
            res.append({"conferencia": f"código do quadro {k}", "esperado": esperado, "medido": medido,
                        "ok": medido in esperado})
        else:
            conf(f"código do quadro {k}", esperado, medido)
    return res


def _codigo(e: dict, k_original: int) -> list[int]:
    return [k_original, tc.rotulo(e["tc_inicio_quadros"] + k_original, e["base"], e["drop_frame"])]


def verificar() -> dict:
    with open(os.path.join(SAIDA, "verdade.json"), encoding="utf-8") as fh:
        v = json.load(fh)
    por_rotulo = {e["rotulo"]: e for e in v["originais"]}
    rel = {"caso": v["caso"], "plataforma": sys.platform, "arquivos": []}
    for e in v["originais"]:
        ult = e["quadros"] - 1
        cod = {k: _codigo(e, k) for k in (0, ult // 2, ult)}
        if e.get("sequencia") == "dpx":
            padrao = os.path.join(SAIDA, e["arquivo"])
            achados = sorted(glob.glob(os.path.join(os.path.dirname(padrao), "*.dpx")))
            res = [{"conferencia": "arquivos DPX", "esperado": e["quadros"], "medido": len(achados),
                    "ok": len(achados) == e["quadros"]}]
            primeiro_nome = os.path.basename(padrao) % e["primeiro_numero"]
            res.append({"conferencia": "nome do 1º quadro", "esperado": primeiro_nome,
                        "medido": os.path.basename(achados[0]) if achados else None,
                        "ok": bool(achados) and os.path.basename(achados[0]) == primeiro_nome})
            w, h = e["raster"]
            lidos = _quadros_da_sequencia(padrao, e["primeiro_numero"], list(cod), w, h)
            for k, esp in cod.items():
                med = list(ler.ler_faixas(lidos[k], w, h)) if k in lidos else None
                res.append({"conferencia": f"código do quadro {k}", "esperado": esp, "medido": med, "ok": med == esp})
            itens = [(e["arquivo"], res)]
        else:
            itens = [(a, _conferir_mov(os.path.join(SAIDA, a), e["fps"], e["quadros"], e["raster"], e["tc_inicio"],
                                       e["reel"], cod)) for a in [e["arquivo"], *e.get("copias", [])]]
        for a, res in itens:
            rel["arquivos"].append({"arquivo": a, "ok": all(x["ok"] for x in res), "conferencias": res})
    for d in v["dailies"]:
        e = por_rotulo[d["de"]]
        if d["fps"] == e["fps"]:
            ult = d["quadros"] - 1
            cod = {k: _codigo(e, k) for k in (0, ult // 2, ult)}
        else:
            # outra taxa: o filtro `fps` do ffmpeg escolhe o quadro do original mais perto do instante — no 59,94 → 23,976
            # o 1º quadro do daily é o quadro 1 do original (medido 2026-11-22; 1/60 s): aceitar ±1 quadro do original
            cod = {0: [_codigo(e, 0), _codigo(e, 1)]}
        res = _conferir_mov(os.path.join(SAIDA, d["arquivo"]), d["fps"], d["quadros"], d["raster"], d["tc_inicio"],
                            d["reel"], cod)
        rel["arquivos"].append({"arquivo": d["arquivo"], "ok": all(x["ok"] for x in res), "conferencias": res})
    rel["ok"] = all(a["ok"] for a in rel["arquivos"])
    with open(os.path.join(SAIDA, "verificacao.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rel, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return rel


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("acao", choices=["gerar", "verificar"])
    a = ap.parse_args(argv)
    if a.acao == "gerar":
        print("pronto:", gerar())
        return 0
    rel = verificar()
    for x in rel["arquivos"]:
        n = sum(c["ok"] for c in x["conferencias"])
        print(f"{'OK   ' if x['ok'] else 'FALHA'} {unicodedata.normalize('NFC', x['arquivo'])}  ({n}/{len(x['conferencias'])})")
        for c in x["conferencias"]:
            if not c["ok"]:
                print(f"        ✗ {c['conferencia']}: esperado {c['esperado']!r}, medido {c['medido']!r}")
    print("TUDO CONFERE" if rel["ok"] else "HÁ DIFERENÇAS — ver verificacao.json")
    return 0 if rel["ok"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
