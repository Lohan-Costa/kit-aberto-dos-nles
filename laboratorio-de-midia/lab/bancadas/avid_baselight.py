"""BL01 no Media Composer (Mac): os "originais de câmera" sintéticos da receita `receitas/baselight/BL01_CONFORM.json`
linkados (AMA) num projeto do MC, a sequência de teste montada na bin e o AAF exportado — o kit K1 da missão Baselight
(`2 ATIVOS/_CICLO ASSIST/docs/plano/2026-11-21-baselight.md`).

    (o MC aberto no projeto LAB BASELIGHT 2398 — ou, com LAB_BL_TAXA=2997DF, no LAB BASELIGHT 2997DF)
    <conformar>/.venv/bin/python -m lab.bancadas.avid_baselight linkar|montar|exportar
"""
from __future__ import annotations

import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFORMAR = os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar")
ASSIST = os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_CICLO ASSIST")
MIDIA = os.path.join(RAIZ, "saida", "baselight", "BL01_CONFORM")

#: A TAXA da rodada (variável LAB_BL_TAXA): "2398" (padrão) ou "2997DF" (os originais D1/D2 da receita, cujo TC passa
#: por 15:00:00;00 e 15:10:00;00 — DÉCIMOS minutos, que NÃO pulam — e o D3, C002C001, por 15:01:00;02, logo depois
#: do pulo dos rótulos ;00 e ;01).
TAXA = os.environ.get("LAB_BL_TAXA", "2398")
CFG = {
    "2398": {"projeto": "LAB BASELIGHT 2398", "pasta": "ORIGINAIS_2398", "fps": 24000 / 1001, "fps_txt": "23.976",
             "b": 24, "df": False, "fle_fps": "24", "trabalho": "avid_baselight", "preset": "DLPC_LAB_DNXLB",
             "originais": ["ORIGINAIS_2398/DIA01/A001/A001C001_251121_R1AB_MOV-PRORES.mov",
                           "ORIGINAIS_2398/DIA01/A001/A001C002_251121_R1AB_MOV-PRORES.mov",
                           "ORIGINAIS_2398/DIA01/B001/B001C001_251121_R2CD_MOV-PRORES.mov",
                           "ORIGINAIS_2398/DIA01/C001/C001C001_251121_R3EF_MOV-PRORES.mov"]},
    "2997DF": {"projeto": "LAB BASELIGHT 2997DF", "pasta": "ORIGINAIS_2997DF", "fps": 30000 / 1001, "fps_txt": "29.97",
               "b": 30, "df": True, "fle_fps": "30DF", "trabalho": "avid_baselight_2997DF",
               "preset": "DLPC_LAB_DNXLB_2997",
               "originais": ["ORIGINAIS_2997DF/DIA02/A002/A002C001_251121_R1AB_MOV-PRORES.mov",
                             "ORIGINAIS_2997DF/DIA02/B002/B002C001_251121_R2CD_MOV-PRORES.mov",
                             "ORIGINAIS_2997DF/DIA02/C002/C002C001_251121_R3EF_MOV-PRORES.mov"]},
}[TAXA]
TRABALHO = os.path.join(RAIZ, "saida", "bancadas", CFG["trabalho"])
PROJETO = CFG["projeto"]
BIN = f"{PROJETO} Bin.avb"
BIN_ABS = os.path.join(os.path.expanduser("~"), "Documents", "Avid Projects", PROJETO, BIN)

ORIGINAIS = CFG["originais"]
ORIGINAIS_2398 = ORIGINAIS          # o nome antigo


def _caminhos() -> None:
    for p in (os.path.join(CONFORMAR, "plugins", "media-composer", "servico"), os.path.join(CONFORMAR, "motor")):
        if p not in sys.path:
            sys.path.insert(0, p)


def linkar() -> dict:
    """AMA-linka os originais de 23,976 na bin do projeto; devolve {arquivo: mob_id da API}."""
    _caminhos()
    from avid.acoes import Acoes
    from avid.mcapi import MediaComposer
    os.makedirs(TRABALHO, exist_ok=True)
    feitos = {}
    with MediaComposer() as m:
        a = Acoes(m)
        for rel in ORIGINAIS:
            t0 = time.time()
            feitos[rel] = a.link_file(os.path.join(MIDIA, rel), BIN)
            print(f"{time.time() - t0:5.1f} s  {rel} → {feitos[rel]}")
    with open(os.path.join(TRABALHO, "linkados.json"), "w", encoding="utf-8") as fh:
        json.dump(feitos, fh, indent=1)
    return feitos


