"""Confere o que um NLE mostrou e renderizou, contra a verdade do caso.

    python3 -m lab.bancadas.conferir saida/bancadas/resolve/B01_FORMATOS saida/base/B01_FORMATOS

Lê o `resolve.json` da bancada (o que o NLE disse pela API), os stills (o que o NLE MOSTROU em cada
posição da timeline) e os renders (o que ele ENTREGA: imagem e som de volta). Grava o resultado em
`resultados/<caso>/<nle>-<versão>-<plataforma>.json` — no Git: é a medição.
"""
from __future__ import annotations

import json
import os
import sys

from .. import ffmpeg, ler, verificar
from .. import tc as _tc

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _verdade_por_nome(caso: str) -> dict:
    with open(os.path.join(caso, "verdade.json"), encoding="utf-8") as fh:
        v = json.load(fh)
    return {os.path.basename(a["arquivo"]): a for a in v["arquivos"]}, v


def conferir(trabalho: str, caso: str) -> dict:
    nome_json = "premiere.json" if os.path.isfile(os.path.join(trabalho, "premiere.json")) else "resolve.json"
    with open(os.path.join(trabalho, nome_json), encoding="utf-8") as fh:
        nle = json.load(fh)
    por_nome, verdade = _verdade_por_nome(caso)
    res = {"caso": verdade["caso"], "variante": nle.get("variante"), "projeto": nle.get("projeto"),
           "ajustes_do_projeto": nle.get("ajustes"), "nle": nle.get("produto"), "versao": nle.get("versao") or nle.get("resolve"),
           "recusados": nle.get("recusados", []), "preferencias": nle.get("preferencias"),
           "plataforma": sys.platform, "ffmpeg": ffmpeg.versao()[0], "pool": [], "timelines": []}

    # 1) o pool: o que o NLE leu do arquivo
    for c in nle["pool"]:
        esp = por_nome.get(c["File Name"], {})
        v = esp.get("video") or {}
        canais = sum(len(t["canais"]) for t in esp.get("audio", []))
        itens = [
            ("Start TC", esp.get("tc_inicio"), c.get("Start TC")),
            ("Frames", str(v["quadros"]) if v else "", c.get("Frames") or ""),
            # a FPS com 3 casas: o Premiere diz 23.976023976…, o Resolve 23.976
            ("FPS", round(float(_tc.taxa(v["fps"] if v else (verdade["arquivos"][0].get("fps") or verdade["arquivos"][0]["video"]["fps"]))), 3), round(float(c.get("FPS") or 0), 3)),
            ("Resolution", f"{v['raster'][0]}x{v['raster'][1]}" if v else "", c.get("Resolution") or ""),
            ("Audio Ch", str(canais), c.get("Audio Ch")),
        ]
        if "drop_frame" in esp and v:
            itens.append(("Drop frame", "1" if esp["drop_frame"] else "0", c.get("Drop frame")))
        res["pool"].append({"clipe": c["File Name"], "tipo": c.get("Type"), "codec": c.get("Video Codec"),
                            "formato": c.get("Format"),
                            "conferencias": [{"campo": n, "esperado": e, "nle": m, "ok": e == m} for n, e, m in itens]})

    # 2) os stills: o quadro que o NLE mostrou em cada posição da timeline
    for t in nle["timelines"]:
        esp = por_nome.get(t.get("clipe", ""), {})
        reg = {"timeline": t["nome"], "inicio_tc": t.get("inicio_tc"), "modo": t.get("modo"), "stills": [], "render": None,
               "trilhas_de_audio": [
                   {"trilha": a["trilha"], "subtipo": a.get("subtipo"), "itens": [i.get("nome") for i in a["itens"]],
                    "canais_da_fonte": [((i.get("mapa_de_canais") or {}).get("track_mapping", {}).get("1") or {}).get("channel_idx")
                                        for i in a["itens"]]}
                   for a in (t.get("trilhas") or {}).get("audio", [])]}
        for s in nle.get("stills", {}).get(t["nome"], []):
            caminho = os.path.join(trabalho, s["arquivo"])
            if not (s["exportou"] and os.path.isfile(caminho)):
                reg["stills"].append({**s, "ok": False, "erro": "still não exportado"})
                continue
            img, w, h = ler.ler_imagem(caminho)
            k = s["posicao_na_timeline"]
            if t.get("modo") in ("hd", "hd_ajustado"):
                # B05: o clipe ajustado ao raster do projeto — onde ficou a imagem?
                vv = esp["video"]
                sw, sh = (int(x) for x in vv.get("sar", "1:1").split(":"))
                dw, dh = vv["raster"][0] * sw / sh, vv["raster"][1]
                esc = min(w / dw, h / dh)
                ew, eh = round(dw * esc), round(dh * esc)
                esperado = [(w - ew) // 2, (h - eh) // 2, (w - ew) // 2 + ew, (h - eh) // 2 + eh]
                lido = list(ler.area_util(img, w, h))
                reg["stills"].append({"posicao_na_timeline": k, "tc_na_agulha": s["tc_na_agulha"], "raster_da_timeline": [w, h],
                                      "esperado_area_util": esperado, "lido_area_util": lido,
                                      "ok": all(abs(a - b) <= 2 for a, b in zip(lido, esperado)) and s["agulha_pegou"]})
                continue
            n, tcq = ler.ler_faixas(img, w, h)
            esperado = verificar.codigo_esperado(esp, k)
            reg["stills"].append({"posicao_na_timeline": k, "tc_na_agulha": s["tc_na_agulha"],
                                  "esperado_quadro_e_tc": esperado, "lido_quadro_e_tc": [n, tcq],
                                  "ok": [n, tcq] == esperado and s["agulha_pegou"]})
        res["timelines"].append(reg)

    # 3) os renders: imagem e som que o NLE entrega de volta
    jobs = {j["timeline"]: j for j in nle.get("renders", {}).get("jobs", [])}
    for reg in res["timelines"]:
        j = jobs.get(reg["timeline"])
        if not j:
            continue
        caminho = os.path.join(trabalho, j["arquivo"])
        if not os.path.isfile(caminho):
            reg["render"] = {"arquivo": j["arquivo"], "ok": False, "erro": "render não encontrado",
                             "status": j.get("status")}
            continue
        esp = por_nome[next(t["clipe"] for t in nle["timelines"] if t["nome"] == reg["timeline"])]
        info = ffmpeg.sondar(caminho, contar_pacotes=True)
        vid = next(s for s in info["streams"] if s["codec_type"] == "video")
        auds = [s for s in info["streams"] if s["codec_type"] == "audio"]
        quadros = int(vid.get("nb_read_packets", -1))
        w, h = int(vid["width"]), int(vid["height"])
        pos = sorted({0, (quadros - 1) // 2, quadros - 1})
        lidos = {i: list(ler.ler_faixas(img, w, h)) for i, img in ler.quadros_cinza(caminho, pos, w, h).items()}
        r = {"arquivo": j["arquivo"], "quadros": quadros, "codigos": {str(i): lidos[i] for i in pos},
             # numa timeline de SYNC a câmera não começa no quadro 0 do render: quem prova é o `sync` abaixo
             "codigos_ok": None if any(x.get("sync") for x in nle["timelines"] if x["nome"] == reg["timeline"])
                           else all(lidos[i] == verificar.codigo_esperado(esp, i) for i in pos),
             "tc_do_render": next((x for x in [info["format"].get("tags", {}).get("timecode")] +
                                   [s.get("tags", {}).get("timecode") for s in info["streams"]] if x), None),
             "audio": []}
        inicio = verificar.inicio_da_janela_de_tom(esp)
        for k, s in enumerate(auds):
            canais, sr = ler.amostras(caminho, k, inicio, 0.1)
            todo, _ = ler.amostras(caminho, k, 0.0, 2.5)
            r["audio"].append({"trilha": k + 1, "canais": int(s["channels"]),
                               "tons_por_canal": [ler.tons_presentes(c, sr) for c in canais],
                               "claques_por_canal": [[round(x, 4) for x in ler.claques(c, sr)] for c in todo]})
        # o render entrega o mesmo relógio e o mesmo sync? (TC = o da timeline, claques nos instantes da verdade)
        esperadas = verificar.claques_esperadas(esp, 2.5)
        r["tc_ok"] = (r["tc_do_render"] or "").replace(";", ":") == (reg["inicio_tc"] or "").replace(";", ":")
        # numa MIXAGEM de 5+ tons de −20 dBFS os picos passam do limiar da claque (e com 16 a soma satura):
        # ali a claque não se mede — None, não falha
        mensuraveis = [(cs, tons) for a in r["audio"] for cs, tons in zip(a["claques_por_canal"], a["tons_por_canal"])
                       if tons and len(tons) * 0.1 < 0.5]
        algum_tom = any(t for a in r["audio"] for t in a["tons_por_canal"])
        r["claques_ok"] = (all(len(cs) == len(esperadas) and all(abs(a - e) <= verificar.TOLERANCIA_CLAQUE_S
                                                                  for a, e in zip(cs, esperadas))
                               for cs, tons in mensuraveis) if mensuraveis else (None if algum_tom else True))
        hz = [[c["hz"]] if c["hz"] else [] for tr in esp["audio"] for c in tr["canais"]]
        saida = [tons for a in r["audio"] for tons in a["tons_por_canal"]]
        # canal a canal só quando o render tem o mesmo número de canais da fonte; senão é MIXAGEM (registrada)
        r["canais_ok"] = (saida == hz) if len(saida) == len(hz) else None
        tl_meta = next(x for x in nle["timelines"] if x["nome"] == reg["timeline"])
        if tl_meta.get("sync"):
            r["sync"] = _presencas(caminho, verdade, tl_meta, nle.get("base", 25), r["quadros"])
        reg["render"] = r
    return res


def _presencas(caminho: str, verdade: dict, tl: dict, base: int, quadros: int) -> dict:
    """B06: onde cada FONTE soa no render, contra onde o TC manda. Cada arquivo de áudio da verdade ocupa, na
    timeline, do seu TC de início ao fim; o tom do canal 1 dele tem de começar e acabar ali (± 20 ms)."""
    from .. import tc as _tc
    fps = _tc.taxa(str(verdade["arquivos"][0]["fps"]))   # a da verdade: o Resolve devolve "25.0"
    ini_tl = _tc.tc_para_quadros(tl["inicio_tc"], base)
    dur = quadros / float(fps)
    canais, sr = ler.amostras(caminho, 0, 0.0, dur)
    saida = {}
    for a in verdade["arquivos"]:
        if not a["audio"]:
            continue
        hz = a["audio"][0]["canais"][0]["hz"]
        q0 = a["tc_inicio_quadros"]
        n = (a["video"] or {}).get("quadros") or round(a["audio"][0]["amostras"] / 48000 * float(fps))
        de = max(0.0, (q0 - ini_tl) / float(fps))
        ate = min(dur, (q0 + n - ini_tl) / float(fps))
        lido = ler.trechos_do_tom(canais[0], sr, hz)
        ok = (len(lido) == 1 and abs(lido[0][0] - de) <= 0.02 and abs(lido[0][1] - ate) <= 0.02) if ate > de else not lido
        saida[a["arquivo"]] = {"hz": hz, "esperado_s": [round(de, 3), round(ate, 3)], "lido_s": lido, "ok": ok}
    return saida


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    trabalho, caso = argv
    res = conferir(trabalho, caso)
    nle = (res["nle"] or "nle").split()[-1].lower() if res["nle"] else "nle"
    destino = os.path.join(RAIZ, "resultados", res["caso"],
                           f"{'resolve' if 'Resolve' in (res['nle'] or '') else 'premiere'}-{res['versao']}-{res['plataforma']}"
                           + (f"-{res['variante']}" if res.get("variante") else "") + ".json")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    for p in res["pool"]:
        ruins = [c for c in p["conferencias"] if not c["ok"]]
        print(f"POOL {'OK   ' if not ruins else 'DIFERE'} {p['clipe']:<24} {p['tipo']:<14} {p['codec'] or ''}")
        for c in ruins:
            print(f"        {c['campo']}: verdade {c['esperado']!r}, NLE {c['nle']!r}")
    for t in res["timelines"]:
        st = ["ok" if s["ok"] else f"✗ {s.get('lido_quadro_e_tc') or s.get('lido_area_util')} (esperado "
              f"{s.get('esperado_quadro_e_tc') or s.get('esperado_area_util')})" for s in t["stills"]]
        if t["stills"] and "raster_da_timeline" in t["stills"][0]:
            st.insert(0, f"área útil {t['stills'][0]['lido_area_util']} em {t['stills'][0]['raster_da_timeline']}")
        print(f"STILL {t['timeline']:<28} início {t['inicio_tc']}  {' · '.join(st)}")
        r = t["render"]
        if r:
            if "erro" in r:
                print(f"      render: {r['erro']}")
            else:
                sim = lambda x: "—" if x is None else ("ok" if x else "✗")
                print(f"      render: {r['quadros']} quadros, códigos {'—' if r['codigos_ok'] is None else ('ok' if r['codigos_ok'] else r['codigos'])}, "
                      f"TC {r['tc_do_render']} {sim(r['tc_ok'])}, canais {sim(r['canais_ok'])}, claques {sim(r['claques_ok'])}")
                for nome, s in (r.get("sync") or {}).items():
                    print(f"        sync {nome} ({s['hz']} Hz): esperado {s['esperado_s']}, lido {s['lido_s']} {'ok' if s['ok'] else '✗'}")
                for a in r["audio"]:
                    cl = [c[:4] + (["…"] if len(c) > 4 else []) for c in a["claques_por_canal"]]
                    print(f"        A{a['trilha']} ({a['canais']} canais): tons {a['tons_por_canal']}  claques {cl}")
    print("resultado:", os.path.relpath(destino, RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
