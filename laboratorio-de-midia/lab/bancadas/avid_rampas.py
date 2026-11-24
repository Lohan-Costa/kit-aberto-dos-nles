"""Bancada das RAMPAS no Media Composer (2026-10-12, pedido do autor: Time Remapping do Premiere → Timewarp do Avid,
inclusive sobre clipe de outra taxa, em laboratório controlado).

Partida (banco, avb/estruturas.md): o adaptador de taxa (MotionEffect `_MIXMATCH_MOTIONADAPTER 2`, sem curva) que o MC
põe num clipe AMA de outra taxa; e o gabarito LAB_EF_TIMEWARP (os 8 presets da paleta Timewarp aplicados pelo MC num
clipe de 23,976): dois modos de gráfico — VELOCIDADE (p0 = curva, p1 = mapa de offset em meio quadro) e POSIÇÃO
(`_MFX_GRAPH_ENABLED 2`; p0 = quadro da fonte em função do quadro da timeline).

Aqui: o preset aplicado PELO MC sobre os segmentos da LAB_TAXAS (AMA 25 / 59,94 / 100 em 23,976) — o que ele grava
(o adaptador e o Timewarp juntos?) e o que o render mostra quadro a quadro.
"""
from __future__ import annotations

import os
import sys
import time

from . import avid as A
from . import avid_collapse as C
from . import avid_efeitos as E

SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "saida", "bancadas",
                     "avid", "rampas")


def foto(nome: str) -> str:
    from . import vigia_windows as V
    return V.foto_da_tela(SAIDA, nome)


def copiar(origem: str, nome: str, mexer=None, prazo: float = 60) -> str:
    """Cópia da sequência `origem` com MobID novo (o MC serve o mob da sessão: escrever no original seria desfeito).
    `mexer(mob)` muda a cópia antes de gravar. Devolve o MobID dela (lido pela API depois de reabrir a bin)."""
    import avb
    from avb.mobid import MobID
    sys.path.insert(0, A.ASSIST)
    from cicloassist.avid.atributos import copiar_atributos
    from cicloassist.avid.timeline import PREFIXO_DE_COMPOSICAO

    def fazer():
        with A.mc() as m:
            try:
                m.fechar_bin(C.BIN)
            except Exception as e:                   # noqa: BLE001 — projeto recém-aberto: a bin ainda fechada
                if "not opened" not in str(e):
                    raise
            temporario = C.BIN + ".novo"
            with avb.open(C.BIN) as f:
                orig = next(x for x in f.content.mobs if x.name == origem and x.mob_type == "CompositionMob")
                mob = orig.copy(f)
                mob.name = nome
                mob.mob_id = MobID(bytes_le=bytes(bytearray(PREFIXO_DE_COMPOSICAO) + os.urandom(16)))
                if mexer:
                    mexer(mob)
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


def aplicar_preset(mob_id: str, linha_preset: int, inicios: list[int], base: int = 24) -> list[dict]:
    """O preset `linha_preset` da categoria Timewarp em cada segmento (`inicios`), pelo laço da bancada de efeitos."""
    E.carregar(mob_id); time.sleep(2)
    # ⛔ a janela SOLTA (abriu assim nesta sessão) levou o clique da categoria uma linha acima: Squeeze em vez de
    # Timewarp, e o Record mostrou "std::exception". As coordenadas da paleta são da janela maximizada.
    C.maximizada(E.janela_mc()); time.sleep(1)
    cat = E.CATEGORIAS.index("Timewarp")
    return A.guardado(lambda: E.aplicar_na_sequencia(len(inicios), cat, SAIDA, inicios=inicios, base=base,
                                                     linhas=[linha_preset] * len(inicios)), 300)


def _aplicar_marcado(mob_id: str, linha_preset: int, trechos: list[tuple[int, int]], nv: int) -> None:
    """Sem ler a marca pela cor (o `V1_Y` do laço da paleta é das LAB_EF, só com V1; aqui há TC1 e A1 e a V1 desce):
    a V1 selecionada pela foto do seletor, IN/OUT pela API dentro do segmento, e o duplo-clique no preset — o efeito
    vai no segmento marcado da trilha selecionada."""
    from . import interface_win as I
    h = E.janela_mc()
    C.maximizada(h)
    I.frente(h); time.sleep(0.5)
    A.sem_dialogos()
    # ⚠️ só a V1 ligada — conferido pela FOTO antes (o `C.selecionar` não reconhece a V1 desta sequência: o azul dela
    # (104, 166, 201) é outro, e a A1 não tem o botão azul de monitor; 2026-10-12). A A1 se desliga com o 6232.
    I.tecla(E.VK_8, E.VK_CTRL); time.sleep(0.6)
    I.clicar(E.CATEGORIA_X, int(E.CATEGORIA_Y0 + E.CATEGORIAS.index("Timewarp") * E.LINHA)); time.sleep(0.8)
    for a, b in trechos:
        I.frente(h)
        I.tecla(E.VK_0, E.VK_CTRL); time.sleep(0.5)
        with A.mc() as m:
            C._ir(m, a); E.comando(m, MARK_IN); time.sleep(0.4)
            C._ir(m, b); E.comando(m, MARK_OUT); time.sleep(0.4)
        I.tecla(E.VK_8, E.VK_CTRL); time.sleep(0.5)
        I.clicar(E.EFEITO_X, int(E.EFEITO_Y0 + linha_preset * E.LINHA), duplo=True)
        time.sleep(2)
        A.sem_dialogos()


MARK_IN, MARK_OUT = 6209, 6210


def aplicar_marcado(mob_id: str, linha_preset: int, trechos: list[tuple[int, int]], nv: int = 1) -> None:
    E.carregar(mob_id); time.sleep(2)
    A.guardado(lambda: _aplicar_marcado(mob_id, linha_preset, trechos, nv), 300)


