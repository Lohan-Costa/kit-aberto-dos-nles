"""Uma fonte de pixels 5×7 desenhada com `drawbox` — o texto queimado sem depender do ffmpeg da máquina.

Por que não `drawtext` + fonte OFL (o que o organograma previa): medido em 2026-10-06, o ffmpeg 8.1.1
do Homebrew (Mac) **não tem o filtro `drawtext`** ("Unknown filter 'drawtext'" — a fórmula `ffmpeg`
do Homebrew vem sem freetype; o completo é `ffmpeg-full`). Uma fonte própria em caixas funciona em
qualquer ffmpeg, dá os MESMOS pixels nas duas máquinas (o freetype de cada build desenharia diferente)
e dispensa o caminho do arquivo de fonte, que no filtro do Windows exigiria escapar o `:` do `D:`.

Só maiúsculas (o texto do quadro não leva acento), algarismos e uns sinais.
"""
from __future__ import annotations

_GLIFOS = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#",
    "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.",
    "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####",
    "F": "#####|#....|#....|####.|#....|#....|#....",
    "G": ".###.|#...#|#....|#.###|#...#|#...#|.####",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#",
    "I": ".###.|..#..|..#..|..#..|..#..|..#..|.###.",
    "J": "..###|...#.|...#.|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#",
    "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#...#|#...#|##..#|#.#.#|#..##|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.",
    "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "Q": ".###.|#...#|#...#|#...#|#.#.#|#..#.|.##.#",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#",
    "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|#.#.#|.#.#.",
    "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..",
    "Z": "#####|....#|...#.|..#..|.#...|#....|#####",
    "0": ".###.|#...#|#..##|#.#.#|##..#|#...#|.###.",
    "1": "..#..|.##..|..#..|..#..|..#..|..#..|.###.",
    "2": ".###.|#...#|....#|...#.|..#..|.#...|#####",
    "3": "#####|...#.|..#..|...#.|....#|#...#|.###.",
    "4": "...#.|..##.|.#.#.|#..#.|#####|...#.|...#.",
    "5": "#####|#....|####.|....#|....#|#...#|.###.",
    "6": "..##.|.#...|#....|####.|#...#|#...#|.###.",
    "7": "#####|....#|...#.|..#..|.#...|.#...|.#...",
    "8": ".###.|#...#|#...#|.###.|#...#|#...#|.###.",
    "9": ".###.|#...#|#...#|.####|....#|...#.|.##..",
    " ": ".....|.....|.....|.....|.....|.....|.....",
    ":": ".....|..#..|..#..|.....|..#..|..#..|.....",
    ".": ".....|.....|.....|.....|.....|..#..|..#..",
    ",": ".....|.....|.....|.....|..##.|..#..|.#...",
    "·": ".....|.....|.....|..#..|.....|.....|.....",
    "×": ".....|#...#|.#.#.|..#..|.#.#.|#...#|.....",
    "-": ".....|.....|.....|.###.|.....|.....|.....",
    "_": ".....|.....|.....|.....|.....|.....|#####",
    "/": "....#|....#|...#.|..#..|.#...|#....|#....",
}
LARGURA, ALTURA, AVANCO = 5, 7, 6   # em pixels da fonte; AVANCO inclui o espaço entre letras


def _retangulos_do_glifo(c: str) -> list[tuple[int, int, int, int]]:
    """(x, y, w, h) em pixels da fonte, juntando trechos acesos da linha e linhas iguais seguidas."""
    linhas = _GLIFOS[c].split("|")
    trechos = []
    for y, linha in enumerate(linhas):
        x = 0
        while x < LARGURA:
            if linha[x] == "#":
                x0 = x
                while x < LARGURA and linha[x] == "#":
                    x += 1
                trechos.append((x0, y, x - x0, 1))
            else:
                x += 1
    juntos: list[tuple[int, int, int, int]] = []
    for x, y, w, h in trechos:
        for i, (jx, jy, jw, jh) in enumerate(juntos):
            if jx == x and jw == w and jy + jh == y:
                juntos[i] = (jx, jy, jw, jh + 1)
                break
        else:
            juntos.append((x, y, w, h))
    return juntos


def largura(texto: str, escala: int) -> int:
    return (len(texto) * AVANCO - 1) * escala


def retangulos(texto: str, x: int, y: int, escala: int) -> list[tuple[int, int, int, int]]:
    """Os retângulos (em pixels do quadro) que desenham `texto` com o canto de cima à esquerda em x, y."""
    texto = texto.upper()
    faltam = sorted({c for c in texto if c not in _GLIFOS})
    if faltam:
        raise ValueError(f"a fonte de pixels não tem: {''.join(faltam)!r}")
    saida = []
    for i, c in enumerate(texto):
        ox = x + i * AVANCO * escala
        for gx, gy, gw, gh in _retangulos_do_glifo(c):
            saida.append((ox + gx * escala, y + gy * escala, gw * escala, gh * escala))
    return saida
