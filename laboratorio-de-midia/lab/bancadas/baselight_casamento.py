"""BL08, etapa 5 — o conform no Baselight e o placar por plano (caminhos A, B e C do plano
`2 ATIVOS/_CICLO ASSIST/docs/plano/2026-11-22-lab-casamento-baselight.md`).

    python3 -m lab.bancadas.baselight_casamento a                # A: bl-conform sozinho, um filtro por scene
    python3 -m lab.bancadas.baselight_casamento ler <scene>      # só lê e classifica uma scene já conformada

Quem decide se o plano está CERTO é a verdade da montagem (`premiere_casamento/montagem.json`: o original de cada
evento). Nota por plano: certo · alerta (offline/sem mídia: o editor VÊ) · errado (arquivo trocado, calado).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unicodedata

from ..casamento import SAIDA
from .avid_baselight import RAIZ

BL = "/Applications/Baselight/7.0.3.26500/Baselight-7.0.3.26500.app/Contents/bin"
PY_FL = "/Library/Application Support/FilmLight/python/3.12-v7-venv/bin/python"
LEITOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselight", "planos_da_scene.py")
JOB = "LAB_BASELIGHT"
TRAB = os.path.join(RAIZ, "saida", "bancadas", "baselight_casamento")
MONTAGEM = os.path.join(RAIZ, "saida", "bancadas", "premiere_casamento", "montagem.json")
XML = os.path.join(RAIZ, "saida", "bancadas", "premiere_casamento", "BL08_CASAMENTO.xml")
ORIGINAIS = os.path.join(SAIDA, "ORIGINAIS")
COPIAS_P9 = {"ORIGINAIS/DIA01/C002/C001C002.mov", "ORIGINAIS/BACKUP/DIA01/C002/C001C002.mov"}


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def conformar(scene: str, extras: list[str], xml: str = XML, srcs: list[str] | None = None) -> str:
    """`bl-conform` numa scene NOVA (apaga a de mesmo nome). Devolve a saída (o fim dela vai ao registro)."""
    args = [os.path.join(BL, "bl-conform"), "--edlname", xml, "--destscene", f"localhost:{JOB}:{scene}",
            "--delscene", "--fps", "23.976", "--space", "Video_Full"]
    for s in srcs or [f"dir={ORIGINAIS}"]:
        args += ["--src", s]
    r = subprocess.run(args + extras, capture_output=True, text=True, timeout=600)
    return (r.stdout + r.stderr).strip()


def ler(scene: str) -> list[dict]:
    r = subprocess.run([PY_FL, LEITOR, f"localhost:{JOB}:{scene}"], capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def classificar(planos: list[dict]) -> dict:
    with open(MONTAGEM, encoding="utf-8") as fh:
        eventos = json.load(fh)["eventos"]
    tl_q = 10594584000
    por_inicio = {int(e["premiere"]["inicio"]) // tl_q: e for e in eventos}
    base = 0                       # a sequência do Premiere começa no quadro 0 (E01)
    linhas, placar = [], {"certo": 0, "alerta": 0, "errado": 0}
    vistos = set()
    for p in sorted(planos, key=lambda p: p["inicio"]):
        e = por_inicio.get(p["inicio"] - base)
        if not e:
            continue
        vistos.add(e["evento"])
        arq = _nfc(p.get("arquivo"))
        rel = os.path.relpath(arq, _nfc(SAIDA)) if arq.startswith(_nfc(SAIDA)) else (arq or None)
        certo = _nfc(e["original_certo"])
        validos = COPIAS_P9 if e["pegadinha"] == "P9" else {certo}
        if e["pegadinha"] == "P10" and rel:
            ok = os.path.dirname(rel) == os.path.dirname(certo)
        else:
            ok = rel in validos
        nota = "certo" if ok else ("alerta" if not rel else "errado")
        placar[nota] += 1
        linhas.append({"evento": e["evento"], "pegadinha": e["pegadinha"], "nota": nota, "certo": certo,
                       "baselight": rel, "src_tc": p.get("src_tc"), "erro": p.get("erro")})
    for e in eventos:
        if e["evento"] not in vistos:
            placar["alerta"] += 1
            linhas.append({"evento": e["evento"], "pegadinha": e["pegadinha"], "nota": "alerta",
                           "certo": e["original_certo"], "baselight": None, "erro": "evento sem plano na scene"})
    return {"placar": placar, "linhas": sorted(linhas, key=lambda x: x["evento"])}


def _mostrar(nome: str, res: dict) -> None:
    print(f"== {nome}: {res['placar']}", flush=True)
    for x in res["linhas"]:
        print(f"  {x['evento']} {x['pegadinha']:4} {x['nota']:7} {x['baselight'] or '-'}"
              + ("" if x["nota"] == "certo" else f"   (certo: {x['certo']})") + (f"  [{x['erro']}]" if x.get("erro") else ""))


RENDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselight", "render_scene.py")


def faixas_com_midia(scene: str) -> list[tuple[int, int]]:
    """Os trechos da scene com mídia (planos offline fora), contíguos juntados."""
    out = []
    for p in sorted(ler(scene), key=lambda p: p["inicio"]):
        if not p.get("arquivo"):
            continue
        if out and out[-1][1] == p["inicio"]:
            out[-1] = (out[-1][0], p["fim"])
        else:
            out.append((p["inicio"], p["fim"]))
    return out


def renderizar(scene: str) -> tuple[str, list[tuple[int, int]]]:
    """ProRes dos trechos com mídia pela FLAPI (a INTERFACE do Baselight aberta: é ela que anda a fila local).
    Devolve (arquivo, faixas): o quadro N da scene está no render em (soma das faixas anteriores) + (N − início)."""
    faixas = faixas_com_midia(scene)
    pasta = os.path.join(TRAB, "renders", scene)
    os.makedirs(pasta, exist_ok=True)
    for n in os.listdir(pasta):
        if n.endswith(".mov"):
            os.remove(os.path.join(pasta, n))
    amb = dict(os.environ, RENDER_FAIXAS=";".join(f"{a},{b}" for a, b in faixas),
               PYTHONPATH="/Volumes/SSD/MIDIAS DE TESTES/9 SAIDAS DOS APPS/_BASELIGHT/estudo/ferramentas")
    r = subprocess.run([PY_FL, RENDER, f"localhost:{JOB}:{scene}", pasta], capture_output=True, text=True, timeout=1200,
                       env=amb)
    movs = [n for n in os.listdir(pasta) if n.endswith(".mov") and not n.startswith("._")]
    if not movs:
        raise RuntimeError("render sem arquivo: " + (r.stdout + r.stderr)[-1500:])
    with open(os.path.join(pasta, "faixas.json"), "w") as fh:
        json.dump(faixas, fh)
    return os.path.join(pasta, movs[0]), faixas


def _cor_media(mov: str, n: int, w: int, h: int) -> tuple[int, int, int]:
    """RGB médio de um pedaço do FUNDO (à esquerda, a meia altura: fora do painel de texto e do círculo)."""
    from .. import ffmpeg as F
    x0, y0, lw, lh = int(w * 0.03), int(h * 0.45), max(2, int(w * 0.04)), max(2, int(h * 0.1))
    bruto = F.rodar([F.achar("ffmpeg"), "-hide_banner", "-v", "error", "-i", mov, "-vf",
                     f"select=eq(n\\,{n}),crop={lw}:{lh}:{x0}:{y0}", "-fps_mode", "passthrough", "-frames:v", "1",
                     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], binario=True)
    k = len(bruto) // 3
    return tuple(round(sum(bruto[i::3]) / max(1, k)) for i in range(3))


def _camera_da_cor(rgb) -> int:
    from .. import video
    def dist(hexa):
        v = int(hexa, 16)
        return sum((a - b) ** 2 for a, b in zip(rgb, ((v >> 16) & 255, (v >> 8) & 255, v & 255)))
    return min(video.CORES_CAMERA, key=lambda c: dist(video.CORES_CAMERA[c]))


def _no_render(n: int, faixas: list) -> int | None:
    pos = 0
    for a, b in faixas:
        if a <= n < b:
            return pos + n - a
        pos += b - a
    return None


def conferir_render(mov: str, faixas: list) -> list[dict]:
    """O plano de cada evento NO RENDER: o quadro do meio dele → (quadro do original, rótulo do TC) pelo código de
    barras + a câmera pela cor ⇒ qual original entrou e em que ponto, contra a verdade (`verdade.json` + montagem)."""
    from .. import ffmpeg as F, ler, tc
    with open(MONTAGEM, encoding="utf-8") as fh:
        eventos = json.load(fh)["eventos"]
    with open(os.path.join(SAIDA, "verdade.json"), encoding="utf-8") as fh:
        orig = {_nfc(o["arquivo"]): o for o in json.load(fh)["originais"]}
    info = F.sondar(mov)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    w, h = v["width"], v["height"]
    tl_q, ticks_s = 10594584000, 254016000000
    linhas = []
    meios = {e["evento"]: _no_render(int(e["premiere"]["inicio"]) // tl_q + 24, faixas) for e in eventos}
    quadros = ler.quadros_cinza(mov, [n for n in meios.values() if n is not None], w, h)
    for e in eventos:
        n = meios[e["evento"]]
        if n is None:
            linhas.append({"evento": e["evento"], "pegadinha": e["pegadinha"], "nota": "alerta",
                           "porque": "plano sem mídia na scene (o Baselight mostra offline)"})
            continue
        q, rot = ler.ler_faixas(quadros[n], w, h)
        cam = _camera_da_cor(_cor_media(mov, n, w, h))
        o = orig[_nfc(e["original_certo"])]
        fps = tc.taxa(o["fps"])
        in_s = int(e["premiere"]["entrada"]) / ticks_s + 24 / (24000 / 1001)       # o meio do plano, na fonte
        q_esp = int(round(in_s * float(fps)))
        rot_esp = tc.rotulo(o["tc_inicio_quadros"] + q_esp, o["base"], o["drop_frame"])
        if e["pegadinha"] == "P9":
            camera_ok = cam == o["camera"]
        else:
            camera_ok = cam == o["camera"]
        dq = q - q_esp
        tol = max(1, round(float(fps) / 24))            # 1 quadro da timeline em quadros da fonte
        nota = "certo" if camera_ok and abs(dq) <= tol and rot - rot_esp == dq else "errado"
        if q == 0 and rot == 0:
            nota = "alerta"                              # sem imagem (offline: o Baselight mostra o aviso)
        linhas.append({"evento": e["evento"], "pegadinha": e["pegadinha"], "nota": nota, "camera": cam,
                       "camera_certa": o["camera"], "quadro": q, "quadro_certo": q_esp, "dif_quadros": dq,
                       "segundos_de_erro": round(dq / float(fps), 3)})
    return linhas


def como_o_disco_lista(rel: str) -> str:
    """O caminho relativo com cada nome COMO A PASTA O LISTA (no exFAT do Mac: NFD). Medido 2026-11-22, Baselight
    7.0.3: o xmeml com `CORAÇÃO_01` em NFC deixa o plano offline; em NFD, casa."""
    atual, partes = SAIDA, []
    for nome in rel.split("/"):
        achado = next((n for n in os.listdir(atual) if _nfc(n) == _nfc(nome)), nome)
        partes.append(achado)
        atual = os.path.join(atual, achado)
    return "/".join(partes)


PAPEL = os.path.join(RAIZ, "saida", "bancadas", "casamento_papel", "papel-nfc.json")
XML_B = os.path.join(TRAB, "BL08_CASAMENTO_B.xml")


def xml_b() -> dict:
    """O xmeml do caminho B: o do Premiere com cada `<file>` reescrito para o ORIGINAL que o Conformar decidiu
    (`casamento_papel --nfc`: caminho, taxa, TC — com DF —, duração, raster). Sem decisão (ambíguo, sem original) =
    OFFLINE de propósito (decisão do autor, 22/11): um caminho que não existe, com o nome marcado, para o Baselight
    não casar por conta própria."""
    import urllib.parse
    import xml.etree.ElementTree as ET
    from .. import tc
    with open(PAPEL, encoding="utf-8") as fh:
        decisao = {_nfc(x["daily"]): x for x in json.load(fh)["linhas"]}
    with open(os.path.join(SAIDA, "verdade.json"), encoding="utf-8") as fh:
        orig = {_nfc(o["arquivo"]): o for o in json.load(fh)["originais"]}
    arv = ET.parse(XML)
    prefixo = "file://localhost" + urllib.parse.quote(SAIDA) + "/"
    feitos = {}
    for f in arv.getroot().iter("file"):
        pu = f.find("pathurl")
        if pu is None:
            continue
        rel = _nfc(urllib.parse.unquote(pu.text.replace("file://localhost", "")))[len(_nfc(SAIDA)) + 1:]
        d = decisao[rel]
        if not d["original"]:
            nome = "OFFLINE_CICLO__" + os.path.basename(rel)
            pu.text = prefixo + urllib.parse.quote("OFFLINE/" + nome)
            f.find("name").text = nome
            feitos[rel] = {"estado": d["estado"], "xml": "offline"}
            continue
        o = orig[_nfc(d["original"])]
        fps = tc.taxa(o["fps"])
        base, ntsc = o["base"], "TRUE" if fps.denominator == 1001 else "FALSE"
        pu.text = prefixo + urllib.parse.quote(como_o_disco_lista(d["original"]))
        f.find("name").text = os.path.basename(d["original"])
        for r in [f.find("rate"), f.find("timecode/rate"), f.find("media/video/samplecharacteristics/rate")]:
            if r is not None:
                r.find("timebase").text, r.find("ntsc").text = str(base), ntsc
        f.find("duration").text = str(o["quadros"])
        t = f.find("timecode")
        t.find("string").text = tc.quadros_para_tc(o["tc_inicio_quadros"], base, o["drop_frame"])
        t.find("frame").text = str(o["tc_inicio_quadros"])
        t.find("displayformat").text = "DF" if o["drop_frame"] else "NDF"
        sc = f.find("media/video/samplecharacteristics")
        sc.find("width").text, sc.find("height").text = str(o["raster"][0]), str(o["raster"][1])
        feitos[rel] = {"estado": d["estado"], "xml": d["original"]}
    arv.write(XML_B, encoding="UTF-8", xml_declaration=True)
    return feitos


def caminho_b() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    feitos = xml_b()
    for k, v in feitos.items():
        print(f"  {k:42} → {v['xml']}", flush=True)
    out = {"xml": feitos}
    for nome, extras in (("FILENAME", ["--multiples", "--Filter", "Filename"]),):
        scene = f"BL08_B_{nome}"
        log = conformar(scene, extras, xml=XML_B)
        print(scene, "|", log.splitlines()[-1] if log else "", flush=True)
        res = classificar(ler(scene))
        _mostrar(scene, res)
        out[nome] = res
    with open(os.path.join(TRAB, "caminho_B.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    return out


MARCAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baselight", "marcar.py")


def tiras(scene: str) -> list[dict]:
    """As tiras de sequência da scene pelo `bl-shots` (in/out na FONTE, início/fim na scene, arquivo)."""
    r = subprocess.run([os.path.join(BL, "bl-shots"), f"localhost:{JOB}:{scene}", "-inputrange", "-outputrange"],
                       capture_output=True, text=True, timeout=120)
    out = []
    for linha in r.stdout.splitlines():
        partes = linha.split(None, 4)
        if len(partes) == 5 and all(x.lstrip("-").isdigit() for x in partes[:4]):
            out.append({"in": int(partes[0]), "out": int(partes[1]), "inicio": int(partes[2]), "fim": int(partes[3]),
                        "arquivo": partes[4].strip().strip('"')})
    return out


def caminho_c(edl: str | None = None, papel: str | None = None, scene: str = "BL08_C") -> dict:
    """B + a conferência DEPOIS do conform: cada plano × a decisão do Ciclo. Diferente → `bl-shots -replace` só naquele
    plano (a faixa de FONTE dele) + marker; sem decisão (offline de propósito) → marker com o motivo e os candidatos."""
    os.makedirs(TRAB, exist_ok=True)
    if edl is None:
        xml_b()
        edl = XML_B
    log = conformar(scene, ["--multiples", "--Filter", "Filename"], xml=edl)
    print(scene, "|", log.splitlines()[-1] if log else "", flush=True)
    with open(MONTAGEM, encoding="utf-8") as fh:
        eventos = json.load(fh)["eventos"]
    with open(papel or PAPEL, encoding="utf-8") as fh:
        decisao = {_nfc(x["daily"]): x for x in json.load(fh)["linhas"]}
    por_inicio = {t["inicio"]: t for t in tiras(scene)}
    trocas, marcas, acoes = [], [], []
    for e in eventos:
        q0 = int(e["premiere"]["inicio"]) // 10594584000
        d = decisao.get(_nfc(e["daily"]))
        if d is None:                      # o plano não está nesta montagem (o MC não linkou o daily com acento)
            acoes.append((e["evento"], "fora da montagem", ""))
            continue
        t = por_inicio.get(q0)
        if not d["original"]:
            cand = ", ".join(d["candidatos"]) or "nenhum arquivo com esse nome nas pastas"
            motivo = {"ambiguo": "AMBÍGUO — mais de um original possível; escolha e religue",
                      "sem_original": "SEM ORIGINAL — não achado pelo nome"}.get(d["estado"], d["estado"])
            marcas.append([q0, f"{e['evento']} {os.path.basename(e['daily'])}: {motivo}. Candidatos: {cand}"])
            acoes.append((e["evento"], "marker", motivo))
            continue
        certo = os.path.join(SAIDA, como_o_disco_lista(d["original"]))
        if t and _nfc(t["arquivo"]) != _nfc(certo) and not t["arquivo"].startswith("%C"):
            trocas.append(f'{t["in"]} {t["out"]} "{t["arquivo"]}" "{certo}"')
            marcas.append([q0, f"{e['evento']}: o conform pôs {os.path.relpath(_nfc(t['arquivo']), _nfc(SAIDA))}; "
                               f"trocado para {d['original']} (decisão do Ciclo: {d['estado']})"])
            acoes.append((e["evento"], "troca", t["arquivo"]))
        elif not t or t["arquivo"].startswith("%C"):
            marcas.append([q0, f"{e['evento']}: o Baselight não achou {d['original']}"])
            acoes.append((e["evento"], "marker", "não achado pelo Baselight"))
    if trocas:
        r = subprocess.run([os.path.join(BL, "bl-shots"), f"localhost:{JOB}:{scene}", "-replace", "-undomessage",
                            "Ciclo Assist: casamento"], input="\n".join(trocas) + "\n", capture_output=True, text=True,
                           timeout=300)
        print("troca:", (r.stdout + r.stderr).strip().splitlines()[-3:], flush=True)
    r = subprocess.run([PY_FL, MARCAR, f"localhost:{JOB}:{scene}"], input=json.dumps(marcas, ensure_ascii=False),
                       capture_output=True, text=True, timeout=300)
    print("markers:", (r.stdout or r.stderr).strip()[-300:], flush=True)
    for a in acoes:
        print("  ", *a, flush=True)
    res = classificar(ler(scene))
    res.update(trocas=trocas, marcas=marcas)
    _mostrar(scene, res)
    with open(os.path.join(TRAB, f"caminho_C_{scene}.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    return res


def caminho_a() -> dict:
    os.makedirs(TRAB, exist_ok=True)
    out = {}
    for filtro in ("Filename", "ClipName", "None"):
        scene = f"BL08_A_{filtro.upper()}"
        log = conformar(scene, ["--multiples", "--Filter", filtro])
        print(scene, "|", log.splitlines()[-1] if log else "", flush=True)
        try:
            res = classificar(ler(scene))
        except Exception as e:
            res = {"placar": None, "erro": str(e)[-500:]}
            print("  leitura falhou:", res["erro"], flush=True)
        res["log_fim"] = log.splitlines()[-15:]
        out[filtro] = res
        if res.get("placar"):
            _mostrar(scene, res)
    with open(os.path.join(TRAB, "caminho_A.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "a":
        caminho_a()
    elif sys.argv[1] == "b":
        caminho_b()
    elif sys.argv[1] == "c":
        caminho_c()
    elif sys.argv[1] == "render":
        mov, faixas = renderizar(sys.argv[2])
        print(mov, faixas)
        for x in conferir_render(mov, faixas):
            print(x)
    elif sys.argv[1] == "ler":
        _mostrar(sys.argv[2], classificar(ler(sys.argv[2])))