# ── PROMOTE (autor, 2026-10-12): o MC NÃO aplica efeito de velocidade sobre o adaptador de taxa — e recusa CALADO
# (o duplo-clique no preset não fez nada). No Motion Effect Editor (DoCommand 6296), "Motion Adapter: Promote" vira o
# adaptador num Timewarp editável. Medido na LAB_RAMPA_MC_P4c (o 25 qps promovido pelo autor): `_MIXMATCH_MOTIONADAPTER`
# 2 → 4; mais `_MFX_VIEW_SPD_TOP/BOTTOM` e `_NEW_SHAPE_REFERENCE_FRAME 1`; param_list = [velocidade (quadros da FONTE
# por quadro da timeline: 25 → 1,0427), posição (o mapa, 0 → 50,05 em 48), 8d568283 inteiro 0]; `speed_ratio` =
# comprimento ÷ clipe de dentro (48/51 = [16, 17]). Âncora = pp code 14 no keyframe (valor = a fonte fixada ali).
ATTRS_PROMOVIDO = {"_MIXMATCH_MOTIONADAPTER": 4, "_MFX_VIEW_SPD_TOP": 300, "_MFX_VIEW_SPD_BOTTOM": -100,
                   "_NEW_SHAPE_REFERENCE_FRAME": 1}


def _translate():
    sys.path.insert(0, A.DLPC)
    from motor.avb_export import translate
    return translate


def rampa_linear(r: float, pontos: list[tuple[float, float]], influencia: float | None = None) -> list[dict]:
    """Keyframes de velocidade (em quadros da fonte por quadro da timeline) com as alças a 1/3 do vizinho: a Bézier
    de cada trecho vira RETA (a transição suavizada do Premiere sem influência). `pontos` = [(t, × tempo real)]."""
    kfs = []
    for i, (t, v) in enumerate(pontos):
        k = {"t": t, "speed": v * r, "in_dt": 0.0, "in_dv": 0.0, "out_dt": 0.0, "out_dv": 0.0, "mode": 1}
        if i:
            t0, v0 = pontos[i - 1]
            k["in_dt"], k["in_dv"] = -(t - t0) / 3, -(v - v0) * r / 3
        if i + 1 < len(pontos):
            t1, v1 = pontos[i + 1]
            k["out_dt"], k["out_dv"] = (t1 - t) / 3, (v1 - v) * r / 3
        if influencia is not None:                   # alças HORIZONTAIS de I × trecho (a Bézier do Premiere com
            k["in_dv"] = k["out_dv"] = 0.0           # influência: P1 = (I·T, v1), P2 = (T − I·T, v2))
            k["in_dt"] = -(t - pontos[i - 1][0]) * influencia if i else 0.0
            k["out_dt"] = (pontos[i + 1][0] - t) * influencia if i + 1 < len(pontos) else 0.0
        kfs.append(k)
    return kfs


def promover_com_rampa(f, me, kfs: list[dict], render: int = 1, kfs_do_mapa: list[dict] | None = None) -> list[tuple]:
    """O adaptador `me` (na bin aberta `f`) → Timewarp promovido com a curva `kfs` pelo escritor de PRODUÇÃO
    (`translate._set_motion_speed`: âncora no 1º keyframe com fonte 0, mapa pela integral). Devolve o mapa escrito."""
    import copy
    T = _translate()
    molde = _molde_promovido(f)
    me.attributes.update(ATTRS_PROMOVIDO)
    me.attributes["_SFX_RENDER"] = render
    pl = me.param_list                               # a lista de referências do pyavb (uma `list` comum não grava)
    novos = [p.copy(f) for p in molde.param_list]
    while len(pl):
        pl.pop()
    for p in novos:
        pl.append(p)
    n = me.length
    T._set_motion_speed(f, me, kfs, n)
    mapa = T._offset_map(kfs, n)
    if kfs_do_mapa is not None:                      # EXPERIMENTO: o mapa (p1) de OUTRA curva — quem o MC segue?
        mapa = T._offset_map(kfs_do_mapa, n)
        me.param_list[1].control_track.control_points = [T._mk_offset_cp(f, t, v) for t, v in mapa]
    dentro = int(mapa[-1][1]) + 2
    sc = [x for x in me.tracks[0].component.components if type(x).__name__ == "SourceClip"][0]
    sc.length = dentro
    me.speed_ratio = [n, dentro]
    me.left_bob = None
    return mapa


_MOLDE = {}


def _molde_promovido(f):
    if "me" not in _MOLDE:
        m = next(x for x in f.content.mobs if x.mob_type == "CompositionMob" and x.name == "LAB_RAMPA_MC_P4c")
        v = next(t for t in m.tracks if t.media_kind == "picture")
        _MOLDE["me"] = next(c for c in v.component.components if type(c).__name__ == "MotionEffect"
                            and (c.attributes or {}).get("_MIXMATCH_MOTIONADAPTER") == 4)
    return _MOLDE["me"]


def _cp(cp) -> tuple:
    off = cp.property_data.get("offset")
    t = off[0] / off[1] if isinstance(off, list) else off
    return (round(float(t), 4), round(float(cp.property_data.get("value")), 4))


def descrever(c, prof: int = 0) -> list:
    """A árvore de vídeo de um componente, com o que importa da velocidade."""
    n = type(c).__name__
    d = {"classe": n, "len": getattr(c, "length", None)}
    if n == "MotionEffect":
        d.update(speed_ratio=list(c.speed_ratio) if c.speed_ratio else None, attrs=dict(c.attributes or {}),
                 params=[])
        for p in c.property_data.get("param_list") or []:
            ct = p.property_data.get("control_track")
            d["params"].append(None if ct is None else [_cp(x) for x in ct.property_data.get("control_points") or []])
    elif n == "SourceClip":
        d["start"] = c.start_time
    elif hasattr(c, "effect_id"):
        d["effect_id"] = c.effect_id
    filhos = []
    if n == "Sequence":
        filhos = [x for x in c.components if not (type(x).__name__ == "Filler" and not x.length)]
    for t in getattr(c, "tracks", None) or []:
        if getattr(t, "component", None) is not None:
            filhos.append(t.component)
    if filhos:
        d["dentro"] = [descrever(x, prof + 1) for x in filhos]
    return d