#: a sequência de corte seco: (câmera do master DNx, in no master, duração) em quadros de 23,976 — quatro câmeras,
#: um clipe que volta (A001C001), ins fora do começo; 384 quadros = 16 s
CORTE_SECO = [("A001C001", 48, 72), ("B001C001", 24, 48), ("A001C002", 120, 60),
              ("C001C001", 0, 96), ("A001C001", 300, 36), ("B001C001", 200, 72)]
#: duas trilhas: V1 = A001C002 inteiro de 10 s; V2 = B001C001 (in 100) dos quadros 72 a 168
DUAS_TRILHAS_V1 = ("A001C002", 0, 240)
DUAS_TRILHAS_V2 = ("B001C001", 100, 96, 72)          # (câmera, in, duração, posição na sequência)
if TAXA == "2997DF":
    # A002C001 começa em 14:59:50;00 e B002C001 em 15:09:55;00: os quadros 300 e 150 são 15:00:00;00 e 15:10:00;00
    # (décimos minutos, SEM pulo — a rodada BL02). C002C001 começa em 15:00:50;00: o quadro 300 é 15:01:00;02, logo
    # depois do PULO (a rodada BL05, 268 quadros).
    CORTE_SECO = [("A002C001", 280, 48), ("B002C001", 120, 60), ("A002C001", 500, 40), ("B002C001", 400, 72)]
    if os.environ.get("LAB_BL_RODADA") == "BL05":
        CORTE_SECO = [("A002C001", 280, 48), ("C002C001", 280, 48), ("B002C001", 120, 60), ("A002C001", 500, 40),
                      ("B002C001", 400, 72)]
    DUAS_TRILHAS_V1 = ("A002C001", 200, 240)
    DUAS_TRILHAS_V2 = ("B002C001", 100, 96, 72)


def _masters_dnx(f) -> dict:
    """{câmera: master DNx} — os `.new.01` do transcode (o offline), não os AMA."""
    return {mm.name[:8]: mm for mm in f.content.mobs if mm.mob_type == "MasterMob" and ".new." in mm.name}


def _masters_todos(f) -> dict:
    """{câmera: master} — todos os masters da bin (a bin dos dailies só tem eles)."""
    return {mm.name[:8]: mm for mm in f.content.mobs if mm.mob_type == "MasterMob"}


def montar(bin_abs: str = BIN_ABS, prefixo: str = "BL01", escolher=_masters_dnx) -> dict:
    """Grava na bin (fechada no MC, a dança do banco) as duas sequências e reabre a bin."""
    _caminhos()
    if ASSIST not in sys.path:
        sys.path.insert(0, ASSIST)
    import avb
    from avid.mcapi import MediaComposer
    from cicloassist.avid import timeline as T

    with MediaComposer() as m:
        try:
            m.fechar_bin(bin_abs)
        except Exception:                    # noqa: BLE001 — bin já fechada responde erro (normal)
            pass
        with avb.open(bin_abs) as f:
            dnx = escolher(f)
            taxa = next(iter(dnx.values())).edit_rate
            ids = {c: str(mm.mob_id) for c, mm in dnx.items()}
            trilhas = {c: tuple(sorted((t.media_kind, t.index) for t in mm.tracks
                                      if t.media_kind in ("picture", "sound"))) for c, mm in dnx.items()}
        corte = [T.Entrada(mob_id=ids[c], duracao=d, trilhas=trilhas[c], start_time=i) for c, i, d in CORTE_SECO]
        T.acrescentar_timeline(bin_abs, f"{prefixo} CORTE SECO", corte, taxa, drop_frame=CFG["df"])

        # a V2: a mesma forma da V1 (Filler, SourceClip, Filler de rabo) com o índice trocado — `montar_camadas` do
        # laboratório (avid.py), validado no MC em 2026-10-12
        c1, i1, d1 = DUAS_TRILHAS_V1
        c2, i2, d2, pos2 = DUAS_TRILHAS_V2
        original = T.montar_timeline

        def com_v2(f, nome_, entradas, edit_rate, *a, **k):
            comp = original(f, nome_, entradas, edit_rate, *a, **k)
            sc = f.create.SourceClip(edit_rate, "picture")
            sc.mob_id = T.MobID(ids[c2])
            sc.track_id = 1
            sc.start_time = i2
            sc.length = d2
            seq = f.create.Sequence(edit_rate, "picture")
            seq.components = [T._filler(f, edit_rate, pos2, "picture"), sc]
            seq.components.append(T._trail_filler(f, edit_rate, "picture", seq.components, d1))
            tr = f.create.Track()
            tr.index = 2
            tr.component = seq
            tr.lock_number = 0
            tr.filler_proxy = T._referencia_de_track(f, edit_rate, "picture")
            tr.session_attr = T._atributos(f, _ENBLSTATE=1, _MONSTATE=1)
            comp.tracks.insert(1, tr)
            return comp

        T.montar_timeline = com_v2
        try:
            T.acrescentar_timeline(bin_abs, f"{prefixo} DUAS TRILHAS",
                                   [T.Entrada(mob_id=ids[c1], duracao=d1, trilhas=trilhas[c1], start_time=i1)], taxa,
                                   drop_frame=CFG["df"])
        finally:
            T.montar_timeline = original
        m.abrir_bin(bin_abs)
        fim, achadas = time.time() + 120, {}
        while time.time() < fim and len(achadas) < 2:
            achadas = {it.name: it.mob_id for it in m.itens_de(bin_abs, flags=("AllTypes",))
                       if it.name.startswith(prefixo + " ")}
            time.sleep(2)
    print(achadas)
    arq = os.path.join(TRABALHO, "sequencias.json")
    todas = json.load(open(arq, encoding="utf-8")) if os.path.exists(arq) else {}
    todas.update(achadas)
    with open(arq, "w", encoding="utf-8") as fh:
        json.dump(todas, fh, indent=1)
    return achadas


