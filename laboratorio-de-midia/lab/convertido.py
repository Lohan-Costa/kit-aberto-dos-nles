"""O CONVERTIDO de um original — o proxy com que a montagem foi feita (roteiro 4, autor, 2026-10-09).

Para o relink "convertido → original" (De Lá Pra Cá, Premiere): o convertido é feito A PARTIR do arquivo
original já gerado, com o MESMO NOME (sem a extensão), o mesmo TC (ou zerado) e a mesma duração, noutro raster
e codec. O quadro sintético (`video.py`: grade, cantos, cruz, círculo) deixa a conferência medir escala, recorte
e deslocamento.

Os modos, como os conversores fazem:

- ``fit``     — cabe inteiro: mesma proporção = só reduz; proporção diferente = TARJA (letterbox/pillarbox);
- ``fill``    — preenche o quadro: corta o que sobra (crop to fill);
- ``stretch`` — deforma para o raster (escala diferente em x e y).

O anamórfico (``sar``) é DESESPREMIDO antes (o convertido sai com pixel quadrado, como o Media Encoder faz).

A conta que a bancada confronta: o fator CERTO para o relink é a escala do CONTEÚDO (pixel do original, já
desespremido → pixel do convertido); a "regra das larguras" do PRODUCAO-G (largura do convertido ÷ largura GUARDADA
do original) só acerta quando a proporção é a mesma e o pixel é quadrado.
"""
from __future__ import annotations

import os
from fractions import Fraction

from . import ffmpeg, video

MODOS = ("fit", "fill", "stretch")


def geometria(ow: int, oh: int, sar: str | None, cw: int, ch: int, modo: str, girado: bool = False) -> dict:
    """Onde o original cai no convertido. `ow`×`oh` = pixels GUARDADOS do original; `sar` = '2:1' etc.;
    `girado` = o original é VISTO a 90°/270° (metadado de rotação) e o convertido foi feito já girado."""
    if modo not in MODOS:
        raise ValueError(f"modo desconhecido: {modo}")
    p = Fraction(sar.replace("/", ":").split(":")[0]) / Fraction(sar.replace("/", ":").split(":")[1]) if sar else Fraction(1)
    dw, dh = Fraction(ow) * p, Fraction(oh)            # o original como se VÊ (desespremido)
    if girado:
        dw, dh = dh, dw
    if modo == "stretch":
        sx, sy = Fraction(cw) / dw, Fraction(ch) / dh
        util = [0, 0, cw, ch]
    else:
        s = (min if modo == "fit" else max)(Fraction(cw) / dw, Fraction(ch) / dh)
        sx = sy = s
        uw, uh = dw * s, dh * s
        util = [float((cw - uw) / 2), float((ch - uh) / 2), float(uw), float(uh)]   # pode sair do quadro no fill
    return {
        "modo": modo,
        "fator_relink": [float(sx), float(sy)] if sx != sy else float(sx),
        "regra_das_larguras": float(Fraction(cw) / ow),
        "regra_acerta": abs(float(Fraction(cw) / ow) - float(sx)) < 1e-6 and sx == sy,
        "imagem_util": [round(v, 3) for v in util],
        "original_visto": [float(dw), float(dh)],
    }


def filtro(cw: int, ch: int, modo: str, sar: str | None, nome_queimado: str | None) -> str:
    partes = []
    if sar:
        partes.append("scale=trunc(iw*sar/2)*2:ih,setsar=1")        # desespreme primeiro
    if modo == "fit":
        partes += [f"scale={cw}:{ch}:force_original_aspect_ratio=decrease",
                   f"pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:black"]
    elif modo == "fill":
        partes += [f"scale={cw}:{ch}:force_original_aspect_ratio=increase", f"crop={cw}:{ch}"]
    else:
        partes.append(f"scale={cw}:{ch}")
    partes.append("setsar=1")
    if nome_queimado:
        # como o data burn-in do proxy ALEXA do PRODB: o nome do clipe no canto de baixo à direita
        esc = max(2, round(3 * video.unidade(cw, ch)))
        from . import fonte_pixel
        larg = fonte_pixel.largura(nome_queimado, esc)
        x, y = cw - larg - 3 * esc, ch - 7 * esc - 3 * esc
        partes.append(video._box(x - esc, y - esc, larg + 2 * esc, 9 * esc, "black@0.6"))
        partes += video._texto(nome_queimado, x, y, esc)
    return ",".join(partes)