def ler(nome: str | None = None, mob_id: str | None = None) -> dict:
    """A trilha V1 da sequência (pelo MobID, se dado — a bin pode ter nomes repetidos). A bin precisa estar fechada
    no MC ou salva (lê o disco)."""
    import avb
    with avb.open(C.BIN) as f:
        for m in f.content.mobs:
            if m.mob_type != "CompositionMob":
                continue
            if (mob_id and str(m.mob_id) == mob_id) or (not mob_id and m.name == nome):
                v = next(t for t in m.tracks if t.media_kind == "picture")
                return descrever(v.component)
    raise KeyError(nome or mob_id)


TAXAS = (25.0, 60000 / 1001, 100.0)          # os três segmentos da LAB_TAXAS (48 quadros cada, em 23,976)
TL = 24000 / 1001


def montar_rampa(nome: str, pontos, render: int = 1, origem: str = "LAB_TAXAS_v1", mxf: bool = True,
                 pontos_do_mapa=None) -> dict:
    """Cópia da LAB_TAXAS com os três adaptadores promovidos e a MESMA rampa (em × tempo real) em cada um. Grava
    `<nome>_esperado.json`: por quadro da timeline, a posição da fonte que o mapa escrito diz."""
    import json
    esperado = {}
    _MOLDE.clear()

    def mexer(mob):
        f = mob.root
        if mxf and trocar_fontes(mob) == 0:
            raise RuntimeError("nenhum SourceClip trocado para a mídia transcodificada")
        v = next(t for t in mob.tracks if t.media_kind == "picture")
        mes = [c for c in v.component.components if type(c).__name__ == "MotionEffect"]
        for i, (me, fps) in enumerate(zip(mes, TAXAS)):
            pts = pontos.get(i) if isinstance(pontos, dict) else pontos     # None: todos ficam com o adaptador     # {segmento: pontos}: os outros ficam
            if pts is None:                                                 # com o adaptador de taxa
                for k in range(me.length):
                    esperado[i * 48 + k] = k * fps / TL
                continue
            outro = rampa_linear(fps / TL, pontos_do_mapa) if pontos_do_mapa else None
            mapa = promover_com_rampa(f, me, rampa_linear(fps / TL, pts), render, outro)
            for t, val in mapa:
                if float(t).is_integer() and t < me.length:
                    esperado[i * 48 + int(t)] = val
    mid = copiar(origem, nome, mexer)
    out = {"nome": nome, "mob_id": mid, "pontos": pontos, "render": render, "esperado": esperado}
    os.makedirs(SAIDA, exist_ok=True)
    out["pontos"] = {str(k): v for k, v in pontos.items()} if isinstance(pontos, dict) else pontos
    json.dump(out, open(os.path.join(SAIDA, nome + "_esperado.json"), "w"), indent=0)
    return out


def medir(arq: str, esperado: dict) -> dict:
    """Por quadro da timeline: o quadro da fonte lido (código de barras no B02 25 / 59,94; dígitos no FRENTE_100),
    a posição que o mapa escrito diz, o piso e o arredondamento dela, e quanto há de mistura na caixa do número."""
    import math
    import subprocess
    from lab import ler
    from lab.mascara_b14 import numero_da_placa
    from . import avid_taxas_render as TR
    W, H = TR.W, TR.H
    g = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-map", "0:v:0", "-fps_mode", "passthrough", "-frames:v",
                        "144", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-vf", r"select=between(n\,96\,143)", "-fps_mode",
                        "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    out = {}
    for n in range(144):
        cz = g[n * W * H:(n + 1) * W * H]
        if n < 96:
            lido = ler.ler_faixas(cz, W, H)[0]
            mix = TR.mistura(cz, 880, 520, 330, 70)
        else:
            lido = numero_da_placa(r.stdout[(n - 96) * W * H * 3:(n - 95) * W * H * 3], "cima")
            mix = TR.mistura(cz, 40, 40, 420, 120)
        pos = float(esperado[str(n)] if str(n) in esperado else esperado[n])
        out[n] = {"lido": lido, "posicao": round(pos, 3), "piso": math.floor(pos + 1e-6), "perto": round(pos),
                  "mistura": round(mix, 4)}
    return out


def resumo(m: dict) -> dict:
    s = {}
    for nome, (a, b) in (("25", (0, 48)), ("59.94", (48, 96)), ("100", (96, 144))):
        fr = [m[n] for n in range(a, b)]
        s[nome] = {"piso": sum(x["lido"] == x["piso"] for x in fr), "perto": sum(x["lido"] == x["perto"] for x in fr),
                   "ilegivel": sum(x["lido"] is None for x in fr),
                   "fora": [(n, m[n]["lido"], m[n]["posicao"]) for n in range(a, b)
                            if m[n]["lido"] not in (m[n]["piso"], None)][:8]}
    return s


def rodada(nome: str, pontos, render: int = 1, prazo: float = 600, **k) -> dict:
    import json
    info = montar_rampa(nome, pontos, render, **k)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(info["mob_id"], os.path.abspath(SAIDA), nome, prazo=prazo), prazo + 30)
    m = medir(arq, info["esperado"])
    json.dump(m, open(os.path.join(SAIDA, nome + "_medido.json"), "w"), indent=0)
    return resumo(m)


# ── a mídia TRANSCODIFICADA na taxa de origem (autor, 2026-10-12: "trabalhar com amalink sempre foi bem ruim"; o export
# da rampa sobre o AMA travou e o MC foi reiniciado). Consolidate/Transcode → "Keep source's frame rate" (DNxHR LB): o
# master sai `<nome>.new.01` na taxa nativa — mesmo comprimento, mesmas trilhas. A sequência de taxa mista aponta para
# ele; o adaptador continua (a taxa segue diferente da timeline).
def trocar_fontes(mob, sufixo: str = ".new.01") -> int:
    """Cada SourceClip (todas as trilhas, dentro dos efeitos) que aponta para um master AMA passa a apontar para o
    master `<nome><sufixo>` da mesma bin. Devolve quantos trocou."""
    f = mob.root
    por_nome = {x.name: x for x in f.content.mobs if x.mob_type == "MasterMob"}
    n = 0

    def andar(c):
        nonlocal n
        if type(c).__name__ == "SourceClip":
            alvo = getattr(c, "mob", None)
            novo = por_nome.get((alvo.name or "") + sufixo) if alvo is not None else None
            if novo is not None:
                c.mob_id = novo.mob_id
                n += 1
        for x in getattr(c, "components", None) or []:
            andar(x)
        for t in getattr(c, "tracks", None) or []:
            if getattr(t, "component", None) is not None:
                andar(t.component)
    for t in mob.tracks:
        andar(t.component)
    return n


