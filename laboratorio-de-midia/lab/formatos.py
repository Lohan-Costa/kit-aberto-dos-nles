"""Os seis perfis de formato (organograma aprovado em 2026-10-06).

Cada perfil diz quais ARQUIVOS um clipe vira e, em cada arquivo, as trilhas de áudio e os canais de
cada trilha (`None` = trilha em silêncio, sem claque). Medido no ffmpeg 8.1.1 (Mac) em 2026-10-06:
os seis muxers gravam e o ffprobe relê codec, canais e TC.
"""
from __future__ import annotations

from dataclasses import dataclass, field

AUDIO_PCM = ["-c:a", "pcm_s24le"]


@dataclass
class Arquivo:
    nome: str                          # relativo à pasta do caso
    video: bool
    trilhas: list                      # [[canal, …], …]; canal None = silêncio
    pix_fmt: str = ""
    args_video: list = field(default_factory=list)
    args_audio: list = field(default_factory=list)
    args_saida: list = field(default_factory=list)   # muxer, TC, metadados
    codec_video: str = ""
    codec_audio: str = ""


def _dnx(w: int, h: int, fps_nome: str) -> tuple[list, str]:
    """DNxHD só existe em rasters e taxas fixos; fora deles, DNxHR HQ. `-b:v 120M` em 1080p25 é o
    DNxHD 120 (8 bits) — aceito pelo ffmpeg em 2026-10-06; as outras taxas o B02 mede."""
    if (w, h) == (1920, 1080) and fps_nome == "25":
        return ["-c:v", "dnxhd", "-b:v", "120M"], "yuv422p"
    return ["-c:v", "dnxhd", "-profile:v", "dnxhr_hq"], "yuv422p"


def arquivos(perfil: str, prefixo: str, w: int, h: int, fps_nome: str, canais: int, tc: str,
             time_reference: int) -> list[Arquivo]:
    todos = list(range(1, canais + 1))
    tcarg = ["-timecode", tc]
    if perfil == "mp4-h264":
        if canais > 8:
            raise ValueError("AAC no mp4: até 8 canais")
        return [Arquivo(f"{prefixo}_MP4-H264.mp4", True, [todos], "yuv420p",
                        ["-c:v", "libx264", "-crf", "16", "-preset", "medium", "-profile:v", "high", "-g", "25"],
                        ["-c:a", "aac", "-b:a", "256k"], tcarg + ["-movflags", "+faststart"], "h264", "aac")]
    if perfil == "mov-prores":
        return [Arquivo(f"{prefixo}_MOV-PRORES.mov", True, [todos], "yuv422p10le",
                        ["-c:v", "prores_ks", "-profile:v", "2", "-vendor", "apl0"], AUDIO_PCM, tcarg,
                        "prores", "pcm_s24le")]
    if perfil == "mov-prores-mono":
        # um mono por canal, cada um na sua trilha (como câmeras e gravadores que não fazem polifônico)
        return [Arquivo(f"{prefixo}_MOV-PRORES-MONO.mov", True, [[c] for c in todos], "yuv422p10le",
                        ["-c:v", "prores_ks", "-profile:v", "2", "-vendor", "apl0"], AUDIO_PCM, tcarg,
                        "prores", "pcm_s24le")]
    if perfil == "mxf-op1a":
        args, pix = _dnx(w, h, fps_nome)
        return [Arquivo(f"{prefixo}_MXF-OP1A.mxf", True, [todos], pix, args, AUDIO_PCM, tcarg,
                        "dnxhd", "pcm_s24le")]
    if perfil == "mxf-xdcam50":
        if canais > 8:
            raise ValueError("XDCAM 50: até 8 canais")
        # 8 trilhas mono, como a câmera grava; as que o caso não usa ficam em silêncio
        trilhas = [[c] for c in todos] + [[None]] * (8 - canais)
        # ⚠️ `-non_linear_quant` exige qmax ≤ 28 (sem isso: "non linear quant only supports qmax <= 28")
        args = ["-c:v", "mpeg2video", "-b:v", "50M", "-minrate", "50M", "-maxrate", "50M",
                "-bufsize", "17825792", "-rc_init_occupancy", "17825792", "-g", "12", "-bf", "2",
                "-flags", "+cgop", "-intra_vlc", "1", "-non_linear_quant", "1", "-qmin", "1", "-qmax", "28",
                "-dc", "10", "-sc_threshold", "1000000000"]
        return [Arquivo(f"{prefixo}_MXF-XDCAM50.mxf", True, trilhas, "yuv422p", args, AUDIO_PCM, tcarg,
                        "mpeg2video", "pcm_s24le")]
    if perfil == "mxf-opatom":
        # um arquivo de vídeo e um mono por canal, com o sufixo de trilha do Avid (`_V01`, `_A01`)
        args, pix = _dnx(w, h, fps_nome)
        pasta = f"{prefixo}_MXF-OPATOM"
        saida = ["-f", "mxf_opatom"] + tcarg
        lista = [Arquivo(f"{pasta}/{prefixo}_V01.mxf", True, [], pix, args, [], saida, "dnxhd", "")]
        for c in todos:
            lista.append(Arquivo(f"{pasta}/{prefixo}_A{c:02d}.mxf", False, [[c]], "", [], AUDIO_PCM,
                                 saida + ["-mxf_audio_edit_rate", _taxa_ffmpeg(fps_nome)], "", "pcm_s24le"))
        return lista
    if perfil == "wav-bwf":
        return [Arquivo(f"{prefixo}_WAV-BWF.wav", False, [todos], "", [], AUDIO_PCM,
                        ["-write_bext", "1", "-metadata", f"time_reference={time_reference}", "-rf64", "auto"],
                        "", "pcm_s24le")]
    raise ValueError(f"perfil desconhecido: {perfil}")


def _taxa_ffmpeg(fps_nome: str) -> str:
    return {"23.976": "24000/1001", "29.97": "30000/1001", "59.94": "60000/1001"}.get(fps_nome, fps_nome)


PERFIS = ("mp4-h264", "mov-prores", "mov-prores-mono", "mxf-op1a", "mxf-xdcam50", "mxf-opatom", "wav-bwf")


# O OP-Atom do ffmpeg 8.1.1 grava a essência CLIP-wrapped (um KLV só) mas a ROTULA como frame-wrapped no
# Preface e no descritor. O Premiere 25.6.5 recusa o vídeo ("File Import Failure — Unsupported format or damaged
# file"); com o rótulo trocado para clip-wrapped ele importa, e os quadros saem exatos (medido 2026-10-06, a
# referência é o OP-Atom que o Resolve 18.5 grava para o Avid). Mesma largura: troca de bytes no lugar.
ROTULOS_CLIP = {
    bytes.fromhex("060e2b340401010a0d01030102110100"): bytes.fromhex("060e2b340401010a0d01030102110200"),  # VC-3/DNx
    bytes.fromhex("060e2b34040101010d01030102060100"): bytes.fromhex("060e2b34040101010d01030102060200"),  # BWF
}


def corrigir_rotulo_opatom(caminho: str) -> int:
    with open(caminho, "rb") as fh:
        dados = fh.read()
    trocas = 0
    for velho, novo in ROTULOS_CLIP.items():
        trocas += dados.count(velho)
        dados = dados.replace(velho, novo)
    if trocas:
        with open(caminho, "wb") as fh:
            fh.write(dados)
    return trocas
