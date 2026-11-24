"""Gravador de OP-Atom do laboratório: costura os arquivos que o ffmpeg grava num CLIPE só, como o Avid.

O ffmpeg (`-f mxf_opatom`) grava uma trilha por arquivo, cada uma com a SUA identidade de clipe
(`material_package_umid`) e o MaterialPackage listando só a própria trilha — o Premiere e o Resolve importam 3
clipes soltos. No OP-Atom que o Resolve grava para o Avid (a referência), CADA arquivo traz o MaterialPackage com
TODAS as trilhas do clipe, cada SourceClip apontando o pacote de arquivo do irmão (banco, protocolos/mxf/README.md
§"O OP-Atom do ffmpeg ROTULA errado"). Este módulo:

1. lê os KLV de cada arquivo do ffmpeg (sem carregar a essência);
2. monta um MaterialPackage comum — mesma UMID, a trilha de TC e uma trilha por arquivo (V1, A1, A2…), com
   InstanceUIDs novos para os sets copiados de um irmão (o ffmpeg repete o mesmo padrão de UID nos três);
3. regrava cada arquivo: cabeçalho novo + a essência e o índice copiados, partições e RIP recalculados;
4. troca o rótulo do container de frame- para clip-wrapped (a essência é clip-wrapped; o rótulo errado faz o
   Premiere recusar o vídeo).

Só biblioteca padrão. `python3 -m lab.opatom saida_dir NOME V01.mxf A01.mxf A02.mxf`
"""
from __future__ import annotations

import os
import shutil
import struct
import sys
import uuid

KAG = 512
CHAVE_PARTICAO = "060e2b34020501010d01020101"       # + 2 bytes (tipo) + 00
CHAVE_PRIMER = bytes.fromhex("060e2b34020501010d01020101050100")
CHAVE_RIP = bytes.fromhex("060e2b34020501010d01020101110100")
CHAVE_FILL = bytes.fromhex("060e2b34010101020301021001000000")
ROTULOS_CLIP = {
    bytes.fromhex("060e2b340401010a0d01030102110100"): bytes.fromhex("060e2b340401010a0d01030102110200"),  # VC-3/DNx
    bytes.fromhex("060e2b34040101010d01030102060100"): bytes.fromhex("060e2b34040101010d01030102060200"),  # BWF
}
# tags (local) das referências fortes e dos campos que o costureiro mexe
T_UID, T_PKG_UID, T_TRACKS, T_TRACK_ID, T_TRACK_NUM, T_SEQ, T_COMPONENTS, T_SRC_PKG, T_SRC_TRACK, T_PACKAGES, \
    T_NAME, T_TRACK_NAME = 0x3c0a, 0x4401, 0x4403, 0x4801, 0x4804, 0x4803, 0x1001, 0x1101, 0x1102, 0x1901, 0x4402, 0x4802
# ULs das propriedades de nome (para o Primer, se o ffmpeg não as declarou)
UL_NOME = {T_NAME: "060e2b34010101010103030201000000", T_TRACK_NAME: "060e2b34010101020107010201000000"}
SET_MATERIAL = 0x36
SET_TC = 0x14


# ----------------------------------------------------------------------------------------------- leitura KLV
def _ber(fh_ou_bytes, pos=None):
    if isinstance(fh_ou_bytes, (bytes, bytearray)):
        d, i = fh_ou_bytes, pos
        n = d[i]
        if n < 0x80:
            return n, i + 1
        k = n & 0x7F
        return int.from_bytes(d[i + 1:i + 1 + k], "big"), i + 1 + k
    fh = fh_ou_bytes
    n = fh.read(1)[0]
    if n < 0x80:
        return n, 1
    k = n & 0x7F
    return int.from_bytes(fh.read(k), "big"), 1 + k


def ler_klvs(caminho: str) -> list[dict]:
    """[{pos, chave, val_pos, tam, valor (None para essência)}]."""
    saida = []
    tam_arq = os.path.getsize(caminho)
    with open(caminho, "rb") as fh:
        pos = 0
        while pos < tam_arq:
            fh.seek(pos)
            chave = fh.read(16)
            if len(chave) < 16:
                break
            n, nb = _ber(fh)
            val_pos = pos + 16 + nb
            essencia = chave[4:6] == b"\x01\x02" and chave[12] in (0x15, 0x16, 0x17, 0x18)
            valor = None if essencia else fh.read(n)
            saida.append({"pos": pos, "chave": chave, "val_pos": val_pos, "tam": n, "valor": valor, "essencia": essencia})
            pos = val_pos + n
    return saida