# ── rampa em clipe NATIVO (23,976 numa timeline de 23,976): o molde do tradutor (`templates.json` →
# EFF_ADV_MOTION_CTL, capturado de rampa real) + `_set_motion_speed` — o caminho de PRODUÇÃO por inteiro.
NATIVO = "B02_2398_MOV-PRORES.mov"


def mover_ancora(f, me, kf: int, mapa: list[tuple]) -> float:
    """A âncora (pp code 14) do 1º keyframe da curva para o keyframe `kf`, com o valor = a posição do mapa ali (a
    convenção lida nos presets: "100% To 0%" = âncora no último keyframe, valor = p1 dele). Devolve o valor."""
    T = _translate()
    cps = me.param_list[0].control_track.control_points
    for cp in cps:
        cp.pp = [q for q in cp.pp if q.code != 14]
    t = cps[kf].offset[0] / cps[kf].offset[1]
    val = next(v for tt, v in mapa if abs(tt - t) < 1e-9)
    cps[kf].pp = [T._mk_pp(f, 14, 2, float(val))] + list(cps[kf].pp)
    return val


def rampa_nativa(f, sc, kfs: list[dict], render: int = 1):
    """O SourceClip `sc` (da sequência aberta em `f`) dentro de um MotionEffect novo do molde de produção. Devolve
    (o efeito, o mapa)."""
    T = _translate()
    T.ER = 24000 / 1001
    me = T.materialize(f, T.capture_templates()["EFF_ADV_MOTION_CTL"])
    n = sc.length
    me.length, me.edit_rate = n, sc.edit_rate
    T._set_motion_speed(f, me, kfs, n)
    mapa = T._offset_map(kfs, n)
    me.attributes["_SFX_RENDER"] = render
    me.attributes["_SFX_IGNORE_RENDER_SETTING"] = 1
    dentro = int(mapa[-1][1]) + 2
    me.speed_ratio = [n, dentro]
    if len(kfs) == 1 and kfs[0]["speed"]:
        # velocidade CONSTANTE: o app lê o `speed_ratio` (timeline ÷ fonte, 85 % = [79, 68]); [n, dentro] dava 0,54 num
        # 50 % (B22, 2026-10-12). Na rampa ele lê o mapa.
        from fractions import Fraction
        fr = Fraction(1 / kfs[0]["speed"]).limit_denominator(10000)
        me.speed_ratio = [fr.numerator, fr.denominator]
    seq = me.tracks[0].component
    alvo = next(c for c in seq.components if type(c).__name__ == "SourceClip")
    alvo.mob_id, alvo.start_time, alvo.length, alvo.edit_rate = sc.mob_id, sc.start_time, dentro, sc.edit_rate
    alvo.track_id = sc.track_id
    return me, mapa


def montar_nativa(nome: str, rampas: list[list[tuple[float, float]]], inicios=(0, 80, 160), render: int = 1,
                  base: str = "LAB_RAMPA_NAT_base", ancora_kf: int | None = None) -> dict:
    """`base` (3 segmentos de 48 do B02 23,976, entradas `inicios`) copiada com cada segmento da V1 numa rampa nativa
    (`rampas[i]` em × tempo real). Grava `<nome>_esperado.json` (posição da fonte = in do segmento + mapa)."""
    import json
    esperado, ancoras = {}, {}

    def mexer(mob):
        f = mob.root
        v = next(t for t in mob.tracks if t.media_kind == "picture")
        comps = v.component.components
        i = 0
        for j in range(len(comps)):
            c = comps[j]
            if type(c).__name__ != "SourceClip" or not c.length:
                continue
            pts, infl = rampas[i] if isinstance(rampas[i], tuple) else (rampas[i], None)
            me, mapa = rampa_nativa(f, c, rampa_linear(1.0, pts, infl), render)
            if ancora_kf is not None:
                ancoras[i] = mover_ancora(f, me, min(ancora_kf, len(pts) - 1), mapa)
            for t, val in mapa:
                if float(t).is_integer() and t < me.length:
                    esperado[i * 48 + int(t)] = c.start_time + val
            comps[j] = me
            i += 1
    mid = copiar(base, nome, mexer)
    out = {"nome": nome, "mob_id": mid, "rampas": rampas, "render": render, "ancoras": ancoras, "esperado": esperado}
    json.dump(out, open(os.path.join(SAIDA, nome + "_esperado.json"), "w"), indent=0)
    return out


def medir_barras(arq: str, esperado: dict, n_quadros: int = 144) -> dict:
    import math
    import subprocess
    from lab import ler
    from . import avid_taxas_render as TR
    W, H = TR.W, TR.H
    g = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-map", "0:v:0", "-fps_mode", "passthrough", "-frames:v",
                        str(n_quadros), "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    out = {}
    for n in range(len(g) // (W * H)):
        cz = g[n * W * H:(n + 1) * W * H]
        pos = float(esperado[str(n)] if str(n) in esperado else esperado[n])
        out[n] = {"lido": ler.ler_faixas(cz, W, H)[0], "posicao": round(pos, 3), "piso": math.floor(pos + 1e-6),
                  "perto": round(pos), "mistura": round(TR.mistura(cz, 880, 520, 330, 70), 4)}
    return out


def rodada_nativa(nome: str, rampas, render: int = 1, prazo: float = 240, **k) -> dict:
    import json
    info = montar_nativa(nome, rampas, render=render, **k)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(info["mob_id"], os.path.abspath(SAIDA), nome, prazo=prazo), prazo + 30)
    m = medir_barras(arq, info["esperado"])
    json.dump(m, open(os.path.join(SAIDA, nome + "_medido.json"), "w"), indent=0)
    s = {}
    for i in range(3):
        fr = [m[n] for n in range(i * 48, i * 48 + 48) if n in m]
        s[i] = {"piso": sum(x["lido"] == x["piso"] for x in fr), "n": len(fr),
                "ilegivel": sum(x["lido"] is None for x in fr),
                "fora": [(n, m[n]["lido"], m[n]["posicao"]) for n in range(i * 48, i * 48 + 48)
                         if n in m and m[n]["lido"] not in (m[n]["piso"], None)][:6]}
    return s


