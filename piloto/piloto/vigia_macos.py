"""VIGIA no macOS — o cão de guarda e os diálogos: o MESMO de `vigia_comum.py` (catálogo por foto, `varrer`, `agir`,
`com_prazo`), com as mãos e os olhos do Mac. Medido no Mac do autor (macOS 15.6.1, Resolve 21.1, 2026-10-14): ver a
matriz de plataforma, seção F.

Diferenças do Windows que quem usa precisa saber:
- o diálogo é achado pela ACESSIBILIDADE (subrole AXDialog/AXSystemDialog ou modal), não pela "janela com dono";
- a foto é PNG (`screencapture -l`), com a barra de título, sem a sombra;
- "sem responder" = o app não atende a acessibilidade em 3 s (não há IsHungAppWindow);
- a variante "por título" do Premiere no Mac é a do laboratório (`lab/bancadas/vigia_dialogos.py`, System Events).
"""
from __future__ import annotations

from .vigia_comum import (DialogoAberto, Travado, agir, carregar_catalogo, com_prazo, reconhecer,  # noqa: F401
                          ultimas_do_eventlog, varrer)
