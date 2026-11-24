"""BL09, o render da cor voltando PELO MEDIA COMPOSER (Ciclo Assist, 2026-11-23): a v2 do BL09 com o S3 trocado pelo
render que a cor devolveu (`RENDER_DA_COR/C001C003_COR.mov`, 47 quadros, TC 17:00:02:12, reel C001C003) montada no MC,
o AAF exportado pelo MC e o caminho do painel do De Lá Pra Cá com o Baselight (`/receber/originais` → revisão →
`/receber/preparar` com `destino: baselight` e `atualizar`), rodado no processo — o mesmo código das rotas.

    (o MC aberto no projeto LAB BASELIGHT 2398; o Baselight com a interface FECHADA — a estação só tem um NLE)
    <assist>/.venv/bin/python mc_render.py linkar | montar | exportar | ler
    (o MC fechado)
    <assist>/.venv/bin/python mc_render.py produto [colorista] [scene base]
"""
from __future__ import annotations

import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import atualizar_corte as B  # noqa: E402
import atualizar_corte_2 as B2  # noqa: E402

p = AQUI
while not os.path.isdir(os.path.join(p, "2 ATIVOS")):
    p = os.path.dirname(p)
ASSIST = os.path.join(p, "2 ATIVOS", "_CICLO ASSIST")
CONFORMAR = os.path.join(ASSIST, "modulos", "conformar")
sys.path[:0] = [os.path.join(CONFORMAR, "plugins", "media-composer", "servico"), os.path.join(CONFORMAR, "motor"),
                CONFORMAR, ASSIST]

PROJETO = "LAB BASELIGHT 2398"
BIN = "BL09 MC RENDER"
BIN_ABS = os.path.join(os.path.expanduser("~"), "Documents", "Avid Projects", PROJETO, BIN + ".avb")
TRAB = os.path.join(B.SAIDA, "mc_render")
SEQ = "BL09 V2 RENDER MC"
AAF = os.path.join(TRAB, "aaf_do_mc", SEQ.replace(" ", "_") + ".aaf")
FPS = 24000 / 1001


def _arquivo(nome: str) -> str:
    if nome == B2.R_NOME:
        return os.path.join(B2.RENDER, nome + ".mov")
    return os.path.join(B.ORIG, nome + ".mov")


def linkar() -> dict:
    from avid.acoes import Acoes
    from avid.mcapi import MediaComposer
    os.makedirs(TRAB, exist_ok=True)
    nomes = sorted({x[1] for x in B2.V2R})
    arq = os.path.join(TRAB, "linkados.json")
    feitos = json.load(open(arq, encoding="utf-8")) if os.path.exists(arq) else {}
    with MediaComposer() as m:
        a = Acoes(m)
        try:
            a.criar_bin(BIN)
        except Exception as e:                # noqa: BLE001 — a bin já existe (2ª rodada)
            print("bin:", str(e)[:120], flush=True)
        for n in [n for n in nomes if not feitos.get(n)]:
            t0 = time.time()
            feitos[n] = a.link_file(_arquivo(n), BIN + ".avb")
            print(f"{time.time() - t0:5.1f} s  {n} → {feitos[n]}", flush=True)
    with open(arq, "w", encoding="utf-8") as fh:
        json.dump(feitos, fh, indent=1)
    return feitos


def _urn(api: str) -> str:
    h = api.replace("-", "")
    return "urn:smpte:umid:" + ".".join(h[i:i + 8] for i in range(0, 64, 8))


