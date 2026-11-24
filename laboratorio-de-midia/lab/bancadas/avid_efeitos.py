"""Bancada de EFEITOS do Media Composer (piloto, 2026-10-11 — ideia do autor): o laboratório monta a timeline e aplica
os efeitos da Effect Palette sozinho; a bin salva diz o que entrou (o id EFF2_ e os parâmetros nomeados)."""
from __future__ import annotations

import os
import re
import sys

from . import avid as A


def efeitos_da_sequencia(bin_avb: str, nome: str) -> list[dict]:
    """Os segmentos de VÍDEO da sequência `nome` com os efeitos que o leitor do De Lá Pra Cá acha neles (a bin precisa
    estar salva no disco: `fechar_bin` antes)."""
    for p in (os.path.join(A.DLPC, "motor"),):
        if p not in sys.path:
            sys.path.insert(0, p)
    from avb_bin.segmentos import ler_timeline_de_arquivo
    leitura = ler_timeline_de_arquivo(bin_avb, nome=nome)
    return [{"tc": s.get("timeline_tc_in"), "dur": s.get("duration_frames"),
             "efeitos": [{k: e.get(k) for k in ("name", "effect_id", "category", "params")} for e in s.get("effects") or []]}
            for s in leitura["segments"] if not s.get("is_audio") and not s.get("is_gap")]


# ── a Effect Palette (encaixada à esquerda da janela principal, MC 25.6, 1920×1020, medido 2026-10-11) ─────────────
#: as linhas das duas listas (categorias à esquerda, efeitos à direita), em pixels da janela principal
LINHA = 18.85
CATEGORIA_X, CATEGORIA_Y0 = 60, 133           # "All" (a 1ª categoria)
EFEITO_X, EFEITO_Y0 = 275, 134                # a 1ª linha da lista de efeitos
VK_CTRL, VK_0, VK_8, VK_T, VK_G = 0x11, 0x30, 0x38, 0x54, 0x47
CMD_INICIO, CMD_PROXIMO_CORTE, CMD_MARCAR_CLIPE = 6102, 6240, 6211   # Go to Start, Go to Next Event, Mark Clip (T)
CMD_DESSELECIONAR, CMD_V1 = 1039, 6231                 # Deselect-All (tira as trilhas também), V1 (liga/desliga)


def comando(m, cmd: int, prazo: float = 10) -> None:
    """`DoCommand` esperando o anterior: ele é ASSÍNCRONO e um segundo em seguida volta "Can't start more than one
    command on time." (ErrorType 73, medido 2026-10-11) — tenta de novo até o prazo."""
    import time
    fim = time.time() + prazo
    while True:
        try:
            m._chamar("DoCommand", _timeout=30, commandId=cmd)
            return
        except Exception as e:                # noqa: BLE001
            if "more than one command" not in str(e) or time.time() > fim:
                raise
            time.sleep(0.2)


def contar_efeitos(foto) -> int:
    """Quantas linhas a lista de efeitos tem (texto claro na coluna dos nomes), pela foto da janela."""
    from PIL import Image
    im = Image.open(foto).convert("L")
    n = 0
    while True:
        y = int(EFEITO_Y0 + n * LINHA)
        faixa = im.crop((EFEITO_X - 10, y - 6, EFEITO_X + 120, y + 6))
        if y > 700 or max(faixa.getdata()) < 120:
            return n
        n += 1


#: a timeline (janela principal 1920×1020, MC 25.6, medido 2026-10-11): a régua (a agulha é uma coluna ciano) e a linha
#: da V1 (clipe MARCADO = azul-acinzentado, sem marca = verde-azulado)
REGUA_Y, V1_Y, TL_X0, TL_X1 = 776, 846, 150, 1820   # a agulha = um par de linhas com a largura de um quadro: vale a esquerda
COR_MARCADO, COR_CLIPE = (96, 141, 175), (32, 131, 143)
PRAZO_RASTREIO, ESTAVEL_RASTREIO = 300, 5   # s: o rastreio do Stabilize num clipe curto; parado = acabou
FAIXA_VAZIA_Y = 800            # a faixa cinza entre a régua e a V1: o clique ali tira a seleção do segmento


def janela_mc() -> int:
    """A janela principal do MC pelo TÍTULO ("Avid Media Composer - <projeto>"): o `principal()` às vezes devolvia um
    popup de 160×156 (2026-10-11)."""
    import ctypes
    from ctypes import wintypes
    achada = []
    u = ctypes.windll.user32

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cada(hwnd, _l):
        b = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(hwnd, b, 256)
        if b.value.startswith("Avid Media Composer - ") and u.IsWindowVisible(hwnd):
            achada.append(hwnd)
        return True
    u.EnumWindows(cada, 0)
    return achada[0] if achada else A.principal()