def _aplicar_laco(mob_id: str, linha_preset: int, quadro: int, foto_nome: str) -> str:
    """O laço da bancada de efeitos (o que funcionou na LAB_EF_*): agulha no `quadro` → G + clique na faixa vazia (tira
    a SELEÇÃO de segmento — o efeito vai para o segmento selecionado, se houver) → T → Ctrl+8 → duplo-clique no preset.
    Devolve a foto tirada logo antes do duplo-clique."""
    from . import interface_win as I
    h = E.janela_mc()
    A.afastar_bins()
    C.maximizada(h)
    I.frente(h); time.sleep(0.5)
    I.tecla(E.VK_0, E.VK_CTRL); time.sleep(0.5)
    with A.mc() as m:
        C._ir(m, quadro)
    agulha, _ = E.ler_timeline(h, SAIDA)
    I.tecla(E.VK_G); time.sleep(0.4)
    I.clicar((agulha or E.TL_X0) + 4, E.FAIXA_VAZIA_Y); time.sleep(0.5)
    I.tecla(E.VK_T); time.sleep(0.8)
    I.tecla(E.VK_8, E.VK_CTRL); time.sleep(0.6)
    I.clicar(E.CATEGORIA_X, int(E.CATEGORIA_Y0 + E.CATEGORIAS.index("Timewarp") * E.LINHA)); time.sleep(0.8)
    p = foto(foto_nome)
    I.clicar(E.EFEITO_X, int(E.EFEITO_Y0 + linha_preset * E.LINHA), duplo=True)
    time.sleep(2)
    A.sem_dialogos()
    return p


def aplicar_laco(mob_id: str, linha_preset: int, quadro: int, foto_nome: str = "laco") -> str:
    E.carregar(mob_id); time.sleep(2)
    return A.guardado(lambda: _aplicar_laco(mob_id, linha_preset, quadro, foto_nome), 180)


def estrutura(nome: str) -> list:
    with A.mc() as m:
        m.fechar_bin(C.BIN)
    try:
        d = ler(nome=nome)
    finally:
        with A.mc() as m:
            m.abrir_bin(C.BIN)
    return [(x["classe"], x.get("effect_id"), x.get("len"), x.get("attrs", {}).get("_SFX_RENDER"),
             [len(p or []) for p in x.get("params") or []]) for x in d["dentro"]]


# ── QUADRO A QUADRO (regra do autor, 2026-10-12): entre NLEs diferentes a rampa NÃO recria curva — um keyframe por
# quadro com o quadro EXATO da fonte. No Avid: o gráfico de POSIÇÃO (`_MFX_GRAPH_ENABLED 2`; p0 = posição da fonte por
# quadro da timeline, p1 = um ponto 0), molde = o preset Speed Boost aplicado pelo MC (LAB_EF_TIMEWARP, 5º clipe).
def _molde_posicao(f):
    m = next(x for x in f.content.mobs if x.mob_type == "CompositionMob" and x.name == "LAB_EF_TIMEWARP")
    v = next(t for t in m.tracks if t.media_kind == "picture")
    mes = [c for c in v.component.components if type(c).__name__ == "MotionEffect"]
    return next(c for c in mes if (c.attributes or {}).get("_MFX_GRAPH_ENABLED") == 2)


def quadro_a_quadro(f, sc, alvos: list[float], render: int = 2):
    """O SourceClip `sc` dentro de um Timewarp de POSIÇÃO com um keyframe por quadro: `alvos[k]` = o quadro da fonte
    (contado do in de `sc`) que o quadro k da timeline deve mostrar."""
    T = _translate()
    me = _molde_posicao(f).copy(f)
    n = len(alvos)
    me.length, me.edit_rate = n, sc.edit_rate
    me.attributes["_SFX_RENDER"] = render
    me.attributes["_SFX_IGNORE_RENDER_SETTING"] = 1
    pos = me.param_list[0].control_track
    pos.length = n
    cps = []
    for k, v in enumerate(alvos):
        cp = f.create.ParamControlPoint()
        cp.offset, cp.timescale, cp.value = [k, 1], 1, float(v)
        cp.pp = [T._mk_pp(f, c, 2, 0.0) for c in (5, 6, 7, 8)] + [T._mk_pp(f, 9, 1, 1)]
        cps.append(cp)
    pos.control_points = cps
    for p in list(me.param_list)[1:]:
        if p.control_track is not None:
            p.control_track.length = n
    dentro = int(max(alvos)) + 2
    me.speed_ratio = [n, dentro]
    alvo = next(c for c in me.tracks[0].component.components if type(c).__name__ == "SourceClip")
    alvo.mob_id, alvo.start_time, alvo.length, alvo.edit_rate = sc.mob_id, sc.start_time, dentro, sc.edit_rate
    alvo.track_id = sc.track_id
    return me


def padrao_irregular() -> list[int]:
    """48 quadros: 0–11 normal, congela no 11 por 3, salta de 3 em 3 (até 47), ré de 2 em 2 por 8, e normal até o fim."""
    a = list(range(12)) + [11, 11, 11]
    while len(a) < 27:
        a.append(a[-1] + 3)
    for _ in range(8):
        a.append(a[-1] - 2)
    while len(a) < 48:
        a.append(a[-1] + 1)
    return a