def _props(valor: bytes) -> list[list]:
    p, out = 0, []
    while p + 4 <= len(valor):
        tag, tam = struct.unpack(">HH", valor[p:p + 4])
        out.append([tag, valor[p + 4:p + 4 + tam]])
        p += 4 + tam
    return out


def _get(props, tag):
    return next((v for t, v in props if t == tag), None)


def _set(props, tag, valor):
    for par in props:
        if par[0] == tag:
            par[1] = valor
            return
    props.append([tag, valor])


def _lote(uids: list[bytes]) -> bytes:
    return struct.pack(">II", len(uids), 16) + b"".join(uids)


def _do_lote(v: bytes) -> list[bytes]:
    n, k = struct.unpack(">II", v[:8])
    return [v[8 + i * k:8 + (i + 1) * k] for i in range(n)]


class Arquivo:
    """Um OP-Atom do ffmpeg, lido: partições, primer, sets do cabeçalho, essência, índice."""

    def __init__(self, caminho: str):
        self.caminho = caminho
        self.klvs = ler_klvs(caminho)
        self.primer = next(k["valor"] for k in self.klvs if k["chave"] == CHAVE_PRIMER)
        self.sets = []           # [(chave, props)] na ordem do arquivo
        for k in self.klvs:
            if k["chave"][4:6] == b"\x02\x53" and k["pos"] < self._pos_corpo():
                self.sets.append((k["chave"], _props(k["valor"])))
        self.por_uid = {_get(p, T_UID): (c, p) for c, p in self.sets}
        self.essencia = next(k for k in self.klvs if k["essencia"])
        self.indice = [k for k in self.klvs if k["chave"][:14] == bytes.fromhex("060e2b34025301010d0102010110")]
        cabecalho = self.klvs[0]["valor"]
        self.particao_cab = cabecalho
        self.op = cabecalho[64:80]
        parts = {k["chave"][13]: k["valor"] for k in self.klvs if k["chave"].hex().startswith(CHAVE_PARTICAO)}
        self.sid_corpo = struct.unpack(">I", parts[0x03][60:64])[0]
        self.sid_indice = struct.unpack(">I", parts[0x04][48:52])[0]

    def _pos_corpo(self) -> int:
        return next(k["pos"] for k in self.klvs if k["chave"].hex().startswith(CHAVE_PARTICAO) and k["chave"][13] == 0x03)

    def tipo(self, chave: bytes) -> int:
        return chave[14]

    def material(self):
        return next((c, p) for c, p in self.sets if c[14] == SET_MATERIAL and c[12] == 0x01)

    def trilhas_material(self):
        """[(track, sequence, [componentes])] do MaterialPackage, cada um como (chave, props)."""
        _, mp = self.material()
        out = []
        for uid in _do_lote(_get(mp, T_TRACKS)):
            tc, tp = self.por_uid[uid]
            sc, sp = self.por_uid[_get(tp, T_SEQ)]
            comps = [self.por_uid[u] for u in _do_lote(_get(sp, T_COMPONENTS))]
            out.append(((tc, tp), (sc, sp), comps))
        return out


def _e_tc(trilha) -> bool:
    _, _, comps = trilha
    return any(c[14] == SET_TC for c, _ in comps)


def _clonar(trilha, novo_id: int, nome: str | None):
    """Cópia de uma trilha do MaterialPackage (track → sequence → componentes) com InstanceUIDs novos."""
    (tc, tp), (sc, sp), comps = trilha
    novos_comps = []
    for c, p in comps:
        p2 = [list(x) for x in p]
        _set(p2, T_UID, uuid.uuid4().bytes)
        novos_comps.append((c, p2))
    sp2 = [list(x) for x in sp]
    _set(sp2, T_UID, uuid.uuid4().bytes)
    _set(sp2, T_COMPONENTS, _lote([_get(p, T_UID) for _, p in novos_comps]))
    tp2 = [list(x) for x in tp]
    _set(tp2, T_UID, uuid.uuid4().bytes)
    _set(tp2, T_SEQ, _get(sp2, T_UID))
    _set(tp2, T_TRACK_ID, struct.pack(">I", novo_id))
    if nome:
        _set(tp2, T_TRACK_NAME, nome.encode("utf-16-be"))
    return [(tc, tp2), (sc, sp2)] + novos_comps