def tc_da_agulha(m) -> str | None:
    """O TC da agulha na Record, pela API (`GetViewerMobs` → `current_timecode`; medido 2026-10-11)."""
    for v in m._chamar("GetViewerMobs").body.mobs:
        if v.view_type == 1 or str(v.view_type).endswith("Record") or "Record" in str(v):
            return v.current_timecode
    return None


def _tc_quadros(tc: str, base: int) -> int:
    h, mi, s, f = (int(x) for x in tc.replace(";", ":").split(":"))
    return ((h * 60 + mi) * 60 + s) * base + f


def carregar(mob_id: str) -> None:
    """A sequência na Record (e as bins soltas afastadas da timeline). Já carregada = o MC responde "Some mobs was
    skipped." — conferido pelo GetViewerMobs."""
    A.afastar_bins()
    with A.mc() as m:
        try:
            m.carregar_no_monitor([mob_id], "Record")
        except Exception as e:                # noqa: BLE001
            if "skipped" not in str(e) or not any(v.mob_id == mob_id for v in m._chamar("GetViewerMobs").body.mobs):
                raise


def ler_timeline(h: int, pasta: str) -> tuple[int | None, tuple[int, int] | None]:
    """(x da agulha, (x0, x1) do trecho MARCADO na V1 ou None), lidos da foto da janela."""
    from PIL import Image
    from . import vigia_windows as V
    im = Image.open(V.fotografar(h, os.path.join(pasta, "tl.bmp"))).convert("RGB")
    agulha = next((x for x in range(TL_X0, TL_X1) if (lambda q: q[0] < 40 and q[1] > 180 and q[2] > 230)(
        im.getpixel((x, REGUA_Y)))), None)
    perto = lambda q, c: sum(abs(a - b) for a, b in zip(q, c)) < 30          # noqa: E731
    xs = [x for x in range(TL_X0, TL_X1) if perto(im.getpixel((x, V1_Y)), COR_MARCADO)]
    return agulha, ((xs[0], xs[-1]) if xs else None)


