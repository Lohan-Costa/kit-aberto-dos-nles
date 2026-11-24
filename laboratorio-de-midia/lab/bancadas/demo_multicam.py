"""Bancada DEMO MULTICAM — o ROTEIRO DE DEMONSTRAÇÃO do laboratório e do piloto (demo de 2026-10-23, pedido do autor).

O teste é o M01 de 21/10 refeito do zero e de um jeito que se VÊ: o laboratório gera quatro câmeras e um gravador
(a CAM 4 sem timecode nenhum), a bancada abre o Premiere (o mais novo instalado; 2026 desde 22/10) com um projeto novo e importa tudo numa bin, o PILOTO
arrasta a bin para a janela do ÓRBITA STANDALONE e clica Sincronizar, e a régua confere a sequência montada contra a
verdade. O fim é um relatório com os gráficos, publicado como Artifact pela sessão. Nada passa pelo Ciclo Assist
(autor, 22/10: é uma operação, sem gastar turno do Assist).

    python -m lab.bancadas.demo_multicam preparar             # rodada nova: mídia (~75 s) + Órbita + Premiere
    python -m lab.bancadas.demo_multicam foto <nome> [legenda]
    python -m lab.bancadas.demo_multicam arrastar X0 Y0 X1 Y1 [legenda]   # coordenadas medidas na foto
    python -m lab.bancadas.demo_multicam clicar X Y [legenda]
    python -m lab.bancadas.demo_multicam esperar               # até a sequência aparecer (prazo de 6 min)
    python -m lab.bancadas.demo_multicam conferir              # régua + formas de onda + relatorio.html
    (e os passos soltos: nova · orbita · premiere · lado-a-lado)

A sessão OLHA a tela entre os gestos (regra máxima do piloto: nunca operar às cegas) — o roteiro inteiro, para a
sessão, está no CLAUDE.md do laboratório, seção "Roteiro de demonstração".

O que a bancada faz sozinha: fecha o Ciclo Assist se estiver aberto (o motor dele ocupa a porta 7817 do Órbita), abre
o `orbita.exe` de desenvolvimento, abre o Premiere e cria o projeto pela API — ou, se ela recusar, uma CÓPIA de `MODELO` (o `app.newProject` lançava "Unknown
error exception" no 23.6 — DRAMASYNC, handoff de 21/10; o modelo vazio foi criado pela tela uma vez) e põe as duas
janelas lado a lado. Recusa começar com o Media Composer aberto (um NLE por vez) ou com o Premiere aberto noutro
projeto. A ponte com o Premiere é a do Órbita (`com.orbita.ponte`, funções do `host.jsx` dele): a do laboratório não
está instalada no Windows.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from array import array

from .. import conferir_multicam, ffmpeg, multicam
from . import _piloto  # noqa: F401 — põe o piloto no caminho

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RECEITA = os.path.join(RAIZ, "receitas", "multicam", "DEMO_4CAMERAS.json")
SAIDA = os.path.join(RAIZ, "saida", "bancadas", "demo_multicam")
MODELO = os.path.join(SAIDA, "MODELO VAZIO 2023.prproj")
MODELO_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_multicam.html")
BIN = "DEMO 4 CAMERAS"
PREMIERE = "Adobe Premiere Pro.exe"
ORBITA = "http://127.0.0.1:7817"
ORBITA_EXE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "orbita-target", "debug", "orbita.exe")
ORBITA_EXE_NOME = "orbita.exe"
FPS = 25.0
ENVELOPE_S = 0.1          # uma barra da forma de onda a cada 100 ms


# ------------------------------------------------------------------ a rodada (uma pasta por ensaio/apresentação)

def _atual() -> str:
    with open(os.path.join(SAIDA, "ATUAL.txt"), encoding="utf-8") as fh:
        return fh.read().strip()


def _estado(rodada: str) -> dict:
    try:
        with open(os.path.join(rodada, "estado.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        return {"passos": [], "fotos": []}


def _gravar(rodada: str, e: dict) -> None:
    tmp = os.path.join(rodada, "estado.json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(e, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(rodada, "estado.json"))


def _passo(rodada: str, nome: str, inicio: float, **extra) -> None:
    e = _estado(rodada)
    e["passos"].append({"nome": nome, "inicio": inicio, "segundos": round(time.time() - inicio, 1), **extra})
    _gravar(rodada, e)


def _dizer(texto: str) -> None:
    print(time.strftime("%H:%M:%S"), texto, flush=True)


# ------------------------------------------------------------------ o piloto

def _foto(rodada: str, nome: str, legenda: str = "") -> str:
    from piloto import olhos
    pasta = os.path.join(rodada, "fotos")
    os.makedirs(pasta, exist_ok=True)
    arq = olhos.foto_da_tela(pasta, nome)
    e = _estado(rodada)
    e["fotos"].append({"arquivo": os.path.relpath(arq, rodada), "legenda": legenda or nome,
                       "quando": time.strftime("%H:%M:%S")})
    _gravar(rodada, e)
    _dizer(f"foto: {arq}")
    return arq


def _janela_orbita() -> int:
    from piloto import olhos
    h = olhos.janela_principal(ORBITA_EXE_NOME)
    if not h:
        raise SystemExit("a janela do Órbita não está aberta (rode `preparar`)")
    return h


def _posicionar(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    """Janela solta, no lugar e no tamanho pedidos (SW_RESTORE antes: maximizada, o MoveWindow não pega)."""
    import ctypes
    u = ctypes.windll.user32
    u.ShowWindow(hwnd, 9)
    time.sleep(0.3)
    u.MoveWindow(hwnd, x, y, w, h, True)


def _tela() -> tuple[int, int]:
    import ctypes
    from ctypes import wintypes
    r = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)    # SPI_GETWORKAREA: sem a barra
    return r.right - r.left, r.bottom - r.top


def lado_a_lado() -> None:
    """O Premiere à esquerda e o Órbita à direita, os dois inteiros na tela principal: o arrasto se vê de ponta a
    ponta, e as coordenadas da foto valem para o clique."""
    from piloto import olhos
    w, h = _tela()
    largura_orbita = 560
    p = olhos.janela_principal(PREMIERE)
    if p:
        _posicionar(p, 0, 0, w - largura_orbita, h)
    o = olhos.janela_principal(ORBITA_EXE_NOME)
    if o:
        _posicionar(o, w - largura_orbita, 0, largura_orbita, h)
        # por cima de tudo até o fim do teste: a janela da sessão (o terminal) cobria o Órbita na foto do ensaio
        _por_cima(o, True)


def orbita(rodada: str) -> None:
    """O Órbita STANDALONE (decisão do autor, 22/10: a demo do laboratório não passa pelo Ciclo Assist). O motor que
    a aba Preparar do Assist sobe usa a MESMA porta 7817: com o Assist aberto, quem responderia seria ele."""
    from piloto import olhos
    t = time.time()
    if olhos.rodando("AvidMediaComposer.exe"):
        raise SystemExit("o Media Composer está aberto: feche-o antes (um NLE por vez) e rode de novo")
    if olhos.rodando("cicloassist.exe"):
        _dizer("fechando o Ciclo Assist (o motor dele ocupa a porta do Órbita)")
        subprocess.run(["taskkill", "/IM", "cicloassist.exe"], capture_output=True)
        limite = time.time() + 30
        while olhos.rodando("cicloassist.exe") and time.time() < limite:
            time.sleep(1)
        if olhos.rodando("cicloassist.exe"):
            subprocess.run(["taskkill", "/F", "/IM", "cicloassist.exe"], capture_output=True)
        time.sleep(3)                                    # os motores saem junto com a janela
    if not olhos.janela_principal(ORBITA_EXE_NOME):
        if olhos.rodando(ORBITA_EXE_NOME):               # um motor sem janela (o do Assist) que ficou para trás
            subprocess.run(["taskkill", "/F", "/IM", ORBITA_EXE_NOME], capture_output=True)
            time.sleep(2)
        _dizer("abrindo o Órbita")
        subprocess.Popen([ORBITA_EXE], cwd=os.path.dirname(ORBITA_EXE), close_fds=True)
    limite = time.time() + 90
    while True:
        try:
            if olhos.janela_principal(ORBITA_EXE_NOME):
                _orbita("/conexao")
                break
        except (OSError, RuntimeError):
            pass
        if time.time() > limite:
            _foto(rodada, "orbita_nao_abriu", "o Órbita não abriu em 90 s")
            raise TimeoutError("o Órbita não respondeu na 7817 em 90 s")
        time.sleep(2)
    lado_a_lado()
    _passo(rodada, "orbita", t)


def _por_cima(hwnd: int, sim: bool) -> None:
    """O alvo do arrasto fica por cima: o clique na origem traria o Premiere à frente e cobriria a janela.
    ⛔ Sem `argtypes` o HWND_TOPMOST (-1) vai como int de 32 bits e não faz nada, calado (skill do piloto)."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                               ctypes.c_int, ctypes.c_uint]
    u.SetWindowPos(hwnd, wintypes.HWND(-1 if sim else -2), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)


