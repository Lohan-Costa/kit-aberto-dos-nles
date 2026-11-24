"""Uma rodada do estudo do AniMatte (2026-10-12): o autor desenha no MC; isto salva a bin (CloseBin/OpenBin), guarda
uma cópia, decodifica o bloco BZFX do `user_param` da V2 da LAB_ANIMATTE, exporta o render e mede a máscara pela
régua do B14 (alfa = mistura entre o fundo azul e a frente laranja, lisos).

Uso (no `laboratorio-de-midia`, MC aberto no "DLPC LAB 23.976"):
`py lab\bancadas\avid\animatte_rodada.py 02 retangulo` (a pasta `avid/` não é pacote: `lab.bancadas.avid` é o
`avid.py`; a raiz do laboratório entra no caminho abaixo)
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import time

import numpy as np

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

BIN = os.path.expanduser(r"~\Documents\Avid Projects\DLPC LAB\DLPC LAB 23.976\DLPC LAB 23.976 Bin.avb")
SEQ = "LAB_ANIMATTE"
SAIDA = os.path.abspath(os.path.join("saida", "bancadas", "avid", "animatte"))
FUNDO, FRENTE = np.array([32, 32, 96.]), np.array([176, 64, 32.])
W, H = 1920, 1080


def salvar_e_copiar(n: str, nome: str) -> tuple[str, str]:
    from lab.bancadas import avid as A
    with A.mc() as m:
        m.fechar_bin(BIN)
        time.sleep(1)
        m.abrir_bin(BIN)
        mob_id = next(it.mob_id for it in m.itens_de(BIN, flags=("AllTypes",)) if it.name == SEQ)
    os.makedirs(SAIDA, exist_ok=True)
    copia = os.path.join(SAIDA, f"animatte_{n}_{nome}.avb")
    shutil.copy(BIN, copia)
    return copia, mob_id


def efeitos_da_v2(copia: str) -> list:
    import avb
    saida = []
    with avb.open(copia) as f:
        mob = next(m for m in f.content.mobs if m.name == SEQ and m.mob_type == "CompositionMob")
        trilha = next(t for t in mob.tracks if t.index == 2 and getattr(t.component, "media_kind", None) == "picture")
        for c in trilha.component.components:
            if type(c).__name__ == "TrackEffect":
                kfs = [{"percent_time": p.percent_time, "user_param": bytes(p.user_param)} for p in c.keyframes.parameters]
                saida.append({"effect_id": c.effect_id, "length": c.length, "attrs": dict(c.attributes),
                              "keyframes": kfs})
    return saida


def bzfx(b: bytes) -> dict:
    """O que já se sabe do bloco: cabeçalho e os registros de vértice (id uint32 ~0x37xx, 2 bytes de bandeira, uint32,
    6 doubles). Os registros são ACHADOS pela forma (id seguido de bandeira e de doubles plausíveis), não por
    posição fixa — o cabeçalho pode mudar de tamanho entre ferramentas."""
    assert b[:4] == b"BZFX", b[:4]
    # Bloco = "BZFX" + uint32 0 + uint32 nº de FORMAS (byte 8) + as formas. Forma = cabeçalho de 276 bytes (uint32 4,
    # uint32 id, … Feathering Hor/Vert doubles em +31/+39, contagem de vértices uint32 em +268) + os registros, 62
    # bytes cada MENOS os 4 do último (os 4 zeros são separador). Conferido: 1 forma de 18 vértices = 1400 bytes; mais
    # um retângulo = 1920 (rodada 09).
    # ⚠️ Versão 1 ACHAVA os registros pela forma e descartava o 3º campo = 0: na curva jogou fora 3 dos 18 vértices.
    nformas = struct.unpack(">I", b[8:12])[0]
    p, formas = 12, []
    for _ in range(nformas):
        cab = p
        n = struct.unpack(">I", b[cab + 268:cab + 272])[0]
        hor, vert = struct.unpack(">2d", b[cab + 31:cab + 47])
        verts = []
        for k in range(n):
            q = cab + 276 + 62 * k
            ds = struct.unpack(">6d", b[q + 10:q + 58])
            verts.append({"off": q, "id": struct.unpack(">I", b[q:q + 4])[0], "band": b[q + 4:q + 6].hex(),
                          "n": struct.unpack(">I", b[q + 6:q + 10])[0], "x": ds[0], "y": ds[1], "a1": ds[2:4], "a2": ds[4:6]})
        formas.append({"off": cab, "id": struct.unpack(">I", b[cab + 4:cab + 8])[0], "feather_hor": hor,
                       "feather_vert": vert, "contagem": n, "vertices": verts})
        p = cab + 276 + 62 * n - 4
    if p != len(b):
        raise ValueError(f"o bloco tem {len(b)} bytes e as formas lidas acabam em {p}")
    # compatível com as rodadas de uma forma: "vertices"/"contagem" = os da 1ª
    return {"tamanho": len(b), "formas": formas, "contagem": formas[0]["contagem"] if formas else 0,
            "vertices": formas[0]["vertices"] if formas else []}


def escrever(nome_novo: str, blocos: list[bytes], prazo: float = 60) -> str:
    """Uma CÓPIA da LAB_ANIMATTE, com MobID NOVO e o nome `nome_novo`, com `blocos` (um BZFX por keyframe, na ordem)
    no `user_param` do AniMatte da V2 — a ESCRITA, o sentido da tradução Premiere/Resolve → Avid. Devolve o mob_id
    (API) da cópia.

    ⛔ Não se reescreve a LAB_ANIMATTE no lugar (rodada 06, 2026-10-12): o MC serve o mob pelo MobID a partir da SESSÃO
    (banco, avb/escrita.md) — a sequência carregada na Record voltou intacta e o CloseBin seguinte regravou a versão
    da memória por cima da escrita. MobID novo = o MC lê do disco.
    A dança do banco: CloseBin → grava ao lado com o UID preservado → troca → OpenBin."""
    import avb
    from avb.mobid import MobID
    from lab.bancadas import avid as A
    sys.path.insert(0, A.ASSIST)
    from cicloassist.avid.atributos import copiar_atributos
    from cicloassist.avid.timeline import PREFIXO_DE_COMPOSICAO
    with A.mc() as m:
        m.fechar_bin(BIN)
        shutil.copy(BIN, os.path.join(SAIDA, f"antes_de_escrever_{nome_novo}.avb"))
        temporario = BIN + ".novo"
        with avb.open(BIN) as f:
            orig = next(x for x in f.content.mobs if x.name == SEQ and x.mob_type == "CompositionMob")
            mob = orig.copy(f)
            mob.name = nome_novo
            mob.mob_id = MobID(bytes_le=bytes(bytearray(PREFIXO_DE_COMPOSICAO) + os.urandom(16)))
            trilha = next(t for t in mob.tracks if t.index == 2 and getattr(t.component, "media_kind", None) == "picture")
            ef = next(c for c in trilha.component.components if type(c).__name__ == "TrackEffect")
            params = ef.keyframes.parameters
            if len(params) != len(blocos):
                raise ValueError(f"{len(params)} keyframes na bin, {len(blocos)} blocos")
            for p, b in zip(params, blocos):
                assert b[:4] == b"BZFX"
                p.user_param = bytearray(b)
            f.content.add_mob(mob).user_placed = True
            f.write(temporario)
        copiar_atributos(BIN, temporario)
        os.replace(temporario, BIN)
        m.abrir_bin(BIN)
        fim = time.time() + prazo
        while time.time() < fim:
            for it in m.itens_de(BIN, flags=("AllTypes",)):
                if it.name == nome_novo:
                    return it.mob_id
            time.sleep(2)
    raise RuntimeError(f"a cópia {nome_novo!r} não apareceu na bin")


def medir_escrita(nome_novo: str, mob_id: str) -> dict:
    """Exporta a cópia escrita e mede (sem salvar/decodificar: o bloco é o que escrevemos)."""
    arq = exportar(mob_id, nome_novo.split("_")[-1], nome_novo)
    return {"render": arq, "medida": medir(arq)}


def com_feather(b: bytes, hor: float, vert: float) -> bytes:
    """O BZFX com o Feathering trocado: doubles big-endian nos bytes 43 (Hor) e 51 (Vert) — os únicos que mudaram
    quando o Hor foi de 0 a 20 no Effect Editor com Fixed Aspect (rodada 05)."""
    b = bytearray(b)
    b[43:51] = struct.pack(">d", hor)
    b[51:59] = struct.pack(">d", vert)
    return bytes(b)


def exportar(mob_id: str, n: str, nome: str) -> str:
    from lab.bancadas import avid as A
    A.instalar_preset("23.976")
    return A.exportar(mob_id, SAIDA, f"ANIMATTE_{n}_{nome.upper()}")


def quadro(arq: str, q: int) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-vf", f"select=eq(n\\,{q})", "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(H, W, 3).astype(float)


def alfa(im: np.ndarray) -> np.ndarray:
    d = FRENTE - FUNDO
    return ((im - FUNDO) @ d) / (d @ d)


def PRODUCAO-A(perfil: np.ndarray) -> list[dict]:
    """Onde o alfa cruza 0,5 (subpixel) e a largura 10–90 % de cada transição."""
    out = []
    for i in range(1, len(perfil)):
        a0, a1 = perfil[i - 1] - 0.5, perfil[i] - 0.5
        if a0 * a1 < 0 or (a1 == 0 and a0 != 0):
            meio = i - 1 + a0 / (a0 - a1)
            j0, j1 = i - 1, i
            while j0 > 0 and 0.1 < perfil[j0] < 0.9:
                j0 -= 1
            while j1 < len(perfil) - 1 and 0.1 < perfil[j1] < 0.9:
                j1 += 1
            out.append({"meio": round(meio, 2), "sobe": bool(perfil[i] > perfil[i - 1]), "largura_10_90": j1 - j0 - 1})
    return out


def medir(arq: str, quadros=(0, 72, 143)) -> dict:
    """Linha e coluna pelo CENTRO da região laranja (média de 9 linhas/colunas, longe do número do quadro)."""
    res = {}
    for q in quadros:
        a = alfa(quadro(arq, q))
        dentro = a > 0.5
        ys, xs = np.nonzero(dentro)
        if not len(xs):
            res[q] = "sem frente"
            continue
        cy, cx = int(np.median(ys)), int(np.median(xs))
        linha = a[cy - 4:cy + 5].mean(axis=0)
        coluna = a[:, cx - 4:cx + 5].mean(axis=1)
        res[q] = {"centro": (cx, cy), "na_linha_y": PRODUCAO-A(linha), "na_coluna_x": PRODUCAO-A(coluna),
                  "fracao_frente": round(float(dentro.mean()), 4)}
    return res


def main(argv=None) -> None:
    argv = argv or sys.argv[1:]
    n, nome = argv[0], argv[1]
    copia, mob_id = salvar_e_copiar(n, nome)
    efs = efeitos_da_v2(copia)
    rel = {"copia": copia, "efeitos": []}
    for e in efs:
        kf = []
        for k in e["keyframes"]:
            d = bzfx(k["user_param"])
            open(copia.replace(".avb", f"_kf{len(kf)}.bin"), "wb").write(k["user_param"])
            kf.append({"percent_time": k["percent_time"], **d})
        rel["efeitos"].append({"effect_id": e["effect_id"], "attrs": e["attrs"], "keyframes": kf})
    arq = exportar(mob_id, n, nome)
    rel["render"] = arq
    rel["medida"] = medir(arq)
    j = copia.replace(".avb", ".json")
    json.dump(rel, open(j, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: list(o))
    print(json.dumps(rel, ensure_ascii=False, indent=1, default=lambda o: list(o)))


if __name__ == "__main__":
    main()
