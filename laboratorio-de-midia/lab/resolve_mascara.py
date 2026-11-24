"""O Magic Mask da página COLOR do DaVinci Resolve por dentro: o cache (`.dvcc`) e as duas anotações do banco do projeto que
dizem ao Resolve que a máscara está "em dia". Com isto uma máscara feita FORA do Resolve (a máscara de objeto do Premiere,
`lab/prmf.py`) vira Magic Mask sem o Resolve rastrear nada.

Decifrado no laboratório (Resolve Studio 21.1, macOS, banco LOCAL em disco, 2026-10-07/08) — banco da família,
`protocolos/drt-drp/magic-mask.md` §5–7:

- **Caminho do cache:** `<CacheClip>/<Project.GetUniqueId()>/AlgoCache/1000/<Sm2Sequence>/<Sm2TiItem>/<LmVersion ativa>/1/0/
  NNNNNNNNNN.dvcc` (um por quadro). `Sm2TiItem` = `TimelineItem.GetUniqueId()`; os outros dois só no `Project.db` (SQLite).
- **`.dvcc`:** cabeçalho de 8192 bytes (TLV: `DVCC`, largura/altura, taxa em float32, timecode "HH:MM:SS:FF", `exr_zip`, a
  etiqueta `g` com o tamanho do EXR) + um OpenEXR de (largura/2)×(altura/2), canal "A" UINT, "ZIP" mas gravado SEM
  compressão; os bytes, em ordem, são a máscara largura×altura de 8 bits (0/255), linhas de cima para baixo. Arquivo
  completado até múltiplo de 8192.
- **Banco:** o tracking (1) APAGA os campos 12 (números de série de modificação) do `ListMgt::LmVersion.Body` da versão ativa
  (0x81 + zstd COM o tamanho e SEM soma de verificação + protobuf) e (2) grava o RECIBO `Sm2TiItem.RenderCacheBA`
  (u32 BE + zlib) com o id da versão. Sem as duas coisas o Resolve refaz o tracking por cima do cache.

⛔ O `Project.db` só se edita com o projeto FECHADO no Resolve (ele o mantém carregado e regrava ao salvar). Sempre com cópia
de segurança antes. Banco em rede (PostgreSQL) / nuvem: não suportado (pendente).
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import zlib

MOLDES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moldes", "resolve")
MOLDE_DVCC = os.path.join(MOLDES, "mascara_modelo.dvcc")
MOLDE_RECIBO = os.path.join(MOLDES, "recibo_modelo.bin")
MOLDE_NO = os.path.join(MOLDES, "no_magic_mask_color.drt")

# ---------------------------------------------------------------- protobuf mínimo (só o necessário para tirar um campo)

def _rv(b: bytes, i: int) -> tuple[int, int]:
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return r, i


def _wv(n: int) -> bytes:
    o = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n:
            o.append(x | 0x80)
        else:
            o.append(x)
            return bytes(o)


def _campos(b: bytes):
    """Os campos de uma mensagem protobuf [(campo, tipo, valor bruto)], ou None se `b` não for uma mensagem inteira."""
    i, out = 0, []
    try:
        while i < len(b):
            k, i = _rv(b, i)
            f, t = k >> 3, k & 7
            if f == 0:
                return None
            if t == 0:
                j = i
                _, i = _rv(b, i)
                out.append((f, t, b[j:i]))
            elif t == 1:
                out.append((f, t, b[i:i + 8]))
                i += 8
            elif t == 5:
                out.append((f, t, b[i:i + 4]))
                i += 4
            elif t == 2:
                n, i = _rv(b, i)
                out.append((f, t, b[i:i + n]))
                i += n
            else:
                return None
        return out if i == len(b) else None
    except IndexError:
        return None


def tirar_campo(b: bytes, campo: int) -> tuple[bytes, int]:
    """Remove, em qualquer profundidade, todo campo varint `campo`; corrige os tamanhos das mensagens que o envolvem.
    Devolve (novo, quantos saíram). Sem o campo, devolve `b` byte a byte."""
    cs = _campos(b)
    if cs is None:
        return b, 0
    o, tot = bytearray(), 0
    for f, t, v in cs:
        if f == campo and t == 0:
            tot += 1
            continue
        if t == 2:
            nv, k = tirar_campo(v, campo)
            if k:
                tot += k
                v = nv
            o += _wv(f << 3 | t) + _wv(len(v)) + v
        else:
            o += _wv(f << 3 | t) + v
    return bytes(o), tot

# ---------------------------------------------------------------- zstd como o Resolve grava

def _zstd() -> str:
    for p in [*os.environ.get("PATH", "").split(os.pathsep), "/opt/homebrew/bin", "/usr/local/bin"]:
        c = os.path.join(p, "zstd.exe" if os.name == "nt" else "zstd")
        if p and p != "." and os.path.isfile(c):
            return c
    raise RuntimeError("zstd não encontrado (Mac: brew install zstd) — procurado no PATH, /opt/homebrew/bin, /usr/local/bin")


def zstd_abrir(z: bytes) -> bytes:
    r = subprocess.run([_zstd(), "-dc"], input=z, capture_output=True)
    if r.returncode:
        raise RuntimeError("zstd falhou: " + r.stderr.decode("utf-8", "replace"))
    return r.stdout


def zstd_comprimir(dados: bytes, nivel: int = 3) -> bytes:
    """Um quadro zstd com o TAMANHO do conteúdo e SEM soma de verificação (cabeçalho `28b52ffd 60…`/`20…`), como o Resolve.
    ⚠️ Pela entrada padrão o zstd grava `04…` (sem tamanho, com soma) e o Resolve NÃO lê o nó."""
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "c")
        with open(a, "wb") as fh:
            fh.write(dados)
        r = subprocess.run([_zstd(), "-q", "-f", f"-{nivel}", "--no-check", a, "-o", a + ".zst"], capture_output=True)
        if r.returncode:
            raise RuntimeError("zstd falhou: " + r.stderr.decode("utf-8", "replace"))
        with open(a + ".zst", "rb") as fh:
            return fh.read()

# ---------------------------------------------------------------- .dvcc

def _exr_cabecalho(exr: bytes) -> tuple[dict, int]:
    """Atributos do cabeçalho EXR {nome: (tipo, posição do valor, valor bruto)} e o fim do cabeçalho."""
    assert exr[:4] == b"v/1\x01", "não é EXR"
    i, at = 8, {}
    while exr[i] != 0:
        j = exr.index(0, i)
        k = exr.index(0, j + 1)
        n = struct.unpack_from("<I", exr, k + 1)[0]
        at[exr[i:j].decode()] = (exr[j + 1:k].decode(), k + 5, exr[k + 5:k + 5 + n])
        i = k + 5 + n
    return at, i + 1


def ler_dvcc(caminho: str) -> tuple[bytes, int, int]:
    """(máscara 8 bits largura×altura, largura, altura) de um `.dvcc` da pasta `0/`."""
    with open(caminho, "rb") as fh:
        raw = fh.read()
    exr = raw[raw.index(b"v/1\x01"):]
    at, p = _exr_cabecalho(exr)
    x0, y0, x1, y1 = struct.unpack("<4i", at["dataWindow"][2])
    w, h = x1 - x0 + 1, y1 - y0 + 1
    n = (h + 15) // 16
    offs = struct.unpack_from(f"<{n}Q", exr, p)
    out = bytearray()
    for o in offs:
        _, sz = struct.unpack_from("<iI", exr, o)
        d = exr[o + 8:o + 8 + sz]
        linhas = min(16, h - (struct.unpack_from("<i", exr, o)[0] - y0))
        if sz < w * 4 * linhas:                                   # bloco comprimido de verdade (ZIP do EXR)
            t = bytearray(zlib.decompress(d))
            for k in range(1, len(t)):
                t[k] = (t[k - 1] + t[k] - 128) & 0xFF
            meio = (len(t) + 1) // 2
            r = bytearray(len(t))
            r[0::2], r[1::2] = t[:meio], t[meio:]
            d = bytes(r)
        out += d
    return bytes(out), w * 2, h * 2


def _tc(quadro: int, fps: float) -> str:
    base = round(fps)
    if base <= 0:
        return "00:00:00:00"
    s, f = divmod(quadro, base)
    m, s = divmod(s, 60)
    hh, m = divmod(m, 60)
    return f"{hh:02d}:{m:02d}:{s:02d}:{f:02d}"


def dvcc(mascara: bytes, largura: int, altura: int, quadro: int, fps: float, molde: str = MOLDE_DVCC) -> bytes:
    """O `.dvcc` de um quadro: `mascara` = largura×altura bytes (0 = fora, 255 = dentro). `quadro` e `fps` vão no cabeçalho
    como o Resolve grava (taxa em float32, timecode a partir do início da mídia)."""
    if largura % 2 or altura % 2:
        raise ValueError("largura e altura têm de ser pares")
    if len(mascara) != largura * altura:
        raise ValueError(f"máscara com {len(mascara)} bytes, esperado {largura * altura}")
    with open(molde, "rb") as fh:
        raw = fh.read()
    i = raw.index(b"v/1\x01")
    cab = bytearray(raw[:i])
    assert cab[8:12] == b"DVCC" and cab[0x30:0x34] == b"k\0\0\0" and cab[0x3C:0x40] == b"n\0\0\0"
    struct.pack_into("<II", cab, 0x14, largura, altura)
    struct.pack_into("<f", cab, 0x38, float(fps))
    cab[0x44:0x4F] = _tc(quadro, fps).encode()
    exr = bytearray(raw[i:])
    at, p = _exr_cabecalho(bytes(exr))
    w, h = largura // 2, altura // 2
    for nome in ("dataWindow", "displayWindow"):
        struct.pack_into("<4i", exr, at[nome][1], 0, 0, w - 1, h - 1)
    exr = bytes(exr[:p])
    n, linha = (h + 15) // 16, w * 4
    blocos, pos = [], p + 8 * n
    for k in range(n):
        ini = k * 16
        corpo = mascara[ini * linha:min(h, ini + 16) * linha]
        blocos.append(struct.pack("<iI", ini, len(corpo)) + corpo)
    offs = []
    for b in blocos:
        offs.append(pos)
        pos += len(b)
    novo = exr + struct.pack(f"<{n}Q", *offs) + b"".join(blocos)
    struct.pack_into("<I", cab, len(cab) - 4, len(novo))          # etiqueta `g` = tamanho do EXR
    tudo = bytes(cab) + novo
    return tudo + b"\0" * ((-len(tudo)) % 8192)

# ---------------------------------------------------------------- banco do projeto

def pasta_das_bibliotecas() -> str:
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Resolve Project Library")
    raise RuntimeError("caminho do banco do Resolve nesta plataforma: pendente (medido só no macOS)")


def achar_banco(projeto_id: str, raiz: str | None = None) -> str:
    """O `Project.db` cujo `SM_Project_id` é o `Project.GetUniqueId()` — vale para projeto dentro de pastas."""
    raiz = raiz or pasta_das_bibliotecas()
    for base, _, arqs in os.walk(raiz):
        if "Project.db" in arqs:
            db = os.path.join(base, "Project.db")
            try:
                con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
                ok = con.execute("select 1 from SM_Project where SM_Project_id=?", (projeto_id,)).fetchone()
                con.close()
            except sqlite3.Error:
                continue
            if ok:
                return db
    raise FileNotFoundError(f"nenhum Project.db com o projeto {projeto_id} em {raiz}")


def ids_do_caminho(db: str, timeline_id: str, item_id: str) -> tuple[str, str]:
    """(Sm2Sequence da timeline, LmVersion ativa do clipe)."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        seq = con.execute("select Sequence from Sm2Timeline where Sm2Timeline_id=?", (timeline_id,)).fetchone()
        ver = con.execute('select pActive from "ListMgt::LmVersionTable" where Sm2TiItem_id=?', (item_id,)).fetchone()
    finally:
        con.close()
    if not seq or not ver:
        raise LookupError("timeline ou clipe não estão no banco — o projeto foi salvo?")
    return seq[0], ver[0]


