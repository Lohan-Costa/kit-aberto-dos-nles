"""Bancada B21 COLLAPSE no Media Composer (pedido do autor, 2026-10-12; mídia e plano em `lab/collapse_b21.py`).

1. `montar(nome, params)` — ESCREVE na bin (pyavb, a dança do banco) a sequência do caso: FUNDO na V1; na V2 a FRENTE e
   a VERDE em SEQUÊNCIA (quadros 0–47); no mosaico (48–143) a FRENTE na V2 e a VERDE na V3, cada uma dentro de um
   Resize (cópia do Resize que o próprio MC aplicou na LAB_EF_IMAGE) com Crop e Position escritos em `params`.
2. O Collapse é feito PELO MC (piloto): é como se aprende a forma que ele grava.
3. `render(mob_id, nome)` + as medidas: a cor de cada coluna/linha diz quem está onde.
"""
from __future__ import annotations

import os
import sys
import time
import uuid as _uuid

from . import avid as A

BIN = os.path.expanduser(r"~\Documents\Avid Projects\DLPC LAB\DLPC LAB 23.976\DLPC LAB 23.976 Bin.avb")
SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "saida", "bancadas",
                     "avid", "collapse")
MASTERS = {"FUNDO": "B14_FUNDO.mov", "FRENTE": "B14_FRENTE.mov", "VERDE": "B21_VERDE.mov"}
TOTAL = 144


#: os moldes: efeitos que o PRÓPRIO MC aplicou nas sequências da bancada de efeitos. ⚠️ O Resize é OPACO (fundo preto
#: cobre a trilha de baixo, v1 de 2026-10-12): mosaico no Avid é o PIP, que deixa ver o que está embaixo.
MOLDES = {"EFF2_BLEND_RESIZE": "LAB_EF_IMAGE", "EFF2_BLEND_PIP": "LAB_EF_BLEND"}


def _molde(f, effect_id: str):
    for mob in f.content.mobs:
        if mob.mob_type == "CompositionMob" and mob.name == MOLDES[effect_id]:
            for t in mob.tracks:
                for x in getattr(t.component, "components", None) or []:
                    if type(x).__name__ == "TrackEffect" and x.effect_id == effect_id:
                        return x
    raise RuntimeError(f"não achei o {effect_id} do MC ({MOLDES[effect_id]}) para servir de molde")


def _fonte(f, T, taxa, mob_id: str, inicio: int, dur: int):
    sc = f.create.SourceClip(taxa, "picture")
    sc.mob_id = T.MobID(mob_id)
    sc.track_id, sc.start_time, sc.length = 1, inicio, dur
    return sc


def _com_efeito(f, T, taxa, molde, mob_id: str, inicio: int, dur: int, params: dict):
    """Um Resize NOVO com o clipe dentro: cópia do molde do MC, sem a referência ao cache de render (`left_bob`), com
    os parâmetros escritos como o MC grava os que saem do padrão (`ParameterItem`, value_type 2, inteiro)."""
    from avb.parameter_uuids import PARAMETER_UUIDS
    por_nome = {n: u for u, n in PARAMETER_UUIDS.items()}
    ef = molde.copy(f)
    ef.length = dur
    ef.left_bob = None                              # apagar a propriedade quebra o write do pyavb: tem de existir, vazia
    # as trilhas INTERNAS seguem o molde: a que tem clipe recebe o nosso; a só de vazio é o FUNDO (o PIP tem duas — a 1ª
    # olha a trilha de baixo, `TrackRef relative_scope 1` —, o Resize uma só; v2 de 2026-10-12: pôr o clipe no lugar
    # do fundo fez o export do MC falhar, "AMA Export failed")
    for tr in ef.tracks:
        if "bob_data" in tr.property_data:
            tr.bob_data = None
        seq = tr.component
        if any(type(c).__name__ == "SourceClip" for c in seq.components):
            seq.components = [T._filler(f, taxa, 0, "picture"), _fonte(f, T, taxa, mob_id, inicio, dur),
                              T._filler(f, taxa, 0, "picture")]
        else:
            seq.components = [T._filler(f, taxa, dur, "picture")]
    for nome, v in params.items():
        item = f.create.ParameterItem()
        item.uuid, item.value_type, item.name = _uuid.UUID(por_nome[nome]), 2, ""
        item.enable, item.control_track, item.contribs_to_sig = True, None, True
        item.value = int(v) if float(v).is_integer() else v
        ef.param_list.append(item)
    return ef