def exportar(prefixo: str = "") -> dict:
    """O AAF de cada sequência pelo `ExportFile` (o preset "AAF" de fábrica do projeto novo) — o que o editor manda
    à cor. ⚠️ O nome do preset não garante o formato (relink.exportar_aaf confere a extensão)."""
    _caminhos()
    from avid.mcapi import MediaComposer
    from relink import exportar_aaf
    with open(os.path.join(TRABALHO, "sequencias.json"), encoding="utf-8") as fh:
        seqs = json.load(fh)
    destino = os.path.join(TRABALHO, "aaf_do_mc")
    feitos = {}
    with MediaComposer() as m:
        for nome, mob in seqs.items():
            if prefixo and not nome.startswith(prefixo + " "):
                continue
            feitos[nome] = exportar_aaf(m, mob, destino, nome.replace(" ", "_"))
            print(nome, "→", feitos[nome])
    return feitos


#: BL02 — o cenário de PROJETO (autor, 2026-11-21): a conversão feita FORA do MC, sem metadado dela. Dailies em
#: ProRes Proxy HD com o MESMO nome (sem extensão) e o MESMO TC dos originais, numa pasta própria; o MC só os vê.
DAILIES = os.path.join(MIDIA, "DAILIES_FORA", "DIA02" if TAXA == "2997DF" else "DIA01")
BIN_DAILIES = "BL02 DAILIES FORA.avb"
BIN_DAILIES_ABS = os.path.join(os.path.dirname(BIN_ABS), BIN_DAILIES)


def dailies() -> list[str]:
    """Os convertidos (`lab/convertido.py`, modo fit para 1920×1080) dos 4 originais de 23,976."""
    sys.path.insert(0, RAIZ)
    import subprocess
    from lab import convertido
    feitos = []
    for rel in ORIGINAIS:
        orig = os.path.join(MIDIA, rel)
        st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                        "stream=codec_type,width,height:stream_tags=timecode", "-of", "json", orig],
                                       capture_output=True, text=True, check=True).stdout)["streams"]
        v = next(x for x in st if x["codec_type"] == "video")
        w, h = v["width"], v["height"]
        tc = next(x["tags"]["timecode"] for x in st if x.get("tags", {}).get("timecode"))
        destino = os.path.join(DAILIES, os.path.splitext(os.path.basename(rel))[0] + ".mov")
        if os.path.exists(destino):          # o daily já linkado no MC não se regrava
            continue
        convertido.gerar(orig, destino, {"raster": [1920, 1080], "modo": "fit"}, w, h, None, tc,
                         fps_original=CFG["fps_txt"])
        feitos.append(destino)
        print(destino)
    return feitos


def linkar_dailies() -> dict:
    """Cria a bin BL02 e AMA-linka nela os dailies (o MC não sabe dos originais)."""
    _caminhos()
    from avid.acoes import Acoes
    from avid.mcapi import MediaComposer
    feitos = {}
    with MediaComposer() as m:
        a = Acoes(m)
        a.criar_bin(BIN_DAILIES[:-4])
        for nome in sorted(os.listdir(DAILIES)):
            if nome.endswith(".mov") and not nome.startswith("._"):
                feitos[nome] = a.link_file(os.path.join(DAILIES, nome), BIN_DAILIES)
                print(nome, "→", feitos[nome])
    return feitos


PRESET_REF = CFG["preset"]          # MXF OP1a DNxHR LB na taxa da rodada (lab/bancadas/avid/presets) — o vid ref
VIDREF = os.path.join(TRABALHO, "vidref")