def arrastar(rodada: str, x0: int, y0: int, x1: int, y1: int, legenda: str) -> None:
    from piloto import maos_windows as mw
    t = time.time()
    _foto(rodada, "arrasto_1_antes", legenda + " — antes")
    alvo = _janela_orbita()
    _por_cima(alvo, True)
    time.sleep(0.5)
    try:
        mw.checar_freio()
        mw._enviar(mw._ponto(x0, y0, mw.MOUSEEVENTF_MOVE)); time.sleep(0.2)
        mw._enviar(mw._ponto(x0, y0, mw.MOUSEEVENTF_LEFTDOWN)); time.sleep(0.3)
        for k in range(1, 6):                        # sair do limiar de arrasto devagar, como a mão
            mw._enviar(mw._ponto(x0 + 4 * k, y0 + 2 * k, mw.MOUSEEVENTF_MOVE)); time.sleep(0.05)
        for k in range(1, 41):
            mw.checar_freio()
            mw._enviar(mw._ponto(x0 + (x1 - x0) * k / 40, y0 + (y1 - y0) * k / 40, mw.MOUSEEVENTF_MOVE))
            time.sleep(0.03)
        time.sleep(0.8)
        _foto(rodada, "arrasto_2_meio", legenda + " — no meio do gesto, botão apertado")
        mw._enviar(mw._ponto(x1, y1, mw.MOUSEEVENTF_LEFTUP)); time.sleep(1.5)
    finally:
        _por_cima(alvo, True)                        # continua por cima (lado_a_lado); o `conferir` solta
    _foto(rodada, "arrasto_3_solto", legenda + " — solto")
    _passo(rodada, "arrastar", t, de=[x0, y0], para=[x1, y1])