def montar() -> dict:
    """A sequência gravada na bin (fechada no MC), como no BL08 (`avid_casamento.montar`): o in de cada plano em quadros
    desde o início do arquivo — o render entra do 4º quadro, 40 de duração (= o original 64..103)."""
    import avb
    from avid.mcapi import MediaComposer
    from cicloassist.avid import timeline as T
    linkados = json.load(open(os.path.join(TRAB, "linkados.json"), encoding="utf-8"))
    with MediaComposer() as m:
        try:
            m.fechar_bin(BIN_ABS)
        except Exception:                    # noqa: BLE001 — bin já fechada responde erro (normal)
            pass
        with avb.open(BIN_ABS) as f:
            masters = {str(mm.mob_id): mm for mm in f.content.mobs if mm.mob_type == "MasterMob"}
            entradas, taxa = [], None
            for _id, nome, ins, dur in B2.V2R:
                mm = masters[_urn(linkados[nome])]
                taxa = taxa or mm.edit_rate
                trilhas = tuple(sorted((t.media_kind, t.index) for t in mm.tracks if t.media_kind in ("picture", "sound")))
                entradas.append(T.Entrada(mob_id=str(mm.mob_id), duracao=dur, trilhas=trilhas, start_time=ins))
        T.acrescentar_timeline(BIN_ABS, SEQ, entradas, taxa, drop_frame=False)
        m.abrir_bin(BIN_ABS)
        fim, achada = time.time() + 120, {}
        while time.time() < fim and not achada:
            achada = {it.name: it.mob_id for it in m.itens_de(BIN_ABS, flags=("AllTypes",)) if it.name == SEQ}
            time.sleep(2)
    print(achada)
    with open(os.path.join(TRAB, "sequencia.json"), "w", encoding="utf-8") as fh:
        json.dump(achada, fh, indent=1)
    return achada


def exportar() -> str:
    from avid.mcapi import MediaComposer
    from relink import exportar_aaf
    mob = json.load(open(os.path.join(TRAB, "sequencia.json"), encoding="utf-8"))[SEQ]
    with MediaComposer() as m:
        aaf = exportar_aaf(m, mob, os.path.dirname(AAF), SEQ.replace(" ", "_"))
    print(aaf)
    return aaf


def ler() -> list:
    from aaf.parser import parse_aaf
    out = []
    for s in parse_aaf(AAF)["segments"]:
        if s.get("is_audio") or s.get("is_gap"):
            continue
        mr = s.get("media_ref") or {}
        out.append({k: s.get(k) for k in ("clip_name", "source_start_frames", "duration_frames", "timeline_tc_in")}
                   | {"tape": mr.get("tape_name"), "caminho": mr.get("local_path"), "tc": mr.get("source_tc_start")})
    for x in out:
        print(x)
    return out


def produto(colorista: str = "BL09 V1", base: str = "BL09 V2 render MC") -> dict:
    """O painel, sem o HTTP: `/receber/abrir` (o AAF avulso) → `/receber/originais` (o casamento dos masters com os
    originais das pastas: `relink.preparar`, rota carta) → `/receber/preparar` (destino baselight, atualizar)."""
    import relink
    import sessao_receber as SR
    rec = SR.SessaoReceber()
    aberto = rec.abrir(AAF)
    t = relink.Trabalho(rota="carta", carta=SR._carta_do_aaf(AAF), pastas=[B.ORIG], sequence=aberto.get("nome") or "")
    relink.preparar(t)
    for c in t.casamentos:
        print(f" casador: {c.master.nome:14} → {c.metodo:11} {os.path.basename(c.arquivo or c.sugestao or ''):14}"
              f" {c.confianca:.2f} {'REVISAR ' if c.precisa_de_revisao else ''}{c.motivo[:110]}")
    r = rec.preparar_avulso(aberto["chave"], "", t.decididos(), [B.ORIG],
                            sinais={"destino": "baselight", "job": B.JOB, "scene": base, "atualizar": colorista,
                                    "markers": True})
    bl = r["baselight"]
    a = bl.get("atualizar") or {}
    print(f"scene {bl['scene']}: {bl['planos']} planos {bl['contagem']}; cor conferida {a.get('conferidos')}/{a.get('de')}"
          f"; offline de propósito {r.get('offline')}; nos originais {r.get('nos_originais')}")
    for x in a.get("planos", []):
        print(f"  {x['inicio']:5} {x['arquivo']:18} {x['estado']:18} {x['motivo']} {x['aviso']}")
    for x in bl.get("problemas", []):
        print("  problema:", x)
    with open(os.path.join(TRAB, f"produto_{bl['scene'].replace(' ', '_').replace('·', '')}.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"casamentos": [c.to_dict() for c in t.casamentos], "resultado": r}, fh, indent=1,
                  ensure_ascii=False, default=str)
    return r


if __name__ == "__main__":
    cmd, *resto = sys.argv[1:]
    {"linkar": linkar, "montar": montar, "exportar": exportar, "ler": ler, "produto": produto}[cmd](*resto)
