"""O passo 4 da publicação (2026-11-25): as suítes do app — a da RAIZ e as dos MÓDULOS — no privado e na cópia
pública, lado a lado. Nasceu do achado de 25/11: o passo 4 rodava só a suíte da raiz, e a cópia publicada tinha testes
de módulo quebrados pela troca de nomes (um apelido com hífen dentro de um `def`, grafias de um nome com apelidos
diferentes) que ninguém tinha rodado.

    python3 conferir_copia.py <pasta do app na cópia>   # ex.: <saída>/kit-aberto-dos-nles/ciclo-assist-kit-nle

⚠️ A cópia tem de estar DENTRO do kit (a pasta do app ao lado do `bancodedadosnles`), como no clone de quem usa: o
código acha o banco e o laboratório subindo de pasta.

O que roda (com os Pythons do PRIVADO — a cópia não tem venv):
  - a raiz: `pytest` com a venv do app;
  - o Conformar ARQUIVO A ARQUIVO (os testes dele são roteiros que saem 0/1; o que só tem `def test_` vai ao pytest);
  - o Sincronizar: `pytest` com a venv DO MÓDULO (`modulos/sincronizar/.venv`: a do app não tem `scipy` — os "15
    erros" de antes eram isso).

Bloqueia (sai 1) se a cópia falhar em algo que passa no privado. Pular na cópia o que roda no privado é esperado
(dado que não vai) e vai à lista, para uma pessoa ler. Só stdlib; Mac e Windows.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
WIN = os.name == "nt"


def _privado() -> str:
    p = AQUI
    while not os.path.isdir(os.path.join(p, "bancodedadosnles")):
        if os.path.dirname(p) == p:
            raise SystemExit("não achei a pasta da família subindo de " + AQUI)
        p = os.path.dirname(p)
    return os.path.join(p, "2 ATIVOS", "_CICLO ASSIST")


def _py(pasta: str) -> str:
    py = os.path.join(pasta, ".venv-win", "Scripts", "python.exe") if WIN else os.path.join(pasta, ".venv", "bin", "python")
    if not os.path.isfile(py):
        raise SystemExit(f"falta a venv desta máquina em {pasta}")
    return py


def _rodar(cmd: list[str], cwd: str) -> tuple[int, str]:
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    return r.returncode, r.stdout + r.stderr


def _pytest(py: str, cwd: str, alvo: str) -> dict:
    """{nó: 'passed'|'failed'|'skipped'|'error'} pelo `-rA` do pytest."""
    _, saida = _rodar([py, "-m", "pytest", alvo, "-q", "-rA", "-p", "no:cacheprovider"], cwd)
    out = {}
    # o id vai até o " - " do motivo (os parâmetros podem ter espaço: `[O PRODA…]` cortava e juntava ids)
    for m in re.finditer(r"^(PASSED|FAILED|SKIPPED|ERROR) (\S+\.py(?:::.+?)?)(?: - .*)?$", saida, re.M):
        out[m.group(2)] = m.group(1).lower()
    if not out:
        out["<coleta>"] = "error: " + saida[-300:]
    return out


def _conformar(py: str, app: str) -> dict:
    pasta = os.path.join(app, "modulos", "conformar")
    testes = sorted(f for f in os.listdir(os.path.join(pasta, "tests")) if f.startswith("test_") and f.endswith(".py"))

    def um(f):
        caminho = os.path.join("tests", f)
        texto = open(os.path.join(pasta, caminho), encoding="utf-8", errors="replace").read()
        if "__main__" in texto or not re.search(r"^def test_", texto, re.M):   # roteiro (sai 0/1)
            cod, saida = _rodar([py, "-X", "utf8", caminho], pasta)
            return f, ("skipped" if cod == 0 and re.search(r"^\s*pulou", saida, re.M | re.I) else
                       "passed" if cod == 0 else "failed")
        r = _pytest(py, pasta, caminho)
        estados = set(v.split(":")[0] for v in r.values())
        return f, ("failed" if estados & {"failed", "error"} else "passed" if "passed" in estados else "skipped")

    with ThreadPoolExecutor(6) as ex:
        return dict(ex.map(um, testes))


def suites(app: str, privado: str) -> dict:
    sinc = os.path.join("modulos", "sincronizar", "motor")
    return {
        "raiz": _pytest(_py(privado), app, "tests"),
        "conformar": _conformar(_py(privado), app),
        "sincronizar": _pytest(_py(os.path.join(privado, "modulos", "sincronizar")), os.path.join(app, sinc), "tests"),
    }


def comparar(priv: dict, pub: dict) -> tuple[list[str], list[str]]:
    quebrados, pulados = [], []
    for suite in priv:
        for no, estado in priv[suite].items():
            novo = pub[suite].get(no, "ausente")
            if estado == "passed" and novo.startswith(("failed", "error")):
                quebrados.append(f"{suite}: {no} ({novo})")
            elif estado == "passed" and novo != "passed":
                pulados.append(f"{suite}: {no} ({novo})")
        for no, novo in pub[suite].items():
            if no not in priv[suite] and novo.startswith(("failed", "error")):
                quebrados.append(f"{suite}: {no} ({novo}, só na cópia)")
    return quebrados, pulados


def _resumo(r: dict) -> str:
    out = []
    for suite, nos in r.items():
        c = {}
        for v in nos.values():
            c[v.split(":")[0]] = c.get(v.split(":")[0], 0) + 1
        out.append(f"{suite}: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
    return " · ".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    copia, privado = os.path.abspath(sys.argv[1]), _privado()
    if not os.path.isdir(os.path.join(os.path.dirname(copia), "bancodedadosnles")):
        raise SystemExit("a cópia do app tem de estar dentro do kit (ao lado do bancodedadosnles)")
    with ThreadPoolExecutor(2) as ex:
        f_priv, f_pub = ex.submit(suites, privado, privado), ex.submit(suites, copia, privado)
        r_priv, r_pub = f_priv.result(), f_pub.result()
    print("privado:", _resumo(r_priv))
    print("cópia:  ", _resumo(r_pub))
    quebrados, pulados = comparar(r_priv, r_pub)
    print(f"\nPassam no privado e PULAM na cópia ({len(pulados)}) — ler: é dado que não vai?")
    print("\n".join("  " + x for x in pulados) or "  nenhum")
    print(f"\nPassam no privado e QUEBRAM na cópia ({len(quebrados)}):")
    print("\n".join("  " + x for x in quebrados) or "  nenhum")
    sys.exit(1 if quebrados else 0)
