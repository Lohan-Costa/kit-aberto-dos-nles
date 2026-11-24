"""VIGIA — o cão de guarda e os diálogos, o MESMO no Windows e no macOS (as mãos e os olhos de cada sistema têm as
mesmas funções; o que é só de um sistema mora em `vigia_windows.py` / `vigia_macos.py`).

Duas regras do autor (2026-10-11) moram aqui:
- "Nenhuma espera sem prazo": toda ação longa roda em `com_prazo` — checagem periódica de app vivo, janela
  respondendo, queda nova no EVENTLOG (MC) e diálogos; estourou o prazo = foto da tela + `Travado`. Nunca esperar
  para sempre.
- O diálogo CONHECIDO é resolvido sozinho; o DESCONHECIDO vira foto + `DialogoAberto` e NUNCA leva clique (o piloto
  para e mostra a foto). Diálogo novo que se repete entra no catálogo do app (`catalogos/<app>/catalogo.json` + a
  foto), com o que fazer.

O diálogo Qt (MC, Resolve) não expõe texto nem botões e o título pode ser genérico: o conhecido é reconhecido pela
FOTO — mesma proporção (± 3 %), levada à escala da referência, diferença média < `limite` (12/255) sem a barra de
título. Tolera a escala da tela (o mesmo diálogo sai com 581 px a 125 % e 465 a 100 %).
"""
from __future__ import annotations

import json
import os
import threading
import time

import sys

if sys.platform == "win32":
    from . import maos_windows as M
    from . import olhos_windows as O
else:
    from . import maos_macos as M
    from . import olhos_macos as O


class DialogoAberto(RuntimeError):
    """Um diálogo desconhecido apareceu: foto em `.foto`, título em `.titulo`."""
    def __init__(self, titulo: str, foto: str):
        super().__init__(f"diálogo aberto: {titulo!r} (foto: {foto})")
        self.titulo, self.foto = titulo, foto


class Travado(RuntimeError):
    """O app parou de responder, caiu, ou a ação não terminou no prazo. `.foto` = a tela no momento."""
    def __init__(self, motivo: str, foto: str | None = None):
        super().__init__(motivo + (f" (foto: {foto})" if foto else ""))
        self.motivo, self.foto = motivo, foto


# ── catálogo por imagem ──────────────────────────────────────────────────────────────────────────────────────────
def carregar_catalogo(pasta: str) -> list[dict]:
    arq = os.path.join(pasta, "catalogo.json")
    if not os.path.isfile(arq):
        return []
    with open(arq, encoding="utf-8") as f:
        itens = json.load(f)
    for it in itens:
        it["_foto"] = os.path.join(pasta, it["foto"])
    return itens


def reconhecer(foto: str, catalogo: list[dict]) -> dict | None:
    """A entrada do catálogo que bate com a foto do diálogo, ou None. A devolvida leva `_escala` (para o clique)."""
    from PIL import Image, ImageChops, ImageStat
    try:
        a = Image.open(foto).convert("L")
    except OSError:
        return None
    for it in catalogo:
        try:
            b = Image.open(it["_foto"]).convert("L")
        except OSError:
            continue
        sx, sy = a.width / b.width, a.height / b.height
        if abs(sx - sy) > 0.03 * max(sx, sy):
            continue
        # ⛔ só a escala de MONITOR (100 % × 125 % = 0,8): o aviso "Some sequences could not be committed" (482×113)
        # bateu com o "layout de teclado (não corresponde)" (753×179, dif 11,6) a 0,64 — o cão de guarda clicou no
        # vazio por 10 min em vez de parar com a foto (2026-10-13)
        if not 0.75 <= sx <= 1.34:
            continue
        a2 = a.resize((b.width, b.height)) if (a.width, a.height) != (b.width, b.height) else a
        corte = 24                                                  # a barra de título, na escala da referência
        dif = ImageStat.Stat(ImageChops.difference(a2.crop((0, corte, b.width, b.height)),
                                                   b.crop((0, corte, b.width, b.height)))).mean[0]
        if dif < it.get("limite", 12):
            return dict(it, _escala=(sx, sy))
    return None


def agir(hwnd: int, entrada: dict) -> bool:
    """Faz o que o catálogo manda (clique num ponto da janela, em pixels da foto de referência, ou tecla ENTER/ESC) e
    devolve se a janela sumiu."""
    if not M.frente(hwnd):
        O.fechar(hwnd)                                          # sem foco: fechar direto (WM_CLOSE / botão de fechar)
    elif "clique" in entrada:
        sx, sy = entrada.get("_escala", (1.0, 1.0))
        M.clicar(*M.relativo(hwnd, int(entrada["clique"][0] * sx), int(entrada["clique"][1] * sy)))
    else:
        M.tecla({"ENTER": M.ENTER, "ESC": M.ESC}[entrada.get("tecla", "ESC")])
    time.sleep(1.0)
    return not O.existe(hwnd)


