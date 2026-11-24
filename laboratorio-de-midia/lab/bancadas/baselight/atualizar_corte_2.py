"""BL09, 2ª parte — o que o "atualizar corte" ainda não tinha medido (Ciclo Assist, 2026-11-22, noite 8):

    grupos        o colorista agrupa planos (Scene.set_group); a v2 chega: o grupo vem? com quais planos?
    multitrilha   a edição entrega trilhas sobrepostas, plano escondido e corte à toa no mesmo take; o colorista
                  achata e junta; a v2 (bagunçada de novo) mexe num plano que ele juntou
    render        o render que a cor devolveu à montagem volta DENTRO da v2 (outro arquivo, o reel e o TC do original)
    camada0       o reposicionamento do colorista (a camada 0) — pilotado na interface

Dois pythons, como no produto: os comandos da FLAPI rodam no python da FilmLight; `produto` roda no python do Ciclo
Assist (`_CICLO ASSIST/.venv`) e chama `motor.baselight.enviar.enviar(..., atualizar=)` — o caminho do painel/chat.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import atualizar_corte as B  # noqa: E402

HOST, JOB, SAIDA, ORIG = B.HOST, B.JOB, B.SAIDA, B.ORIG


def copiar(origem: str, nova: str) -> None:
    """Duplica uma scene sem tocar nela (banco: bl-export → bl-import numa pasta → rename_scene para a raiz)."""
    if nova in B.scenes():
        return
    tmp = os.path.join(SAIDA, "copia.blscene")
    r = B.bl("bl-export", f"{HOST}:{JOB}:{origem}", tmp)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    import flapi
    c = flapi.Connection(HOST)
    c.connect()
    try:
        try:
            c.JobManager.create_folder(HOST, JOB, "COPIAS")
        except flapi.FLAPIException:
            pass
        r = B.bl("bl-import", f"{HOST}:{JOB}:COPIAS", tmp)
        if r.returncode:
            raise SystemExit(r.stdout + r.stderr)
        c.JobManager.rename_scene(HOST, JOB, f"COPIAS:{origem}", nova)
    finally:
        c.close()
    os.remove(tmp)


def _planos_ids(s) -> dict[int, dict]:
    out = {}
    for info in s.get_shot_ids():
        sh = s.get_shot(info.ShotId)
        try:
            sd = sh.get_sequence_descriptor()
            out[info.ShotId] = {"rec": info.StartFrame, "arquivo": os.path.basename(sd.get_full_filename_with_F()) if sd else "",
                                "src": [sh.get_src_start_frame(), sh.get_src_end_frame()]}
        finally:
            sh.release()
    return out


def grupos(scene: str) -> dict[str, list[dict]]:
    flapi, c, s = B._abrir(scene, leitura=True)
    try:
        planos = _planos_ids(s)
        return {g: [planos.get(i, {"id_sem_plano": i}) for i in (s.get_group(g) or [])] for g in s.get_groups()}
    finally:
        s.close_scene()
        c.close()


#: os grupos do colorista na v1 (pelo id do plano na v1)
GRUPOS_V1 = {"EXTERIOR DIA": ["S1", "S6"], "SALA": ["S2", "S7", "S3"], "NOITE": ["S4", "S5"]}


def grupos_v1() -> None:
    copiar("BL09 V1", "BL09 V1 grupos")
    flapi, c, s = B._abrir("BL09 V1 grupos")
    try:
        ids = [i.ShotId for i in s.get_shot_ids()]
        por_id = {p[0]: ids[k] for k, p in enumerate(B.V1)}
        s.start_delta("BL09: os grupos do colorista")
        for g, membros in GRUPOS_V1.items():
            s.set_group(g, [por_id[m] for m in membros])
        s.end_delta()
        s.save_scene()
    finally:
        s.close_scene()
        c.close()
    print(json.dumps(grupos("BL09 V1 grupos"), ensure_ascii=False, indent=1))


def mp_grupos(destino: str, origem: str = "BL09 V1 grupos") -> None:
    """O Multi-Paste com PasteGroups=1 numa v2 recém-conformada: o grupo vem? com quem?"""
    if destino not in B.scenes():
        B.conformar("BL09_V2.xml", destino, "--TimeType", "Source")
    flapi, c, s = B._abrir(destino)
    try:
        ms = flapi.MultiPasteSettings(
            Source="MultipleScenes", SourceScenes=[f"{HOST}:{JOB}:{origem}"], MatchBy=["Filename", "Timecode"],
            MatchQuality="ExactMatch", PasteGrades=1, LayerZeroBehaviour="StackOnly", SourceShots="CopyAll",
            DestShots="OverwriteAll", DetectGradeChanges=0, PasteLocation="Above", MaintainTracks=0, PasteMetadata=0,
            PasteGroups=1)
        mp = c.MultiPaste.create()
        s.start_delta("Multi-Paste com os grupos")
        n = mp.multi_paste(s, ms, [i.ShotId for i in s.get_shot_ids()])
        s.end_delta()
        s.save_scene()
        log = [getattr(x, "Summary", "") for x in (mp.get_log() or [])]
    finally:
        s.close_scene()
        c.close()
    print("colados:", n)
    for l in log:
        if "roup" in l:
            print("  log:", l)
    print(json.dumps(grupos(destino), ensure_ascii=False, indent=1))


def produto(xml: str, colorista: str, base: str) -> None:
    """O caminho do produto (rodar no python do Ciclo Assist)."""
    p = AQUI
    while not os.path.isdir(os.path.join(p, "2 ATIVOS")):
        p = os.path.dirname(p)
    sys.path.insert(0, os.path.join(p, "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar"))
    from motor.baselight import enviar as EV
    r = EV.enviar(os.path.join(SAIDA, xml), JOB, base, 23.976, [ORIG], atualizar=colorista,
                  andamento=lambda e, t, **k: print("  ·", t))
    nome = "produto_" + r["scene"].replace(" ", "_").replace("·", "") + ".json"
    with open(os.path.join(SAIDA, nome), "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1, default=str)
    a = r.get("atualizar") or {}
    print(f"scene {r['scene']}: {r['planos']} planos {r['contagem']}; cor conferida {a.get('conferidos')}/{a.get('de')}")
    for x in a.get("planos", []):
        print(f"  {x['inicio']:5} {x['arquivo']:14} {x['estado']:18} {x['motivo']} {x['aviso']}")
    print("  marcas movidas", a.get("marcas_movidas"), "perdidas", a.get("marcas_perdidas"))
    print("  json:", os.path.join(SAIDA, nome))


# ── multitrilha: a timeline bagunçada da edição ─────────────────────────────────────────────────────────────────────

#: (id, arquivo, in, duração, início na timeline) por trilha (V1, V2). k da cor = o número do id.
#: V1: S1 | S2 | S3 | S4a+S4b (corte À TOA: fonte emendada) | S5 (ESCONDIDO sob o S5x da V2) | S6 | S7
#: V2: INSERTO sobre a 2ª metade do S2 (A006C001 200+24) e o S5x (C001C004 0+48) cobrindo o S5 inteiro
MT_V1 = {
    "V1": [("S1", "B001C007", 48, 48, 0), ("S2", "A001C008", 24, 48, 48), ("S3", "C001C003", 60, 48, 96),
           ("S4a", "B001C008", 100, 24, 144), ("S4b", "B001C008", 124, 24, 168), ("S5", "A006C001", 30, 48, 192),
           ("S6", "B001C007", 150, 48, 240), ("S7", "A001C008", 120, 48, 288)],
    "V2": [("IN", "A006C001", 200, 24, 72), ("S5x", "C001C004", 0, 48, 192)],
}
#: o que o COLORISTA deixou (uma trilha, achatada e juntada): o S2 só até o inserto, o inserto, o S4 inteiro, o S5x
MT_COLORISTA = [("S1", "B001C007", 48, 48), ("S2", "A001C008", 24, 24), ("IN", "A006C001", 200, 24),
                ("S3", "C001C003", 60, 48), ("S4", "B001C008", 100, 48), ("S5x", "C001C004", 0, 48),
                ("S6", "B001C007", 150, 48), ("S7", "A001C008", 120, 48)]
MT_K = {"S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 5, "S6": 6, "S7": 7, "IN": 9, "S5x": 10}
#: a v2 da edição: bagunçada IGUAL, e o S4 que o colorista juntou APARADO (cabeça +6, cauda −6; o corte à toa continua)
MT_V2 = {"V1": [x if not x[0].startswith("S4") else x for x in MT_V1["V1"]], "V2": list(MT_V1["V2"])}
MT_V2["V1"][3] = ("S4a", "B001C008", 106, 18, 144)
MT_V2["V1"][4] = ("S4b", "B001C008", 124, 18, 162)
MT_V2["V1"][5:] = [(i, a, n, d, s - 12) for i, a, n, d, s in MT_V2["V1"][5:]]
MT_V2["V2"][1] = ("S5x", "C001C004", 0, 48, 180)
#: a cor esperada em cada plano VISÍVEL da v2 (quem cobre quem: a V2 por cima)
MT_ESPERADO = {"S1": "S1", "S2": "S2", "IN": "IN", "S3": "S3", "S4a": "S4", "S4b": "S4", "S5x": "S5x", "S6": "S6",
               "S7": "S7", "S5": None}


def xmeml_trilhas(nome: str, trilhas: dict[str, list[tuple]]) -> str:
    vistos: set = set()
    fim = max(s + d for tr in trilhas.values() for _, _, _, d, s in tr)
    tracks = []
    n = 0
    for tr in trilhas.values():
        itens = []
        for pid, arq, ini, dur, st in tr:
            n += 1
            itens.append(f'<clipitem id="clipitem-{n}"><name>{arq}.mov</name><enabled>TRUE</enabled>'
                         f'<duration>{B.MIDIA[arq][2]}</duration>{B.RATE}<start>{st}</start><end>{st + dur}</end>'
                         f'<in>{ini}</in><out>{ini + dur}</out>{B._file(arq, "file-" + arq, vistos)}</clipitem>')
        tracks.append(f'<track>{"".join(itens)}</track>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><sequence id="sequence-1">'
            f'<duration>{fim}</duration>{B.RATE}<name>{nome}</name><timecode>{B.RATE}<string>01:00:00:00</string>'
            f'<frame>{B.tc_q("01:00:00:00")}</frame><displayformat>NDF</displayformat></timecode><media><video><format>'
            f'<samplecharacteristics>{B.RATE}<width>1920</width><height>1080</height></samplecharacteristics></format>'
            f'{"".join(tracks)}</video></media></sequence></xmeml>\n')


def mt_preparar() -> None:
    for arq, trilhas in (("BL09_MT_V1.xml", MT_V1), ("BL09_MT_V2.xml", MT_V2)):
        with open(os.path.join(SAIDA, arq), "w", encoding="utf-8") as fh:
            fh.write(xmeml_trilhas(arq[:-4].replace("_", " "), trilhas))
    with open(os.path.join(SAIDA, "BL09_MT_COLORISTA.xml"), "w", encoding="utf-8") as fh:
        fh.write(B.xmeml("BL09 MT colorista", MT_COLORISTA))
    print("ok")


def ler_trilhas(scene: str) -> list[dict]:
    """Plano a plano COM a trilha (ShotInfo) e a cor (o k do slope R)."""
    flapi, c, s = B._abrir(scene, leitura=True)
    out = []
    try:
        for info in s.get_shot_ids():
            sh = s.get_shot(info.ShotId)
            try:
                sd = sh.get_sequence_descriptor()
                d = {k: getattr(info, k) for k in dir(info) if k[0].isupper()}
                d.update({"arquivo": os.path.basename(sd.get_full_filename_with_F()) if sd else None,
                          "src": [sh.get_src_start_frame(), sh.get_src_end_frame()], "blg": B.cores_do_plano(sh)})
                out.append(d)
            finally:
                sh.release()
    finally:
        s.close_scene()
        c.close()
    return out


def mt_colorir(scene: str) -> None:
    """O colorista: um CDL por plano da scene achatada (slope R = 1 + k/100)."""
    flapi, c, s = B._abrir(scene)
    try:
        s.start_delta("BL09 MT: a cor do colorista")
        for (pid, *_), info in zip(MT_COLORISTA, list(s.get_shot_ids())):
            sh = s.get_shot(info.ShotId)
            sh.insert_cdl_layer(B._cdl(MT_K[pid]))
            sh.release()
        s.end_delta()
        s.save_scene()
    finally:
        s.close_scene()
        c.close()


# ── o render da cor voltando dentro da v2 ───────────────────────────────────────────────────────────────────────────

RENDER = os.path.join(SAIDA, "RENDER_DA_COR")
#: o render do S3 da V1 colorida (render_scene.py, RENDER_FAIXA=96,143): 47 quadros, TC 17:00:02:12, reel C001C003
#: (medido: o Baselight grava o TC de FONTE e o reel do original)
R_NOME, R_TC, R_DUR = "C001C003_COR", "17:00:02:12", 47
#: a v2 = a v1 com o S3 trocado pelo RENDER (aparado: o render do 4º ao 44º quadro = o original 64..104)
V2R = [p if p[0] != "S3" else ("S3", R_NOME, 4, 40) for p in B.V1]


def r_preparar() -> None:
    B.MIDIA[R_NOME] = ("", R_TC, R_DUR)
    x = B.xmeml("BL09 V2 render", V2R)
    from urllib.parse import quote
    x = x.replace(quote(os.path.join(ORIG, R_NOME + ".mov")), quote(os.path.join(RENDER, R_NOME + ".mov")))
    x = x.replace(f"<reel><name>{R_NOME}</name></reel>", "<reel><name>C001C003</name></reel>")
    with open(os.path.join(SAIDA, "BL09_V2_RENDER.xml"), "w", encoding="utf-8") as fh:
        fh.write(x)
    print("ok")


def produto_casado(xml: str, colorista: str, base: str) -> None:
    """O caminho do painel (Carta → Conformar → Baselight): o casador do Premiere acha o original de cada arquivo nas
    pastas dos originais, a decisão reescreve o xmeml e o `entregar_xmeml` conforma e leva a cor (rodar no python do
    Ciclo Assist)."""
    p = AQUI
    while not os.path.isdir(os.path.join(p, "2 ATIVOS")):
        p = os.path.dirname(p)
    raiz = os.path.join(p, "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar")
    sys.path[:0] = [os.path.join(raiz, "motor"), os.path.join(raiz, "plugins", "media-composer", "servico"), raiz]
    from baselight import entrega as E
    from baselight import enviar as EV
    from baselight import xmeml as X
    from prproj.originais import casar, indexar
    caminho = os.path.join(SAIDA, xml)
    leitura = X.ler(caminho)
    casamento = casar([s for s in leitura["segmentos"] if not s.get("disabled")], [ORIG], indice=indexar([ORIG]))
    for k, v in casamento.items():
        print(" casador:", os.path.basename(k), "→", v.get("estado"), os.path.basename(v.get("original") or ""),
              (v.get("motivo") or "")[:120])
    decisao = {}
    for k, v in casamento.items():
        o = v.get("original") if v.get("estado") in ("original", "proprio") else None
        decisao[k] = (E.descrever(o, EV._sondar(E.como_o_disco_lista(o)), fps_sequencia=leitura["fps"], trecho=v.get("trecho"))
                      if o and os.path.isfile(o) else None)
    r = EV.entregar_xmeml(caminho, decisao, JOB, base, [ORIG], os.path.join(SAIDA, "trabalho"), atualizar=colorista,
                          andamento=lambda e, t, **k: print("  ·", t))
    a = r.get("atualizar") or {}
    print(f"scene {r['scene']}: {r['planos']} planos {r['contagem']}; cor conferida {a.get('conferidos')}/{a.get('de')}"
          f"; offline de propósito {r.get('offline_de_proposito')}")
    for x in a.get("planos", []):
        print(f"  {x['inicio']:5} {x['arquivo']:18} {x['estado']:18} {x['motivo']} {x['aviso']}")
    for x in r.get("problemas", []):
        print("  problema:", x)


# ── o reposicionamento do colorista (camada Transform) e a camada 0 (o espaço de cor de entrada) ─────────────────────

ESTUDO = "/Volumes/SSD/MIDIAS DE TESTES/9 SAIDAS DOS APPS/_BASELIGHT/estudo"
#: S4: reposicionado (escala 1,2, x +100 px, y +50 px) — o S4 é o APARADO na v2; S6: reposicionado e ESTENDIDO
REPOSICAO = {"S4": (1.2, 1.2, 0.0, 100.0, 50.0), "S6": (1.5, 1.5, 3.0, -80.0, 0.0)}
#: S2: o colorista trocou o espaço de cor de ENTRADA (a camada 0)
ENTRADA = {"S2": "Legacy_Video"}


def reposicao_v1() -> None:
    sys.path.insert(0, os.path.join(ESTUDO, "ferramentas"))
    import blg_transform as T
    molde = open(os.path.join(ESTUDO, "conform", "BL04_shot8_payload.dec"), encoding="latin1").read()
    # ⚠️ (2026-11-22) a 1ª tentativa morreu com o delta aberto (espaço de cor inexistente no end_delta): a scene "BL09 V1
    # reposicao" ficou com a trava de escrita do flapid, e o bl-unlock -a não a tira. Daí o "2" e o cancel_delta abaixo.
    copiar("BL09 V1", "BL09 V1 reposicao2")
    flapi, c, s = B._abrir("BL09 V1 reposicao2")
    try:
      s.start_delta("BL09: o reposicionamento e a entrada do colorista")
      try:
        for (pid, *_), info in zip(B.V1, list(s.get_shot_ids())):
            sh = s.get_shot(info.ShotId)
            try:
                if pid in REPOSICAO:
                    res = sh.get_blg_resources()
                    sh.delete_all_layers()
                    sh.apply_blg_payload(T.gravar(T.transform(molde, *REPOSICAO[pid])), res)
                    sh.insert_cdl_layer(B._cdl(B.K[pid]))
                if pid in ENTRADA:
                    print(pid, "entrada antes:", sh.get_input_colour_space())
                    sh.set_input_colour_space(ENTRADA[pid])
                    print(pid, "entrada depois:", sh.get_input_colour_space())
            finally:
                sh.release()
        s.end_delta()
      except Exception:
        s.cancel_delta()
        raise
      s.save_scene()
    finally:
        s.close_scene()
        c.close()


def camada0(scene: str) -> None:
    """Plano a plano: o espaço de entrada, o formato de entrada e as camadas (para ver o Transform)."""
    sys.path.insert(0, os.path.join(AQUI, "..", "..", "..", "..", "2 ATIVOS", "_CICLO ASSIST", "modulos", "conformar",
                                    "motor", "baselight"))
    import atualizar as A
    flapi, c, s = B._abrir(scene, leitura=True)
    try:
        for info in s.get_shot_ids():
            sh = s.get_shot(info.ShotId)
            try:
                p = sh.get_blg_payload() or ""
                tr = [x for x in A.texto_blg(p).splitlines() if "GR_TransformRop" in x]
                print(info.StartFrame, os.path.basename(sh.get_sequence_descriptor().get_full_filename_with_F()),
                      [sh.get_src_start_frame(), sh.get_src_end_frame()], "entrada:", sh.get_input_colour_space(),
                      "formato:", sh.get_input_format(), "cores:", B.cores_do_plano(sh),
                      "camadas:", [x["nome"] for x in A.camadas(p)], "transform:", len(tr))
            finally:
                sh.release()
    finally:
        s.close_scene()
        c.close()


def main(argv: list[str]) -> int:
    cmd = argv[0]
    if cmd == "copiar":
        copiar(argv[1], argv[2])
    elif cmd == "grupos":
        print(json.dumps(grupos(argv[1]), ensure_ascii=False, indent=1))
    elif cmd == "grupos-v1":
        grupos_v1()
    elif cmd == "mp-grupos":
        mp_grupos(argv[1])
    elif cmd == "mt-preparar":
        mt_preparar()
    elif cmd == "conformar":            # conformar <xml> <scene>
        if argv[2] not in B.scenes():
            print(B.conformar(argv[1], argv[2], "--TimeType", "Source")[-800:])
    elif cmd == "trilhas":
        for p in ler_trilhas(argv[1]):
            print(p)
    elif cmd == "mt-colorir":
        mt_colorir(argv[1])
    elif cmd == "r-preparar":
        r_preparar()
    elif cmd == "produto-casado":
        produto_casado(argv[1], argv[2], argv[3])
    elif cmd == "reposicao-v1":
        reposicao_v1()
    elif cmd == "camada0":
        camada0(argv[1])
    elif cmd == "produto":
        produto(argv[1], argv[2], argv[3])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