def rodada_quadro_a_quadro(nome: str, renders=(2, 4, 6), base: str = "LAB_RAMPA_NAT_base", prazo: float = 240) -> dict:
    import json
    alvos = padrao_irregular()
    esperado = {}

    def mexer(mob):
        f = mob.root
        v = next(t for t in mob.tracks if t.media_kind == "picture")
        comps = v.component.components
        i = 0
        for j in range(len(comps)):
            c = comps[j]
            if type(c).__name__ != "SourceClip" or not c.length:
                continue
            for k, a in enumerate(alvos):
                esperado[i * 48 + k] = c.start_time + a
            comps[j] = quadro_a_quadro(f, c, alvos, renders[i])
            i += 1
    mid = copiar(base, nome, mexer)
    json.dump({"nome": nome, "mob_id": mid, "renders": renders, "alvos": alvos, "esperado": esperado},
              open(os.path.join(SAIDA, nome + "_esperado.json"), "w"), indent=0)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(mid, os.path.abspath(SAIDA), nome, prazo=prazo), prazo + 30)
    m = medir_barras(arq, esperado)
    json.dump(m, open(os.path.join(SAIDA, nome + "_medido.json"), "w"), indent=0)
    s = {}
    for i, r in enumerate(renders):
        fr = [m[n] for n in range(i * 48, i * 48 + 48) if n in m]
        s[r] = {"exato": sum(x["lido"] == round(x["posicao"]) for x in fr), "n": len(fr),
                "ilegivel": sum(x["lido"] is None for x in fr),
                "mistura_max": max(x["mistura"] for x in fr),
                "fora": [(n, m[n]["lido"], m[n]["posicao"]) for n in range(i * 48, i * 48 + 48)
                         if n in m and m[n]["lido"] != round(m[n]["posicao"])][:6]}
    return s


# ── HÍBRIDO (autor, 2026-10-12): um segmento com trechos de velocidade CONSTANTE e trechos de CURVA. Só a curva se
# queima quadro a quadro; no constante, um keyframe no início e outro no fim, com interpolação LINEAR (`interp_kind 3`)
# = velocidade constante exata entre eles. No Premiere o início/fim da curva já vêm marcados (o par 7 → 8).
def posicoes(pontos: list[tuple[float, float]], n: int, influencia: float = 0.5) -> list[float]:
    """A posição exata da fonte em cada quadro 0..n-1 para a velocidade `pontos` [(t, ×)] com as transições suaves
    (Bézier de alças horizontais, a do Premiere com influência)."""
    T = _translate()
    mapa = dict(T._offset_map(rampa_linear(1.0, pontos, influencia), n))
    return [mapa[float(k)] for k in range(n)]


def hibrido(f, sc, pos: list[float], keyframes: list[int], render: int = 2):
    """Timewarp de POSIÇÃO com keyframes só nos quadros `keyframes` (valor exato), interpolação LINEAR."""
    me = quadro_a_quadro(f, sc, pos, render)
    ct = me.param_list[0].control_track
    ct.interp_kind = 3
    ct.control_points = [cp for cp in ct.control_points if int(cp.offset[0] / cp.offset[1]) in set(keyframes)]
    return me


def rodada_hibrida(nome: str, casos: list[tuple], base: str = "LAB_RAMPA_NAT_base", prazo: float = 240) -> dict:
    """`casos[i]` = (pontos de velocidade, trechos de curva [(t0, t1)] ou None = tudo denso). Mede: quadro da fonte =
    piso(posição exata)."""
    import json
    import math
    esperado, info = {}, []

    def mexer(mob):
        f = mob.root
        v = next(t for t in mob.tracks if t.media_kind == "picture")
        comps = v.component.components
        i = 0
        for j in range(len(comps)):
            c = comps[j]
            if type(c).__name__ != "SourceClip" or not c.length:
                continue
            pontos, curvas = casos[i]
            pos = posicoes(pontos, 48)
            if curvas is None:
                kfs = list(range(48))
            else:
                kfs = {0, 47}
                for t0, t1 in curvas:
                    kfs |= set(range(int(t0), int(math.ceil(t1)) + 1))
                kfs = sorted(kfs)
            info.append({"keyframes": len(kfs), "quadros": kfs})
            for k in range(48):
                esperado[i * 48 + k] = c.start_time + pos[k]
            comps[j] = hibrido(f, c, pos, kfs)
            i += 1
    mid = copiar(base, nome, mexer)
    json.dump({"nome": nome, "mob_id": mid, "casos": casos, "info": info, "esperado": esperado},
              open(os.path.join(SAIDA, nome + "_esperado.json"), "w"), indent=0)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(mid, os.path.abspath(SAIDA), nome, prazo=prazo), prazo + 30)
    m = medir_barras(arq, esperado)
    json.dump(m, open(os.path.join(SAIDA, nome + "_medido.json"), "w"), indent=0)
    s = {}
    for i in range(len(casos)):
        fr = [m[n] for n in range(i * 48, i * 48 + 48) if n in m]
        s[i] = {"keyframes": info[i]["keyframes"], "piso": sum(x["lido"] == x["piso"] for x in fr), "n": len(fr),
                "fora": [(n, m[n]["lido"], m[n]["posicao"]) for n in range(i * 48, i * 48 + 48)
                         if n in m and m[n]["lido"] != m[n]["piso"]][:6]}
    return s


# ── B22: Premiere → Avid (a origem é `premiere_rampas`: A e B com curva, C 50 % com Optical Flow) ──
def _janelas_de_curva(curva, inq: int, n: int = 48) -> list[tuple[float, float]]:
    """Os trechos 7 → 8 do Time Remapping, em quadros da TIMELINE (descontado o in), cortados ao clipe."""
    from . import premiere_rampas as P
    out = []
    for a, b in zip(curva, curva[1:]):
        if a[2] == "7" and b[2] == "8":
            t0, t1 = a[0] / P.Q - inq, b[0] / P.Q - inq
            if t1 > 0 and t0 < n - 1:
                out.append((max(0.0, t0), min(n - 1.0, t1)))
    return out


