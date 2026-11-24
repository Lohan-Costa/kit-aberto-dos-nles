"""GDeflate em Python puro (só leitura): o deflate com os bits espalhados em 32 sub-fluxos, criado pela NVIDIA e pela
Microsoft (DirectStorage) para descompressão em GPU. O Premiere 2026 comprime com ele a MÁSCARA DE OBJETO (os .prmf da
pasta "<projeto> Masks"; o binário do Premiere tem "SelectionFoundation.RasterSelection.ShouldUseGDeflateCompressionAlgorithm").

Formato (TileStream, 8 bytes): id=4, magic=id^0xFF (0xFB), nº de tiles (u16), depois u32 com tileSizeIdx (2 bits, =1 →
tiles de 64 KiB) e o tamanho do último tile (18 bits). Seguem os offsets dos tiles (u32 × nº de tiles: o 1º é o tamanho
comprimido do último tile; os outros, o início de cada tile) e os dados. Cada tile é um fluxo DEFLATE64 (RFC 1951 + comprimento 285 = 3 + 16 bits e distâncias até 64 KiB) cujos
bits foram distribuídos em 32 sub-fluxos: cada sub-fluxo tem um buffer que, ao cair para <= 32 bits, lê o próximo u32 do
fluxo, na ordem dos sub-fluxos; o cabeçalho do bloco vai no sub-fluxo 0, os comprimentos do precode e dos códigos em
rodízio, e cada literal / comprimento+distância inteiro num sub-fluxo, com a distância uma rodada DEPOIS do comprimento.

Portado da referência (Apache-2.0 / MIT): microsoft/DirectStorage GDeflate + NVIDIA/libdeflate
`lib/gdeflate_decompress_template.h` (commit 8ba9502). Laboratório de mídia, 2026-10-07.
"""
from __future__ import annotations

import struct

FLUXOS = 32
TILE = 64 * 1024
_ORDEM_PRECODE = (16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15)
# ⚠️ o GDeflate é DEFLATE64: o símbolo 285 é 3 + 16 bits extras (não 258), e as distâncias 30/31 valem (até 64 KiB)
_BASE_COMP = [3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 15, 17, 19, 23, 27, 31, 35, 43, 51, 59, 67, 83, 99, 115, 131, 163, 195, 227, 3]
_EXTRA_COMP = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 16]
_BASE_DIST = [1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193, 257, 385, 513, 769, 1025, 1537, 2049, 3073,
              4097, 6145, 8193, 12289, 16385, 24577, 32769, 49153]
_EXTRA_DIST = [0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14]


class ErroGDeflate(ValueError):
    pass


def _tabela(comprimentos):
    """Código canônico (RFC 1951) → {(nº de bits, código invertido): símbolo} e o maior comprimento."""
    maxl = max(comprimentos) if comprimentos else 0
    cont = [0] * (maxl + 1)
    for l in comprimentos:
        if l:
            cont[l] += 1
    prox, c = [0] * (maxl + 2), 0
    for b in range(1, maxl + 1):
        c = (c + cont[b - 1]) << 1
        prox[b] = c
    t = {}
    for s, l in enumerate(comprimentos):
        if l:
            cod = prox[l]; prox[l] += 1
            inv = int(format(cod, f"0{l}b")[::-1], 2)
            t[(l, inv)] = s
    return t, maxl


class _Fluxos:
    def __init__(self, dados: bytes):
        self.d = dados + b"\x00" * 8 * FLUXOS            # a referência lê u32 além do fim (bits sem uso)
        self.p = 0
        self.buf = [0] * FLUXOS
        self.n = [0] * FLUXOS
        self.i = 0

    def garantir(self):
        i = self.i
        if self.n[i] < 32:
            self.buf[i] |= struct.unpack_from("<I", self.d, self.p)[0] << self.n[i]
            self.p += 4
            self.n[i] += 32

    def avancar(self):                                    # ADVANCE(): completa o atual e passa para o próximo
        self.garantir()
        self.i = (self.i + 1) % FLUXOS

    def bits(self, k):
        i = self.i
        v = self.buf[i] & ((1 << k) - 1)
        self.buf[i] >>= k
        self.n[i] -= k
        return v

    def simbolo(self, tabela):
        t, maxl = tabela
        i = self.i
        b = self.buf[i]
        for l in range(1, maxl + 1):
            s = t.get((l, b & ((1 << l) - 1)))
            if s is not None:
                self.buf[i] >>= l
                self.n[i] -= l
                return s
        raise ErroGDeflate("código Huffman inválido")