def clicar(rodada: str, x: int, y: int, legenda: str) -> None:
    from piloto import maos
    t = time.time()
    maos.checar_freio()
    maos.clicar(x, y)
    time.sleep(1.2)
    _foto(rodada, "clique_" + time.strftime("%H%M%S"), legenda)
    _passo(rodada, "clicar", t, ponto=[x, y], legenda=legenda)


# ------------------------------------------------------------------ o Órbita e a ponte dele com o Premiere

def _token() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    with open(os.path.join(base, "Orbita", "plugin-token"), encoding="utf-8") as fh:
        return fh.read().strip()


def _orbita(caminho: str, corpo: dict | None = None, prazo: float = 15) -> dict:
    req = urllib.request.Request(ORBITA + caminho, data=json.dumps(corpo).encode() if corpo is not None else None,
                                 headers={"Content-Type": "application/json", "X-Orbita-Token": _token()},
                                 method="POST" if corpo is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=prazo) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Órbita HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None


def ponte(funcao: str, *args, prazo: float = 120) -> str:
    """Uma função do `host.jsx` do Órbita no Premiere: enfileira e pergunta pelo resultado, com prazo."""
    pid = _orbita("/premiere/chamar", {"funcao": funcao, "args": list(args)})["id"]
    limite = time.time() + prazo
    while time.time() < limite:
        r = _orbita(f"/premiere/resultado?id={pid}")
        if r.get("pronto"):
            return str(r.get("r") or "")
        if r.get("viva") is False:
            raise RuntimeError("a ponte do Premiere caiu no meio do pedido")
        time.sleep(0.4)
    raise TimeoutError(f"{funcao}: o Premiere não respondeu em {prazo:.0f} s")


