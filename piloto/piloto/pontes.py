"""PONTES — falar com o app por dentro, quando ele tem API. O piloto (mãos/olhos/vigia) cobre o que a API não alcança;
o que a API faz bem, faz pela API (é mais rápido e não depende de pixel).

O código pesado das pontes mora nos apps que já o mantêm; aqui só o achamos (subindo de pasta, nunca caminho fixo:
regra da família) e o devolvemos pronto.

| app | ponte | onde mora | estado |
|---|---|---|---|
| Media Composer | gRPC do próprio MC em [::1]:9100 (`MediaComposer`, o cliente do De Lá Pra Cá) | `2 ATIVOS/_DeLaPraCa/plugins/media-composer/servico/avid/mcapi.py` | Windows `confirmado` · Mac `pendente` |
| Premiere | ponte CEP do laboratório (ExtendScript por HTTP local) | `laboratorio-de-midia/lab/bancadas/premiere.py` | Mac e Windows `confirmado` no laboratório |
| Resolve | API de script (`fuscript`/DaVinciResolveScript) | `laboratorio-de-midia/lab/bancadas/resolve.py` | Windows `confirmado` no laboratório |
"""
from __future__ import annotations

import os
import sys


def familia() -> str:
    """A pasta `PROGRAMAS COM CLAUDE` (a que tem o `bancodedadosnles`), subindo a partir daqui."""
    p = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(p, "bancodedadosnles")):
            return p
        pai = os.path.dirname(p)
        if pai == p:
            raise RuntimeError("não achei a pasta da família (a que tem o bancodedadosnles) acima do piloto")
        p = pai


def _no_caminho(*partes: str) -> str:
    alvo = os.path.join(familia(), *partes)
    if not os.path.isdir(alvo):
        raise RuntimeError(f"a ponte mora em {alvo}, que não existe (o app mudou de lugar? ver CATALOGO.md)")
    if alvo not in sys.path:
        sys.path.insert(0, alvo)
    return alvo


def media_composer():
    """O cliente da API do MC (gRPC), como contexto: `with pontes.media_composer() as m: m._chamar("DoCommand", …)`.
    DoCommand é ASSÍNCRONO: um segundo em seguida responde "Can't start more than one command" — ver `comando`."""
    dlpc = os.path.join("2 ATIVOS", "_DeLaPraCa")
    _no_caminho(dlpc, "motor")
    _no_caminho(dlpc, "plugins", "media-composer", "servico")
    from avid.mcapi import MediaComposer
    return MediaComposer()


def comando(m, cmd: int, prazo: float = 10) -> None:
    """`DoCommand` do MC esperando o anterior (ErrorType 73 "more than one command", medido 2026-10-11). Os ids:
    banco, `plugins/avid-panel-sdk/dados/docommand-comandos.md`."""
    import time
    fim = time.time() + prazo
    while True:
        try:
            m._chamar("DoCommand", _timeout=30, commandId=cmd)
            return
        except Exception as e:                # noqa: BLE001
            if "more than one command" not in str(e) or time.time() > fim:
                raise
            time.sleep(0.2)
