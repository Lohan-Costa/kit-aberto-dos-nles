"""Bancada NEST → COLLAPSE no Media Composer (pedido do autor, 2026-10-13: Collapse, velocidade e a tradução do Nest são
fundamentais para levar o R04 PRODUCAO-C do Premiere ao Avid).

A ORIGEM é a do B16_NEST_MASCARA (`lab/bancadas/premiere_mascara_nest.py`): nests do Premiere com escala, in deslocado,
corte dentro, nest de nest e VELOCIDADE (nest acelerado, clipe acelerado dentro de nest a 1×), já renderizada pelo
Premiere (a verdade). Aqui o caminho é o do APP: o leitor do `.prproj` (`prproj/leitura.py`, os segmentos com a marca
`composto`) → o escritor do Avid (`avb_export/translate.py`, que agrupa cada nest num Collapse) → bin do projeto
"DLPC LAB NEST 23.976" → export do MC → o NÚMERO DA PLACA em cada quadro, MC × Premiere.

    py -m lab.bancadas.avid_nest masters        (uma vez: copia os masters do DLPC LAB 23.976 para a bin do projeto)
    py -m lab.bancadas.avid_nest montar NOME    (escreve a sequência pelo app; devolve o mob_id)
    py -m lab.bancadas.avid_nest rodada NOME    (montar + exportar + medir)

Fora desta rodada (registrado no resultado): a MÁSCARA (vira AniMatte — outra etapa), a ESCALA/posição do Motion (o
escritor do Avid ainda não traduz o Motion do Premiere) e a placa de 100 qps (o adaptador de taxa ainda não está no
escritor: o segmento sai vazio).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from . import avid as A

PROJETO = "DLPC LAB NEST 23.976"
BIN = os.path.join(A.PROJETOS, PROJETO, PROJETO + " Bin.avb")
BIN_LAB = os.path.join(A.PROJETOS, "DLPC LAB 23.976", "DLPC LAB 23.976 Bin.avb")
#: os masters que a origem usa (nome na bin do DLPC LAB 23.976). A FRENTE_100 é o Transcode "Keep source's frame
#: rate" (o `.new.01`, 100 qps — memória `outra-taxa-no-avid-transcode-keep-source`).
MASTERS = ("B14_FUNDO.mov", "B14_FRENTE.mov", "B14_FRENTE_100.new.01", "B21_VERDE.mov")
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B16 = os.path.join(_RAIZ, "saida", "bancadas", "premiere", "B16_NEST_MASCARA")
PRPROJ = os.path.join(B16, "B16 NEST MASCARA.prproj")
RENDER_PREMIERE = os.path.join(B16, "renders", "B16_RENDER.mov")
SAIDA = os.path.join(_RAIZ, "saida", "bancadas", "avid", "nest")


def _motor():
    p = os.path.join(A.DLPC, "motor")
    if p not in sys.path:
        sys.path.insert(0, p)


def _dança(escrever, prazo: float = 60, achar: str | None = None):
    """A dança do banco: CloseBin → pyavb grava ao lado → atributos da bin → troca → OpenBin. `escrever(f)` mexe no
    arquivo aberto; com `achar`, devolve o mob_id DA API da sequência com esse nome."""
    import avb
    if A.ASSIST not in sys.path:
        sys.path.insert(0, A.ASSIST)
    from cicloassist.avid.atributos import copiar_atributos
    with A.mc() as m:
        try:
            m.fechar_bin(BIN)
        except Exception:                           # noqa: BLE001 — já fechada
            pass
        temporario = BIN + ".novo"
        with avb.open(BIN) as f:
            escrever(f)
            f.write(temporario)
        copiar_atributos(BIN, temporario)
        os.replace(temporario, BIN)
        m.abrir_bin(BIN)
        if not achar:
            return None
        fim = time.time() + prazo
        while time.time() < fim:
            for it in m.itens_de(BIN, flags=("AllTypes",)):
                if it.name == achar:
                    return it.mob_id
            time.sleep(2)
    raise RuntimeError(f"a sequência {achar!r} não apareceu na bin")


def _copiar_masters(f) -> list[str]:
    """Os masters (e os mobs de que dependem: os de arquivo, os físicos) do DLPC LAB 23.976 para a bin do projeto,
    com o MESMO mob_id — o MC acha os .mxf pelo índice da MediaFiles, qualquer que seja o projeto."""
    import avb
    tem = {str(m.mob_id) for m in f.content.mobs}
    feitos = []
    with avb.open(BIN_LAB) as g:
        for mm in g.content.mobs:
            if mm.mob_type == "MasterMob" and mm.name in MASTERS:
                for x in [mm] + list(mm.dependant_mobs()):
                    if str(x.mob_id) not in tem:
                        f.content.add_mob(x.copy(f))
                        tem.add(str(x.mob_id))
                feitos.append(mm.name)
    return feitos


def masters() -> list[str]:
    out = []
    A.guardado(lambda: _dança(lambda f: out.extend(_copiar_masters(f))), 120)
    return out


def segmentos() -> dict:
    _motor()
    from prproj.leitura import ler_sequencia
    return ler_sequencia(PRPROJ, "B16")


def _escrever(f, nome: str, r: dict, colapsar: bool = True) -> dict:
    _motor()
    from avb_export import translate as T
    ms = {m.name: m for m in f.content.mobs if m.mob_type == "MasterMob"}
    # o nome do clipe no Premiere → o master (a de 100 qps: o Transcode na taxa nativa, que o escritor põe no adaptador)
    pelo_nome = {"b14_fundo": "B14_FUNDO.mov", "b14_frente": "B14_FRENTE.mov", "b14_frente_100": "B14_FRENTE_100.new.01"}
    name2h = {k: ms[v].mob_id.bytes_le.hex() for k, v in pelo_nome.items()}
    fps = r["fps"]
    T.ER = ms["B14_FUNDO.mov"].edit_rate
    T.set_remap(None)
    T.set_master_len({ms[v].mob_id.bytes_le.hex(): ms[v].length for v in pelo_nome.values()})
    T.set_origem("premiere", fps)
    try:
        tpl = T.capture_templates()
        # o segmento do .prproj não traz mob_id (o caminho Premiere → Avid ainda não casa mídia): o escritor exige um e
        # cai no casamento pelo NOME quando o m2h não o conhece
        segs = [dict(s, mob_id=s.get("mob_id") or s.get("clip_name"), **({} if colapsar else {"composto": None}))
                for s in r["segmentos"] if not s.get("is_audio")]
        pic, _snd = T.tracks_from_segments(segs, fps, {}, name2h)
        comp = T.build(f, nome, pic, tpl, 24, 9, "HD 1080p/23.976")
    finally:
        T.set_origem(None, None)
        T.set_master_len({})
    # ⛔ o `translate.build` grava a trilha de vídeo DESLIGADA (`_ENBLSTATE 0`/`_MONSTATE 0`): o export do MC a vê
    # vazia — 'Sequence "" cannot be committed because it is empty' (2026-10-13); o Ciclo Assist já registrara o desvio
    for t in comp.tracks:
        if t.media_kind == "picture":
            t.session_attr = T._attrs(f, _ENBLSTATE=1, _MONSTATE=1)
    colapsos = []
    for t in comp.tracks:
        if t.media_kind == "picture":
            pos = 0
            for c in t.component.components:
                if type(c).__name__ == "TrackEffect" and c.effect_id == "EFF_SUBMASTER":
                    colapsos.append({"trilha": t.index, "inicio": pos, "dur": c.length, "internas": len(c.tracks)})
                pos += getattr(c, "length", 0) or 0
    return {"colapsos": colapsos}


def montar(nome: str, colapsar: bool = True) -> dict:
    r = segmentos()
    info = {}
    mid = A.guardado(lambda: _dança(lambda f: info.update(_escrever(f, nome, r, colapsar)), achar=nome), 180)
    return {"mob_id": mid, **info}


def _quadros(arquivo: str):
    from .. import ffmpeg as ff
    from ..mascara_b14 import H, W
    p = subprocess.Popen([ff.achar("ffmpeg"), "-v", "error", "-i", arquivo, "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield b
    p.wait()


def placas(arquivo: str) -> list[dict]:
    """Por quadro: o número da FRENTE (em cima à esquerda) e do FUNDO (embaixo à direita); None = não se lê."""
    from ..mascara_b14 import numero_da_placa
    return [{"q": i, "frente": numero_da_placa(b, "cima"), "fundo": numero_da_placa(b, "baixo")}
            for i, b in enumerate(_quadros(arquivo))]


def comparar(mc: list[dict], pr: list[dict], r: dict) -> dict:
    """Por segmento do B16 (o nome do nest/clipe na timeline): quadros em que os dois leem a FRENTE e quantos batem."""
    _motor()
    from avb_export.translate import _tc_frames
    rotulo = {}
    for s in r["segmentos"]:
        if s.get("track") == 2 and not s.get("is_gap") and not s.get("is_audio"):
            nome = (s.get("composto") or {}).get("nome") or s.get("clip_name")
            a = _tc_frames(s["timeline_tc_in"], r["fps"])
            for q in range(a, a + s["duration_frames"]):
                rotulo[q] = nome
    por = {}
    for a, b in zip(mc, pr):
        k = rotulo.get(a["q"], "—")
        d = por.setdefault(k, {"lidos": 0, "iguais": 0, "difere": [], "so_premiere": 0})
        if a["frente"] is not None and b["frente"] is not None:
            d["lidos"] += 1
            if a["frente"] == b["frente"]:
                d["iguais"] += 1
            else:
                d["difere"].append((a["q"], b["frente"], a["frente"]))
        elif b["frente"] is not None:
            d["so_premiere"] += 1
    fundo = sum(1 for a, b in zip(mc, pr) if a["fundo"] is not None and a["fundo"] == b["fundo"])
    return {"por_segmento": por, "fundo_iguais": fundo, "quadros": [len(mc), len(pr)]}


def rodada(nome: str, prazo: float = 600, colapsar: bool = True) -> dict:
    os.makedirs(SAIDA, exist_ok=True)
    feito = montar(nome, colapsar)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(feito["mob_id"], SAIDA, nome, prazo=prazo), prazo + 30)
    mc, pr = placas(arq), placas(RENDER_PREMIERE)
    res = {"montagem": feito, "render": arq, "comparacao": comparar(mc, pr, segmentos())}
    with open(os.path.join(SAIDA, nome + "_medido.json"), "w", encoding="utf-8") as fp:
        json.dump({"res": res, "mc": mc, "premiere": pr}, fp, ensure_ascii=False, indent=0)
    return res


if __name__ == "__main__":
    acao = sys.argv[1] if len(sys.argv) > 1 else ""
    if acao == "masters":
        print(masters())
    elif acao == "montar":
        print(json.dumps(montar(sys.argv[2]), ensure_ascii=False))
    elif acao == "rodada":
        print(json.dumps(rodada(sys.argv[2], colapsar="--sem-collapse" not in sys.argv), ensure_ascii=False,
                         default=str)[:4000])
    else:
        print(__doc__)