def umid_nova() -> bytes:
    """UMID básica SMPTE 330M: o rótulo de 12 bytes, comprimento 0x13, instância 0, material de 16 bytes."""
    return bytes.fromhex("060a2b340101010501010d00") + b"\x13\x00\x00\x00" + uuid.uuid4().bytes


# ----------------------------------------------------------------------------------------------- escrita
def _klv(chave: bytes, valor: bytes) -> bytes:
    n = len(valor)
    return chave + bytes([0x83]) + n.to_bytes(3, "big") + valor if n < (1 << 24) else \
        chave + bytes([0x88]) + n.to_bytes(8, "big") + valor


def _fill_ate(pos: int, kag: int = KAG) -> bytes:
    """Um KLV de preenchimento que leva `pos` ao próximo múltiplo de `kag` (no mínimo 20 bytes: chave + BER 4)."""
    falta = (-pos) % kag
    if falta == 0:
        return b""
    if falta < 20:
        falta += kag
    return CHAVE_FILL + bytes([0x83]) + (falta - 20).to_bytes(3, "big") + b"\x00" * (falta - 20)


def _serializar_set(chave: bytes, props) -> bytes:
    return _klv(chave, b"".join(struct.pack(">HH", t, len(v)) + v for t, v in props))


def _particao(tipo: bytes, this: int, prev: int, footer: int, hbc: int, ibc: int, isid: int, bsid: int,
              op: bytes, containers: list[bytes]) -> bytes:
    v = struct.pack(">HHIQQQQQIQI", 1, 3, KAG, this, prev, footer, hbc, ibc, isid, 0, bsid) + op + _lote(containers)
    return _klv(bytes.fromhex(CHAVE_PARTICAO) + tipo + b"\x00", v)


def _rotulo_clip(b: bytes) -> bytes:
    for velho, novo in ROTULOS_CLIP.items():
        b = b.replace(velho, novo)
    return b


def costurar(caminhos: list[str], destinos: list[str], nome_clipe: str) -> dict:
    """`caminhos[0]` é o vídeo (ou a primeira trilha), os demais os irmãos. Grava cada um em `destinos[i]`."""
    arqs = [Arquivo(c) for c in caminhos]
    umid = umid_nova()
    # as trilhas do clipe: o TC do primeiro e a trilha de essência de cada arquivo, nesta ordem
    tc = next(t for t in arqs[0].trilhas_material() if _e_tc(t))
    essencias = [next(t for t in a.trilhas_material() if not _e_tc(t)) for a in arqs]
    nomes = []
    nv = na = 0
    for a in arqs:
        if "Picture" in _tipo_dados(a) or a.essencia["chave"][12] == 0x15:
            nv += 1
            nomes.append(f"V{nv}")
        else:
            na += 1
            nomes.append(f"A{na}")
    resumo = {"umid": umid.hex(), "trilhas": ["TC1"] + nomes, "arquivos": []}
    for i, a in enumerate(arqs):
        sets_novos = []
        trilhas_mp = _clonar(tc, 1, "TC1")
        for j, e in enumerate(essencias):
            trilhas_mp += _clonar(e, 2 + j, nomes[j])
        mc, mp = a.material()
        mp2 = [list(x) for x in mp]
        _set(mp2, T_PKG_UID, umid)
        _set(mp2, T_NAME, nome_clipe.encode("utf-16-be"))
        _set(mp2, T_TRACKS, _lote([_get(p, T_UID) for c, p in trilhas_mp if c[14] == 0x3b]))
        velhos = set()
        for trilha in a.trilhas_material():
            (tcx, tpx), (scx, spx), comps = trilha
            velhos |= {_get(tpx, T_UID), _get(spx, T_UID)} | {_get(p, T_UID) for _, p in comps}
        for c, p in a.sets:
            uid = _get(p, T_UID)
            if uid in velhos:
                continue
            if c[14] == SET_MATERIAL and c[12] == 0x01:
                sets_novos.append((c, mp2))
                sets_novos += trilhas_mp
            else:
                p2 = [list(x) for x in p]
                if c[14] == 0x37:          # SourcePackage (o do arquivo): o nome do clipe também
                    _set(p2, T_NAME, nome_clipe.encode("utf-16-be"))
                sets_novos.append((c, p2))
        resumo["arquivos"].append(_gravar(a, sets_novos, destinos[i]))
    return resumo


def _tipo_dados(a: Arquivo) -> str:
    return "Picture" if a.essencia["chave"][12] == 0x15 else "Sound"