def recibo(versao_id: str, primeiro: int, ultimo: int, serie: int = 0x7FFFFFF0, molde: str = MOLDE_RECIBO) -> bytes:
    """O `Sm2TiItem.RenderCacheBA`: o recibo do Magic Mask — id da versão em ASCII (0x10), a faixa em QUADROS DA MÍDIA
    (primeiro em 0x86 e 0xA6, quantidade em 0x8E, último em 0xAE; medido com um clipe aparado 50→298) e dois números de série
    (0x4C e 0x96). Tudo u32 big-endian."""
    with open(molde, "rb") as fh:
        m = fh.read()
    d = bytearray(zlib.decompress(m[4:]))
    assert len(d) == 178 and d[0x10:0x34].count(b"-") == 4
    d[0x10:0x34] = versao_id.encode()
    struct.pack_into(">I", d, 0x4C, serie)
    struct.pack_into(">I", d, 0x96, serie + 3)
    for pos, v in ((0x86, primeiro), (0x8E, ultimo - primeiro + 1), (0xA6, primeiro), (0xAE, ultimo)):
        struct.pack_into(">I", d, pos, v)
    return struct.pack(">I", len(d)) + zlib.compress(bytes(d))


def marcar_em_dia(db: str, item_id: str, primeiro: int, ultimo: int, pasta_copia: str) -> dict:
    """Edita o banco (projeto FECHADO): tira os campos 12 da versão ativa e grava o recibo. Copia o banco antes."""
    os.makedirs(pasta_copia, exist_ok=True)
    copia = os.path.join(pasta_copia, time.strftime("Project-%Y%m%d-%H%M%S.db"))
    shutil.copy2(db, copia)
    con = sqlite3.connect(db)
    try:
        ver = con.execute('select pActive from "ListMgt::LmVersionTable" where Sm2TiItem_id=?', (item_id,)).fetchone()[0]
        body = con.execute('select Body from "ListMgt::LmVersion" where "ListMgt::LmVersion_id"=?', (ver,)).fetchone()[0]
        i = body.index(b"\x28\xb5\x2f\xfd")
        novo, k = tirar_campo(zstd_abrir(body[i:]), 12)
        con.execute('update "ListMgt::LmVersion" set Body=? where "ListMgt::LmVersion_id"=?',
                    (body[:i] + zstd_comprimir(novo), ver))
        con.execute("update Sm2TiItem set RenderCacheBA=? where Sm2TiItem_id=?", (recibo(ver, primeiro, ultimo), item_id))
        con.commit()
    finally:
        con.close()
    return {"copia": copia, "versao": ver, "campos_12": k}
