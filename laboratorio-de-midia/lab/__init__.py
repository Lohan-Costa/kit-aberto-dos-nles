"""Laboratório de Mídia — mídia sintética que diz em cada quadro e em cada canal o que é.

Só biblioteca padrão do Python + o ffmpeg/ffprobe da máquina (nenhuma dependência a instalar):
o laboratório roda igual no Windows e no Mac, do mesmo SSD. Plano: `docs/organograma-2026-10-06.html`.

    python3 -m lab.gerar receitas/base/B01.json      # gera a mídia + verdade.json em saida/
    python3 -m lab.verificar saida/base/B01_FORMATOS # confere cada arquivo contra a verdade
"""
