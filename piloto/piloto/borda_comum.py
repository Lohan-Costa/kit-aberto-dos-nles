"""A BORDA do piloto (autor, 2026-10-30): o que o piloto e o processo da borda combinam, sem tocar na tela.

Ideia vista no Post Producer (banco, `transversal/post-producer-arquitetura.md`) e que o autor já queria: uma faixa
colorida em volta da tela diz QUANDO o piloto está agindo, QUANDO o freio vale, e SE o freio funcionou.

| modo | cor | quer dizer |
|---|---|---|
| `ativo` | azul | o piloto está operando; F12 para, e mexer no mouse/teclado PAUSA |
| `pausado` | âmbar | você mexeu: o piloto espera você ficar parado `QUIETO_S` e continua |
| `parado` | vermelho | o freio pegou (F12, arquivo PARAR, ou a pausa virou parada); some sozinha |
| `livre` | — | sem borda: o piloto não está agindo, e F12 não faz nada |

O piloto e a borda são DOIS processos (o piloto roda em comandos curtos; a borda tem de ficar de pé entre eles) e
conversam por dois arquivos pequenos em `saida/borda/`:

- `estado.json`, escrito pelo piloto: o modo, o texto, e `ate` — o prazo de vida. ⛔ Sem prazo, um piloto que morre
  deixaria a borda azul dizendo "estou agindo" para sempre; com ele, ela some `TTL_S` depois da última ação.
- `toque.json`, escrito pela borda: quando foi o último toque FÍSICO (o sintético do piloto vem marcado pelo sistema
  e não conta). A pausa por toque só existe com a borda de pé — e isso é coerente: borda acesa = freios armados.
"""
from __future__ import annotations

import json
import os
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, "saida", "borda")
ESTADO = os.path.join(PASTA, "estado.json")
TOQUE = os.path.join(PASTA, "toque.json")
VIVO = os.path.join(PASTA, "vivo.json")
FREIO = os.path.join(PASTA, "freio.json")   # o F12 FÍSICO ouvido pela borda, com o pid dela (vale só nesta borda)

MODOS = ("ativo", "pausado", "parado", "livre")
CORES = {"ativo": (0x2E, 0x8B, 0xFF), "pausado": (0xFF, 0xB0, 0x20), "parado": (0xE5, 0x39, 0x35)}
TEXTOS = {
    "ativo": "PILOTO AGINDO  ·  ESPAÇO pausa  ·  F12 para",
    "pausado": "PAUSADO  ·  fique parado para continuar  ·  F12 para",
    "parado": "PAROU",
}

TTL_S = 45.0          # sem ação nem checagem do freio por isto, a borda some (o piloto morreu ou esqueceu de desligar)
RENOVAR_S = 2.0       # o piloto reescreve o prazo no máximo a cada isto (é chamado em TODO envio)
QUIETO_S = 10.0       # parado por isto, a pausa acaba (era 1,5 s: "muito rápido", o autor esperava 10–15 s, 2026-10-30)
PAUSA_MAX_S = 120.0    # pausado por mais que isto, para de vez: você está usando a máquina
PARADO_VISIVEL_S = 4.0  # o vermelho fica isto na tela, para dar tempo de ver que o freio pegou
VIVO_S = 1.5          # a borda bate o ponto a cada tique; mais velho que isto = ela não está de pé


def _gravar(caminho: str, dados: dict) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = f"{caminho}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)
    os.replace(tmp, caminho)


def _ler(caminho: str) -> dict:
    try:
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def escrever_estado(modo: str, texto: str | None = None, agora: float | None = None) -> dict:
    if modo not in MODOS:
        raise ValueError(f"modo desconhecido: {modo!r}")
    agora = time.time() if agora is None else agora
    d = {"modo": modo, "texto": texto or TEXTOS.get(modo, ""), "desde": agora, "ate": agora + TTL_S, "pid": os.getpid()}
    _gravar(ESTADO, d)
    return d


def ler_estado() -> dict:
    return _ler(ESTADO)


def ultimo_toque() -> float:
    return float(_ler(TOQUE).get("t", 0.0) or 0.0)


def gravar_toque(t: float, tipo: str, t_tecla: float = 0.0) -> None:
    _gravar(TOQUE, {"t": t, "tipo": tipo, "t_tecla": t_tecla})


def ultima_tecla() -> float:
    """O último toque de TECLADO físico. ⛔ A pausa segura as mãos do piloto, não a tecla do autor: ela chega ao
    programa da frente — no meio de uma digitação, DENTRO do texto (2ª rodada no Resolve: o projeto nasceu
    "PILOTO  BORDA TESTE 2", com um espaço a mais)."""
    return float(_ler(TOQUE).get("t_tecla", 0.0) or 0.0)


def bater_ponto(agora: float | None = None) -> None:
    _gravar(VIVO, {"pid": os.getpid(), "t": time.time() if agora is None else agora})


def gravar_freio(t: float) -> None:
    _gravar(FREIO, {"t": t, "pid": os.getpid()})


def freio_apertado() -> bool:
    """O F12 que a BORDA ouviu, enquanto ela estiver de pé. ⛔ O piloto só confere o freio quando AGE; entre um
    comando e outro (o Claude pensando) ninguém olhava, e o F12 apertado ali se perdia. A borda está de pé o tempo
    todo e ouve o teclado: ela guarda o aperto. Vale só para a borda VIVA que o ouviu — a próxima tarefa sobe outra
    borda, com outro pid, e um F12 velho não a para."""
    f, v = _ler(FREIO), _ler(VIVO)
    return bool(f) and f.get("pid") == v.get("pid") and borda_viva()


def borda_viva(agora: float | None = None) -> bool:
    agora = time.time() if agora is None else agora
    return agora - float(_ler(VIVO).get("t", 0.0) or 0.0) < VIVO_S


def texto_da_pausa(agora: float, toque: float) -> str:
    """A etiqueta âmbar com a contagem: sem ela, 10 s de espera parados se leem como travamento."""
    falta = max(1, int(QUIETO_S - (agora - toque) + 0.999))
    return f"PAUSADO  ·  continua em {falta} s sem mexer  ·  F12 para"


# ⭐ A TECLA DE PAUSA é o ESPAÇO (autor, 2026-10-30): com a borda acesa ela é ENGOLIDA pela borda — pausa e nunca chega
# ao programa, então não vira um espaço no nome que o piloto digita. As outras teclas passam (é ação de pânico do
# autor; numa digitação elas param o piloto em vez de pausar). Não se mata o teclado.
TECLA_DE_PAUSA = 0x20


def o_que_mostrar(estado: dict, agora: float, toque: float = 0.0, freio: bool = False) -> str | None:
    """O modo que a borda deve desenhar agora, ou None (nada na tela, e a borda pode sair).

    ⛔ O prazo vale para `ativo` e `pausado`: piloto morto não pode deixar cor nenhuma acesa. O `parado` vence o
    prazo só pelo tempo de ser visto — é a confirmação de que o freio pegou."""
    modo = estado.get("modo")
    if freio and modo in ("ativo", "pausado") and agora < float(estado.get("ate", 0)):
        return "parado"                     # o F12 aparece NA HORA, antes de o piloto agir de novo
    if modo == "ativo" and agora - toque < QUIETO_S and agora < float(estado.get("ate", 0)):
        return "pausado"                    # o toque aparece NA HORA: a próxima ação vai esperar
    if modo == "parado":
        return "parado" if agora - float(estado.get("desde", 0)) < PARADO_VISIVEL_S else None
    if modo in ("ativo", "pausado") and agora < float(estado.get("ate", 0)):
        return modo
    return None
