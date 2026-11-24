"""B16 NEST MÁSCARA — a máscara de opacidade dentro e em cima de NEST, e sobre PROXY com escala X ≠ Y (condições #5 e #6 do
caso real R04: `docs/condicoes-R04-we-speak-dance.md`). Continua o B14 (`lab/mascara_b14.py`): as mesmas placas FUNDO/FRENTE/
FRENTE_100, a mesma máscara de borda reta conhecida e a mesma régua; aqui só muda ONDE a máscara está.

Cada segmento diz: onde fica a máscara (`alvo`: o clipe de DENTRO do nest, o clipe do NEST na timeline, o nest de dentro de
outro nest, ou o clipe solto), a montagem (escala do nest, escala do clipe de dentro, corte dentro do nest, in do nest
deslocado, proxy 1024×540 com Scale Width 187,5 / Height 200) e `escala_tela`: quanto 1 px do quadro da máscara vale na
timeline — a borda esperada é 960 + (x − 0,5) × 1920 × escala_tela. A VERDADE continua sendo o render do Premiere.

    python -m lab.mascara_b16          (gera a placa do proxy; as outras vêm do B14)
"""
from __future__ import annotations

import json
import os
import subprocess

from . import ffmpeg as ff
from . import mascara_b14 as b14
from . import video

PW, PH = 1024, 540                     # o proxy do R04 (JUL_7644, LOU_7237…): largura × 3,75 e altura × 4 = 1920 × 1080 com
                                       # W 187,5 % e H 200 % (Uniform Scale desligado)