def _primer_com(primer: bytes, tags: set[int]) -> bytes:
    n, k = struct.unpack(">II", primer[:8])
    itens = {int.from_bytes(primer[8 + i * 18:10 + i * 18], "big"): primer[10 + i * 18:26 + i * 18] for i in range(n)}
    for t in tags:
        if t not in itens and t in UL_NOME:
            itens[t] = bytes.fromhex(UL_NOME[t])
    return struct.pack(">II", len(itens), 18) + b"".join(t.to_bytes(2, "big") + ul for t, ul in sorted(itens.items()))


def _gravar(a: Arquivo, sets, destino: str) -> dict:
    containers = [_rotulo_clip(c) for c in _do_lote(a.particao_cab[80:])]
    tags = {t for _, p in sets for t, _ in p}
    corpo_meta = _klv(CHAVE_PRIMER, _primer_com(a.primer, tags))
    for c, p in sets:
        corpo_meta += _rotulo_clip(_serializar_set(c, p)) if c[14] in (0x2f, 0x28, 0x48, 0x42, 0x47, 0x44) \
            else _serializar_set(c, p)
    # cabeçalho: partição (tamanho fixo) + fill até o KAG, e o metadado até o próximo KAG
    tam_part = len(_particao(b"\x02\x04", 0, 0, 0, 0, 0, 0, 0, a.op, containers))
    inicio_meta = tam_part + len(_fill_ate(tam_part))
    meta = corpo_meta + _fill_ate(inicio_meta + len(corpo_meta))
    pos_corpo = inicio_meta + len(meta)
    part_corpo_tam = tam_part
    inicio_ess = pos_corpo + part_corpo_tam + len(_fill_ate(pos_corpo + part_corpo_tam))
    e = a.essencia
    cab_ess = e["chave"] + bytes([0x88]) + e["tam"].to_bytes(8, "big")
    fim_ess = inicio_ess + len(cab_ess) + e["tam"]
    pos_rodape = fim_ess + len(_fill_ate(fim_ess))
    indice = b"".join(_klv(k["chave"], k["valor"]) for k in a.indice)
    ini_idx = pos_rodape + tam_part + len(_fill_ate(pos_rodape + tam_part))
    idx_bloco = indice + _fill_ate(ini_idx + len(indice))
    # IndexSID e BodySID como o ffmpeg declarou nas partições dele (o EssenceContainerData copiado aponta os mesmos)
    sid_idx = a.sid_indice
    sid_corpo = a.sid_corpo
    with open(destino, "wb") as out:
        out.write(_particao(b"\x02\x04", 0, 0, pos_rodape, len(meta), 0, 0, 0, a.op, containers))
        out.write(_fill_ate(tam_part))
        out.write(meta)
        out.write(_particao(b"\x03\x04", pos_corpo, 0, pos_rodape, 0, 0, 0, sid_corpo, a.op, containers))
        out.write(_fill_ate(pos_corpo + part_corpo_tam))
        assert out.tell() == inicio_ess
        out.write(cab_ess)
        with open(a.caminho, "rb") as src:
            src.seek(e["val_pos"])
            restante = e["tam"]
            while restante:
                bloco = src.read(min(restante, 16 * 1024 * 1024))
                out.write(bloco)
                restante -= len(bloco)
        out.write(_fill_ate(fim_ess))
        assert out.tell() == pos_rodape
        out.write(_particao(b"\x04\x04", pos_rodape, pos_corpo, pos_rodape, 0, len(idx_bloco), sid_idx, 0, a.op, containers))
        out.write(_fill_ate(pos_rodape + tam_part))
        out.write(idx_bloco)
        rip = struct.pack(">IQ", 0, 0) + struct.pack(">IQ", sid_corpo, pos_corpo) + struct.pack(">IQ", 0, pos_rodape)
        tam_rip = 16 + 4 + len(rip) + 4
        out.write(CHAVE_RIP + bytes([0x83]) + (len(rip) + 4).to_bytes(3, "big") + rip + struct.pack(">I", tam_rip))
    return {"destino": destino, "bytes": os.path.getsize(destino), "essencia": e["tam"]}


if __name__ == "__main__":
    pasta, nome, *arqs = sys.argv[1:]
    os.makedirs(pasta, exist_ok=True)
    import json
    print(json.dumps(costurar(arqs, [os.path.join(pasta, os.path.basename(a)) for a in arqs], nome), indent=1))
