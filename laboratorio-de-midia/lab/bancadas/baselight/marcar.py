"""Markers "[Ciclo] …" numa scene (troca os nossos, deixa os outros). Entrada (stdin): [[quadro, nota], …].
    "/Library/Application Support/FilmLight/python/3.12-v7-venv/bin/python" marcar.py localhost:JOB:SCENE < marcas.json
"""
import json
import sys

import flapi

PREFIXO = "[Ciclo] "
marcas = json.load(sys.stdin)
c = flapi.Connection("localhost")
c.connect()
s = c.Scene.open_scene(c.Scene.parse_path(sys.argv[1]), set())
s.wait_until_open()
try:
    cats = s.get_mark_categories()
    cat = next((x for x in cats if "Cyan" in str(x) or "cyan" in str(x)), cats[0])
    s.start_delta("markers do Ciclo Assist (casamento)")
    for i in s.get_mark_ids():
        mk = s.get_mark(i)
        try:
            if str(mk.get_note_text() or "").startswith(PREFIXO):
                s.delete_mark(i)
        finally:
            mk.release()
    ids = [s.add_mark(q, cat, PREFIXO + nota) for q, nota in marcas]
    s.end_delta()
    s.save_scene()
    print(json.dumps({"categoria": str(cat), "markers": len(ids)}))
finally:
    s.close_scene()
    c.close()
