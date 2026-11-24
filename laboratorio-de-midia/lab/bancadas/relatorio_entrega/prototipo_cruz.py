"""Protótipo do relatório de entrega (PRODA): completo × só atenção. Mede tempo e tamanho."""
import sys, os, json, time, base64, subprocess, html, hashlib
APP = "/Volumes/SSD/PROGRAMAS COM CLAUDE/2 ATIVOS/_DeLaPraCa"
sys.path.insert(0, APP + "/motor")
import cv2, numpy as np
from aaf.leitura import ler_timeline_aaf
from notas import das_notas
CONF = os.path.expanduser("~/Library/Caches/DeLaPraCa/Conferências/PRODA_CORTE.02.Exported.01 · 2026-10-24 13h30")
AAF = "/Volumes/SSD/MIDIAS DE TESTES/1 PRODUCOES/PRODUCAO-A/PRODA_RELINKER_ALTA.aaf"
TW, TH = 192, 108
t0 = time.time(); T = {}
plano = json.load(open(CONF + "/_interno/plano.json")); res = json.load(open(CONF + "/_interno/resultados.json"))
leitura = ler_timeline_aaf(AAF); notas = das_notas(leitura); T["ler"] = time.time() - t0
fps = 24
def tc(q):
    q += 3600 * fps
    return f"{q//86400:02d}:{q//1440%60:02d}:{q//24%60:02d}:{q%24:02d}"
def b64(img):
    ok, b = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 72]); return base64.b64encode(b).decode()
# miniaturas da timeline (os JPEG da conferência)
t = time.time(); mt = {}
for k, v in res.items():
    im = cv2.imread(CONF + "/" + v["imagem"], cv2.IMREAD_REDUCED_COLOR_8)   # decodifica já em 1/8 (240×135)
    mt[int(k)] = b64(cv2.resize(im, (TW, TH), interpolation=cv2.INTER_AREA))
T["thumbs_tl"] = time.time() - t
# miniaturas da referência: um passe do ffmpeg
t = time.time()
qs = sorted(mt)
from concurrent.futures import ThreadPoolExecutor
n = TW * TH * 3
rf = plano.get("ref_fps") or 23.976
def um(q):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{(q + 0.5) / rf:.4f}", "-i", plano["referencia"], "-frames:v", "1",
                        "-vf", f"scale={TW}:{TH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return q, (b64(np.frombuffer(r[:n], np.uint8).reshape(TH, TW, 3)) if len(r) >= n else "")
with ThreadPoolExecutor(6) as ex:
    mr = dict(ex.map(um, qs))
T["thumbs_ref"] = time.time() - t; print("ref:", len(mr), "de", len(qs))
# planos da timeline (vídeo) e os pontos
segs = [s for s in leitura["segments"] if not s.get("is_audio") and not s.get("is_gap")]
def quadro(s):
    h, m, ss, f = [int(x) for x in s["timeline_tc_in"].replace(";", ":").split(":")]; return ((h*60+m)*60+ss)*fps+f
total = max(quadro(s) + int(s["duration_frames"]) for s in segs)
trilhas = sorted({int(s["track"]) for s in segs})
pontos = {p["quadro"]: p for p in plano["pontos"]}
def atencao_no(q, trilha):
    for nt in notas:
        if nt.get("cor") and nt["inicio"] <= q < nt["inicio"] + nt["dur"]:
            return nt["cor"], nt.get("nome") or ""
    return None, ""
COR = {"refazer": "#d64541", "conferir": "#e0b400", "distorcao": "#c2185b", None: "#3aa65b"}
ROT = {"refazer": "refazer", "conferir": "conferir", "distorcao": "Stretch", None: "confere"}
cartoes = []
for q in qs:
    p = pontos.get(q, {}); corr = res[str(q)]["corr"]
    cor, txt = atencao_no(q, p.get("trilha"))
    if corr < 0.95: cor, txt = "refazer", f"diferente da referência (corr {corr:.3f})"
    cartoes.append({"q": q, "p": p, "corr": corr, "cor": cor, "txt": txt})
