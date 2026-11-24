"""Receita → mídia + `verdade.json`. Um passe do ffmpeg por arquivo.

    python3 -m lab.gerar receitas/base/B01.json
    python3 -m lab.gerar receitas/base/B01.json --segundos 2 --saida /tmp/x   (para os testes)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import tempfile
from fractions import Fraction

from . import audio, ffmpeg, formatos, tc, video

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _filtro_audio(trilha: list, rotulo: str, fonte: int, amostras: int, claques: list) -> str:
    exprs = [audio.expressao_lista(None if c is None else audio.hz(fonte, c), claques) for c in trilha]
    layout = {1: ":channel_layout=mono", 2: ":channel_layout=stereo"}.get(len(exprs), "")
    return (f"aevalsrc=exprs={video._esc('|'.join(exprs))}:s={audio.AMOSTRAGEM}{layout},"
            f"atrim=end_sample={amostras}[{rotulo}]")


def variantes(r: dict) -> list[dict]:
    """As variantes de uma receita. Sem `variantes`, a receita é uma só (o B01). Cada variante herda o
    resto da receita e troca o que declarar (`fps`, `drop_frame`, `tc_inicio`…); `rotulo` entra no nome."""
    if "variantes" not in r:
        return [{"rotulo": None, **r}]
    base = {k: v for k, v in r.items() if k != "variantes"}
    return [{**base, **v} for v in r["variantes"]]


def _caminho_da_receita(caminho: str) -> str:
    """`receitas/<pacote>/<arquivo>` para a verdade. Não por `relpath`: no Mac ele compara com
    maiúsculas (`/volumes/…` × `/Volumes/…` dá `../../..`, matriz de plataforma, linha "maiusculas")."""
    absoluto = os.path.abspath(caminho)
    return "/".join(["receitas", os.path.basename(os.path.dirname(absoluto)), os.path.basename(absoluto)])


def gerar(caminho_receita: str, saida: str | None = None, segundos: float | None = None,
          perfis: list[str] | None = None, avisar=print, so: list[str] | None = None) -> str:
    """`so` = só estas variantes (pelo `rotulo`)."""
    with open(caminho_receita, encoding="utf-8") as fh:
        r = json.load(fh)
    pacote = os.path.basename(os.path.dirname(os.path.abspath(caminho_receita)))
    pasta = saida or os.path.join(RAIZ, "saida", pacote, r["caso"])
    os.makedirs(pasta, exist_ok=True)
    caso_curto = r["caso"].split("_")[0]

    verdade = {
        "caso": r["caso"], "pergunta": r.get("pergunta", ""),
        "receita": _caminho_da_receita(caminho_receita),
        "gerado_em": datetime.date.today().isoformat(),
        "ffmpeg": ffmpeg.versao()[0], "plataforma": sys.platform,
        "convencoes": {
            "quadro": "contado a partir de 0, na ordem de decodificação (faixa de cima do código)",
            "tc_codigo": "o RÓTULO do TC como número: HH·3600·b + MM·60·b + SS·b + FF, base nominal b "
                         "(faixa de baixo; sem drop-frame = quadros desde a meia-noite)",
            "hz": "300 + 1700·(fonte−1) + 100·(canal−1), a −20 dBFS",
            "claque": "1 ms no primeiro quadro de cada segundo de TC (FF=00; no minuto que o drop-frame pula, o ;02)",
        },
        "arquivos": [],
    }
    convertidos = []

    for v in variantes(r):
        if so and v["rotulo"] not in so:
            continue
        fps = tc.taxa(v["fps"])
        b = tc.base(fps)
        df = bool(v.get("drop_frame"))
        seg = segundos if segundos is not None else v["segundos"]
        quadros = max(1, int(round(Fraction(str(seg)) * fps)))
        amostras = int(Fraction(quadros) / fps * audio.AMOSTRAGEM)
        w, h = v["raster"]
        tc_q = tc.tc_para_quadros(v["tc_inicio"], b, df)
        claques = audio.instantes_claque(tc_q, b, df, fps, quadros)
        time_reference = int(Fraction(tc_q) / fps * audio.AMOSTRAGEM)
        # `nome` troca o prefixo (os HOMÔNIMOS: dois originais com o mesmo nome) e `pasta_original` põe o
        # original numa subpasta (DRONE_A, DRONE_B…) — roteiro 4, 2026-10-09
        prefixo = v.get("nome") or (caso_curto + (f"_{v['rotulo']}" if v["rotulo"] else ""))
        sub = v.get("pasta_original") or ""
        taxa_txt = v["fps"].replace(".", ",") + (" DF" if df else "")

        for perfil in perfis or v["perfis"]:
            opatom = []          # (temporário do ffmpeg, destino final): costurados num clipe só depois
            for arq in formatos.arquivos(perfil, prefixo, w, h, v["fps"], v["canais"], v["tc_inicio"], time_reference):
                if sub:
                    arq.nome = f"{sub}/{arq.nome}"
                destino = os.path.join(pasta, arq.nome)
                if perfil == "mxf-opatom":
                    opatom.append((destino + ".ffmpeg.mxf", destino))
                    destino = opatom[-1][0]
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                partes, mapas = [], []
                if arq.video:
                    linhas = [f"{taxa_txt} FPS · {w}×{h}" + (f" · PAR {v['sar'].replace(':', '/')}" if v.get("sar") else ""),
                              f"{r['caso'].replace('_', ' ')} · {perfil}"]
                    partes.append(video.filtro(w=w, h=h, fps=fps, quadros=quadros, tc_inicio_q=tc_q, base=b,
                                               camera=v["camera"], take=v["take"], linhas=linhas,
                                               pix_fmt=arq.pix_fmt, df=df, sar=v.get("sar")))
                    mapas += ["-map", "[v]"]
                for i, trilha in enumerate(arq.trilhas):
                    partes.append(_filtro_audio(trilha, f"a{i}", v["fonte"], amostras, claques))
                    mapas += ["-map", f"[a{i}]"]
                with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
                    fh.write(";\n".join(partes))
                    script = fh.name
                cor = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"] if arq.video else []
                args = [ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y",
                        *ffmpeg.opcao_script_de_filtro(script), *mapas,
                        *arq.args_video, *cor, *arq.args_audio, *arq.args_saida, destino]
                avisar(f"gerando {arq.nome}")
                try:
                    ffmpeg.rodar(args)
                finally:
                    os.unlink(script)
                if arq.video and (v.get("rotacao_metadado") or v.get("flip_metadado")):
                    # a câmera que grava o quadro DEITADO e diz no metadado como mostrar (ALEXA a 90°, drone): os
                    # pixels ficam como desenhados, só a matriz de exibição muda (B12, 2026-10-09)
                    from . import convertido as _conv
                    bruto = destino + ".sem-metadado.mov"
                    os.replace(destino, bruto)
                    _conv.gravar_metadado(bruto, destino, int(v.get("rotacao_metadado") or 0), v.get("flip_metadado"))
                    os.remove(bruto)
                verdade["arquivos"].append({
                    "arquivo": arq.nome, "perfil": perfil, "variante": v["rotulo"],
                    "camera": v["camera"] if arq.video else None, "take": v["take"], "fonte": v["fonte"],
                    "video": {"codec": arq.codec_video, "fps": v["fps"], "quadros": quadros, "raster": [w, h],
                              "pix_fmt": arq.pix_fmt, "sar": v.get("sar") or "1:1"} if arq.video else None,
                    "fps": v["fps"], "base": b, "drop_frame": df,
                    "tc_inicio": v["tc_inicio"], "tc_inicio_quadros": tc_q, "tc_inicio_rotulo": tc.rotulo(tc_q, b, df),
                    "time_reference": time_reference if perfil == "wav-bwf" else None,
                    "audio": [{"trilha": i + 1, "codec": arq.codec_audio, "amostragem": audio.AMOSTRAGEM,
                               "amostras": amostras,
                               "canais": [{"canal": c, "hz": audio.hz(v["fonte"], c)} if c else {"canal": None, "hz": None}
                                          for c in trilha]}
                              for i, trilha in enumerate(arq.trilhas)],
                    "claque": {"instantes_s": [round(float(x), 6) for x in claques]},
                    **({"metadado_de_exibicao": {"rotacao": v.get("rotacao_metadado"), "flip": v.get("flip_metadado")}}
                       if (v.get("rotacao_metadado") or v.get("flip_metadado")) else {}),
                })
                if arq.video and v.get("convertido"):
                    from . import convertido as _conv
                    c = v["convertido"]
                    nome_c = f"{c.get('pasta', 'CONVERTIDOS')}/{os.path.splitext(os.path.basename(arq.nome))[0]}.mov"
                    e = _conv.gerar(destino, os.path.join(pasta, nome_c), c, w, h, v.get("sar"), v["tc_inicio"], avisar,
                                    rotacao=int(v.get("rotacao_metadado") or 0), flip=v.get("flip_metadado"),
                                    trilhas=len(arq.trilhas), fps_original=v["fps"])
                    e.update(arquivo=nome_c, derivado_de=arq.nome, variante=v["rotulo"], quadros=quadros, fps=v["fps"])
                    convertidos.append(e)
            if opatom:
                # o gravador do laboratório: uma identidade de clipe, todas as trilhas em cada arquivo, rótulo
                # clip-wrapped (lab/opatom.py) — como o OP-Atom que o Avid recebe
                from . import opatom as _opatom
                _opatom.costurar([t for t, _ in opatom], [d for _, d in opatom], prefixo)
                for temporario, _ in opatom:
                    os.remove(temporario)

    if convertidos:
        # fora de `arquivos` de propósito: o verificador lê os códigos do quadro, e o recorte (fill) os corta
        verdade["convertidos"] = convertidos
    with open(os.path.join(pasta, "verdade.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(verdade, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return pasta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gera a mídia de um caso a partir da receita.")
    ap.add_argument("receita")
    ap.add_argument("--saida", help="pasta de saída (padrão: saida/<pacote>/<caso>)")
    ap.add_argument("--segundos", type=float, help="encurta o caso (testes)")
    ap.add_argument("--perfil", action="append", help="só estes perfis (pode repetir)")
    ap.add_argument("--variante", action="append", help="só estas variantes, pelo rótulo (pode repetir)")
    ap.add_argument("--verificar", action="store_true", help="conferir cada arquivo ao terminar")
    a = ap.parse_args(argv)
    pasta = gerar(a.receita, a.saida, a.segundos, a.perfil, so=a.variante)
    print("pronto:", pasta)
    if a.verificar:
        from . import verificar
        return verificar.main([pasta])
    return 0


if __name__ == "__main__":
    sys.exit(main())