def traduzir_b22(nome: str = "LAB_B22_AVID", base: str = "LAB_B22_base", prazo: float = 240) -> dict:
    import json
    import math
    from . import premiere_rampas as P
    esp_pr = P.esperado()
    esperado, info = {}, {}

    def mexer(mob):
        f = mob.root
        v = next(t for t in mob.tracks if t.media_kind == "picture")
        comps = v.component.components
        i = 0
        for j in range(len(comps)):
            c = comps[j]
            if type(c).__name__ != "SourceClip" or not c.length:
                continue
            nome_c = list(P.CASOS)[i]
            pos = esp_pr[nome_c]
            for k in range(48):
                esperado[i * 48 + k] = c.start_time + pos[k]
            caso = P.CASOS[nome_c]
            if caso is None:                                         # C: constante nativa 50 %, FluidMotion
                me, _ = rampa_nativa(f, c, rampa_linear(1.0, [(0, 0.5)]), render=6)
                info[nome_c] = "constante 0,5 nativa, FluidMotion (6)"
            else:                                                    # A, B: híbrido — só a curva quadro a quadro
                curva, inq = caso()
                janelas = _janelas_de_curva(curva, inq)
                kfs = {0, 47}
                for t0, t1 in janelas:
                    kfs |= set(range(int(math.floor(t0)), int(math.ceil(t1)) + 1))
                kfs = sorted(k for k in kfs if 0 <= k < 48)
                me = hibrido(f, c, pos, kfs, render=2)
                info[nome_c] = {"janelas": janelas, "keyframes": len(kfs)}
            comps[j] = me
            i += 1
    mid = copiar(base, nome, mexer)
    json.dump({"nome": nome, "mob_id": mid, "info": info, "esperado": esperado},
              open(os.path.join(SAIDA, nome + "_esperado.json"), "w"), indent=0, default=str)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(mid, os.path.abspath(SAIDA), nome, prazo=prazo), prazo + 30)
    m = medir_barras(arq, esperado)
    json.dump(m, open(os.path.join(SAIDA, nome + "_medido.json"), "w"), indent=0)
    return {"info": info, "arquivo": arq}


def comparar_b22(arq_avid: str) -> dict:
    """Avid × Premiere quadro a quadro: o número lido nos dois e a diferença média de pixel na caixa do número."""
    import json
    import subprocess
    from lab import ler
    from . import premiere_rampas as P
    W, H = 1920, 1080

    def quadros(arq):
        g = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-map", "0:v:0", "-frames:v", "144", "-f", "rawvideo",
                            "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        return [g[n * W * H:(n + 1) * W * H] for n in range(len(g) // (W * H))]
    a, p = quadros(arq_avid), quadros(P.RENDER)
    out = {}
    for i, nome in enumerate(P.CASOS):
        iguais, difs, linhas = 0, [], []
        for k in range(48):
            n = i * 48 + k
            la, lp = ler.ler_faixas(a[n], W, H)[0], ler.ler_faixas(p[n], W, H)[0]
            caixa = [(y * W + x) for y in range(520, 590, 2) for x in range(880, 1210, 2)]
            d = sum(abs(a[n][q] - p[n][q]) for q in caixa) / len(caixa)
            iguais += la == lp
            difs.append(round(d, 2))
            linhas.append((k, la, lp, round(d, 2)))
        out[nome] = {"mesmo_numero": iguais, "dif_media_max": max(difs), "linhas": linhas}
    json.dump(out, open(os.path.join(SAIDA, "B22_avid_x_premiere.json"), "w"), indent=0)
    return {k: {x: v[x] for x in ("mesmo_numero", "dif_media_max")} for k, v in out.items()}


# ── B22 no sentido AVID → PREMIERE: a origem é uma rampa nativa do Avid (gráfico de VELOCIDADE, Bézier) ──
ORIGEM_AVID = {
    "RAMPA_A": ([(0, 1.2), (12, 1.2), (30, 1.9), (47, 1.9)], 0.5),   # constante → curva → constante
    "RAMPA_B": ([(0, 1.4), (14, 0.6), (47, 0.6)], 0.5),              # já começa desacelerando → constante
    "RAMPA_C": None,                                                 # 50 % constante, FluidMotion
}


def posicoes_da_bin(nome: str, n: int = 48) -> dict:
    """O LEITOR (o lado Avid da tradução): para cada segmento de vídeo com Timewarp, a posição da fonte em cada quadro
    — do mapa p1 (o que o render segue; gráfico de velocidade) ou do p0 (gráfico de posição) — contada do início da
    MÍDIA (in do clipe de dentro + mapa), e o tipo de render."""
    import avb
    with avb.open(C.BIN) as f:
        mob = next(x for x in f.content.mobs if x.mob_type == "CompositionMob" and x.name == nome)
        v = next(t for t in mob.tracks if t.media_kind == "picture")
        out = []
        for c in v.component.components:
            if type(c).__name__ != "MotionEffect":
                continue
            graf = (c.attributes or {}).get("_MFX_GRAPH_ENABLED") == 2
            ct = c.param_list[0 if graf else 1].control_track
            pts = sorted((cp.offset[0] / cp.offset[1], float(cp.value)) for cp in ct.control_points)
            sc = next(x for x in c.tracks[0].component.components if type(x).__name__ == "SourceClip")

            def em(k):
                for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
                    if t0 <= k <= t1:
                        return v0 + (v1 - v0) * (k - t0) / (t1 - t0) if t1 > t0 else v0
                return pts[-1][1] if k > pts[-1][0] else pts[0][1]
            out.append({"in": sc.start_time, "render": (c.attributes or {}).get("_SFX_RENDER"),
                        "pos": [sc.start_time + em(k) for k in range(min(n, c.length))]})
        return out