def _montar(nome: str, params_frente: dict, params_verde: dict, efeito: str = "EFF2_BLEND_PIP", prazo: float = 60) -> str:
    """A sequência do B21 numa bin FECHADA no MC (CloseBin → grava ao lado → troca → OpenBin). Devolve o mob_id."""
    import avb
    T = A._timeline()
    sys.path.insert(0, A.ASSIST)
    from cicloassist.avid.atributos import copiar_atributos
    with A.mc() as m:
        try:
            m.fechar_bin(BIN)
        except Exception:                           # noqa: BLE001 — já fechada
            pass
        temporario = BIN + ".novo"
        with avb.open(BIN) as f:
            masters = {mm.name: mm for mm in f.content.mobs if mm.mob_type == "MasterMob"}
            ids = {k: str(masters[v].mob_id) for k, v in MASTERS.items()}
            taxa = masters[MASTERS["FUNDO"]].edit_rate
            molde = _molde(f, efeito)
            comp = T.montar_timeline(f, nome, [T.Entrada(mob_id=ids["FUNDO"], duracao=TOTAL,
                                                         trilhas=(("picture", 1),), start_time=0)], taxa)
            v2 = [T._filler(f, taxa, 0, "picture"), _fonte(f, T, taxa, ids["FRENTE"], 0, 24),
                  _fonte(f, T, taxa, ids["VERDE"], 24, 24),
                  _com_efeito(f, T, taxa, molde, ids["FRENTE"], 48, 96, params_frente)]
            v3 = [T._filler(f, taxa, 48, "picture"), _com_efeito(f, T, taxa, molde, ids["VERDE"], 48, 96, params_verde)]
            for indice, comps in ((2, v2), (3, v3)):
                seq = f.create.Sequence(taxa, "picture")
                seq.components = comps
                seq.components.append(T._trail_filler(f, taxa, "picture", seq.components, TOTAL))
                tr = f.create.Track()
                tr.index, tr.component, tr.lock_number = indice, seq, 0
                tr.filler_proxy = T._referencia_de_track(f, taxa, "picture")
                tr.session_attr = T._atributos(f, _ENBLSTATE=1, _MONSTATE=1)
                comp.tracks.insert(indice - 1, tr)
            f.write(temporario)
        copiar_atributos(BIN, temporario)
        os.replace(temporario, BIN)
        m.abrir_bin(BIN)
        fim = time.time() + prazo
        while time.time() < fim:
            for it in m.itens_de(BIN, flags=("AllTypes",)):
                if it.name == nome:
                    return it.mob_id
            time.sleep(2)
    raise RuntimeError(f"a sequência {nome!r} não apareceu na bin")


def _molde_em(f, sequencia: str, effect_id: str):
    for mob in f.content.mobs:
        if mob.mob_type == "CompositionMob" and mob.name == sequencia:
            for t in mob.tracks:
                for x in getattr(t.component, "components", None) or []:
                    if type(x).__name__ == "TrackEffect" and x.effect_id == effect_id:
                        return x
    raise RuntimeError(f"não achei {effect_id} em {sequencia}")


def _trilha_interna(f, T, taxa, indice: int, comps: list, olha_embaixo: bool):
    seq = f.create.Sequence(taxa, "picture")
    seq.components = comps
    tr = f.create.Track()
    tr.index, tr.component, tr.lock_number = indice, seq, 0
    tr.filler_proxy = T._referencia_de_track(f, taxa, "picture")
    tr.filler_proxy.relative_scope = 1 if olha_embaixo else 0
    return tr


def _colapso(f, T, taxa, molde, dur: int, trilhas: list[list]):
    """Um Collapse ESCRITO: cópia do recipiente que o MC gravou (Submaster ou outro efeito aplicado sobre o Collapse)
    com as trilhas internas na forma medida (2026-10-12, B21): UMA trilha colapsada = uma trilha interna (índice 1,
    os vazios olham a trilha de baixo); VÁRIAS = a 1ª interna é só FUNDO (Filler do tamanho todo, olha embaixo) e
    depois uma por trilha colapsada (índices 2…, não olham embaixo)."""
    ef = molde.copy(f)
    ef.left_bob = None
    ef.length = dur
    if len(trilhas) == 1:
        ef.tracks = [_trilha_interna(f, T, taxa, 1, [T._filler(f, taxa, 0, "picture")] + trilhas[0]
                                     + [T._filler(f, taxa, 0, "picture")], True)]
    else:
        ef.tracks = [_trilha_interna(f, T, taxa, 1, [T._filler(f, taxa, dur, "picture")], True)] + [
            _trilha_interna(f, T, taxa, i + 2, [T._filler(f, taxa, 0, "picture")] + comps
                            + [T._filler(f, taxa, 0, "picture")], False) for i, comps in enumerate(trilhas)]
    return ef


