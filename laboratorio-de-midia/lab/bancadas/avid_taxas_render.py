"""O TIPO DE RENDER do adaptador de taxa do MC (2026-10-12): o adaptador que o MC grava ao editar um clipe AMA de outra
taxa (MotionEffect `EFF_TIMEWARP.MOTION_CTL`, `_MIXMATCH_MOTIONADAPTER 2`) veio com `_SFX_RENDER 4` e o render MISTURA
dois quadros da fonte quando a posição cai entre eles (o 59,94 no quadro 51 mostra 7 e 8 sobrepostos). O Premiere e o
Resolve mostram quadro inteiro. Aqui: uma CÓPIA da sequência (MobID novo — o MC serve o mob da sessão) com outro
`_SFX_RENDER` em todos os adaptadores, render e a leitura do número do quadro."""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import time

from . import avid as A
from . import avid_collapse as C
from . import avid_taxas as T

W, H = 1920, 1080


def copia_com_render(origem: str, nome: str, valor: int, prazo: float = 60) -> str:
    import avb
    from avb.mobid import MobID
    sys.path.insert(0, A.ASSIST)
    from cicloassist.avid.atributos import copiar_atributos
    from cicloassist.avid.timeline import PREFIXO_DE_COMPOSICAO

    def fazer():
        with A.mc() as m:
            m.fechar_bin(C.BIN)
            temporario = C.BIN + ".novo"
            with avb.open(C.BIN) as f:
                orig = next(x for x in f.content.mobs if x.name == origem and x.mob_type == "CompositionMob")
                mob = orig.copy(f)
                mob.name = nome
                mob.mob_id = MobID(bytes_le=bytes(bytearray(PREFIXO_DE_COMPOSICAO) + os.urandom(16)))
                n = 0
                for t in mob.tracks:
                    for c in getattr(t.component, "components", None) or []:
                        if type(c).__name__ == "MotionEffect" and c.attributes.get("_MIXMATCH_MOTIONADAPTER"):
                            c.attributes["_SFX_RENDER"] = valor
                            c.left_bob = None
                            n += 1
                if not n:
                    raise RuntimeError("nenhum adaptador na sequência")
                f.content.add_mob(mob).user_placed = True
                f.write(temporario)
            copiar_atributos(C.BIN, temporario)
            os.replace(temporario, C.BIN)
            m.abrir_bin(C.BIN)
            fim = time.time() + prazo
            while time.time() < fim:
                for it in m.itens_de(C.BIN, flags=("AllTypes",)):
                    if it.name == nome:
                        return it.mob_id
                time.sleep(2)
        raise RuntimeError(f"a cópia {nome!r} não apareceu")
    return A.guardado(fazer, 180)


def mistura(img: bytes, x0: int, y0: int, w: int, h: int) -> float:
    """Fração de pixels CINZA-MÉDIOS (60–190) numa caixa de dígitos brancos sobre fundo escuro/colorido: dígito
    inteiro ≈ 0 (só branco e fundo), quadros misturados = bordas semitransparentes."""
    n = meio = 0
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            v = img[y * W + x]
            n += 1
            meio += 90 < v < 190
    return meio / n


def medir(arq: str) -> dict:
    """Por quadro da timeline: o número lido (código de barras no B02, dígitos no FRENTE_100) e quanto há de mistura na
    caixa do número."""
    from lab import ler
    from lab.mascara_b14 import numero_da_placa
    # todos os quadros em ordem (o `select` com 144 `eq()` estoura o ffmpeg)
    g = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-map", "0:v:0", "-fps_mode", "passthrough", "-frames:v",
                        "144", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    cz = {n: g[n * W * H:(n + 1) * W * H] for n in range(144)}
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-vf", "select=between(n\\,96\\,143)", "-fps_mode",
                        "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    out = {}
    for n in range(144):
        fps, k = (25, n) if n < 48 else ((60000 / 1001, n - 48) if n < 96 else (100, n - 96))
        pos = k * 1001 / 24000 * fps
        if n < 96:
            lido = ler.ler_faixas(cz[n], W, H)[0]
            mix = mistura(cz[n], 880, 520, 330, 70)           # o "QUADRO 000000" do B02
        else:
            rgb = r.stdout[(n - 96) * W * H * 3:(n - 95) * W * H * 3]
            lido = numero_da_placa(rgb, "cima")
            mix = mistura(cz[n], 40, 40, 420, 120)            # os 5 dígitos do FRENTE_100
        out[n] = {"lido": lido, "posicao": round(pos, 3), "piso": math.floor(pos + 1e-9), "perto": round(pos),
                  "mistura": round(mix, 4)}
    return out


def resumo(m: dict) -> dict:
    s = {}
    for nome, (a, b) in (("25", (0, 48)), ("59.94", (48, 96)), ("100", (96, 144))):
        fr = [m[n] for n in range(a, b)]
        s[nome] = {"piso": sum(x["lido"] == x["piso"] for x in fr), "perto": sum(x["lido"] == x["perto"] for x in fr),
                   "ilegivel": sum(x["lido"] is None for x in fr),
                   "mistura_media": round(sum(x["mistura"] for x in fr) / len(fr), 4)}
    return s


def rodada(valor: int, origem: str = "LAB_TAXAS_v1") -> dict:
    nome = f"LAB_TAXAS_r{valor}"
    mid = copia_com_render(origem, nome, valor)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(mid, os.path.abspath(T.SAIDA), f"TAXAS_r{valor}"), 600)
    m = medir(arq)
    json.dump(m, open(os.path.join(T.SAIDA, f"TAXAS_r{valor}.json"), "w"), indent=0)
    return resumo(m)
