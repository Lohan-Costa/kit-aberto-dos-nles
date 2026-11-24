"""Exemplo (e teste ao vivo) do piloto no Media Composer, só com o piloto: carregar uma sequência na Record pela API,
agulha no início, marcar o clipe, abrir o Effect Editor, fotografar e fechar — tudo sob o cão de guarda.

    py exemplos\\mc_effect_editor.py "<caminho da bin .avb>" "<nome da sequência>"

O MC precisa estar aberto no projeto da bin. Freio: F12.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from piloto import apps, maos, olhos, pontes, vigia  # noqa: E402

GO_TO_START, MARK_CLIP, EFFECT_EDITOR = 6102, 6211, 1939       # banco: docommand-comandos.md
FOTOS = os.path.join(apps.SAIDA, "exemplos")


def main(bin_avb: str, sequencia: str) -> str:
    mc = apps.app("avid")
    catalogo = vigia.carregar_catalogo(apps.catalogo("avid"))

    def abrir() -> int:
        with pontes.media_composer() as m:
            mob = next(it.mob_id for it in m.itens_de(bin_avb, flags=("AllTypes",)) if it.name == sequencia)
            try:
                m.carregar_no_monitor([mob], "Record")
            except Exception as e:                                # noqa: BLE001 — já carregada responde "skipped"
                if "skipped" not in str(e):
                    raise
            principal = olhos.janela_principal(mc["windows"])
            if not maos.frente(principal):
                raise RuntimeError("o MC não veio para a frente — não teclo no programa errado")
            for cmd in (GO_TO_START, MARK_CLIP, EFFECT_EDITOR):
                pontes.comando(m, cmd)
                time.sleep(0.6)
        fim = time.time() + 10
        while time.time() < fim:
            ee = next((d["hwnd"] for d in olhos.dialogos(mc["windows"]) if d["titulo"] == "Effect Editor"), None)
            if ee:
                return ee
            time.sleep(0.3)
        raise RuntimeError("o Effect Editor não abriu")

    ee = vigia.com_prazo(abrir, 60, mc["windows"], FOTOS, catalogo, ignorar=mc["nao_modais"] + ("Effect Editor",),
                         eventlog=mc["eventlog_windows"])
    foto = olhos.fotografar(ee, os.path.join(FOTOS, "effect_editor.bmp"))
    if maos.frente(ee):
        maos.tecla(0x57, maos.CTRL)                             # Ctrl+W: fecha o editor e sai do modo de efeito
        time.sleep(1.2)
    print("foto:", foto, "| editor fechado:", not olhos.existe(ee))
    return foto


if __name__ == "__main__":
    main(*sys.argv[1:3])