#: `alvo`: DENTRO (o clipe dentro do nest) · FORA (o clipe do nest na timeline) · NEST_DE_NEST (o clipe do nest de dentro,
#: dentro do nest de fora) · SOLTO. `t0_ticks` = o tempo da MÍDIA do alvo no 1º quadro do segmento.
PLANO = [
    {"rotulo": "N_DENTRO", "alvo": "DENTRO", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0, "expansao": 0,
     "clipe": "FRENTE", "escala_tela": 1.0},
    {"rotulo": "N_DENTRO_Z150", "alvo": "DENTRO", "quadros": 12, "anim": (0.3, 0.7), "passo": 1, "feather": 50,
     "expansao": 0, "clipe": "FRENTE", "nest_escala": 150, "escala_tela": 1.5},
    {"rotulo": "N_FORA", "alvo": "FORA", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0, "expansao": 0,
     "clipe": "FRENTE", "escala_tela": 1.0},
    {"rotulo": "N_FORA_ESPARSO", "alvo": "FORA", "quadros": 12, "anim": (0.2, 0.8), "passo": 4, "feather": 0,
     "expansao": 0, "clipe": "FRENTE", "escala_tela": 1.0},
    {"rotulo": "N_FORA_DENTRO50", "alvo": "FORA", "quadros": 12, "anim": (0.3, 0.7), "passo": 1, "feather": 50,
     "expansao": 0, "clipe": "FRENTE", "dentro_escala": 50, "escala_tela": 1.0},
    {"rotulo": "N_FORA_CORTE", "alvo": "FORA", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0, "expansao": 0,
     "clipe": "FRENTE", "corte_100": 6, "escala_tela": 1.0},
    {"rotulo": "N_FORA_IN", "alvo": "FORA", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0, "expansao": 0,
     "clipe": "FRENTE", "nest_in": 6, "t0_ticks": 6 * b14.TICKS_QUADRO, "escala_tela": 1.0},
    {"rotulo": "N_NEST_NEST", "alvo": "NEST_DE_NEST", "quadros": 12, "anim": (0.3, 0.7), "passo": 1, "feather": 0,
     "expansao": 0, "clipe": "FRENTE", "nest_escala": 150, "escala_tela": 1.5},
    {"rotulo": "PROXY_XY", "alvo": "SOLTO", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 50, "expansao": 0,
     "clipe": "FRENTE_PROXY", "escala_xy": (187.5, 200.0), "escala_tela": 1.875 * PW / b14.W},
    {"rotulo": "PROXY_NEST_FORA", "alvo": "FORA", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 50,
     "expansao": 0, "clipe": "FRENTE_PROXY", "escala_xy": (187.5, 200.0), "escala_tela": 1.0},
]
#: VELOCIDADE (o R04: os nests das transições estão acelerados — "poste" 466,67 %, "perna" 228,6 % com o in deslocado, e o
#: clipe dentro do "poste" é de 100 qps). `vel` = quadros da mídia do ALVO por quadro da timeline; o conteúdo do nest
#: tem quadros para isso. A velocidade vai pelo QE (`setSpeed`, sem ripple: a duração fica).
PLANO += [
    {"rotulo": "N_DENTRO_VEL4", "alvo": "DENTRO", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0,
     "expansao": 0, "clipe": "FRENTE", "nest_vel": 4.0, "vel": 4.0, "escala_tela": 1.0},
    {"rotulo": "N_FORA_VEL4", "alvo": "FORA", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0, "expansao": 0,
     "clipe": "FRENTE", "nest_vel": 4.0, "vel": 4.0, "escala_tela": 1.0},
    {"rotulo": "N_DENTRO_VEL_100", "alvo": "DENTRO", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0,
     "expansao": 0, "clipe": "FRENTE_100", "nest_vel": 14 / 3, "vel": 14 / 3, "escala_tela": 1.0},
    {"rotulo": "N_FORA_VEL_IN", "alvo": "FORA", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0,
     "expansao": 0, "clipe": "FRENTE", "nest_vel": 16 / 7, "vel": 16 / 7, "nest_in": 6, "t0_ticks": 6 * b14.TICKS_QUADRO,
     "escala_tela": 1.0},
    # in 5 ÷ 2,2857 = 2,19 quadros de clipe: separa "arredonda" (2 → 4,57) de "teto" (3 → 6,86) no encaixe do in
    {"rotulo": "N_FORA_VEL_IN5", "alvo": "FORA", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0,
     "expansao": 0, "clipe": "FRENTE", "nest_vel": 16 / 7, "vel": 16 / 7, "nest_in": 5, "t0_ticks": 5 * b14.TICKS_QUADRO,
     "escala_tela": 1.0},
    # velocidade 1, mídia de 100 qps com o in fora da grade da timeline (7 e 9 quadros do arquivo = 1,68 e 2,16 quadros da
    # timeline): separa piso / arredonda / teto / nenhum encaixe
    {"rotulo": "SOLTO_100_IN7", "alvo": "SOLTO", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0,
     "expansao": 0, "clipe": "FRENTE_100", "in_ticks": 7 * 2540160000, "t0_ticks": 7 * 2540160000, "escala_tela": 1.0},
    {"rotulo": "SOLTO_100_IN9", "alvo": "SOLTO", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0,
     "expansao": 0, "clipe": "FRENTE_100", "in_ticks": 9 * 2540160000, "t0_ticks": 9 * 2540160000, "escala_tela": 1.0},
    # o "POSTE" do R04 (transicao-poste): nest a 1× com o clipe ACELERADO dentro (466,67 %; lá é de 100 qps, aqui 23,976:
    # o `setSpeed` do QE erra a velocidade de um clipe de 100 qps — 4,667 vira 3,89/4,11), o in do clipe fora
    # da grade do tempo do clipe (24 ÷ 4,667 = 5,14), máscara no clipe do NEST; e o mesmo clipe acelerado solto, e um
    # 23,976 a 3,99935 (a velocidade "quebrada" dos planos soltos do R04, que tocam SEM encaixe do in)
    {"rotulo": "POSTE", "alvo": "FORA", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0, "expansao": 0,
     "clipe": "FRENTE", "dentro_vel": 14 / 3, "dentro_in": 24, "escala_tela": 1.0},
    {"rotulo": "POSTE_SOLTO", "alvo": "SOLTO", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0, "expansao": 0,
     "clipe": "FRENTE", "clipe_vel": 14 / 3, "solto_in": 24, "vel": 14 / 3, "t0_ticks": 24 * b14.TICKS_QUADRO,
     "escala_tela": 1.0},
    {"rotulo": "SOLTO_VEL_FRAC", "alvo": "SOLTO", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0,
     "expansao": 0, "clipe": "FRENTE", "clipe_vel": 3.999345977763244, "solto_in": 24, "vel": 3.999345977763244,
     "t0_ticks": 24 * b14.TICKS_QUADRO, "escala_tela": 1.0},
    {"rotulo": "SOLTO_VEL2", "alvo": "SOLTO", "quadros": 12, "anim": (0.2, 0.8), "passo": 1, "feather": 0, "expansao": 0,
     "clipe": "FRENTE", "clipe_vel": 2.0, "vel": 2.0, "escala_tela": 1.0},
]


