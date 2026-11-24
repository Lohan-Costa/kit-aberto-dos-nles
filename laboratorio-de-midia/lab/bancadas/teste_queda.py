"""Teste de QUEDA: derruba o Premiere de propósito no meio de uma rodada e confere que o laboratório se vira sozinho —
o vigia fecha as janelas de falha e `premiere.retomar()` reabre o Premiere e refaz o caso (pedido do autor, 2026-10-07:
"force também um encerramento do premiere para ver como o vigia deve lidar com quedas inesperadas e voltar ao premiere").

    python3 -m lab.bancadas.teste_queda 2026 [segundos até derrubar, padrão 20]
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time

from . import premiere as p
from . import vigia_dialogos

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _derrubar(ano: str, depois_s: float, feito: list) -> None:
    time.sleep(depois_s)
    r = subprocess.run(["pgrep", "-f", "^" + p._app(ano) + "/Contents/MacOS/" + p._nome(ano) + "$"], capture_output=True, text=True)
    for pid in r.stdout.split():
        os.kill(int(pid), signal.SIGABRT)            # como uma queda de verdade: o macOS mostra "encerrou inesperadamente"
        feito.append({"quando": time.strftime("%H:%M:%S"), "pid": int(pid), "sinal": "SIGABRT"})
        print(time.strftime("%H:%M:%S"), "💥 derrubei o Premiere", pid, flush=True)


def caso(trab: str, ano: str) -> dict:
    t0 = time.time()
    r = p.preparar("saida/base/B01_FORMATOS", trab, "LAB TESTE QUEDA")
    s = p.stills(trab)
    j = p.renderizar(trab, ano)
    return {"pool": r["pool"], "stills_ok": all(all(v) for v in s.values()), "renders": [x["job"] for x in j["jobs"]],
            "s": round(time.time() - t0, 1)}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ano = argv[0] if argv else "2026"
    depois = float(argv[1]) if len(argv) > 1 else 20
    os.chdir(RAIZ)
    p.reabrir_premiere(ano)
    p.esperar_ponte(300)
    trab = os.path.join("saida", "bancadas", "teste-queda", time.strftime("%Y%m%d-%H%M%S"))
    quedas: list = []
    threading.Thread(target=_derrubar, args=(ano, depois, quedas), daemon=True).start()
    t0 = time.time()
    r = p.retomar(ano, caso, trab, ano)
    out = {"ano": ano, "quedas_provocadas": quedas, "resultado": r, "total_s": round(time.time() - t0, 1)}
    with open(os.path.join(vigia_dialogos.PASTA, "vigia.jsonl"), encoding="utf-8") as fh:
        out["vigia"] = [json.loads(x) for x in fh if x.strip()][-6:]
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
    return 0 if r["stills_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