def _premiere_vivo_sem_dialogo(rodada: str) -> None:
    from piloto import olhos
    if not olhos.rodando(PREMIERE):
        _foto(rodada, "premiere_caiu", "o Premiere não está mais rodando")
        raise RuntimeError("o Premiere fechou ou caiu")
    d = olhos.dialogos(PREMIERE)
    if d:
        _foto(rodada, "dialogo", f"diálogo do Premiere: {d[0].get('titulo', '')}")
        raise RuntimeError(f"o Premiere abriu um diálogo ({d[0].get('titulo', '')!r}): olhe a foto e decida")


def _premiere_exe() -> str:
    """O Premiere mais NOVO instalado. O 2023 quebrou nesta máquina em 22/10 (caía ao abrir, 2 de 2) e o autor
    instalou o 2026: a bancada não fixa versão."""
    base = r"C:\Program Files\Adobe"
    anos = sorted(d for d in os.listdir(base) if d.startswith("Adobe Premiere Pro 20")
                  and os.path.exists(os.path.join(base, d, PREMIERE)))
    if not anos:
        raise SystemExit("não achei o Premiere Pro instalado")
    return os.path.join(base, anos[-1], PREMIERE)


def _esperar_ponte(rodada: str, t: float, prazo: float = 240) -> None:
    limite = time.time() + prazo
    while True:
        try:
            if _orbita("/conexao").get("premiere"):
                ponte("orbitaEstado", prazo=20)
                return
        except (OSError, RuntimeError, TimeoutError):
            pass
        if time.time() > limite:
            _foto(rodada, "premiere_sem_ponte", f"o Premiere não ligou a ponte em {prazo:.0f} s")
            raise TimeoutError("o Premiere não conectou ao Órbita (a ponte com.orbita.ponte está instalada? "
                               "o Órbita instala pela rota /app/instalar-premiere)")
        if time.time() - t > 20:
            _premiere_vivo_sem_dialogo(rodada)
        time.sleep(3)


def premiere(rodada: str) -> None:
    """Abre o Premiere e CRIA o projeto da rodada. Primeiro pela API (`orbitaNovoProjeto` → `app.newProject`); se ela
    recusar (o 23.6 lançava "Unknown error exception"), reabre o Premiere com uma cópia de `MODELO`."""
    from piloto import olhos
    t = time.time()
    projeto = os.path.join(rodada, "DEMO 4 CAMERAS.prproj")
    if olhos.rodando(PREMIERE):
        aberto = ""
        try:
            aberto = ponte("orbitaProjectPath", prazo=20)
        except Exception:  # noqa: BLE001 — a pergunta é só para dar a mensagem certa
            pass
        if aberto and os.path.normcase(aberto) != os.path.normcase(projeto):
            raise SystemExit(f"o Premiere já está aberto com outro projeto ({aberto}): feche-o e rode de novo")
    else:
        _dizer("abrindo o Premiere")
        subprocess.Popen([_premiere_exe()], close_fds=True)
    _esperar_ponte(rodada, t)
    r = ponte("orbitaNovoProjeto", projeto, prazo=120)
    _dizer(f"novo projeto: {r}")
    if os.path.normcase(r) != os.path.normcase(projeto):
        if not os.path.exists(MODELO):
            raise RuntimeError(f"o Premiere não criou o projeto ({r}) e não há {MODELO}")
        _dizer("a API não criou o projeto; abrindo uma cópia do modelo vazio")
        shutil.copy2(MODELO, projeto)
        subprocess.Popen([_premiere_exe(), projeto], close_fds=True)
        limite = time.time() + 120
        while os.path.normcase(ponte("orbitaProjectPath", prazo=20)) != os.path.normcase(projeto):
            if time.time() > limite:
                raise TimeoutError("o Premiere não abriu o modelo")
            time.sleep(3)
    try:
        e = _estado(rodada)
        e["premiere"] = ponte("orbitaAppVersion", prazo=20)
        _gravar(rodada, e)
    except (OSError, RuntimeError, TimeoutError):
        pass
    _dizer("ponte viva; importando a mídia")
    midia = os.path.join(rodada, "midia")
    with open(os.path.join(midia, "verdade.json"), encoding="utf-8") as fh:
        v = json.load(fh)
    caminhos = [os.path.join(midia, a["arquivo"]).replace("/", "\\") for a in v["arquivos"]]
    rotulos = [c + "\t" + a["fonte"] for c, a in zip(caminhos, v["arquivos"])]
    r = ponte("orbitaImportMissing", "\n".join(caminhos), BIN, "\n".join(rotulos), prazo=180)
    _dizer(f"import: {r}")
    if not r.startswith("ok|"):
        raise RuntimeError(f"o import falhou: {r}")
    ponte("orbitaSelecionarBin", BIN)
    lado_a_lado()
    time.sleep(1.5)
    _foto(rodada, "premiere_importado", f"o Premiere com a bin {BIN} (CAM 1–4 e SOM DIRETO)")
    _passo(rodada, "premiere", t, importou=r)


