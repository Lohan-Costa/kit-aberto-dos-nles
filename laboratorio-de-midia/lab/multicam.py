"""Pacote MULTICAM (pedido do autor, 2026-10-21): uma CENA com relógio próprio, gravada em trechos por N câmeras e
um gravador de som — cada fonte com o seu TC (ou nenhum), a sua taxa, o atraso do seu microfone.

    python -m lab.multicam receitas/multicam/M01_4ANGULOS.json
    python -m lab.multicam receitas/multicam/M01_4ANGULOS.json --segundos 20 --saida /tmp/x   (testes)

## Por que um gerador próprio, e não o `gerar.py`

O `gerar.py` faz UMA fonte por arquivo, com o tom do canal e a CLAQUE A CADA SEGUNDO de TC. Para sync por forma de onda
a claque periódica não serve: ela casa em qualquer múltiplo de 1 s. Aqui o comum a todas as fontes é a CENA: ruído rosa
vezes um envelope de senoides de frequências incomensuráveis (rajadas irregulares que não se repetem), gravado em cada
fonte com atraso, ganho e filtro próprios (microfone de câmera × lapela), um ruído de sala INDEPENDENTE por fonte e o
tom da fonte (`audio.hz`) em nível baixo — ele ainda diz de que fonte veio o som. O vídeo é o desenho do laboratório
(`video.filtro`: quadro, TC, cor da câmera), sem mudança.

## A receita

    {"caso": "M01_4ANGULOS", "pergunta": "…",
     "cena": {"segundos": 150, "relogio": "10:00:00:00", "semente": 7},
     "raster": [1280, 720], "perfil_video": "mp4-h264",
     "fontes": [
       {"nome": "CAM 1", "camera": 1, "fps": "25", "tc": "relogio", "atraso_ms": 4, "ganho_db": -4,
        "filtro": "lowpass=f=7000", "tomadas": [[5, 55], [70, 140]]},
       {"nome": "CAM 3", "camera": 3, "fps": "25", "fps_captura": "100", "audio": false, "tomadas": [[30, 45]]},
       {"nome": "SOM DIRETO", "som": true, "canais": 2, "tc": "relogio", "tomadas": [[2, 148]]}]}

- `tc`: `"relogio"` (o TC do primeiro quadro = relógio da cena + o instante da tomada), `"nenhum"` (o arquivo não tem
  trilha de TC) ou `{"deslocado_s": 3.2}` (relógio + deslocamento: a câmera mal jamada).
- `fps_captura` (câmera em slow): a câmera grava a essa taxa e o arquivo se declara em `fps` — cada segundo de cena
  vira `fps_captura / fps` segundos de arquivo. Sem `audio` (câmera de alta velocidade não grava som).
- `atraso_ms`: quanto o som da cena demora a chegar ao microfone da fonte (distância; ~3 ms por metro).
- `nomes` (opcional): o nome-base de cada tomada, na ordem de `tomadas` — o que o gravador escreveu. Ex.: a claquete no
  nome do WAV (`"M07 C1 P1-T001"`), que é como o Órbita lê cena/plano/take (`media/claquete.py`). Sem ele,
  `<caso>_<fonte>_T01`.

## A verdade (`verdade.json`)

Por arquivo: a fonte, a tomada, `inicio_na_cena_s` (o instante da cena do primeiro quadro/amostra), a duração de
cena coberta, a taxa, o TC gravado (ou nenhum) e o atraso. O sync CERTO põe cada arquivo em `inicio_na_cena_s`; o som
de uma câmera chega `atraso_ms` depois do da cena, e é isso que a forma de onda mede (até ±1 quadro de diferença
entre "imagem certa" e "som certo" é física, não erro).
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
AMOSTRAGEM = audio.AMOSTRAGEM

#: o envelope da cena: senoides de frequências incomensuráveis (razões irracionais) somadas e cortadas — rajadas de
#: tamanho e espaçamento irregulares que não se repetem na duração de uma cena
ENVELOPE = ("0.08+0.92*pow(max(0,(sin(2*PI*0.371*t)+sin(2*PI*0.6180339*t+1.3)+sin(2*PI*1.1414*t+2.1)"
            "+sin(2*PI*2.7182818*t+0.4))/4-0.15),1.5)")


def _cena(r: dict, pasta: str, segundos: float, avisar) -> str:
    """O áudio da cena (mono, 48 kHz) — a fonte comum de todo som gravado. Gerado uma vez por caso."""
    destino = os.path.join(pasta, "_cena.wav")
    sem = int(r["cena"].get("semente", 1))
    grafo = (f"anoisesrc=color=pink:seed={sem}:sample_rate={AMOSTRAGEM}:amplitude=0.6:duration={segundos}[ru];"
             f"aevalsrc=exprs={video._esc(ENVELOPE)}:s={AMOSTRAGEM}:d={segundos}[env];"
             f"[ru][env]amultiply,atrim=end_sample={int(segundos * AMOSTRAGEM)}[a]")
    avisar("gerando a cena (_cena.wav)")
    ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-filter_complex", grafo,
                  "-map", "[a]", "-c:a", "pcm_s24le", destino])
    return destino


def _tc_da_tomada(f: dict, relogio: str, inicio_s: float, fps: Fraction) -> tuple[int | None, str | None]:
    """(quadros desde a meia-noite, rótulo) do primeiro quadro — ou (None, None) sem TC."""
    modo = f.get("tc", "relogio")
    if modo == "nenhum":
        return None, None
    b = tc.base(fps)
    desl = float(modo.get("deslocado_s", 0)) if isinstance(modo, dict) else 0.0
    # o relógio da cena em quadros desta taxa; o instante da tomada em quadros REAIS desde o começo da cena
    q = tc.tc_para_quadros(relogio, b) + round((inicio_s + desl) * fps)
    q %= b * 86400
    return q, tc.quadros_para_tc(q, b)


def gerar(caminho: str, saida: str | None = None, segundos: float | None = None, avisar=print) -> str:
    with open(caminho, encoding="utf-8") as fh:
        r = json.load(fh)
    pasta = saida or os.path.join(RAIZ, "saida", "multicam", r["caso"])
    os.makedirs(pasta, exist_ok=True)
    curto = r["caso"].split("_")[0]
    seg_cena = float(segundos or r["cena"]["segundos"])
    escala = seg_cena / float(r["cena"]["segundos"])   # --segundos encolhe as tomadas na mesma proporção
    relogio = r["cena"].get("relogio", "10:00:00:00")
    w, h = r.get("raster", [1280, 720])
    perfil_v = r.get("perfil_video", "mov-h264")
    cena = _cena(r, pasta, seg_cena + 2, avisar)

    verdade = {
        "caso": r["caso"], "pergunta": r.get("pergunta", ""),
        "receita": "receitas/multicam/" + os.path.basename(caminho),
        "gerado_em": datetime.date.today().isoformat(), "ffmpeg": ffmpeg.versao()[0], "plataforma": sys.platform,
        "cena": {"segundos": seg_cena, "relogio": relogio, "semente": r["cena"].get("semente", 1)},
        "convencoes": {
            "inicio_na_cena_s": "instante da cena do primeiro quadro (vídeo) ou da primeira amostra (som); o sync "
                                "certo põe cada arquivo aí",
            "atraso_ms": "o som da cena chega a esta fonte tanto depois (distância do microfone)",
            "tc": "relógio da cena + instante, na base da taxa do arquivo; null = arquivo sem trilha de TC",
        },
        "arquivos": [],
    }

    for f in r["fontes"]:
        som = bool(f.get("som"))
        fps = tc.taxa(f.get("fps", "25"))
        # a taxa de CAPTURA não é taxa de TC (100, 120, 240…): fração direta, fora da tabela do `tc`
        fps_cap = Fraction(str(f["fps_captura"])) if f.get("fps_captura") else fps
        tem_audio = som or f.get("audio", True)
        canais = int(f.get("canais", 2))
        fonte = int(f.get("fonte", 4 if som else f.get("camera", 1)))
        atraso = float(f.get("atraso_ms", 0)) / 1000.0
        subpasta = f["nome"]
        for k, (s0, s1) in enumerate(f["tomadas"], start=1):
            s0, s1 = float(s0) * escala, float(s1) * escala
            if som:
                quadros = None
                dur_arquivo = s1 - s0
                dur_cena = dur_arquivo
            else:
                quadros = max(1, round((s1 - s0) * fps_cap))           # quadros CAPTURADOS = quadros do arquivo
                dur_arquivo = float(Fraction(quadros) / fps)
                dur_cena = float(Fraction(quadros) / fps_cap)
            tc_q, tc_rot = _tc_da_tomada(f, relogio, s0, fps)
            nome_base = f"{curto}_{f['nome'].replace(' ', '')}_T{k:02d}"
            if f.get("nomes"):                  # o nome que o gravador/câmera escreveu (ex.: a claquete no nome do WAV)
                nome_base = f["nomes"][k - 1]
            perfil = "wav-bwf" if som else perfil_v
            ref = 0
            if som and tc_q is not None:
                # BWF: amostras desde a meia-noite = relógio (em segundos) + instante da tomada (+ deslocamento)
                desl = float(f["tc"].get("deslocado_s", 0)) if isinstance(f.get("tc"), dict) else 0.0
                h_, m_, s_, q_ = (int(x) for x in relogio.split(":"))
                # o gravador volta a zero na meia-noite, como o TC (M03)
                ref = int(round((h_ * 3600 + m_ * 60 + s_ + q_ / tc.base(fps) + s0 + desl) * AMOSTRAGEM)) % (86400 * AMOSTRAGEM)
                # ⭐ a DATA e a HORA DE PAREDE do gravador (bext OriginationDate/Time): é por elas que um app sabe que o
                # take das 00:00:37 vem DEPOIS do das 23:59:35 (o Órbita decide o dia do som assim, `sync/daycycle.py`).
                # Sem elas o M03 falhou no Órbita (2026-10-21): o take pós-meia-noite foi para o começo do dia.
                parede = (datetime.datetime.fromisoformat(r["cena"].get("data", "2026-10-20"))
                          + datetime.timedelta(seconds=h_ * 3600 + m_ * 60 + s_ + s0 + desl))
                origem = ["-metadata", f"origination_date={parede:%Y-%m-%d}",
                          "-metadata", f"origination_time={parede:%H:%M:%S}"]
            mov_h264 = perfil == "mov-h264"
            arq = formatos.arquivos("mp4-h264" if mov_h264 else perfil, nome_base, w, h, f.get("fps", "25"), canais,
                                    tc_rot or "00:00:00:00", ref)[0]
            if mov_h264:
                # ⛔ o muxer MP4 do ffmpeg NÃO grava a trilha de TC (`write_tmcd` só liga sozinho no MOV; medido no
                # ffmpeg 7.1 do Windows, 2026-10-21): câmera de verdade grava MOV/MXF, e o caso precisa do TC
                arq.nome = arq.nome.replace("_MP4-H264.mp4", "_MOV-H264.mov")
            if f.get("nomes"):                  # o nome do gravador sai EXATO: o sufixo do perfil quebraria a claquete
                arq.nome = nome_base + os.path.splitext(arq.nome)[1]
            destino = os.path.join(pasta, subpasta, os.path.basename(arq.nome))
            os.makedirs(os.path.dirname(destino), exist_ok=True)

            partes, mapas, entradas = [], [], []
            if not som:
                linhas = [f"{f.get('fps', '25').replace('.', ',')} FPS" +
                          (f" · CAPTURA {f['fps_captura']}" if f.get("fps_captura") else "") + f" · {w}×{h}",
                          f"{r['caso'].replace('_', ' ')} · {f['nome']} · T{k:02d}"]
                partes.append(video.filtro(w=w, h=h, fps=fps, quadros=quadros, tc_inicio_q=tc_q or 0,
                                           base=tc.base(fps), camera=int(f.get("camera", 1)), take=k,
                                           linhas=linhas, pix_fmt=arq.pix_fmt))
                mapas += ["-map", "[v]"]
            if tem_audio:
                amostras = int(dur_arquivo * AMOSTRAGEM)
                entradas = ["-ss", f"{max(0.0, s0 - atraso):.6f}", "-t", f"{dur_arquivo + 0.1:.6f}", "-i", cena]
                filtro = f.get("filtro")
                ganho = float(f.get("ganho_db", 0))
                tom = audio.hz(min(fonte, 4), 1)
                pan = "|".join(f"c{c}=c0" for c in range(canais))
                lay = {1: "mono", 2: "stereo"}.get(canais, f"{canais}c")
                partes.append(
                    f"[0:a]volume={ganho}dB" + (f",{filtro}" if filtro else "") + "[amb];"
                    f"anoisesrc=color=white:seed={1000 + fonte * 37 + k}:sample_rate={AMOSTRAGEM}"
                    f":amplitude=0.015:duration={dur_arquivo + 0.1}[sala];"
                    f"aevalsrc=exprs={video._esc(f'0.01*sin(2*PI*{tom}*t)')}:s={AMOSTRAGEM}:d={dur_arquivo + 0.1}[tom];"
                    f"[amb][sala][tom]amix=inputs=3:normalize=0,"
                    f"pan={lay}|{pan},atrim=end_sample={amostras}[a0]")
                mapas += ["-map", "[a0]"]
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
                fh.write(";\n".join(partes))
                script = fh.name
            saida_args = list(arq.args_saida)
            if tc_q is None and "-timecode" in saida_args:
                i = saida_args.index("-timecode")
                del saida_args[i:i + 2]
            if som and tc_q is None:
                saida_args = ["-rf64", "auto"]
            elif som:
                saida_args = saida_args + origem
            cor = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"] if not som else []
            if not som:
                # ⛔ sem a taxa DECLARADA na saída o MOV não grava a trilha de TC: o grafo do `video.filtro` (loop +
                # setpts) não a anuncia, e o `-timecode` some calado (medido 2026-10-21, ffmpeg 7.1 Windows)
                cor += ["-r", f"{fps.numerator}/{fps.denominator}"]
            args = [ffmpeg.achar("ffmpeg"), "-hide_banner", "-v", "error", "-y", *entradas,
                    *ffmpeg.opcao_script_de_filtro(script), *mapas,
                    *(arq.args_video if not som else []), *cor, *(arq.args_audio if tem_audio else []),
                    *saida_args, destino]
            avisar(f"gerando {subpasta}/{os.path.basename(destino)}")
            try:
                ffmpeg.rodar(args)
            finally:
                os.unlink(script)
            verdade["arquivos"].append({
                "arquivo": f"{subpasta}/{os.path.basename(destino)}", "fonte": f["nome"], "som": som,
                "camera": None if som else int(f.get("camera", 1)), "tomada": k,
                "inicio_na_cena_s": round(s0, 6), "duracao_na_cena_s": round(dur_cena, 6),
                "duracao_do_arquivo_s": round(dur_arquivo, 6),
                "fps": None if som else f.get("fps", "25"), "fps_captura": f.get("fps_captura"),
                "quadros": quadros, "tc": tc_rot, "time_reference": ref if som and tc_q is not None else None,
                "atraso_ms": float(f.get("atraso_ms", 0)) if tem_audio else None,
                "audio": {"canais": canais, "tom_hz": audio.hz(min(fonte, 4), 1)} if tem_audio else None,
            })

    with open(os.path.join(pasta, "verdade.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(verdade, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return pasta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Gera um caso do pacote multicam.")
    ap.add_argument("receita")
    ap.add_argument("--saida")
    ap.add_argument("--segundos", type=float, help="encolhe a cena (e as tomadas na mesma proporção)")
    a = ap.parse_args(argv)
    print("pronto:", gerar(a.receita, a.saida, a.segundos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