def aplicar_na_sequencia(n_efeitos: int, categoria_linha: int, fotos: str, inicios: list[int], base: int = 24,
                         passo_a_passo: str | None = None, linhas: list[int] | None = None) -> list[dict]:
    """Com a sequência carregada na timeline (um clipe por efeito) e a paleta visível, o laço ensinado pelo autor
    (2026-10-11), com um PORTÃO em cada passo (a tela confirma antes do seguinte):
    Ctrl+0 (foco na timeline) → T (marca o clipe sob a agulha; a V1 ligada) → [a marca começa na agulha?] → Ctrl+8 (a
    paleta) → duplo-clique no efeito i → Ctrl+0 → Go to Next Event → [a agulha andou?] → T → … O 1º clipe NÃO leva Next
    Event. O MC aceita UM efeito por clipe (outro duplo-clique SUBSTITUI); para empilhar, Alt no duplo-clique.
    ⚠️ O DoCommand volta ANTES de o MC agir (um T logo depois marcava o clipe de onde a agulha ainda não tinha saído):
    por isso os portões olham a tela. Diálogo depois do duplo-clique = foto + Esc + anotado."""
    from . import interface_win as I
    from . import vigia_windows as V
    import time
    h = janela_mc()
    I.frente(h)
    time.sleep(0.8)
    A.sem_dialogos()
    I.tecla(VK_8, VK_CTRL); time.sleep(0.6)
    I.clicar(CATEGORIA_X, int(CATEGORIA_Y0 + categoria_linha * LINHA))
    time.sleep(0.8)
    with A.mc() as m:
        comando(m, CMD_INICIO)
    trabalho = passo_a_passo or fotos
    notas = []
    agulha_antes = None
    for i in range(n_efeitos):
        nota = {"linha": i}
        # Ctrl+0: o DoCommand age na janela que tem o FOCO (com a paleta em foco o Go to Start não fazia nada)
        I.frente(h)
        I.tecla(VK_0, VK_CTRL); time.sleep(0.5)
        if i:
            with A.mc() as m:
                comando(m, CMD_PROXIMO_CORTE)
        # portão 1: a agulha está no 1º quadro do clipe i (TC da Record pela API; 01:00:00:00 + início do clipe)
        alvo = _tc_quadros("01:00:00:00", base) + inicios[i]
        fim = time.time() + 6
        while True:
            with A.mc() as m:
                tc = tc_da_agulha(m)
            if tc and _tc_quadros(tc, base) == alvo:
                break
            if time.time() > fim:
                raise RuntimeError(f"clipe {i}: a agulha está em {tc}, não no quadro {alvo}")
            time.sleep(0.3)
        # portão 2: G (limpa o IN/OUT) + um clique na faixa CINZA vazia da timeline (tira a seleção do segmento que o
        # duplo-clique deixou) → só então o T marca o clipe sob a agulha (autor, 2026-10-11: "só após não haver marca
        # de in e out e nenhum segmento estar selecionado"). O clique é na COLUNA da agulha, para não movê-la — e o TC
        # é conferido de novo depois dele.
        for tentativa in range(4):
            agulha, _ = ler_timeline(h, trabalho)
            I.frente(h)
            I.tecla(VK_0, VK_CTRL); time.sleep(0.3)
            I.tecla(VK_G); time.sleep(0.4)
            I.clicar((agulha or TL_X0) + 4, FAIXA_VAZIA_Y); time.sleep(0.5)
            with A.mc() as m:
                tc = tc_da_agulha(m)
            if not tc or _tc_quadros(tc, base) != alvo:
                raise RuntimeError(f"clipe {i}: o clique na faixa vazia moveu a agulha para {tc}")
            I.tecla(VK_T)
            fim = time.time() + 3
            marca = None
            while time.time() < fim:
                agulha, marca = ler_timeline(h, trabalho)
                if marca and abs(marca[0] - agulha) <= 6:
                    break
                time.sleep(0.3)
            if marca and abs(marca[0] - agulha) <= 6:
                break
        else:
            raise RuntimeError(f"clipe {i}: o T não marcou o clipe da agulha (agulha {agulha}, marca {marca})")
        nota.update({"agulha": agulha, "marca": marca, "tentativas_T": tentativa + 1})
        agulha_antes = agulha
        I.tecla(VK_8, VK_CTRL); time.sleep(0.5)
        # `linhas`: qual efeito da lista vai em cada clipe (padrão: o i-ésimo — um efeito por clipe)
        I.clicar(EFEITO_X, int(EFEITO_Y0 + (linhas[i] if linhas else i) * LINHA), duplo=True)
        time.sleep(1.5)
        abertos = [d for d in V.dialogos(V.AVID) if d["titulo"] not in A.NAO_MODAIS]
        if any(d["titulo"] == "Tracking" for d in abertos):
            # ⛔ O Stabilize RASTREIA ao ser aplicado (autor, 2026-10-11): a janela "Tracking" é o trabalho do efeito,
            # não um aviso — Esc nela deixava o efeito sem o rastreamento. Esperar ela sumir sozinha (com prazo).
            # A janela de Tracking NÃO some ao terminar (é a ferramenta, fica aberta com o Effect Editor — 2026-10-11):
            # o fim do rastreio é ela parar de mudar por `ESTAVEL_RASTREIO` s; só então ela e o Effect Editor fecham.
            from PIL import Image, ImageChops
            jt = next(d["hwnd"] for d in abertos if d["titulo"] == "Tracking")
            inicio, antes, parada = time.time(), None, time.time()
            while time.time() - parada < ESTAVEL_RASTREIO:
                if time.time() - inicio > PRAZO_RASTREIO:
                    raise V.Travado(f"clipe {i}: o rastreamento não parou em {PRAZO_RASTREIO} s",
                                    V.foto_da_tela(fotos, "rastreio"))
                agora = Image.open(V.fotografar(jt, os.path.join(fotos, "tracking.bmp"))).convert("L")
                if antes is None or antes.size != agora.size or ImageChops.difference(antes, agora).getbbox():
                    parada = time.time()
                antes = agora
                time.sleep(1)
            nota["rastreio_s"] = round(time.time() - inicio - ESTAVEL_RASTREIO, 1)
        if abertos:
            nota["dialogos"] = [{"titulo": d["titulo"], "foto": V.fotografar(d["hwnd"], os.path.join(
                fotos, f"efeito_{categoria_linha:02d}_{i:02d}.bmp"))} for d in abertos]
            for d in abertos:
                V.esc(d["hwnd"])
            time.sleep(1)
        notas.append(nota)
    return notas


def efeitos_pelo_nome(bin_avb: str, nome: str, mob_id: str | None = None) -> list[dict]:
    """Os clipes de VÍDEO da sequência com, para cada efeito, o que a BIN guarda: o id EFF2_, e os atributos
    `_EFFECT_PLUGIN_NAME` / `_EFFECT_PLUGIN_CLASS` / `_EFFECT_PLUGIN_TYPE` (o nome e a categoria da paleta)."""
    import avb

    def attrs(o) -> dict:
        a = getattr(o, "attributes", None) or {}
        try:
            return {k: a[k] for k in a if str(k).startswith("_EFFECT")}
        except Exception:                     # noqa: BLE001
            return {}

    fora = []
    with avb.open(bin_avb) as f:
        # pelo MobID quando vier (a bin pode ter duas sequências com o mesmo nome — 2026-10-11); senão a ÚLTIMA
        alvo = None
        if mob_id:
            sys.path.insert(0, os.path.join(A.DLPC, "plugins", "media-composer", "servico"))
            from avid.mcapi import mob_id_para_pyavb
            alvo = mob_id_para_pyavb(mob_id)
        seqs = [m for m in f.content.mobs if (nome is None or m.name == nome) and m.mob_type == "CompositionMob"
                and (alvo is None or m.mob_id.bytes_le.hex() == alvo)]
        seq = seqs[-1]
        trilha = next(t for t in seq.tracks if t.media_kind == "picture")
        pos = 0
        for c in trilha.component.components:
            item = {"inicio": pos, "dur": c.length, "classe": type(c).__name__}
            if type(c).__name__ == "TrackEffect" or hasattr(c, "effect_id"):
                item.update({"effect_id": getattr(c, "effect_id", None), **attrs(c)})
            pos += c.length
            fora.append(item)
    return fora