def vidref(nome: str = "BL02 CORTE SECO") -> str:
    """O vídeo de referência da sequência (o que o editor anexa para a cor): o preset do laboratório entra pelo
    `LoadSetting` e o `ExportFile` renderiza; espera o arquivo parar de crescer."""
    _caminhos()
    import glob
    from avid.mcapi import MediaComposer
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "avid", "presets", PRESET_REF + ".xml"),
              encoding="utf-8") as fh:
        xml = fh.read()
    seqs = json.load(open(os.path.join(TRABALHO, "sequencias.json"), encoding="utf-8"))
    os.makedirs(VIDREF, exist_ok=True)
    arq = nome.replace(" ", "_") + "_REF"
    for velho in glob.glob(os.path.join(VIDREF, arq + ".*")):
        os.remove(velho)
    with MediaComposer() as m:
        m._chamar("LoadSetting", _timeout=60, unique_id=PRESET_REF, xml_setting=xml)
        m._chamar("ExportFile", _timeout=60, mob_id=seqs[nome], file_name=arq, export_settings_name=PRESET_REF,
                  destination_path=VIDREF)
    ultimo, iguais, t0 = None, 0, time.time()
    while time.time() - t0 < 600:
        agora = [(f, os.path.getsize(f)) for f in glob.glob(os.path.join(VIDREF, arq + ".*"))]
        iguais = iguais + 1 if agora and agora == ultimo else 0
        ultimo = agora
        if iguais >= 4:
            print(agora[0][0], f"{time.time() - t0:.0f} s")
            return agora[0][0]
        time.sleep(3)
    raise RuntimeError("o vid ref não terminou em 600 s")


RELIGADO = os.path.join(TRABALHO, "aaf_religado")


def religar(nome: str = "BL02 CORTE SECO") -> dict:
    """O passo do EDITOR ONLINE pelo motor do Conformar: o AAF offline (só conhece os dailies) → casar cada segmento
    com os ORIGINAIS (pasta ORIGINAIS_2398, pelo nome/TC — sem o metadado da conversão) → o AAF com os Locators nos
    originais (rota A da missão Baselight). Devolve o relatório."""
    _caminhos()
    from aaf.parser import parse_aaf
    from aaf.writer import build_url_map, relink_aaf
    from media.indexer import index_folder
    from media.matcher import match_segments
    entrada = os.path.join(TRABALHO, "aaf_do_mc", nome.replace(" ", "_") + ".aaf")
    saida = os.path.join(RELIGADO, nome.replace(" ", "_") + "_ORIGINAIS.aaf")
    os.makedirs(RELIGADO, exist_ok=True)
    p = parse_aaf(entrada)
    idx = index_folder([os.path.join(MIDIA, CFG["pasta"])])
    casou = match_segments(p["segments"], idx)
    url_map = build_url_map(p["segments"], casou["results"])
    r = relink_aaf(entrada, saida, url_map)
    resumo = {"segmentos": len(p["segments"]), "stats": casou["stats"],
              "casamentos": [{k: x.get(k) for k in ("segment_index", "matched_path", "method", "score", "confidence")}
                             for x in casou["results"]],
              "atualizados": r["updated_count"], "preservados": r["skipped_count"], "erros": r["error_count"],
              "saida": saida}
    with open(os.path.join(RELIGADO, nome.replace(" ", "_") + ".json"), "w", encoding="utf-8") as fh:
        json.dump(resumo, fh, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(resumo, indent=1, ensure_ascii=False, default=str)[:3000])
    return resumo


BIN_ONLINE = "BL02 ONLINE.avb"


def online(nome: str = "BL02 CORTE SECO") -> dict:
    """O editor online no MC (a ordem do `relink.py` do Conformar): bin nova → `LinkFile` dos originais → `ImportFile`
    do AAF religado. Devolve {nome do item: mob_id} da bin."""
    _caminhos()
    from avid.acoes import Acoes
    from avid.mcapi import MediaComposer
    aaf = os.path.join(RELIGADO, nome.replace(" ", "_") + "_ORIGINAIS.aaf")
    bin_abs = os.path.join(os.path.dirname(BIN_ABS), BIN_ONLINE)
    with MediaComposer() as m:
        a = Acoes(m)
        a.criar_bin(BIN_ONLINE[:-4])
        for rel in ORIGINAIS:
            print("link", rel, a.link_file(os.path.join(MIDIA, rel), BIN_ONLINE))
        print("import", a.import_file(aaf, BIN_ONLINE))
        time.sleep(3)
        itens = {it.name: it.mob_id for it in m.itens_de(bin_abs, flags=("AllTypes",))}
    print(itens)
    return itens