def esperar(rodada: str, prazo: float = 360) -> None:
    """Do clique em Sincronizar até a sequência montada aparecer no Premiere — sem esperar para sempre."""
    t = time.time()
    ultima = time.time()
    anterior = ""
    while time.time() - t < prazo:
        r = ""
        try:
            r = ponte("orbitaResumoDaSequencia", prazo=30)
        except (OSError, RuntimeError, TimeoutError) as e:
            r = f"err|{e}"
        # completa = duas leituras iguais seguidas: uma leitura no meio da montagem passaria por sequência pronta
        pronta = not r.startswith("err|") and r.count("\n") >= 10 and r == anterior
        anterior = r
        if pronta:
            with open(os.path.join(rodada, "resumo.txt"), "w", encoding="utf-8") as fh:
                fh.write(r)
            _dizer(f"sequência montada: {r.splitlines()[0].split(chr(9))[-1]} ({r.count(chr(10))} clipes)")
            _passo(rodada, "esperar a sequência", t)
            time.sleep(2)
            _foto(rodada, "premiere_sequencia", "a sequência que o Órbita montou no Premiere")
            return
        if time.time() - ultima > 60:              # vigia de minuto em minuto: a tela, o processo, os diálogos
            ultima = time.time()
            _premiere_vivo_sem_dialogo(rodada)
            _foto(rodada, "esperando_" + time.strftime("%H%M%S"), "esperando o sync")
        time.sleep(3)
    _foto(rodada, "sem_sequencia", f"nenhuma sequência em {prazo:.0f} s")
    raise TimeoutError(f"a sequência não apareceu em {prazo:.0f} s")


# ------------------------------------------------------------------ a régua e o relatório