_ESTATICO = None


def _tile(dados: bytes, tamanho: int) -> bytes:
    global _ESTATICO
    f = _Fluxos(dados)
    for _ in range(FLUXOS):
        f.avancar()
    saida = bytearray(tamanho)
    pos = 0
    while True:
        f.i = 0
        final = f.bits(1)
        tipo = f.bits(2)
        f.garantir()
        if tipo == 2:
            hlit, hdist, hclen = f.bits(5) + 257, f.bits(5) + 1, f.bits(4) + 4
            f.garantir()
            pre = [0] * 19
            for k in range(hclen):
                pre[_ORDEM_PRECODE[k]] = f.bits(3)
                f.avancar()
            tpre = _tabela(pre)
            f.i = 0
            lens = []
            while len(lens) < hlit + hdist:
                s = f.simbolo(tpre)
                if s < 16:
                    lens.append(s)
                elif s == 16:
                    if not lens:
                        raise ErroGDeflate("repetição sem comprimento anterior")
                    lens += [lens[-1]] * (3 + f.bits(2))
                elif s == 17:
                    lens += [0] * (3 + f.bits(3))
                else:
                    lens += [0] * (11 + f.bits(7))
                f.avancar()
            tlit, tdist = _tabela(lens[:hlit]), _tabela(lens[hlit:hlit + hdist])
        elif tipo == 1:
            if _ESTATICO is None:
                _ESTATICO = (_tabela([8] * 144 + [9] * 112 + [7] * 24 + [8] * 8), _tabela([5] * 32))
            tlit, tdist = _ESTATICO
        elif tipo == 0:
            n = f.bits(16)
            for _ in range(n):
                saida[pos] = f.bits(8); pos += 1
                f.avancar()
            if final:
                return bytes(saida[:pos])
            continue
        else:
            raise ErroGDeflate("tipo de bloco inválido")
        # o laço principal: um símbolo por sub-fluxo por rodada; a distância vem na rodada seguinte, no mesmo sub-fluxo
        f.i = 0
        pend = [None] * FLUXOS                          # (comprimento, onde escrever) esperando a distância
        while True:
            i = f.i
            if pend[i] is None:
                s = f.simbolo(tlit)
                if s < 256:
                    saida[pos] = s; pos += 1
                elif s == 256:
                    break
                else:
                    k = s - 257
                    comp = _BASE_COMP[k] + (f.bits(_EXTRA_COMP[k]) if _EXTRA_COMP[k] else 0)
                    pend[i] = (comp, pos)
                    pos += comp
            else:
                comp, onde = pend[i]
                k = f.simbolo(tdist)
                dist = _BASE_DIST[k] + (f.bits(_EXTRA_DIST[k]) if _EXTRA_DIST[k] else 0)
                if dist > onde:
                    raise ErroGDeflate("distância antes do início")
                for j in range(comp):
                    saida[onde + j] = saida[onde - dist + j]
                pend[i] = None
            f.avancar()
        for _ in range(FLUXOS):                         # as cópias que ficaram para a última rodada
            i = f.i
            if pend[i] is not None:
                comp, onde = pend[i]
                k = f.simbolo(tdist)
                dist = _BASE_DIST[k] + (f.bits(_EXTRA_DIST[k]) if _EXTRA_DIST[k] else 0)
                for j in range(comp):
                    saida[onde + j] = saida[onde - dist + j]
                pend[i] = None
            f.avancar()
        if final:
            return bytes(saida[:pos])


def descomprimir(fluxo: bytes) -> bytes:
    """Um TileStream GDeflate inteiro → os bytes originais."""
    ident, magia, ntiles = struct.unpack_from("<BBH", fluxo, 0)
    if ident != 4 or magia != ident ^ 0xFF:
        raise ErroGDeflate(f"não é GDeflate (id {ident}, magia {magia:#x})")
    campos = struct.unpack_from("<I", fluxo, 4)[0]
    ultimo = (campos >> 2) & 0x3FFFF
    offs = struct.unpack_from("<%dI" % ntiles, fluxo, 8)
    dados = fluxo[8 + 4 * ntiles:]
    saida = bytearray()
    for t in range(ntiles):
        ini = offs[t] if t > 0 else 0
        fim = offs[t + 1] if t < ntiles - 1 else ini + offs[0]
        tam = ultimo if (t == ntiles - 1 and ultimo) else TILE
        saida += _tile(dados[ini:fim], tam)
    return bytes(saida)