def gerar(original: str, destino: str, conv: dict, ow: int, oh: int, sar: str | None, tc_inicio: str,
          avisar=print, rotacao: int = 0, flip: str | None = None, trilhas: int = 1, fps_original: str = "24") -> dict:
    """Grava o convertido de `original` em `destino` e devolve a entrada da verdade.

    `rotacao`/`flip` = o METADADO do original (`gerar.py` o grava por remux). `conv["rotacao"]`:
    ``"assado"`` (padrão: o ffmpeg gira ao ler, o convertido sai com os pixels já girados e sem metadado — o
    proxy que um conversor faz) ou ``"metadado"`` (pixels como guardados + o mesmo metadado copiado).
    `conv["canais"]` = mistura o áudio para N canais (várias trilhas mono são juntadas antes).
    `conv["trecho"]` = [início, duração] em segundos: só um pedaço do original (o "offline recortado"), com o TC
    do ponto em que começa. `conv["fps"]` = outra taxa (quadros repetidos/descartados pelo `fps`).
    `conv["reel"]` = o nome da fita gravado na trilha de TC do mov (vazio ou ausente = sem reel; BL08)."""
    from . import tc as _tc
    cw, ch = conv["raster"]
    modo = conv.get("modo", "fit")
    nome = os.path.splitext(os.path.basename(original))[0]
    queimado = nome.upper() if conv.get("queimar_nome") else None
    manter_metadado = conv.get("rotacao") == "metadado"
    trecho = conv.get("trecho")
    fps_c = conv.get("fps")
    b = _tc.base(_tc.taxa(fps_original))
    desloc = int(round(Fraction(str(trecho[0])) * _tc.taxa(fps_original))) if trecho else 0
    if conv.get("tc_zerado"):
        tc = "00:00:00:00"
    else:
        # o drop-frame do original (separador ';') fica no convertido: relido sem ele, o TC saía NDF ("14:59:50:00")
        df = ";" in (tc_inicio or "")
        tc = _tc.quadros_para_tc(_tc.tc_para_quadros(tc_inicio, b, df) + desloc, b, df)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    import tempfile
    # o filtro vai por ARQUIVO: o nome queimado são centenas de drawbox e a linha do Windows tem ~32 mil caracteres
    fv = filtro(cw, ch, modo, sar, queimado)
    if fps_c:
        fv += f",fps={_tc.taxa(fps_c).numerator}/{_tc.taxa(fps_c).denominator}"
    partes = [f"[0:v:0]{fv}[v]"]
    mapa_a = ["-map", "0:a?"]
    if conv.get("canais"):
        if trilhas > 1:
            partes.append("".join(f"[0:a:{i}]" for i in range(trilhas)) + f"amerge=inputs={trilhas}[am]")
            mapa_a = ["-map", "[am]"]
        mapa_a += ["-ac", str(conv["canais"])]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(";\n".join(partes))
        script = fh.name
    entrada = (["-noautorotate"] if manter_metadado else []) \
        + (["-ss", str(trecho[0]), "-t", str(trecho[1])] if trecho else [])
    temporario = destino + ".sem-metadado.mov" if (manter_metadado and (rotacao or flip)) else destino
    args = [ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y", *entrada, "-i", original,
            *ffmpeg.opcao_script_de_filtro(script), "-map", "[v]", *mapa_a,
            "-c:v", "prores_ks", "-profile:v", "0", "-vendor", "apl0", "-pix_fmt", "yuv422p10le",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-c:a", "pcm_s16le", "-timecode", tc,
            *(["-metadata:s:v:0", f"reel_name={conv['reel']}"] if conv.get("reel") else []), temporario]
    avisar(f"convertendo {os.path.basename(destino)} ({modo}, {cw}×{ch})")
    try:
        ffmpeg.rodar(args)
    finally:
        os.unlink(script)
    if temporario != destino:
        gravar_metadado(temporario, destino, rotacao, flip)
        os.remove(temporario)
    girado = bool(rotacao) and rotacao % 180 != 0 and not manter_metadado
    g = geometria(ow, oh, sar, cw, ch, modo, girado=girado)
    return {"arquivo": None, "derivado_de": None, "raster": [cw, ch], "codec": "prores_proxy", "sar": "1:1",
            "tc_inicio": tc, "tc_zerado": bool(conv.get("tc_zerado")), "nome_queimado": queimado,
            "rotacao": ("metadado" if manter_metadado else "assado") if (rotacao or flip) else None,
            "canais": conv.get("canais"), "trecho": trecho, "deslocamento_quadros": desloc,
            "fps_convertido": fps_c, **g}


def gravar_metadado(origem: str, destino: str, rotacao: int = 0, flip: str | None = None) -> None:
    """Remux com a matriz de exibição (rotação anti-horária em graus e/ou flip), sem tocar nos pixels.
    ⚠️ No ffmpeg 8 `-display_rotation`/`-display_hflip` são opções de ENTRADA (2026-10-09)."""
    opcoes = []
    if rotacao:
        opcoes += ["-display_rotation:v:0", str(rotacao)]
    if flip == "h":
        opcoes += ["-display_hflip:v:0"]
    elif flip == "v":
        opcoes += ["-display_vflip:v:0"]
    ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y", *opcoes, "-i", origem,
                  "-map", "0", "-c", "copy", destino])