def inicio(i: int) -> int:
    return sum(s["quadros"] for s in PLANO[:i])


def borda_esperada(seg: dict, k: int) -> float:
    """A borda na timeline (px). No PROXY_XY a máscara está no quadro do proxy (1024 px de largura → 1920 na tela)."""
    x = b14.x_em(seg, k)
    if seg["alvo"] == "SOLTO" and "escala_xy" in seg:
        return x * b14.W
    return b14.W / 2 + (x - 0.5) * b14.W * seg["escala_tela"]


def largura_esperada(seg: dict) -> float:
    """10–90 % = 0,915 × Feather (B14) em px do quadro da máscara, × quanto esse px vale na tela."""
    por_px = (1.875 if seg["alvo"] == "SOLTO" and "escala_xy" in seg else seg["escala_tela"])
    return 0.915 * seg["feather"] * por_px


def _filtro_proxy() -> str:
    alt, larg = 60, 33
    partes = []
    for i in range(5):
        partes += video._digito(20 + (4 - i) * (larg + 9), 20, larg, alt, f"mod(floor(n/{10 ** i}),10)")
    partes += video._texto("PROXY", 20, 20 + alt + 10, 3)
    return ",".join(partes)


def _gerar_proxy(arq: str) -> None:
    subprocess.run([ff.achar("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"color=c={b14._hex(b14.COR_FRENTE)}:s={PW}x{PH}:r={b14.FPS}:d=6", "-vf", _filtro_proxy(),
                    "-c:v", "prores_ks", "-profile:v", "2", "-pix_fmt", "yuv422p10le", "-color_primaries", "bt709",
                    "-color_trc", "bt709", "-colorspace", "bt709", arq], check=True)


def gerar(saida: str) -> dict:
    os.makedirs(saida, exist_ok=True)
    arq = os.path.join(saida, "B16_FRENTE_PROXY.mov")
    # a placa é sempre a mesma: não refaz (aberta no Premiere, o Windows trava o arquivo)
    if not os.path.exists(arq) or not os.path.getsize(arq):
        _gerar_proxy(arq)
    verdade = {"caso": "B16_NEST_MASCARA", "base": "B14_MASCARA", "proxy": os.path.basename(arq),
               "segmentos": [dict(s, inicio=inicio(i), borda_esperada=[borda_esperada(s, k) for k in range(s["quadros"])],
                                  largura_esperada=largura_esperada(s)) for i, s in enumerate(PLANO)]}
    with open(os.path.join(saida, "verdade.json"), "w", encoding="utf-8") as f:
        json.dump(verdade, f, ensure_ascii=False, indent=1)
    return verdade


def alvos(itens: list) -> list:
    """Para `mascara_b14.aplicar`: o clipe cujo SubClip se chama "B16_<rótulo>" recebe a máscara daquele segmento."""
    por_nome = {f"B16_{s['rotulo']}": s for s in PLANO}
    achados = [(i, por_nome[i["nome"]]) for i in itens if i["nome"] in por_nome]
    faltam = set(por_nome) - {i["nome"] for i, _ in achados}
    if faltam or len(achados) != len(PLANO):
        raise ValueError(f"alvos: faltam {sorted(faltam)}, achados {len(achados)}")
    return achados


def main(argv=None) -> int:
    from .gerar import RAIZ
    v = gerar(os.path.join(RAIZ, "saida", "base", "B16_NEST_MASCARA"))
    print(v["proxy"], len(v["segmentos"]), "segmentos,", inicio(len(PLANO)), "quadros")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