#: as categorias da aba Filters, na ordem da lista (MC 25.6, lida na tela em 2026-10-11). Fora, a pedido do autor:
#: "All" (tudo junto) e "Color Correction Presets" (o mesmo efeito com parâmetros diferentes — fica para o lab de cor)
CATEGORIAS = ["All", "Blend", "Box Wipe", "Color Correction Presets", "Conceal", "Edge Wipe", "Film", "Generator",
              "Illusion FX", "Image", "Key", "L-Conceal", "Matrix Wipe", "Peel", "PlasmaWipe Avid Borders",
              "PlasmaWipe Avid Center", "PlasmaWipe Avid Horiz", "PlasmaWipe Avid Lava", "PlasmaWipe Avid Paint",
              "PlasmaWipe Avid Techno", "Push", "Reformat", "S3D", "Sawtooth Wipe", "Shape Wipe", "Spin", "Squeeze",
              "Timewarp", "Title", "Xpress 3D Effect"]
FORA = {"All", "Color Correction Presets"}
SAIDA_EFEITOS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                             "saida", "bancadas", "avid", "efeitos")


def rodar_categoria(nome: str, bin_avb: str, master: str, sufixo: str = "") -> dict:
    """Uma categoria inteira: clicar nela → contar os efeitos pela foto → a sequência LAB_EF_<CAT> (um clipe de 24
    quadros do master por efeito) → carregar → aplicar → ler a bin. Grava `<saida>/efeitos/<CAT>.json`."""
    import json
    import time
    from . import interface_win as I
    from . import vigia_windows as V
    linha = CATEGORIAS.index(nome)
    os.makedirs(SAIDA_EFEITOS, exist_ok=True)
    h = janela_mc()
    I.frente(h); time.sleep(0.8)
    A.sem_dialogos()
    I.tecla(VK_8, VK_CTRL); time.sleep(0.6)
    I.clicar(CATEGORIA_X, int(CATEGORIA_Y0 + linha * LINHA)); time.sleep(1)
    n = contar_efeitos(V.fotografar(h, os.path.join(SAIDA_EFEITOS, "paleta.bmp")))
    seq = "LAB_EF_" + re.sub(r"[^A-Z0-9]+", "_", nome.upper()).strip("_") + sufixo
    fora = {"categoria": nome, "linha": linha, "efeitos_na_lista": n, "sequencia": seq, "mob_id": None,
            "lista_cheia": int(EFEITO_Y0 + n * LINHA) > 700}
    if not n:
        fora["erro"] = "nenhum efeito na lista"
    else:
        sid = A.montar_sequencia(bin_avb, seq, [(master, (i * 12) % 216, 24) for i in range(n)])
        fora["mob_id"] = sid                      # a bin pode ter várias sequências com o mesmo nome
        carregar(sid); time.sleep(2)
        t0 = time.time()
        try:
            fora["notas"] = aplicar_na_sequencia(n, linha, SAIDA_EFEITOS, inicios=[i * 24 for i in range(n)])
        except Exception as e:                # noqa: BLE001 — registrado; a categoria seguinte roda
            fora["erro"] = f"{type(e).__name__}: {e}"
            A.sem_dialogos()
        fora["segundos"] = round(time.time() - t0)
        with A.mc() as m:
            m.fechar_bin(bin_avb)
        fora["clipes"] = [{k: c.get(k) for k in ("inicio", "effect_id", "_EFFECT_PLUGIN_NAME", "_EFFECT_PLUGIN_CLASS",
                                                 "_EFFECT_PLUGIN_TYPE")}
                          for c in efeitos_pelo_nome(bin_avb, seq, sid) if c["dur"]]
        with A.mc() as m:
            m.abrir_bin(bin_avb)
    with open(os.path.join(SAIDA_EFEITOS, seq + ".json"), "w", encoding="utf-8") as f:
        json.dump(fora, f, ensure_ascii=False, indent=1, default=str)
    return fora


if __name__ == "__main__":
    # py -m lab.bancadas.avid_efeitos [categoria …]   (sem argumento: todas, menos All e Color Correction Presets)
    BIN = os.path.join(A.PROJETOS, "DLPC LAB 23.976", "DLPC LAB 23.976 Bin.avb")
    for cat in (sys.argv[1:] or [c for c in CATEGORIAS if c not in FORA]):
        r = rodar_categoria(cat, BIN, "B02_2398_MOV-PRORES.mov")
        nomes = [c.get("_EFFECT_PLUGIN_NAME") for c in r.get("clipes", [])]
        print(f"{cat}: {r['efeitos_na_lista']} na lista, {sum(1 for x in nomes if x)} aplicados, "
              f"{r.get('segundos')} s{'  ERRO ' + r['erro'] if r.get('erro') else ''}", flush=True)