def varrer(imagem: str, catalogo: list[dict], pasta_fotos: str, ignorar: tuple = (), contexto: str = "") -> list[dict]:
    """Uma passada: cada diálogo visível do app é fotografado; o do catálogo é resolvido, o desconhecido levanta
    `DialogoAberto` (com a foto). `ignorar` = títulos que NÃO são modais. Entrada com `"so_quando"` só vale no
    `contexto` dito (ex.: "Leave the application?" só quando o piloto mandou sair); com `"esperar": true` só passa
    (tela de abertura, barra de progresso). Devolve o que foi resolvido."""
    from PIL import Image, ImageStat
    feitos = []
    for d in O.dialogos(imagem):
        if d["titulo"] in ignorar:
            continue
        foto = O.fotografar(d["hwnd"], os.path.join(pasta_fotos, time.strftime("%H%M%S") + f"_{d['hwnd']}{O.EXT_FOTO}"))
        # foto UNIFORME = a janela ainda não se desenhou (a de progresso do MC, fotografada cedo, 2026-10-11): é cedo,
        # não é desconhecida — a próxima passada olha de novo
        try:
            if ImageStat.Stat(Image.open(foto).convert("L")).stddev[0] < 2.0:
                continue
        except OSError:
            pass
        it = reconhecer(foto, [c for c in catalogo if c.get("so_quando") in (None, contexto)])
        if it is None:
            raise DialogoAberto(d["titulo"], foto)
        if it.get("esperar"):
            continue
        feitos.append({"nome": it["nome"], "ok": agir(d["hwnd"], it)})
    return feitos


# ── o cão de guarda ──────────────────────────────────────────────────────────────────────────────────────────────
def ultimas_do_eventlog(eventlog: str | None, n: int = 10) -> list[str]:
    """As últimas linhas de um log de eventos do app (o do MC: `AAAAMMDDhhmmss Tipo Mensagem`, separado com NUL)."""
    if not eventlog:
        return []
    try:
        with open(eventlog, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 20000))
            txt = f.read().replace(b"\0", b"").decode("utf-8", "replace")
    except OSError:
        return []
    return [l.strip() for l in txt.replace("\r", "\n").split("\n") if l.strip()][-n:]


def com_prazo(acao, prazo: float, imagem: str, pasta_fotos: str, catalogo: list[dict] | None = None,
              pronto=None, intervalo: float = 2.0, ignorar: tuple = (), eventlog: str | None = None, saude=None):
    """Roda `acao()` numa thread e, até ela terminar e `pronto()` (opcional) dar verdadeiro, checa a cada `intervalo`
    o app (`imagem`): vivo, respondendo, sem falha nova no `eventlog`, diálogos (catálogo) e a `saude()` de quem chama
    (devolve um MOTIVO quando o app saiu do estado de trabalho — ex.: o MC voltou à tela de projetos —, None se está
    tudo bem). Estourou `prazo`, travou, caiu ou adoeceu → `Travado` com a foto da tela. Devolve o resultado da ação.

    ⛔ Toda ação que espera o app vai AQUI DENTRO (autor, 2026-10-12: o MC caiu e reabriu na tela de projetos, e uma
    montagem fora do cão de guarda ficou 2 minutos esperando uma bin que não existia mais, sem ninguém olhar)."""
    resultado, erro = {}, {}

    def rodar():
        try:
            resultado["v"] = acao()
        except BaseException as e:      # noqa: BLE001 — devolvido a quem chamou (inclusive o Parado do freio)
            erro["e"] = e
    base = set(ultimas_do_eventlog(eventlog, 400))
    t = threading.Thread(target=rodar, daemon=True)
    inicio = time.time()
    t.start()
    while True:
        t.join(intervalo)
        M.checar_freio()
        if not O.rodando(imagem):
            raise Travado(f"{imagem} não está rodando (caiu?)", O.foto_da_tela(pasta_fotos, "caiu"))
        novas = [l for l in ultimas_do_eventlog(eventlog, 40) if l not in base and (" Fatal" in l or " Dump" in l)]
        if novas:
            raise Travado("o app registrou falha: " + " | ".join(novas[-3:]), O.foto_da_tela(pasta_fotos, "falha"))
        motivo = saude() if saude else None
        if motivo:
            raise Travado(motivo, O.foto_da_tela(pasta_fotos, "saude"))
        h = O.janela_principal(imagem)
        if h and not O.respondendo(h):
            if time.time() - inicio > prazo:
                raise Travado(f"{imagem} sem responder há mais de {prazo:.0f} s", O.foto_da_tela(pasta_fotos, "travado"))
        else:
            varrer(imagem, catalogo or [], pasta_fotos, ignorar)
        if not t.is_alive() and (pronto is None or pronto()):
            break
        if time.time() - inicio > prazo:
            raise Travado(f"a ação não terminou em {prazo:.0f} s", O.foto_da_tela(pasta_fotos, "prazo"))
    if "e" in erro:
        raise erro["e"]
    return resultado.get("v")