def _envelope(arquivo: str) -> list[float]:
    """RMS a cada ENVELOPE_S do som (mono, 8 kHz), em 0–1 — o desenho da forma de onda, sem numpy."""
    taxa = 8000
    bruto = ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-v", "error", "-i", arquivo, "-map", "0:a:0", "-ac", "1", "-ar", str(taxa),
                          "-f", "s16le", "-"], binario=True)
    bruto = getattr(bruto, "stdout", bruto)
    a = array("h")
    a.frombytes(bruto[: len(bruto) // 2 * 2])
    n = int(taxa * ENVELOPE_S)
    env = []
    for i in range(0, len(a) - n + 1, n):
        s = 0
        for x in a[i:i + n]:
            s += x * x
        env.append((s / n) ** 0.5)
    pico = max(env) or 1.0
    return [round(e / pico, 3) for e in env]


def _jpeg(arquivo: str, largura: int = 1280) -> str:
    """A foto vira JPEG pequeno embutido (data: URI) — o relatório é um arquivo só."""
    saida = arquivo + ".rel.jpg"
    ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-v", "error", "-y", "-i", arquivo, "-vf", f"scale={largura}:-2", "-q:v", "5", saida])
    with open(saida, "rb") as fh:
        return "data:image/jpeg;base64," + base64.b64encode(fh.read()).decode()


def mosaico(rodada: str, instante: float = 20.0) -> str:
    """As quatro câmeras no MESMO instante da cena: quatro cores, e a CAM 4 marcando outro relógio."""
    midia = os.path.join(rodada, "midia")
    with open(os.path.join(midia, "verdade.json"), encoding="utf-8") as fh:
        v = json.load(fh)
    quadros = []
    for a in v["arquivos"]:
        if a["som"] or not (a["inicio_na_cena_s"] <= instante < a["inicio_na_cena_s"] + a["duracao_na_cena_s"]):
            continue
        if any(q[0] == a["fonte"] for q in quadros):
            continue
        n = round((instante - a["inicio_na_cena_s"]) * FPS)        # quadro por posição: nunca -ss (regra da casa)
        png = os.path.join(rodada, f"_q{len(quadros)}.png")
        ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-v", "error", "-y", "-i", os.path.join(midia, a["arquivo"]), "-vf",
                      f"select=eq(n\\,{n}),scale=640:-2", "-fps_mode", "passthrough", "-frames:v", "1", png])
        quadros.append((a["fonte"], png))
    quadros.sort()
    saida = os.path.join(rodada, "mosaico.png")
    ent = sum((["-i", q[1]] for q in quadros[:4]), [])
    ffmpeg.rodar([ffmpeg.achar("ffmpeg"), "-v", "error", "-y", *ent, "-filter_complex", "[0][1]hstack[a];[2][3]hstack[b];[a][b]vstack", saida])
    for q in quadros:
        os.remove(q[1])
    return saida


def conferir(rodada: str) -> str:
    t = time.time()
    midia = os.path.join(rodada, "midia")
    with open(os.path.join(midia, "verdade.json"), encoding="utf-8") as fh:
        v = json.load(fh)
    resumo = conferir_multicam.ler_resumo(os.path.join(rodada, "resumo.txt"))
    r = conferir_multicam.conferir(v, resumo, FPS)
    with open(os.path.join(rodada, "regua.json"), "w", encoding="utf-8") as fh:
        json.dump(r, fh, ensure_ascii=False, indent=1)
    _dizer(f"régua: {r['veredito']} (pior {r['pior_erro_quadros']} quadro)")
    na_seq = {}
    for _trilha, nome, ini, _fim in resumo:
        na_seq.setdefault(nome, ini)
    seq = next((ln.split("\t")[1] for ln in open(os.path.join(rodada, "resumo.txt"), encoding="utf-8")
                if ln.startswith("SEQ\t")), "")
    fontes = []
    for f in json.loads(open(RECEITA, encoding="utf-8").read())["fontes"]:
        fontes.append({"nome": f["nome"], "som": bool(f.get("som")), "sem_tc": f.get("tc") == "nenhum"})
    arquivos = []
    for a, ln in zip(v["arquivos"], r["arquivos"]):
        nome = os.path.basename(a["arquivo"])
        medido = (na_seq[nome] - r["zero_s"]) if nome in na_seq else None
        arquivos.append({"arquivo": nome, "fonte": a["fonte"], "som": a["som"], "tomada": a["tomada"],
                         "inicio": a["inicio_na_cena_s"], "duracao": a["duracao_na_cena_s"], "tc": a["tc"],
                         "medido": None if medido is None else round(medido, 3),
                         "erro_ms": ln.get("erro_ms"), "erro_quadros": ln.get("erro_quadros"),
                         "atraso_ms": a.get("atraso_ms"), "explicado": ln.get("explicado_pelo_atraso", False),
                         "envelope": _envelope(os.path.join(midia, a["arquivo"]))})
    e = _estado(rodada)
    fotos = [{"src": _jpeg(os.path.join(rodada, f["arquivo"])), "legenda": f["legenda"], "quando": f["quando"]}
             for f in e["fotos"]]
    dados = {"caso": v["caso"], "pergunta": v["pergunta"], "rodada": os.path.basename(rodada), "sequencia": seq,
             "quando": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "fps": FPS, "envelope_s": ENVELOPE_S,
             "cena_s": v["cena"]["segundos"], "relogio": v["cena"]["relogio"], "veredito": r["veredito"],
             "pior_erro_quadros": r["pior_erro_quadros"], "fora": r["fora_da_sequencia"],
             "premiere": e.get("premiere", ""), "fontes": fontes, "arquivos": arquivos, "passos": e["passos"], "fotos": fotos,
             "mosaico": _jpeg(os.path.join(rodada, "mosaico.png"), 1280)}
    with open(MODELO_HTML, encoding="utf-8") as fh:
        html = fh.read()
    # `</` dentro de JSON fecharia o <script>: escapado
    html = html.replace("/*DADOS*/null", json.dumps(dados, ensure_ascii=False).replace("</", "<\\/"))
    saida = os.path.join(rodada, "relatorio.html")
    with open(saida, "w", encoding="utf-8") as fh:
        fh.write(html)
    _passo(rodada, "conferir", t)
    try:
        _por_cima(_janela_orbita(), False)
    except SystemExit:
        pass
    _dizer(f"relatório: {saida}")
    return saida