def escrever_parametros(bin_avb: str, mob_id: str, valores: dict[int, dict[str, float]]) -> list:
    """Escreve parâmetros nos EFEITOS da sequência (o molde aplicado pelo MC): `valores` = {índice do clipe com
    efeito: {nome AAF do parâmetro (ex. "AFX_SCALE_X_U"): valor}}. O parâmetro que já existe tem o valor trocado; o
    que não existe (o MC só grava o que saiu do padrão) entra como um `ParameterItem` novo, `value_type` 2 (número,
    como num Resize real: escala 130, posição -15/55). A bin precisa estar FECHADA no MC (banco, avb/escrita.md):
    grava ao lado e troca, com o UID preservado."""
    import avb
    from avb.parameter_uuids import PARAMETER_UUIDS
    import uuid as _uuid
    sys.path.insert(0, os.path.join(A.DLPC, "plugins", "media-composer", "servico"))
    from avid.mcapi import mob_id_para_pyavb
    sys.path.insert(0, A.ASSIST)
    from cicloassist.avid.atributos import copiar_atributos
    por_nome = {n: u for u, n in PARAMETER_UUIDS.items()}
    alvo = mob_id_para_pyavb(mob_id)
    temporario = bin_avb + ".novo"
    feito = []
    with avb.open(bin_avb) as f:
        seq = next(m for m in f.content.mobs if m.mob_type == "CompositionMob" and m.mob_id.bytes_le.hex() == alvo)
        tr = next(t for t in seq.tracks if t.media_kind == "picture")
        efeitos = [c for c in tr.component.components if type(c).__name__ == "TrackEffect"]
        for k, params in valores.items():
            te = efeitos[k]
            for nome, v in params.items():
                u = _uuid.UUID(por_nome[nome])
                item = next((p for p in te.param_list if p.uuid == u), None)
                if item is None:
                    item = f.create.ParameterItem()
                    item.uuid, item.value_type, item.name = u, 2, ""
                    item.enable, item.control_track, item.contribs_to_sig = True, None, True
                    te.param_list.append(item)
                item.value = int(v) if float(v).is_integer() else v   # inteiro, como o MC grava (Resize real: 130)
                feito.append((k, nome, v))
        f.write(temporario)
    copiar_atributos(bin_avb, temporario)
    os.replace(temporario, bin_avb)
    return feito


# ── o Effect Editor (catálogo de parâmetros e padrões; autor + bancada, 2026-10-11) ──────────────────────────────────
CMD_EFFECT_EDITOR, VK_W = 1939, 0x57
EDITOR_RET = (395, 0, 441, 1000)         # a janela solta, aumentada: todos os grupos abertos cabem
CATALOGO_EE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avid", "effect_editor")


#: ⛔ Até 2026-10-11 a varredura parava em x=95: letras altas ("t" de "Rgt") passavam pelo detector antigo e um clique
#: levou o Crop Rgt a −999 (desfeito com Ctrl+Z). Com o MOLDE do ▶ (abaixo) a varredura vai até 200 — os subgrupos do
#: Color Correction ("Clip", nível 5) ficam em x≈113; os controles deslizantes começam em x≈159 e não têm o desenho.
SETA_X1 = 200


def _e_seta(pts) -> bool:
    """O MOLDE do ▶ do Effect Editor (MC 25.6, medido nas fotos de 2026-10-11): 9 linhas, BORDA ESQUERDA RETA (todas as
    linhas começam na mesma coluna), largura 2→4→6→7→8→7→6→4→2 — sobe até o meio e desce, simétrica. Nenhuma letra
    tem esse perfil (o "D" é reto à esquerda mas largo em cima; o "t" não é simétrico). O ▶ do editor de PINTURA é
    outro desenho, apagado (cinza 110): 12 linhas, 1→1→2→3→5→6→6→5→3→2→1→1 — o mesmo molde aceita os dois."""
    linhas: dict[int, list[int]] = {}
    for px, py in pts:
        linhas.setdefault(py, []).append(px)
    ys = sorted(linhas)
    if not 7 <= len(ys) <= 13 or ys[-1] - ys[0] + 1 != len(ys):
        return False
    esq = [min(linhas[y]) for y in ys]
    larg = [max(linhas[y]) - min(linhas[y]) + 1 for y in ys]
    if max(esq) - min(esq) > 1 or larg[0] > 3 or larg[-1] > 3 or not 5 <= max(larg) <= 10:
        return False
    # o pico: no terço do meio (o ▶ apagado sai com a suavização torta: 1-2-3-5-5-6-5-3-2-2-1 no Blur, 2026-10-11)
    meio = larg.index(max(larg))
    if not len(larg) // 3 <= meio <= len(larg) - 1 - len(larg) // 3:
        return False
    sobe = all(b >= a for a, b in zip(larg[:meio + 1], larg[1:meio + 1]))
    desce = all(b <= a for a, b in zip(larg[meio:], larg[meio + 1:]))
    simetrica = all(abs(larg[i] - larg[-1 - i]) <= 2 for i in range(len(larg)))
    return sobe and desce and simetrica