def _montar_colapsado(nome: str, params_frente: dict, params_verde: dict, recipiente_mosaico: str = "EFF_SUBMASTER",
                     prazo: float = 60) -> str:
    """A MESMA sequência do B21, mas já COLAPSADA pela escrita (o caminho Nest do Premiere → Collapse do Avid): na V2 o
    Collapse dos sequenciais (Submaster) e o do mosaico (`recipiente_mosaico`: Submaster, ou o Flop =
    "EFF2_BLEND_FLIP_HORZ" — um efeito aplicado sobre o Collapse vira o recipiente). Moldes: o que o MC gravou na
    LAB_B21_v4 (Submaster) e na LAB_B21_v5 (Flop)."""
    import avb
    T = A._timeline()
    sys.path.insert(0, A.ASSIST)
    from cicloassist.avid.atributos import copiar_atributos
    moldes = {"EFF_SUBMASTER": "LAB_B21_v4", "EFF2_BLEND_FLIP_HORZ": "LAB_B21_v5"}
    with A.mc() as m:
        try:
            m.fechar_bin(BIN)
        except Exception:                           # noqa: BLE001
            pass
        temporario = BIN + ".novo"
        with avb.open(BIN) as f:
            masters = {mm.name: mm for mm in f.content.mobs if mm.mob_type == "MasterMob"}
            ids = {k: str(masters[v].mob_id) for k, v in MASTERS.items()}
            taxa = masters[MASTERS["FUNDO"]].edit_rate
            pip = _molde(f, "EFF2_BLEND_PIP")
            sub = _molde_em(f, moldes["EFF_SUBMASTER"], "EFF_SUBMASTER")
            rec = _molde_em(f, moldes[recipiente_mosaico], recipiente_mosaico)
            comp = T.montar_timeline(f, nome, [T.Entrada(mob_id=ids["FUNDO"], duracao=TOTAL,
                                                         trilhas=(("picture", 1),), start_time=0)], taxa)
            seq_col = _colapso(f, T, taxa, sub, 48, [[_fonte(f, T, taxa, ids["FRENTE"], 0, 24),
                                                     _fonte(f, T, taxa, ids["VERDE"], 24, 24)]])
            mos_col = _colapso(f, T, taxa, rec, 96, [[_com_efeito(f, T, taxa, pip, ids["FRENTE"], 48, 96, params_frente)],
                                                    [_com_efeito(f, T, taxa, pip, ids["VERDE"], 48, 96, params_verde)]])
            for indice, comps in ((2, [T._filler(f, taxa, 0, "picture"), seq_col, mos_col]),
                                  (3, [T._filler(f, taxa, TOTAL, "picture")])):
                seq = f.create.Sequence(taxa, "picture")
                seq.components = comps
                seq.components.append(T._trail_filler(f, taxa, "picture", seq.components, TOTAL))
                tr = f.create.Track()
                tr.index, tr.component, tr.lock_number = indice, seq, 0
                tr.filler_proxy = T._referencia_de_track(f, taxa, "picture")
                tr.session_attr = T._atributos(f, _ENBLSTATE=1, _MONSTATE=1)
                comp.tracks.insert(indice - 1, tr)
            f.write(temporario)
        copiar_atributos(BIN, temporario)
        os.replace(temporario, BIN)
        m.abrir_bin(BIN)
        fim = time.time() + prazo
        while time.time() < fim:
            for it in m.itens_de(BIN, flags=("AllTypes",)):
                if it.name == nome:
                    return it.mob_id
            time.sleep(2)
    raise RuntimeError(f"a sequência {nome!r} não apareceu na bin")


#: DoCommand (banco, docommand-comandos.md); V1/V2/V3 LIGAM/DESLIGAM a seleção da trilha; 1039 tira tudo (trilhas também)
CMD = {"inicio": 6102, "mais8": 6236, "mais1": 6207, "in": 6209, "out": 6210, "collapse": 6251, "nada": 1039,
       1: 6231, 2: 6230, 3: 6176, "A1": 6232, "A2": 6233}