def online_produto(nome: str = "BL02 CORTE SECO", nome_bin: str = "BL02 ONLINE PRODUTO") -> dict:
    """O editor online pelo FLUXO DO PRODUTO (`relink.preparar` + `relink.aplicar`: LinkFile dos originais → achatar +
    remapear os masters → ImportFile). ⛔ Importar direto o AAF do `relink_aaf` (o `online` acima) reaproveita os masters
    dos DAILIES que já estão no projeto (mesmos MobIDs) — o remapear existe para isso (medido 2026-11-21)."""
    _caminhos()
    import relink
    from avid.mcapi import MediaComposer
    t = relink.Trabalho(aaf=os.path.join(TRABALHO, "aaf_do_mc", nome.replace(" ", "_") + ".aaf"),
                        pastas=[os.path.join(MIDIA, CFG["pasta"])])
    relink.preparar(t)
    print("preparar:", t.resumo())
    pasta_trab = os.path.join(TRABALHO, "aaf_produto")
    os.makedirs(pasta_trab, exist_ok=True)
    with MediaComposer() as m:
        r = relink.aplicar(m, t, os.path.dirname(BIN_ABS), nome_bin, pasta_trab)
        time.sleep(3)
        itens = {it.name: it.mob_id for it in m.itens_de(os.path.join(os.path.dirname(BIN_ABS), nome_bin + ".avb"),
                                                           flags=("AllTypes",))}
    print("aplicar:", r)
    print(itens)
    return {"aplicar": r, "itens": itens}


def _local(caminho: str) -> str:
    """O Locator do MC no Mac vem com o NOME do volume (`/SSD/…`), sem `/Volumes/` (medido 2026-11-21)."""
    if not os.path.exists(caminho) and os.path.exists("/Volumes" + caminho):
        return "/Volumes" + caminho
    return caminho


