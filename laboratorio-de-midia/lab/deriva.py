"""Pacote DERIVA (ideia do autor, 2026-10-30): câmera e gravador de som que começam em sync e se perdem ao longo do
tempo, porque cada aparelho tem o SEU relógio de cristal.

    py -m lab.deriva receitas/deriva/D01_CRISTAL_6PPM.json
    py -m lab.deriva receitas/deriva/D01_CRISTAL_6PPM.json --segundos 60 --saida <pasta>   (testes)

## O modelo físico

A cena acontece no tempo verdadeiro (o relógio do laboratório). Um aparelho com o relógio adiantado em `e` (ppm)
pega `48000 × (1 + e)` amostras por segundo verdadeiro e as rotula como 48000: no arquivo, o instante verdadeiro T
aparece em `(T − T0) × (1 + e)`. Tocado a 48 kHz, o som desse aparelho ATRASA `(T − T0) × e` em relação à cena —
a deriva cresce em reta, e um conteúdo longo a amplifica. A câmera grava o vídeo e o som guia pelo MESMO relógio
(o dela): o som guia é a régua da imagem. Sem erro de relógio na câmera (`relogio_ppm` 0), ela é o tempo verdadeiro.

A correção que devolve o sync: o clipe do gravador a `(1 + e_som) / (1 + e_camera)` de velocidade (100,0006 % para
+6 ppm), sem preservar o tom (0,1 % ≈ 1,7 cent, inaudível). O vídeo não se toca.

Como o relógio é emulado: a cena (48 kHz) é ROTULADA como 1 MHz (`asetrate`, sem mexer nas amostras), reamostrada
pelo soxr para `1 000 000 × (1 + e)` e rotulada de volta como 48 kHz — o número de amostras cresce exatamente
`(1 + e)`, com resolução de 1 ppm.

## A receita

    {"caso": "D01_CRISTAL_6PPM", "pergunta": "…",
     "cena": {"segundos": 3600, "relogio": "10:00:00:00", "semente": 21},
     "raster": [640, 360], "fps": "25",
     "camera": {"inicio_s": 5, "fim_s": 3595, "atraso_ms": 3, "relogio_ppm": 0},
     "som": {"inicio_s": 2, "fim_s": 3598, "relogio_ppm": 6, "canais": 1}}

`inicio_s`/`fim_s` são instantes da cena (tempo verdadeiro). O TC de cada arquivo = relógio da cena + o instante em
que o aparelho começou (os dois foram jamados no começo do dia: o TC do primeiro quadro/amostra está certo, e a
deriva é o que acontece DEPOIS).

## A verdade (`verdade.json`)

Por arquivo: o instante de início na cena, o relógio (ppm), o TC; e para o caso: `deriva_ppm` (som em relação à
câmera), `velocidade_de_correcao` (o fator do clipe do som) e `atraso_no_fim_ms` (quanto o som chega atrasado no
fim da câmera, com o sync certo no começo).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import tempfile
from fractions import Fraction

from . import audio, ffmpeg, multicam, tc, video

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMOSTRAGEM = audio.AMOSTRAGEM
ROTULO = 1_000_000                      # a taxa-rótulo da reamostragem: resolução de 1 ppm


def _relogio(cena: str, ppm: float, pasta: str, avisar) -> str:
    """A cena como um aparelho de relógio `ppm` a gravaria: (1 + ppm·10⁻⁶) vezes mais amostras, rotuladas 48 kHz."""
    if not ppm:
        return cena
    alvo = ROTULO + round(ppm)
    if alvo - ROTULO != ppm:
        raise ValueError(f"relógio de {ppm} ppm: só ppm inteiros (resolução da reamostragem)")
    destino = os.path.join(pasta, f"_cena_{'+' if ppm > 0 else ''}{int(ppm)}ppm.wav")
    if not os.path.isfile(destino):
        avisar(f"cena no relógio de {ppm:+g} ppm")
        ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-i", cena, "-af",
                      f"asetrate={ROTULO},aresample={alvo}:resampler=soxr:precision=28,asetrate={AMOSTRAGEM}",
                      "-c:a", "pcm_s24le", destino])
    return destino


def _tc(relogio: str, inicio_s: float, fps: Fraction) -> tuple[int, str]:
    b = tc.base(fps)
    q = (tc.tc_para_quadros(relogio, b) + round(inicio_s * fps)) % (b * 86400)
    return q, tc.quadros_para_tc(q, b)


def gerar(caminho: str, saida: str | None = None, segundos: float | None = None, avisar=print) -> str:
    with open(caminho, encoding="utf-8") as fh:
        r = json.load(fh)
    pasta = saida or os.path.join(RAIZ, "saida", "deriva", r["caso"])
    os.makedirs(pasta, exist_ok=True)
    curto = r["caso"].split("_")[0]
    escala = float(segundos) / float(r["cena"]["segundos"]) if segundos else 1.0
    seg_cena = float(r["cena"]["segundos"]) * escala
    relogio = r["cena"].get("relogio", "10:00:00:00")
    w, h = r.get("raster", [640, 360])
    fps_nome = str(r.get("fps", "25"))
    fps = tc.taxa(fps_nome)
    cam, som = r["camera"], r["som"]
    e_cam, e_som = float(cam.get("relogio_ppm", 0)), float(som.get("relogio_ppm", 0))
    # a cena precisa cobrir o maior aparelho no relógio dele (mais 2 s de folga)
    cena = multicam._cena(r, pasta, seg_cena * (1 + max(e_cam, e_som, 0) * 1e-6) + 4, avisar)
    arquivos = []

    # ---- a câmera: vídeo + som guia no relógio dela
    c0, c1 = float(cam["inicio_s"]) * escala, float(cam["fim_s"]) * escala
    k_cam = 1 + e_cam * 1e-6
    quadros = round((c1 - c0) * k_cam * fps)                  # quadros que o relógio da câmera contou
    dur_cam = float(Fraction(quadros) / fps)
    q_tc, tc_cam = _tc(relogio, c0, fps)
    cena_cam = _relogio(cena, e_cam, pasta, avisar)
    atraso = float(cam.get("atraso_ms", 0)) / 1000.0
    destino_cam = os.path.join(pasta, f"{curto}_CAMERA_MOV-H264.mov")
    linhas = [f"{fps_nome.replace('.', ',')} FPS · {w}×{h} · CAMERA",
              f"{r['caso'].replace('_', ' ')} · RELOGIO {e_cam:g} PPM"]
    grafo = video.filtro(w=w, h=h, fps=fps, quadros=quadros, tc_inicio_q=q_tc, base=tc.base(fps), camera=1,
                         take=1, linhas=linhas, pix_fmt="yuv420p")
    canais_cam = int(cam.get("canais", 2))
    pan = "|".join(f"c{c}=c0" for c in range(canais_cam))
    amostras = round(dur_cam * AMOSTRAGEM)
    grafo += (f";[0:a]volume={float(cam.get('ganho_db', -4))}dB,lowpass=f=7000[amb];"
              f"anoisesrc=color=white:seed=101:sample_rate={AMOSTRAGEM}:amplitude=0.015:duration={dur_cam + 0.1}[sala];"
              f"[amb][sala]amix=inputs=2:normalize=0,pan={'mono' if canais_cam == 1 else 'stereo'}|{pan},"
              f"atrim=end_sample={amostras}[a0]")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(grafo)
        script = fh.name
    avisar(f"gerando {os.path.basename(destino_cam)} ({quadros} quadros)")
    try:
        # o som guia em PCM (como a maioria das câmeras de cinema/broadcast): o AAC traria o atraso do codificador
        # (1024 amostras de "priming"), que cada NLE trata do seu jeito — ruído que não é deriva
        ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y",
                      "-ss", f"{max(0.0, (c0 - atraso) * k_cam):.6f}", "-i", cena_cam,
                      *ffmpeg.opcao_script_de_filtro(script), "-map", "[v]", "-map", "[a0]",
                      "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-g", "50", "-pix_fmt", "yuv420p",
                      "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                      "-r", f"{fps.numerator}/{fps.denominator}",
                      "-c:a", "pcm_s16le", "-ar", str(AMOSTRAGEM), "-timecode", tc_cam, destino_cam])
    finally:
        os.unlink(script)
    arquivos.append({"arquivo": os.path.basename(destino_cam), "papel": "camera", "inicio_na_cena_s": round(c0, 6),
                     "relogio_ppm": e_cam, "quadros": quadros, "duracao_do_arquivo_s": round(dur_cam, 6),
                     "tc": tc_cam, "atraso_ms": atraso * 1000, "canais": canais_cam})

    # ---- o gravador: BWF no relógio dele
    s0, s1 = float(som["inicio_s"]) * escala, float(som["fim_s"]) * escala
    k_som = 1 + e_som * 1e-6
    dur_som = (s1 - s0) * k_som
    cena_som = _relogio(cena, e_som, pasta, avisar)
    canais = int(som.get("canais", 1))
    h_, m_, s_, q_ = (int(x) for x in relogio.split(":"))
    # ⛔ o BWF guarda o TC do gravador em AMOSTRAS: quadro do rótulo ÷ taxa REAL × 48 000. A 29,97 NDF o rótulo anda
    # 0,1 % atrás da parede — converter o rótulo como se fosse hora de parede pôs o som 39 s antes da câmera no
    # Resolve (D03, 2026-10-30). O gravador em modo 29,97 faz como aqui.
    q_som, _ = _tc(relogio, s0, fps)
    ref = round(q_som * AMOSTRAGEM / fps)
    parede = (datetime.datetime.fromisoformat(r["cena"].get("data", "2026-10-30"))
              + datetime.timedelta(seconds=h_ * 3600 + m_ * 60 + s_ + s0))
    destino_som = os.path.join(pasta, f"{curto}_SOMDIRETO_WAV-BWF.wav")
    pan = "|".join(f"c{c}=c0" for c in range(canais))
    af = (f"volume={float(som.get('ganho_db', 0))}dB,"
          f"pan={'mono' if canais == 1 else 'stereo'}|{pan},atrim=end_sample={round(dur_som * AMOSTRAGEM)}")
    avisar(f"gerando {os.path.basename(destino_som)} ({dur_som:.3f} s de arquivo)")
    ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y",
                  "-ss", f"{s0 * k_som:.6f}", "-i", cena_som, "-af", af, "-c:a", "pcm_s24le", "-rf64", "auto",
                  "-write_bext", "1", "-metadata", f"time_reference={ref}",
                  "-metadata", f"origination_date={parede:%Y-%m-%d}", "-metadata", f"origination_time={parede:%H:%M:%S}",
                  "-metadata", f"description=sTAKE=1\r\nsSPEED={fps_nome}\r\n", destino_som])
    arquivos.append({"arquivo": os.path.basename(destino_som), "papel": "som", "inicio_na_cena_s": round(s0, 6),
                     "relogio_ppm": e_som, "duracao_do_arquivo_s": round(dur_som, 6),
                     "tc": tc.quadros_para_tc(round(ref * fps / AMOSTRAGEM), tc.base(fps)), "time_reference": ref,
                     "canais": canais})

    # ---- a verdade do caso
    razao = k_som / k_cam
    # no fim da câmera (tempo verdadeiro c1), com o sync certo no começo (T = c0): o som chega atrasado
    # (c1 − c0)·k_som − (c1 − c0)·k_cam no relógio da câmera, menos o atraso do microfone da câmera (constante)
    atraso_fim = (c1 - c0) * (k_som - k_cam) / k_cam
    verdade = {
        "caso": r["caso"], "pergunta": r.get("pergunta", ""), "receita": "receitas/deriva/" + os.path.basename(caminho),
        "gerado_em": datetime.date.today().isoformat(), "ffmpeg": ffmpeg.versao()[0], "plataforma": sys.platform,
        "cena": {"segundos": seg_cena, "relogio": relogio, "semente": r["cena"].get("semente", 1)},
        "fps": fps_nome, "raster": [w, h],
        "deriva_ppm": round((razao - 1) * 1e6, 6),
        "velocidade_de_correcao": razao,
        "velocidade_de_correcao_pct": round(razao * 100, 6),
        "atraso_no_fim_ms": round(atraso_fim * 1000, 3),
        "atraso_no_fim_quadros": round(atraso_fim * float(fps), 3),
        "convencoes": {
            "inicio_na_cena_s": "instante verdadeiro da cena do primeiro quadro/amostra",
            "deriva_ppm": "quanto o relógio do som anda a mais que o da câmera (positivo = o som atrasa ao longo do tempo)",
            "velocidade_de_correcao": "o fator de velocidade do clipe do SOM que devolve o sync (o vídeo não muda)",
            "atraso_no_fim_ms": "com o sync certo no começo, quanto o som chega atrasado no último quadro da câmera "
                                "(sem contar o atraso constante do microfone da câmera)",
        },
        "arquivos": arquivos,
    }
    with open(os.path.join(pasta, "verdade.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(verdade, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return pasta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gera um caso do pacote DERIVA.")
    ap.add_argument("receita")
    ap.add_argument("--saida")
    ap.add_argument("--segundos", type=float, help="encolhe a cena (e os trechos na mesma proporção)")
    a = ap.parse_args(argv)
    print("pronto:", gerar(a.receita, a.saida, a.segundos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