def _ir(m, quadro: int) -> None:
    from . import avid_efeitos as E
    E.comando(m, CMD["inicio"]); time.sleep(0.4)
    for _ in range(quadro // 8):
        E.comando(m, CMD["mais8"]); time.sleep(0.15)
    for _ in range(quadro % 8):
        E.comando(m, CMD["mais1"]); time.sleep(0.15)
    time.sleep(0.4)
    tc = E.tc_da_agulha(m)
    if E._tc_quadros(tc, 24) - E._tc_quadros("01:00:00:00", 24) != quadro:
        raise RuntimeError(f"a agulha foi para {tc}, não para o quadro {quadro}")


#: os seletores de trilha (MC 25.6, 2026-10-12): cada LINHA de trilha tem, da esquerda para a direita, a caixa VERDE
#: da trilha da FONTE (só com fonte carregada — e ela EMPURRA o resto para a direita), a caixa do NOME da trilha da
#: sequência (cinza (48, 48, 48) ou AZUL (48, 89, 122) = selecionada), o cadeado e o botão de MONITOR (sempre azul).
#: ⛔ Posição fixa não serve: muda com o nº de trilhas e com a fonte carregada (a taxa mista quebrou a leitura de
#: x=105 e y fixos medida no B21). A leitura acha as linhas pelo padrão.
CINZA, AZUL, VERDE_FONTE = (48, 48, 48), (48, 89, 122), (43, 112, 92)


def _perto(c, alvo, tol=12) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(c, alvo))


def maximizada(h: int) -> None:
    """⛔ As posições lidas na tela (seletores de trilha) valem para a janela principal MAXIMIZADA. Reaberto depois de
    uma queda, o MC voltou com a janela solta (5, 19, 1925, 1039) e o 2º Collapse da v8 leu a seleção no lugar
    errado e colapsou só a V1 (2026-10-12). Maximiza e confere."""
    import ctypes
    from . import interface_win as I
    def cobre(r):                                          # (0, 0, 1920, 1020) ou (-9, -9, 1929, 1029): os dois são
        return r[0] <= 0 and r[1] <= 0 and r[2] >= 1920 and r[3] >= 1020     # "maximizada" (borda fora da tela)
    if not cobre(I.retangulo(h)):
        ctypes.windll.user32.ShowWindow(h, 3)                 # SW_MAXIMIZE
        time.sleep(1.5)
    if not cobre(I.retangulo(h)):
        raise RuntimeError(f"a janela do MC não maximizou: {I.retangulo(h)}")