def _setas_fechadas(foto) -> list[tuple[int, int]]:
    """As setas ▶ (grupo FECHADO) da coluna da árvore do Effect Editor, pelo molde (`_e_seta`). Varre x 30–200 (os
    níveis da árvore) e a altura toda."""
    from PIL import Image
    rgb = Image.open(foto).convert("RGB")
    im = rgb.convert("L")
    w, h = im.size
    claro = lambda x, y: im.getpixel((x, y)) > 70            # noqa: E731 — as ▶ do editor de pintura são apagadas (70–110)
    vistos, fora = set(), []
    # desde o topo da lista: rolada, a 1ª linha pode ser um grupo fechado (Spot Color, "Luma Clip" em y≈36); o ícone
    # colorido do título não passa pelo `neutra` nem pelo molde
    for y in range(20, h - 40):
        for x in range(30, min(SETA_X1, w)):
            if (x, y) in vistos or not claro(x, y):
                continue
            pilha, pts = [(x, y)], []
            while pilha:
                p = pilha.pop()
                if p in vistos or not (30 <= p[0] < min(SETA_X1, w) and 0 <= p[1] < h) or not claro(*p):
                    continue
                vistos.add(p); pts.append(p)
                pilha += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            cor = [rgb.getpixel(p) for p in pts]
            neutra = sum(max(c) - min(c) for c in cor) / len(cor) < 25        # a seta é CINZA; o ícone do efeito, não
            if neutra and _e_seta(pts):
                fora.append(((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2))
    return fora


#: a barra de rolagem da janela aumentada (x≈379): o clique na FAIXA passa uma página; nunca a roda do mouse — sobre um
#: controle deslizante do Qt ela muda o VALOR do parâmetro
BARRA_X, BARRA_TOPO_Y, BARRA_PE_Y = 379, 52, 938


def _rolar(ee: int, para_baixo: bool, tmp: str) -> bool:
    """Uma página para baixo (ou para cima) pela faixa da barra. Devolve se a lista MUDOU (False = já estava no fim)."""
    import time
    from PIL import ImageChops, Image
    from . import interface_win as I
    from . import vigia_windows as V
    antes = Image.open(V.fotografar(ee, tmp)).convert("L").crop((30, 20, 375, 960))
    I.frente(ee)
    I.clicar(*I.relativo(ee, BARRA_X, BARRA_PE_Y if para_baixo else BARRA_TOPO_Y))
    time.sleep(0.5)
    depois = Image.open(V.fotografar(ee, tmp)).convert("L").crop((30, 20, 375, 960))
    return ImageChops.difference(antes, depois).getbbox() is not None


class SemParametros(RuntimeError):
    """O Effect Editor abriu sem nenhum controle (Flip, Flop: efeitos sem parâmetro)."""


def _abrir_grupos(ee: int, tmp: str) -> int:
    """Abre todas as ▶ VISÍVEIS (a mais de baixo primeiro, para as de cima não mudarem de lugar). Devolve quantas."""
    import time
    from . import interface_win as I
    from . import vigia_windows as V
    antes = None
    for k in range(60):
        setas = _setas_fechadas(V.fotografar(ee, tmp))
        if not setas:
            return k
        x, y = max(setas, key=lambda s: s[1])
        if antes is not None and abs(x - antes[0]) <= 2 and abs(y - antes[1]) <= 2:
            # freio: a MESMA seta continua fechada — o clique não abriu nada; parar antes de clicar no que não é seta.
            # (O NÚMERO de setas pode crescer: um grupo aberto mostra subgrupos fechados — Color Correction.)
            raise RuntimeError(f"o clique não abriu o grupo em {antes}: foto em {tmp}")
        antes = (x, y)
        I.frente(ee)
        I.clicar(*I.relativo(ee, x, y))
        time.sleep(0.5)
    raise RuntimeError(f"mais de 60 grupos abertos sem acabar: foto em {tmp}")


def fotografar_editor(nome_foto: str) -> list[str]:
    """Com o clipe marcado: abre o Effect Editor, aumenta a janela, abre TODOS os grupos — página a página, rolando pela
    barra até o fim — e volta ao topo para fotografar as PÁGINAS em `avid/effect_editor/<nome_foto>[_pN].png` (uma só =
    sem sufixo). Sai com Ctrl+W. Devolve os caminhos das fotos."""
    import ctypes
    import time
    from PIL import Image
    from . import interface_win as I
    from . import vigia_windows as V
    with A.mc() as m:
        comando(m, CMD_EFFECT_EDITOR)
    fim = time.time() + 8
    ee = None
    while time.time() < fim and ee is None:
        ee = next((d["hwnd"] for d in V.dialogos(V.AVID) if d["titulo"] == "Effect Editor"), None)
        time.sleep(0.3)
    if ee is None:
        raise RuntimeError("o Effect Editor não abriu")
    ctypes.windll.user32.MoveWindow(ee, *EDITOR_RET, True)
    time.sleep(0.8)
    tmp = os.path.join(SAIDA_EFEITOS, "ee.bmp")
    # 1) abrir tudo, em PASSADAS do topo ao fim, até uma passada não abrir nada: abrir um grupo empurra o resto para
    #    fora da janela (Color Correction: a foto única perdia o fim), e o editor de PINTURA ROLA SOZINHO ao abrir um
    #    grupo — os de cima saem da vista (Spot Color, 2026-10-11: Acceleration/Tracking/Luma Range ficaram fechados)
    for passada in range(6):
        for _ in range(30):                         # ao topo
            if not _rolar(ee, False, tmp):
                break
        abertos = 0
        for _ in range(30):
            abertos += _abrir_grupos(ee, tmp)
            if not _rolar(ee, True, tmp):
                break
        if not abertos:
            break
    else:
        raise RuntimeError(f"6 passadas e ainda há grupo abrindo: foto em {tmp}")
    # 2) de volta ao topo
    for _ in range(30):
        if not _rolar(ee, False, tmp):
            break
    # ⛔ foto VAZIA = o clipe não tem efeito (2026-10-11: uma LAB_EF_IMAGE antiga, sem efeitos, deu 19 fotos vazias)
    cheio = sum(1 for p in Image.open(V.fotografar(ee, tmp)).convert("L").crop((30, 20, 380, 1000)).getdata() if p > 120)
    if cheio < 400:
        I.frente(ee); I.tecla(VK_W, VK_CTRL); time.sleep(1)
        raise SemParametros("o Effect Editor abriu VAZIO: o efeito não tem parâmetros (Flip, Flop) — ou o clipe não "
                            "tem efeito")
    # 3) as páginas, descendo
    os.makedirs(CATALOGO_EE, exist_ok=True)
    paginas = [Image.open(V.fotografar(ee, tmp)).convert("RGB")]
    for _ in range(30):
        if not _rolar(ee, True, tmp):
            break
        paginas.append(Image.open(tmp).convert("RGB"))
    # o editor de pintura tem linhas VAZIAS embaixo: página sem texto não vai para o catálogo
    texto = lambda f: sum(1 for p in f.convert("L").crop((30, 20, 375, 960)).getdata() if p > 120)   # noqa: E731
    while len(paginas) > 1 and texto(paginas[-1]) < 40:          # a página só com o "Spin" do pincel tem ~100
        paginas.pop()
    destinos = []
    for k, foto in enumerate(paginas, 1):
        destino = os.path.join(CATALOGO_EE, nome_foto + (f"_p{k}" if len(paginas) > 1 else "") + ".png")
        foto.save(destino)
        destinos.append(destino)
    I.frente(ee); time.sleep(0.3)
    I.tecla(VK_W, VK_CTRL)                               # Ctrl+W: fecha o editor e SAI do modo de efeito (autor)
    time.sleep(1.2)
    return destinos


#: o freio só pega uma QUEDA: com o MC aberto esta máquina (16 GB) fica com 0,3–0,7 GB disponíveis já recém-reiniciada
#: (2026-10-11, 21h15: o MC residente 1,1 GB, o resto travado fora do processo — cache de vídeo pelo driver?), e foi
#: assim que a categoria Image e as 20 categorias de aplicação rodaram
MEMORIA_MINIMA_MB = 200
#: ⚠️ O MC 25.6 RESERVA ~11,4 GB de memória privada AO ABRIR (2026-10-11: 11,8 GB depois de 1h30 de bancada e 11,3 GB
#: um minuto depois de reaberto — não é inchaço do uso, reabrir não solta nada). Residente fica 0,6–0,9 GB; o resto vai
#: para a paginação. Numa máquina de 16 GB com o Windows ligado há 27 h (pool não paginado 1,3 GB) sobraram 0,2–0,3 GB.


def memoria_livre_mb() -> int:
    import ctypes

    class _M(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + \
                   [(n, ctypes.c_ulonglong) for n in ("tot", "livre", "pt", "plivre", "vt", "vlivre", "ext")]
    m = _M(); m.dwLength = ctypes.sizeof(_M)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return int(m.livre // 2**20)


def catalogar_categorias(sequencias: dict[str, dict], pular: tuple[str, ...] = ()) -> None:
    """O Effect Editor de TODAS as sequências LAB_EF_* (`sequencias` = {nome: {mob_id, nomes}}, tirado da bin): uma
    por vez, o resultado de cada uma em `saida/bancadas/avid/efeitos/catalogo_<CAT>.json` ao terminar (a rodada pode
    cair no meio). Já feita (o JSON existe) = pulada. Para com memória livre < `MEMORIA_MINIMA_MB`."""
    import json
    import time
    for nome, s in sequencias.items():
        cat = nome.removeprefix("LAB_EF_")
        destino = os.path.join(SAIDA_EFEITOS, f"catalogo_{cat}.json")
        if cat in pular or os.path.exists(destino) or not s.get("mob_id"):
            continue
        livre = memoria_livre_mb()
        if livre < MEMORIA_MINIMA_MB:
            print(f"PARADO: memória disponível {livre} MB < {MEMORIA_MINIMA_MB}", flush=True)
            return
        t0 = time.time()
        n = len(s["nomes"]) or s.get("n", 0)
        r = catalogar_sequencia(s["mob_id"], n, cat, s["nomes"])
        # ⚠️ Um diálogo do MC (2026-10-12: o aviso de "Keyboard Input Locale") deixa a API em "Media composer is
        # Busy" e TODO clipe falha: categoria sem nenhuma foto não ganha o JSON (senão a retomada a pularia) e a rodada
        # para — seguir só repetiria a falha nas outras
        if r and all(i.get("erro") for i in r):
            print(f"PARADO em {cat}: todos os clipes falharam — {r[0]['erro'][:160]}", flush=True)
            return
        json.dump({"sequencia": nome, "mob_id": s["mob_id"], "segundos": round(time.time() - t0), "clipes": r},
                  open(destino, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        erros = [(i["nome"], i["erro"][:80]) for i in r if i.get("erro")]
        print(f"{cat}: {len(r)} clipes, {sum(len(i.get('fotos', [])) for i in r)} fotos, "
              f"{round(time.time() - t0)} s, livre {memoria_livre_mb()} MB, erros {erros}", flush=True)


def catalogar_sequencia(mob_id: str, n: int, prefixo: str, nomes: list[str], base: int = 24,
                        so: list[int] | None = None) -> list[dict]:
    """Para cada clipe da sequência (um efeito por clipe, 24 quadros): agulha no clipe [portão: TC pela API] → G +
    clique na faixa vazia + T [portão: a marca] → `fotografar_editor` → Ctrl+W. Erro num clipe é registrado, o editor
    é fechado e o laço segue. `so` = só esses clipes (refazer os parciais)."""
    import time
    from . import interface_win as I
    from . import vigia_windows as V
    carregar(mob_id); time.sleep(2)
    h = janela_mc()
    fora = []
    for i in range(n):
        if so is not None and i not in so:
            continue
        item = {"clipe": i, "nome": nomes[i] if i < len(nomes) else None}
        try:
            I.frente(h); time.sleep(0.4)
            I.tecla(VK_0, VK_CTRL); time.sleep(0.4)
            with A.mc() as m:
                comando(m, CMD_INICIO)
                time.sleep(0.6)
                for _ in range(i):
                    comando(m, CMD_PROXIMO_CORTE)
                    time.sleep(0.4)
            alvo = _tc_quadros("01:00:00:00", base) + i * 24
            fim = time.time() + 6
            while True:
                with A.mc() as m:
                    tc = tc_da_agulha(m)
                if tc and _tc_quadros(tc, base) == alvo:
                    break
                if time.time() > fim:
                    raise RuntimeError(f"a agulha está em {tc}")
                time.sleep(0.3)
            I.tecla(VK_G); time.sleep(0.3)
            agulha, _ = ler_timeline(h, SAIDA_EFEITOS)
            I.clicar((agulha or TL_X0) + 4, FAIXA_VAZIA_Y); time.sleep(0.4)
            I.tecla(VK_T); time.sleep(0.8)
            agulha, marca = ler_timeline(h, SAIDA_EFEITOS)
            if not (marca and abs(marca[0] - agulha) <= 6):
                raise RuntimeError(f"a marca não está no clipe (agulha {agulha}, marca {marca})")
            nome = re.sub(r"[^A-Za-z0-9]+", "_", item["nome"] or f"clipe{i}").strip("_")
            item["fotos"] = fotografar_editor(f"{prefixo}_{i:02d}_{nome}")
        except SemParametros:
            item["sem_parametros"] = True
        except Exception as e:                    # noqa: BLE001 — registrado; o próximo clipe segue
            item["erro"] = f"{type(e).__name__}: {e}"
            for d in V.dialogos(V.AVID):
                if d["titulo"] == "Effect Editor":
                    I.frente(d["hwnd"]); I.tecla(VK_W, VK_CTRL); time.sleep(1)
        fora.append(item)
    return fora