def pagina(so_atencao):
    lista = [c for c in cartoes if c["cor"]] if so_atencao else cartoes
    mapa = []
    for s in segs:
        a = quadro(s); w = int(s["duration_frames"])
        cor, _ = atencao_no(a, s["track"])
        mapa.append(f'<i style="left:{a/total*100:.3f}%;width:{max(w/total*100,0.08):.3f}%;top:{(len(trilhas)-trilhas.index(int(s["track"]))-1)*10}px;background:{COR[cor] if cor else "#5b6b7a"}" title="V{s["track"]} {html.escape(s.get("clip_name") or "")} {tc(a)}"></i>')
    for c in lista:
        mapa.append(f'<a href="#q{c["q"]}" class="pino" style="left:{c["q"]/total*100:.3f}%;background:{COR[c["cor"]]}"></a>')
    cards = []
    for c in lista:
        p = c["p"]
        cards.append(f'''<figure id="q{c["q"]}" style="--c:{COR[c["cor"]]}">
<div class="tc">{tc(c["q"])} <b>V{p.get("trilha","")}</b> · {"início" if p.get("ponta")=="entrada" else "fim"}</div>
<img src="data:image/jpeg;base64,{mr.get(c["q"],"")}" title="referência"><img src="data:image/jpeg;base64,{mt[c["q"]]}" title="timeline entregue">
<figcaption><span class="nome">{html.escape(p.get("arquivo",""))}</span><span class="st">{ROT[c["cor"]]} · {c["corr"]:.3f}</span>{('<span class="nt">'+html.escape(c["txt"][:90])+'</span>') if c["txt"] else ""}</figcaption></figure>''')
    n_at = sum(1 for c in cartoes if c["cor"])
    return f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Entrega {html.escape(plano["timeline"])}</title><style>
:root{{--bg:#16181b;--fg:#e8e8e8;--mut:#8a9099;--card:#202328}}
body{{margin:0;background:var(--bg);color:var(--fg);font:13px/1.35 -apple-system,Segoe UI,sans-serif}}
header{{padding:16px 20px;border-bottom:1px solid #2c3036}} h1{{font-size:17px;margin:0 0 6px}}
.termo{{color:var(--mut);display:flex;flex-wrap:wrap;gap:4px 18px}} .placar{{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}}
.placar span{{padding:3px 9px;border-radius:10px;background:#2a2e34}}
.mapa{{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 20px 6px;border-bottom:1px solid #2c3036}}
.faixa{{position:relative;height:{len(trilhas)*10+14}px}} .faixa i{{position:absolute;height:8px;border-radius:1px}}
.pino{{position:absolute;bottom:0;width:3px;height:12px;margin-left:-1px;border-radius:1px}}
.regua{{display:flex;justify-content:space-between;color:var(--mut);font-size:11px}}
.fita{{display:flex;gap:10px;overflow-x:auto;padding:16px 20px 24px;scroll-snap-type:x proximity}}
figure{{margin:0;flex:0 0 {TW}px;background:var(--card);border-top:3px solid var(--c);border-radius:4px;padding:6px;scroll-snap-align:start}}
figure img{{display:block;width:{TW}px;height:{TH}px;margin-bottom:3px;background:#000}}
.tc{{font-variant-numeric:tabular-nums;color:var(--mut);margin-bottom:4px}} .tc b{{color:var(--fg)}}
figcaption span{{display:block}} .nome{{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.st{{color:var(--c)}} .nt{{color:var(--mut);font-size:11.5px}} .leg{{color:var(--mut);font-size:11px;margin-top:4px}}
</style><header><h1>{"Pontos de atenção" if so_atencao else "Relatório de entrega"} — {html.escape(plano["timeline"])}</h1>
<div class="termo"><span>De Lá Pra Cá v0.1.148</span><span>DaVinci Resolve Studio 21.1</span><span>conferido em 24/10/2026 13h30</span>
<span>referência: {html.escape(os.path.basename(plano["referencia"]))}</span><span>{len(segs)} planos de vídeo · {len(qs)} quadros conferidos (início e fim de cada plano)</span></div>
<div class="placar"><span>✅ {sum(1 for c in cartoes if c["corr"]>=0.95)} de {len(cartoes)} conferem com a referência</span><span>🟡 {n_at} com atenção (notas)</span></div></header>
<div class="mapa"><div class="faixa">{"".join(mapa)}</div><div class="regua"><span>{tc(0)}</span><span>{tc(total//2)}</span><span>{tc(total)}</span></div>
<div class="leg">cada faixa é uma trilha (V1 embaixo) · os pinos levam ao quadro · em cima de cada cartão a referência, embaixo a timeline entregue</div></div>
<div class="fita">{"".join(cards)}</div></html>'''
for nome, so in (("completo", False), ("atencao", True)):
    t = time.time(); h = pagina(so); open(f"relatorio_{nome}.html", "w").write(h); T["html_" + nome] = time.time() - t
    print(nome, f"{len(h.encode())/1e6:.2f} MB", "sha256", hashlib.sha256(h.encode()).hexdigest()[:12])
T["total"] = time.time() - t0
print({k: round(v, 2) for k, v in T.items()})
