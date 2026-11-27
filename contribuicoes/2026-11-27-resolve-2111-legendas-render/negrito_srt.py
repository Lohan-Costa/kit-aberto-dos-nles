"""Copia um SRT envolvendo em <b>...</b> toda legenda não vazia que ainda não esteja inteira em <b>.

Uso: python3 negrito_srt.py ORIGEM.srt DESTINO.srt
Para o Resolve manter o peso Bold da trilha também nas legendas em <i> (relato, item 3).
Preserva o fim de linha (CRLF ou LF) do arquivo de origem. Não altera a origem.
"""
import os
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
if os.path.abspath(src) == os.path.abspath(dst):
    sys.exit("o destino precisa ser outro arquivo")
raw = open(src, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in raw else "\n"
txt = raw.replace("\r\n", "\n")
blocos = re.split(r"\n\s*\n", txt.strip())
out = []
mud = 0
for b in blocos:
    linhas = b.split("\n")
    if len(linhas) >= 2 and "-->" in linhas[1]:
        corpo = "\n".join(linhas[2:])
        s = corpo.strip()
        if s and not (s.startswith("<b>") and s.endswith("</b>")):
            corpo = "<b>" + s + "</b>"
            mud += 1
        b = "\n".join(linhas[:2] + ([corpo] if corpo else []))
    out.append(b)
open(dst, "w", encoding="utf-8", newline="").write(("\n\n".join(out) + "\n").replace("\n", nl))
print(os.path.basename(dst), "blocos", len(out), "ganharam negrito", mud)
