"""A RÉGUA do pacote multicam: a sequência que um app montou × a verdade.

    python -m lab.conferir_multicam saida/multicam/M01_4ANGULOS/verdade.json resumo.txt [--fps 25]

`resumo.txt` = uma linha por clipe da sequência, `<trilha>\\t<nome do clipe>\\t<início s>\\t<fim s>` (o que a função
`orbitaResumoDaSequencia` do Órbita devolve pela ponte do Premiere; a 1ª linha `SEQ\\t<nome>` é ignorada).

O sync está certo quando `início na timeline − início na cena` dá O MESMO número para todo arquivo (a sequência pode
começar onde quiser; o que importa é a posição RELATIVA). A régua toma a mediana desse número como zero e diz, por
arquivo, quanto ele se afastou — em milissegundos e em quadros da sequência. O som de uma câmera chega `atraso_ms`
depois: um sync pela forma de onda pode deixar a IMAGEM da câmera adiantada desse tanto, e isso é física, não erro
(a régua mostra o atraso ao lado).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys


def ler_resumo(caminho: str) -> list[tuple[str, str, float, float]]:
    linhas = []
    with open(caminho, encoding="utf-8") as fh:
        for ln in fh:
            p = ln.rstrip("\n").split("\t")
            if len(p) == 4 and p[0] != "SEQ":
                linhas.append((p[0], p[1], float(p[2]), float(p[3])))
    return linhas


def conferir(verdade: dict, resumo: list, fps: float) -> dict:
    # o primeiro uso de cada arquivo na sequência (vídeo e áudio de um mesmo arquivo caem juntos)
    na_seq: dict[str, float] = {}
    for trilha, nome, ini, _fim in resumo:
        na_seq.setdefault(nome, ini)
    linhas, desvios = [], []
    for a in verdade["arquivos"]:
        nome = os.path.basename(a["arquivo"])
        if nome not in na_seq:
            linhas.append({"arquivo": a["arquivo"], "na_sequencia": False})
            continue
        d = na_seq[nome] - a["inicio_na_cena_s"]
        desvios.append(d)
        linhas.append({"arquivo": a["arquivo"], "na_sequencia": True, "d": d, "atraso_ms": a.get("atraso_ms")})
    zero = statistics.median(desvios) if desvios else 0.0
    quadro_ms = 1000 / fps
    for ln in linhas:
        if ln.get("na_sequencia"):
            ln["erro_ms"] = round(1000 * (ln.pop("d") - zero), 1)
            ln["erro_quadros"] = round(ln["erro_ms"] / 1000 * fps, 2)
            # alinhada pelo SOM, a imagem de uma câmera adianta o atraso do microfone, arredondado ao quadro: é o
            # resultado CERTO de um sync por forma de onda (M01/M02, CAM 4 a 21 ms → −1 quadro a 25 q/s)
            at = ln.get("atraso_ms") or 0
            ln["explicado_pelo_atraso"] = bool(at) and abs(ln["erro_ms"] + round(at / quadro_ms) * quadro_ms) < 1
    fora = [ln for ln in linhas if not ln["na_sequencia"]]
    piores = max((abs(ln["erro_quadros"]) for ln in linhas if ln.get("na_sequencia")), default=0.0)
    return {"caso": verdade["caso"], "zero_s": round(zero, 4), "arquivos": linhas,
            "fora_da_sequencia": len(fora), "pior_erro_quadros": piores,
            "veredito": "certo (≤ 1 quadro)" if piores <= 1.0 and not fora else
                        ("faltou arquivo na sequência" if fora else f"erro de até {piores:.1f} quadros")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Confere uma sequência montada contra a verdade de um caso multicam.")
    ap.add_argument("verdade")
    ap.add_argument("resumo")
    ap.add_argument("--fps", type=float, default=25.0, help="taxa da sequência (para dizer o erro em quadros)")
    a = ap.parse_args(argv)
    # o console do Windows é cp1252 e não escreve "≤" (matriz de plataforma, encoding de console)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    with open(a.verdade, encoding="utf-8") as fh:
        v = json.load(fh)
    r = conferir(v, ler_resumo(a.resumo), a.fps)
    print(f"{r['caso']}: {r['veredito']}")
    for ln in r["arquivos"]:
        if ln["na_sequencia"]:
            extra = f"   (som da câmera chega {ln['atraso_ms']:.0f} ms depois)" if ln.get("atraso_ms") else ""
            if ln.get("explicado_pelo_atraso") and ln["erro_ms"]:
                extra += "  ← o som alinhado; a imagem adianta o atraso do microfone (certo)"
            print(f"  {ln['arquivo']:<44} {ln['erro_ms']:+8.1f} ms  {ln['erro_quadros']:+6.2f} q{extra}")
        else:
            print(f"  {ln['arquivo']:<44} NÃO ESTÁ NA SEQUÊNCIA")
    return 0 if r["veredito"].startswith("certo") else 1


if __name__ == "__main__":
    sys.exit(main())