def linhas_de_trilha(h: int) -> list[dict]:
    """As linhas de trilha da timeline, de CIMA para BAIXO: [{y, x, selecionada}] (y/x da caixa do nome, na TELA).
    Uma linha = uma faixa de y onde, varrendo da esquerda, depois da caixa verde da fonte (se houver) vem uma caixa
    cinza ou azul de ≥ 25 px e, até 90 px adiante, o botão azul de monitor."""
    from PIL import Image
    from . import vigia_windows as V
    from . import interface_win as I
    im = Image.open(V.fotografar(h, os.path.join(SAIDA, "tl.bmp"))).convert("RGB")
    ox, oy = -I.retangulo(h)[0], -I.retangulo(h)[1]       # a foto é da JANELA (maximizada: começa em -9, -9)
    achadas = []
    for y in range(780, 1005):
        x, caixa = 40, None
        while x < 420:
            c = im.getpixel((x + ox, y + oy))
            cinza, azul = _perto(c, CINZA, 3), _perto(c, AZUL, 6)
            if cinza or azul:
                x0 = x
                while x < 420 and _perto(im.getpixel((x + ox, y + oy)), c, 3):
                    x += 1
                if x - x0 >= 25:
                    adiante = [im.getpixel((xx + ox, y + oy)) for xx in range(x, min(x + 90, 420))]
                    if any(_perto(a, AZUL, 6) for a in adiante):
                        caixa = ((x0 + x) // 2, azul)
                        break
            x += 1
        if caixa:
            if achadas and y - achadas[-1]["y1"] <= 2 and abs(achadas[-1]["x"] - caixa[0]) < 10:
                achadas[-1]["y1"] = y
                achadas[-1]["azul"].append(caixa[1])
            else:
                achadas.append({"y0": y, "y1": y, "x": caixa[0], "azul": [caixa[1]]})
    return [{"y": (a["y0"] + a["y1"]) // 2, "x": a["x"], "selecionada": sum(a["azul"]) > len(a["azul"]) / 2}
            for a in achadas if a["y1"] - a["y0"] >= 8]


def trilhas_selecionadas(h: int, nv: int | None = None) -> set:
    """As trilhas selecionadas: 1, 2… = V1, V2…; "A1", "A2"… = áudio. As linhas vêm V_n…V1, TC, A1…; `nv` = nº de
    trilhas de vídeo (sem ele, supõe sequência sem áudio)."""
    linhas = linhas_de_trilha(h)
    nv = len(linhas) - 1 if nv is None else nv
    nomes = list(range(nv, 0, -1)) + ["TC"] + [f"A{i}" for i in range(1, len(linhas) - nv)]
    if len(nomes) != len(linhas):
        raise RuntimeError(f"achei {len(linhas)} linhas de trilha; esperava {len(nomes)}")
    return {n for n, l in zip(nomes, linhas) if l["selecionada"] and n != "TC"}


def selecionar(m, h: int, trilhas: tuple, nv: int | None = None) -> None:
    """Só `trilhas` selecionadas. ⛔ O DoCommand 1039 (Deselect All) NÃO tira a seleção das trilhas e os comandos
    V1/V2/V3 INVERTEM o estado (2026-10-12: o 1º Collapse do B21 saiu em V1+V3) — por isso: ler pela foto, inverter
    só o que difere, conferir."""
    from . import avid_efeitos as E
    # ⚠️ a tela demora a mostrar a troca: reler cedo demais viu o estado velho e inverteu de novo (v4: as três ficaram
    # selecionadas). Esperar 1 s depois de cada comando.
    for _ in range(3):
        time.sleep(1.0)
        agora = trilhas_selecionadas(h, nv)
        if agora == set(trilhas):
            return
        for t in agora ^ set(trilhas):
            E.comando(m, CMD[t]); time.sleep(1.0)
    raise RuntimeError(f"não consegui deixar só {trilhas} selecionadas (estão {trilhas_selecionadas(h, nv)})")


def _colapsar(mob_id: str, inicio: int, fim: int, trilhas: tuple[int, ...]) -> None:
    """O Collapse PELO MC: a sequência na Record, só `trilhas` selecionadas, IN em `inicio`, OUT em `fim` (inclusive),
    DoCommand Collapse. Quem chama confere o resultado pela foto e pela bin."""
    from . import avid_efeitos as E
    from . import interface_win as I
    E.carregar(mob_id); time.sleep(1.5)
    h = A.principal()
    if not I.frente(h):
        raise RuntimeError("o MC não veio para a frente")
    maximizada(h)
    with A.mc() as m:
        selecionar(m, h, trilhas)
        _ir(m, inicio)
        E.comando(m, CMD["in"]); time.sleep(0.3)
        _ir(m, fim)
        E.comando(m, CMD["out"]); time.sleep(0.3)
        E.comando(m, CMD["collapse"]); time.sleep(2)


def render(mob_id: str, nome: str) -> str:
    A.instalar_preset("23.976")
    return A.exportar(mob_id, SAIDA, nome)


CORES = {"FUNDO": (32, 32, 96), "FRENTE": (176, 64, 32), "VERDE": (32, 144, 64)}


def quem(rgb) -> str:
    """A placa mais perto da cor do pixel (ou '?' se nenhuma está perto)."""
    d = {k: sum((a - b) ** 2 for a, b in zip(rgb, c)) for k, c in CORES.items()}
    k = min(d, key=d.get)
    return k if d[k] < 40 ** 2 else "?"


def faixas(linha) -> list[tuple[int, int, str]]:
    """[(x0, x1, placa)] ao longo de uma linha da imagem (numpy (W, 3))."""
    out, x0, atual = [], 0, quem(linha[0])
    for x in range(1, len(linha)):
        q = quem(linha[x])
        if q != atual:
            out.append((x0, x - 1, atual))
            x0, atual = x, q
    out.append((x0, len(linha) - 1, atual))
    return out


def montar(*a, **k):
    """`_montar` sob o cão de guarda do piloto (prazo, queda, diálogos, MC num projeto)."""
    return A.guardado(lambda: _montar(*a, **k), 180)


def montar_colapsado(*a, **k):
    """`_montar_colapsado` sob o cão de guarda do piloto (prazo, queda, diálogos, MC num projeto)."""
    return A.guardado(lambda: _montar_colapsado(*a, **k), 180)


def colapsar(*a, **k):
    """`_colapsar` sob o cão de guarda do piloto (prazo, queda, diálogos, MC num projeto)."""
    return A.guardado(lambda: _colapsar(*a, **k), 120)