def nova() -> str:
    t = time.time()
    rodada = os.path.join(SAIDA, datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(rodada)
    with open(os.path.join(SAIDA, "ATUAL.txt"), "w", encoding="utf-8") as fh:
        fh.write(rodada)
    _gravar(rodada, {"passos": [], "fotos": []})
    _dizer(f"rodada {rodada}")
    multicam.gerar(RECEITA, os.path.join(rodada, "midia"), avisar=lambda s: _dizer(s))
    _dizer(f"mosaico: {mosaico(rodada)}")
    _passo(rodada, "gerar a mídia", t)
    return rodada


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Bancada da demo: multicam sintético → Premiere → Órbita, pelo piloto.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("nova")
    sub.add_parser("premiere")
    sub.add_parser("preparar")
    sub.add_parser("lado-a-lado")
    p = sub.add_parser("foto"); p.add_argument("nome"); p.add_argument("legenda", nargs="?", default="")
    p = sub.add_parser("arrastar")
    for k in ("x0", "y0", "x1", "y1"):
        p.add_argument(k, type=int)
    p.add_argument("legenda", nargs="?", default="o piloto arrasta a bin do Premiere para o Órbita")
    p = sub.add_parser("clicar"); p.add_argument("x", type=int); p.add_argument("y", type=int)
    p.add_argument("legenda", nargs="?", default="clique")
    p = sub.add_parser("esperar"); p.add_argument("--prazo", type=float, default=360)
    sub.add_parser("conferir")
    a = ap.parse_args(argv)
    if a.cmd == "nova":
        nova()
        return 0
    if a.cmd == "lado-a-lado":
        lado_a_lado()
        return 0
    if a.cmd == "preparar":                       # tudo o que não é gesto do piloto, de uma vez
        rodada = nova()
        orbita(rodada)
        premiere(rodada)
        return 0
    rodada = _atual()
    if a.cmd == "premiere":
        premiere(rodada)
    elif a.cmd == "foto":
        _foto(rodada, a.nome, a.legenda)
    elif a.cmd == "arrastar":
        arrastar(rodada, a.x0, a.y0, a.x1, a.y1, a.legenda)
    elif a.cmd == "clicar":
        clicar(rodada, a.x, a.y, a.legenda)
    elif a.cmd == "esperar":
        esperar(rodada, a.prazo)
    elif a.cmd == "conferir":
        conferir(rodada)
    return 0


if __name__ == "__main__":
    sys.exit(main())
