"""Só LEITURA: o arquivo, o TC e o quadro de fonte de cada plano de uma scene, em JSON no stdout.
Roda no Python da FilmLight (tem o `flapi`):
    "/Library/Application Support/FilmLight/python/3.12-v7-venv/bin/python" planos_da_scene.py localhost:JOB:SCENE
"""
import json
import sys

import flapi

c = flapi.Connection("localhost")
c.connect()
s = c.Scene.open_scene(c.Scene.parse_path(sys.argv[1]), {flapi.OPENFLAG_READ_ONLY})
s.wait_until_open()
planos = []
try:
    for info in s.get_shot_ids():
        sh = s.get_shot(info.ShotId)
        try:
            sd = sh.get_sequence_descriptor()
            planos.append({"inicio": info.StartFrame, "fim": info.EndFrame,
                           "arquivo": sd.get_full_filename_with_F() if sd else None,
                           "src_tc": str(sh.get_src_start_timecode()), "src_quadro": sh.get_src_start_frame()})
        except Exception as e:                      # plano sem mídia (offline) ou composto
            planos.append({"inicio": info.StartFrame, "fim": info.EndFrame, "arquivo": None, "erro": str(e)})
        finally:
            sh.release()
finally:
    s.close_scene()
    c.close()
print(json.dumps(planos, ensure_ascii=False))