def origem_avid_b22(nome: str = "LAB_B22_AV_ORIGEM", base: str = "LAB_B22_base", prazo: float = 240) -> dict:
    import json
    esperado = {}

    def mexer(mob):
        f = mob.root
        v = next(t for t in mob.tracks if t.media_kind == "picture")
        comps = v.component.components
        i = 0
        for j in range(len(comps)):
            c = comps[j]
            if type(c).__name__ != "SourceClip" or not c.length:
                continue
            caso = list(ORIGEM_AVID.values())[i]
            if caso is None:
                me, mapa = rampa_nativa(f, c, rampa_linear(1.0, [(0, 0.5)]), render=6)
            else:
                pts, infl = caso
                me, mapa = rampa_nativa(f, c, rampa_linear(1.0, pts, infl), render=2)
            comps[j] = me
            i += 1
    mid = copiar(base, nome, mexer)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(mid, os.path.abspath(SAIDA), nome, prazo=prazo), prazo + 30)
    with A.mc() as m:
        m.fechar_bin(C.BIN)
    try:
        lidos = posicoes_da_bin(nome)
    finally:
        with A.mc() as m:
            m.abrir_bin(C.BIN)
    for i, s in enumerate(lidos):
        for k, pos in enumerate(s["pos"]):
            esperado[i * 48 + k] = pos
    m = medir_barras(arq, esperado)
    json.dump({"nome": nome, "mob_id": mid, "arquivo": arq, "segmentos": lidos},
              open(os.path.join(SAIDA, nome + ".json"), "w"), indent=0)
    s = {}
    for i in range(len(lidos)):
        fr = [m[n] for n in range(i * 48, i * 48 + 48) if n in m]
        s[list(ORIGEM_AVID)[i]] = {"piso": sum(x["lido"] == x["piso"] for x in fr), "n": len(fr),
                                   "render": lidos[i]["render"]}
    return s


def traduzir_posicoes(origem_json: str, nome: str, base: str = "LAB_B22_base", prazo: float = 240) -> dict:
    """Qualquer origem → Avid, pelas POSIÇÕES por quadro (o modelo neutro): constante em todo o segmento → velocidade
    constante nativa (FluidMotion se a origem pediu fluxo óptico em câmera lenta); com curva → HÍBRIDO (keyframe onde
    a velocidade muda: um por quadro na curva, só as pontas no constante). Renderiza e compara com o render da origem."""
    import json
    from . import premiere_rampas as P
    dados = json.load(open(origem_json, encoding="utf-8"))
    info = {}

    def mexer(mob):
        f = mob.root
        v = next(t for t in mob.tracks if t.media_kind == "picture")
        comps = v.component.components
        i = 0
        for j in range(len(comps)):
            c = comps[j]
            if type(c).__name__ != "SourceClip" or not c.length:
                continue
            s = dados["segmentos"][i]
            pos = [p - c.start_time for p in s["pos"]]
            d = [b - a for a, b in zip(pos, pos[1:])]
            if all(abs(x - d[0]) < 1e-6 for x in d):
                r = 6 if (s.get("render") == 6 and d[0] < 1) else 2
                me, _ = rampa_nativa(f, c, rampa_linear(1.0, [(0, d[0])]), render=r)
                info[i] = f"constante {d[0]:.4f}, render {r}"
            else:
                kfs = [0] + [k for k in range(1, len(pos) - 1) if abs(d[k] - d[k - 1]) >= 1e-6] + [len(pos) - 1]
                me = hibrido(f, c, pos, kfs, render=2)
                info[i] = f"híbrido, {len(kfs)} keyframes"
            comps[j] = me
            i += 1
    mid = copiar(base, nome, mexer)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(mid, os.path.abspath(SAIDA), nome, prazo=prazo), prazo + 30)
    return {"info": info, "comparacao": P.comparar(dados["arquivo"], arq, ["RAMPA_A", "RAMPA_B", "RAMPA_C"])}


def traduzir_b22_pelo_app(nome: str = "LAB_B22_AVID_APP", base: str = "LAB_B22_base", prazo: float = 240) -> dict:
    """A B22 com os Timewarps de POSIÇÃO escritos pelo ESCRITOR DO APP (`translate._motion_entry_from_seg` +
    `_build_one`, origem "premiere"), não pelo `hibrido` daqui. Medido 2026-10-12 (MC 25.6): A 48/48 (21 keyframes),
    B 48/48 (16); C = a constante nativa daqui (FluidMotion: os x,5 sintetizados)."""
    import json
    from . import premiere_rampas as P
    sys.path.insert(0, os.path.join(A.DLPC, "motor"))
    from avb_export import translate as T
    esp_pr, esperado, info = P.esperado(), {}, {}
    tpl = T.capture_templates()

    def mexer(mob):
        f = mob.root
        comps = next(t for t in mob.tracks if t.media_kind == "picture").component.components
        T.set_remap(None)
        T.set_origem("premiere", TL)
        i = 0
        for j in range(len(comps)):
            c = comps[j]
            if type(c).__name__ != "SourceClip" or not c.length:
                continue
            nome_c = list(P.CASOS)[i]
            pos = esp_pr[nome_c]
            for k in range(48):
                esperado[i * 48 + k] = c.start_time + pos[k]
            if P.CASOS[nome_c] is None:
                me, _ = rampa_nativa(f, c, rampa_linear(1.0, [(0, 0.5)]), render=6)
                info[nome_c] = "constante 0,5 nativa (bancada), FluidMotion (6)"
            else:
                s = {"motion_effect_type": "ramp", "duration_frames": 48, "source_start_frames": c.start_time,
                     "source_offset_map": [(float(k), float(p)) for k, p in enumerate(pos)], "source_fps": TL,
                     "clip_name": nome_c, "speed_keyframes": [], "retime": None}
                T.ER = c.edit_rate
                e = T._motion_entry_from_seg(s, c.mob_id.bytes_le.hex())
                me = T._build_one(f, e, "picture", tpl)
                next(x for x in me.tracks[0].component.components if type(x).__name__ == "SourceClip").track_id = \
                    c.track_id
                info[nome_c] = {"keyframes": len(e[1][2]), "pelo": "translate do app"}
            comps[j] = me
            i += 1
        T.set_origem(None, None)
    mid = copiar(base, nome, mexer)
    A.instalar_preset("23.976")
    arq = A.guardado(lambda: A.exportar(mid, os.path.abspath(SAIDA), nome, prazo=prazo), prazo + 30)
    m = medir_barras(arq, esperado)
    json.dump(m, open(os.path.join(SAIDA, nome + "_medido.json"), "w"), indent=0)
    return {"info": info, "arquivo": arq}