def conferir(aaf: str = "", ref: str = "", sabotar: dict | None = None, segmentos: list | None = None) -> dict:
    """A conferência ANTES do Baselight (o diferencial do plano, autor 2026-11-21): para cada evento de imagem do AAF
    que vai à cor, o quadro do ORIGINAL no in de fonte × o quadro do VID REF na posição da timeline — no primeiro, no
    do meio e no último quadro do evento. Duas medidas:
    - EXATA (só no laboratório): o número do quadro e o TC lidos no código de barras dos dois;
    - por IMAGEM (a que vale em material real): diferença média de cinza 0–255, original reduzido a 1920×1080 × ref,
      e a mesma conta contra o quadro VIZINHO do original (+1), para saber se a imagem separa o certo do errado."""
    sys.path.insert(0, RAIZ)
    _caminhos()
    from aaf.parser import parse_aaf
    from lab import ler
    aaf = aaf or os.path.join(TRABALHO, "aaf_online", "BL02_CORTE_SECO_ONLINE_PRODUTO.aaf")
    ref = ref or os.path.join(VIDREF, "BL02_CORTE_SECO_REF.mxf")
    W, H = 1920, 1080
    todos = segmentos if segmentos is not None else \
        [s for s in parse_aaf(aaf)["segments"] if not s["is_audio"] and not s["is_gap"]]
    # a posição de cada segmento na sua trilha (o parser dá o TC de gravação) e, por quadro, a trilha mais ALTA que
    # tem imagem ali — é ela que o vid ref mostra
    from aaf.parser import _tc_to_frames
    fps = CFG["fps"]
    for x in todos:
        x.setdefault("_pos", _tc_to_frames(x["timeline_tc_in"], fps) if "timeline_tc_in" in x else 0)
    for n, v in (sabotar or {}).items():       # a prova ao contrário (só eventos da V1, pela ordem)
        alvo = [x for x in todos if x["track"] == 1][n - 1]
        if isinstance(v, int):
            alvo["source_start_frames"] += v
        else:
            alvo["media_ref"]["local_path"] = v
    trans = [(x["_pos"], x["_pos"] + x["duration_frames"]) for x in todos if x.get("is_transition")]
    todos = [x for x in todos if not x.get("is_transition")]

    def fonte(seg, k):
        """O quadro de fonte do quadro k do evento: o mapa (velocidade/reverso/congelado) ou o linear."""
        m = seg.get("source_offset_map") or []
        if not m:
            return seg["source_start_frames"] + k
        for (t0, v0), (t1, v1) in zip(m, m[1:]):
            if t0 <= k <= t1:
                v = v0 + (v1 - v0) * (k - t0) / ((t1 - t0) or 1)
                break
        else:
            v = m[-1][1]
        import math
        return seg["source_start_frames"] + int(math.floor(v + 1e-6))

    eventos = []
    for s in sorted(todos, key=lambda x: (x["_pos"], -x["track"])):
        d, ini, pos = s["duration_frames"], s["source_start_frames"], s["_pos"]
        acima = [x for x in todos if x["track"] > s["track"]]
        visiveis = [k for k in range(d) if not any(x["_pos"] <= pos + k < x["_pos"] + x["duration_frames"] for x in acima)
                    and not any(a <= pos + k < b for a, b in trans)]
        if not visiveis:
            continue
        ks = sorted({visiveis[0], visiveis[len(visiveis) // 2], visiveis[-1]})
        orig = _local(s["media_ref"]["local_path"])
        q_ref = ler.quadros_cinza(ref, [pos + k for k in ks], W, H)
        geo = [e for e in s.get("effects") or [] if e.get("name") not in ("Motion Control",)]
        fk = {k: fonte(s, k) for k in ks}
        if geo:
            # Resize/3D Warp: a barra sai do lugar. O original com a transformação DO AAF aplicada × o ref, nos pixels
            # que mudam entre o quadro certo e os vizinhos (lab/geometria.py; unidades medidas na BL04 R2)
            from lab import geometria as G
            if len(geo) > 1 or geo[0].get("name") not in ("PaintResize_v2", "SBlend_v2", "PIP_v2"):
                eventos.append({"evento": len(eventos) + 1, "trilha": s["track"], "clipe": s["clip_name"],
                                "posicao": pos, "in": ini, "duracao": d, "exato": None,
                                "geometria": [e.get("name") for e in geo]})
                print(f"{len(eventos)} efeito sem conferência: {[e.get('name') for e in geo]}")
                continue
            t = G.do_avid(geo[0]["name"], geo[0].get("params") or {})
            amostras = []
            for k in ks:
                qs = [q for q in (fk[k] - 1, fk[k], fk[k] + 1) if q >= 0]
                c = G.conferir_quadro(q_ref[pos + k], ler.quadros_cinza(orig, qs, W, H), fk[k], t)
                amostras.append({"k": k, "fonte": fk[k], **{a: c[a] for a in ("dif", "dif_vizinho", "dif_imagem",
                                                                                "exato")}})
            exato = all(a["exato"] for a in amostras)
            eventos.append({"evento": len(eventos) + 1, "trilha": s["track"], "clipe": s["clip_name"], "posicao": pos,
                            "in": ini, "duracao": d, "exato": exato, "geometria": geo[0]["name"], "transformacao": t,
                            "amostras": amostras})
            print(f"{len(eventos)} V{s['track']} {s['clip_name'][:20]}  pos {pos:4}  in {ini:4}  "
                  f"{'OK ' if exato else 'ERRO'}  {geo[0]['name']}  "
                  + "  ".join(f"[{a['fonte']} dif {a['dif']} viz {a['dif_vizinho']}]" for a in amostras))
            continue
        q_ori = ler.quadros_cinza(orig, sorted({fk[k] for k in ks} | {fk[k] + 1 for k in ks}), W, H)
        amostras = []
        for k in ks:
            r, o, viz = q_ref[pos + k], q_ori[fk[k]], q_ori[fk[k] + 1]
            dif = sum(abs(a - b) for a, b in zip(r[::97], o[::97])) / len(r[::97])
            dif_viz = sum(abs(a - b) for a, b in zip(r[::97], viz[::97])) / len(r[::97])
            amostras.append({"k": k, "ref": ler.ler_faixas(r, W, H), "original": ler.ler_faixas(o, W, H),
                             "dif": round(dif, 2), "dif_vizinho": round(dif_viz, 2)})
        exato = all(a["ref"] == a["original"] for a in amostras)
        eventos.append({"evento": len(eventos) + 1, "trilha": s["track"], "clipe": s["clip_name"], "posicao": pos,
                        "in": ini, "duracao": d, "exato": exato, "amostras": amostras})
        print(f"{len(eventos)} V{s['track']} {s['clip_name'][:20]}  pos {pos:4}  in {ini:4}  {'OK ' if exato else 'ERRO'}  "
              + "  ".join(f"[{a['ref'][0]}/{a['original'][0]} dif {a['dif']} viz {a['dif_vizinho']}]" for a in amostras))
    res = {"aaf": aaf, "ref": ref, "eventos": eventos,
           "todos_exatos": all(e["exato"] for e in eventos if e["exato"] is not None),
           "sem_conferencia": [e["evento"] for e in eventos if e["exato"] is None]}
    with open(os.path.join(TRABALHO, ("sabotada_" if sabotar else "conferencia_")
                           + os.path.basename(aaf).replace(".aaf", ".json")), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    print("TODOS EXATOS" if res["todos_exatos"] else "HÁ EVENTO ERRADO")
    return res


FLE = os.path.join(TRABALHO, "fle")


def _tc_do_arquivo(caminho: str) -> str:
    import subprocess
    st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream_tags=timecode", "-of", "json",
                                    caminho], capture_output=True, text=True, check=True).stdout)["streams"]
    return next(x["tags"]["timecode"] for x in st if x.get("tags", {}).get("timecode"))


def gerar_fle(aaf: str = "") -> list[str]:
    """A rota B: o FLE (EDL da FilmLight, `bancodedadosnles/protocolos/fle/`) da trilha V1 do AAF que vai à cor —
    eventos de TIMECODE (saída INCLUSIVA) com o arquivo do original. Duas variantes para medir no Baselight: o caminho
    COMPLETO (a spec proíbe espaço no nome — os nossos têm) e só o NOME (o Baselight acha pela pasta de busca).
    ⚠️ `# fps 24` para 23,976: a spec só lista 24/25/30/30DF (hipótese a medir). Em 29,97 DF: `# fps 30DF`, os rótulos
    drop-frame com ':' (a spec não diz o separador — hipótese a medir)."""
    sys.path.insert(0, RAIZ)
    _caminhos()
    from aaf.parser import parse_aaf
    from lab import tc as TC
    aaf = aaf or os.path.join(TRABALHO, "aaf_online", "BL02_CORTE_SECO_ONLINE_PRODUTO.aaf")
    p = parse_aaf(aaf)
    from aaf.parser import _tc_to_frames
    imagem = [x for x in p["segments"] if not x["is_audio"] and not x["is_gap"]]
    trilhas = sorted({x["track"] for x in imagem})
    os.makedirs(FLE, exist_ok=True)
    feitos = []
    b, df, fps = CFG["b"], CFG["df"], CFG["fps"]
    for variante in ("caminho", "nome"):
        linhas = ["# FilmLight EDL", "#", "# version 1.0", f"# title {os.path.basename(aaf)[:-4]}",
                  f"# fps {CFG['fle_fps']}", "#"]
        for t in trilhas:
            linhas.append(f"# track {t}")
            cursor = 0
            for x in sorted((x for x in imagem if x["track"] == t), key=lambda x: _tc_to_frames(x["timeline_tc_in"], fps)):
                pos = _tc_to_frames(x["timeline_tc_in"], fps)
                if pos > cursor:                     # o buraco: evento SEM nome (quadros, saída inclusiva)
                    linhas.append(f"{0:04d} {pos - cursor - 1:04d}")
                orig = _local(x["media_ref"]["local_path"])
                ini = TC.tc_para_quadros(_tc_do_arquivo(orig), b, df) + x["source_start_frames"]
                fim = ini + x["duration_frames"] - 1                       # INCLUSIVA
                alvo = os.path.splitext(orig)[0] if variante == "caminho" else os.path.splitext(os.path.basename(orig))[0]
                tcs = [TC.quadros_para_tc(q, b, df).replace(";", ":") for q in (ini, fim)]
                linhas.append(f"{tcs[0]} {tcs[1]} {alvo}")
                cursor = pos + x["duration_frames"]
        linhas += ["#", "# end", ""]
        destino = os.path.join(FLE, os.path.basename(aaf)[:-4] + f"_{variante.upper()}.fle")
        with open(destino, "w", encoding="ascii") as fh:
            fh.write("\n".join(linhas))
        feitos.append(destino)
        print(destino)
        print("\n".join(linhas))
    return feitos


#: BL04 — os EFEITOS escritos PELA BIN (autor, 2026-11-21) pelo `avb_export.build_avb` do Conformar, sobre os
#: dailies (o offline): (câmera, in, duração na timeline, efeito). Quadros de 23,976.
EFEITOS = [
    ("A001C001", 48, 60, None),                    # sai em dissolve de 12 (os 12 últimos sobrepõem o próximo)
    ("B001C001", 24, 72, "dissolve"),              # entra pelo dissolve
    ("A001C002", 120, 48, ("velocidade", 0.5)),    # 50 %: 24 quadros de fonte em 48
    ("C001C001", 0, 48, ("velocidade", 2.0)),      # 200 %: 96 de fonte em 48
    ("A001C001", 300, 48, ("reverso", 1.0)),       # para trás a 100 %
    ("B001C001", 200, 24, ("congelado", 0.0)),     # o quadro 200 parado
    ("A001C002", 0, 48, ("resize", {"scale_x": 1.5, "scale_y": 1.5, "pos_x": 100.0, "pos_y": 50.0})),
    ("C001C001", 200, 48, ("warp", {"rot_z": 10.0})),
]
DISSOLVE = 12
BIN_EFEITOS = "BL04 EFEITOS.avb"


def _tc_rel(q: int) -> str:
    return f"{q // 86400:02d}:{q // 1440 % 60:02d}:{q // 24 % 60:02d}:{q % 24:02d}"


def segmentos_efeitos(ids: dict) -> list[dict]:
    """Os segmentos NEUTROS (a forma do `aaf.parser`) da BL04: `ids` = {câmera: mob_id}. Origem "premiere" no
    `build_avb`: a velocidade constante vai pelo `speed_ratio` RECÍPROCO e a geometria pelo efeito "Motion"."""
    base = {"is_gap": False, "is_transition": False, "is_effect": False, "is_audio": False, "disabled": False,
            "track": 1, "source_fps": 23.976023976023978, "source_slot_id": 1, "cutpoint": 0,
            "has_motion_effect": False, "motion_effect_type": None, "speed_ratio": 1.0, "speed_keyframes": [],
            "source_offset_map": [], "effects": [], "retime": None}
    out, pos = [], 0
    for cam, ini, dur, ef in EFEITOS:
        s = dict(base, clip_name=cam, mob_id=ids[cam], source_start_frames=ini, duration_frames=dur)
        if ef == "dissolve":
            pos -= DISSOLVE
            out.append(dict(base, is_transition=True, duration_frames=DISSOLVE, cutpoint=DISSOLVE // 2,
                            timeline_tc_in=_tc_rel(pos), clip_name="dissolve", mob_id=None, source_start_frames=0))
        elif isinstance(ef, tuple) and ef[0] in ("velocidade", "reverso"):
            s.update(has_motion_effect=True, motion_effect_type="reverse" if ef[0] == "reverso" else "constant",
                     speed_ratio=1.0 / ef[1])
        elif isinstance(ef, tuple) and ef[0] == "congelado":
            s.update(has_motion_effect=True, motion_effect_type="freeze",
                     speed_keyframes=[{"t": 0.0, "speed": 0.0, "in_dt": 0.0, "in_dv": 0.0, "out_dt": 0.0,
                                       "out_dv": 0.0, "mode": 1}], source_offset_map=[(0.0, 0.0), (float(dur), 0.0)])
        elif isinstance(ef, tuple) and ef[0] in ("resize", "warp"):
            s["effects"] = [{"name": "Motion", "params": ef[1]}]
        s["timeline_tc_in"] = _tc_rel(pos)
        out.append(s)
        pos += dur
    return out


def montar_efeitos(rodada: str = "") -> dict:
    """A BL04 numa bin NOVA (`build_avb` lê a bin dos dailies, fechada no MC, e grava outra) e a abre no MC.
    `rodada` ("R2"…) vai no nome da bin e da sequência: a rodada anterior fica como estava (nunca sobrescrever)."""
    _caminhos()
    nome = "BL04 EFEITOS" + (f" {rodada}" if rodada else "")
    import avb
    from avb_export import build_avb
    from avid.mcapi import MediaComposer
    destino = os.path.join(os.path.dirname(BIN_ABS), nome + ".avb")
    with MediaComposer() as m:
        try:
            m.fechar_bin(BIN_DAILIES_ABS)
        except Exception:                    # noqa: BLE001 — já fechada
            pass
        with avb.open(BIN_DAILIES_ABS) as f:
            mm = _masters_todos(f)
            ids = {c: str(x.mob_id) for c, x in mm.items()}
            hexa = {str(x.mob_id): x.mob_id.bytes_le.hex() for x in mm.values()}
        segs = segmentos_efeitos(ids)
        r = build_avb(segs, 23.976023976023978, BIN_DAILIES_ABS, destino, nome, origem="premiere",
                      mob_hex=hexa)
        print("build_avb:", r)
        m.abrir_bin(BIN_DAILIES_ABS)
        m.abrir_bin(destino)
        fim, achada = time.time() + 120, {}
        while time.time() < fim and not achada:
            achada = {it.name: it.mob_id for it in m.itens_de(destino, flags=("AllTypes",)) if it.name == nome}
            time.sleep(2)
    print(achada)
    arq = os.path.join(TRABALHO, "sequencias.json")
    todas = json.load(open(arq, encoding="utf-8"))
    todas.update(achada)
    json.dump(todas, open(arq, "w", encoding="utf-8"), indent=1)
    return achada


if __name__ == "__main__":
    acao = sys.argv[1]
    if acao == "montar_dailies":
        montar(BIN_DAILIES_ABS, "BL02", _masters_todos)
    elif acao == "exportar_dailies":
        exportar("BL02")
    else:
        {"linkar": linkar, "montar": montar, "exportar": exportar, "dailies": dailies,
         "linkar_dailies": linkar_dailies, "vidref": vidref, "religar": religar, "online": online, "online_produto": online_produto, "conferir": conferir, "fle": gerar_fle, "montar_efeitos": montar_efeitos}[acao](*sys.argv[2:])
