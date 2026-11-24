"""Bancada da TAXA MISTA no Media Composer (2026-10-12, pedido do autor: velocidade Premiere → Avid em laboratório
controlado; o R04 PRODUCAO-C tem 80 de 89 clipes em 25/60/100 qps numa timeline de 23,976).

Achados de partida (banco, avb/estruturas.md): o ImportFile CONVERTE a mídia para a taxa do projeto em tempo real
(o master sai a 23,976); o LinkFile (AMA) mantém a taxa NATIVA (master a 25 / 59,94 / 100). O caso real é o AMA: o
clipe de outra taxa editado PELO MC numa timeline de 23,976 — é o MC que decide o que gravar (o adaptador).

`editar(seq_mob, fonte_mob, quadro_da_timeline, duracao)`: a fonte no monitor de ORIGEM, IN no 1º quadro dela; na
Record IN/OUT no trecho; Overwrite (6216). Tudo sob o cão de guarda.
"""
from __future__ import annotations

import os
import time

from . import avid as A
from . import avid_collapse as C
from . import avid_efeitos as E
from . import interface_win as I

SAIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "saida", "bancadas",
                     "avid", "taxas")
OVERWRITE, MARK_IN, MARK_OUT, INICIO = 6216, 6209, 6210, 6102
VK_0 = 0x30


def foto(nome: str) -> str:
    from . import vigia_windows as V
    return V.foto_da_tela(SAIDA, nome)


def _editar(seq_mob: str, fonte_mob: str, quadro: int, dur: int) -> None:
    h = A.principal()
    if not I.frente(h):
        raise RuntimeError("o MC não veio para a frente")
    C.maximizada(h)
    with A.mc() as m:
        try:
            m.carregar_no_monitor([fonte_mob], "Source")
        except Exception as e:                       # noqa: BLE001 — já carregada responde "Some mobs was skipped."
            if "skipped" not in str(e):
                raise
        time.sleep(1.5)
        E.comando(m, INICIO); time.sleep(0.6)        # a Source é a ativa logo depois de carregada (conferido na foto)
        E.comando(m, MARK_IN); time.sleep(0.6)
    I.frente(h)
    I.tecla(VK_0, I.CTRL); time.sleep(0.6)           # Ctrl+0: o foco na timeline (a Record passa a ser a ativa)
    with A.mc() as m:
        C.selecionar(m, h, (1,))
        C._ir(m, quadro)
        E.comando(m, MARK_IN); time.sleep(0.4)
        C._ir(m, quadro + dur - 1)
        E.comando(m, MARK_OUT); time.sleep(0.4)
        E.comando(m, OVERWRITE); time.sleep(2)


def editar(seq_mob: str, fonte_mob: str, quadro: int, dur: int) -> None:
    E.carregar(seq_mob); time.sleep(1.5)
    A.guardado(lambda: _editar(seq_mob, fonte_mob, quadro, dur), 120)
