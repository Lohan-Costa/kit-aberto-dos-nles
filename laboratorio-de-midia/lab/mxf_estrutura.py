"""O cabeçalho de um MXF, set por set: para comparar o OP-Atom que o laboratório grava com o de um NLE.

Só LÊ, e só o começo do arquivo (até a primeira essência): serve também para a `Avid MediaFiles` protegida.
Os nomes das propriedades vêm da tabela de local tags padrão (SMPTE 377M) e, para as dinâmicas (≥ 0x8000), do
UL no Primer Pack (impresso em hexa quando não é conhecido).

    python3 -m lab.mxf_estrutura arquivo.mxf
    python3 -m lab.mxf_estrutura a.mxf b.mxf      # lado a lado: os sets e as propriedades que só um tem
"""
from __future__ import annotations

import json
import struct
import sys

SETS = {  # byte 14 (índice 13) do UL de set do header metadata: 06 0e 2b 34 02 53 01 01 0d 01 01 01 01 01 XX 00
    0x2f: "Preface", 0x30: "Identification", 0x18: "ContentStorage", 0x23: "EssenceContainerData",
    0x36: "MaterialPackage", 0x37: "SourcePackage", 0x3b: "TimelineTrack", 0x39: "EventTrack", 0x3a: "StaticTrack",
    0x0f: "Sequence", 0x11: "SourceClip", 0x14: "TimecodeComponent", 0x41: "DMSegment", 0x44: "MultipleDescriptor",
    0x28: "CDCIEssenceDescriptor", 0x29: "RGBAEssenceDescriptor", 0x42: "GenericSoundDescriptor",
    0x47: "AES3PCMDescriptor", 0x48: "WAVEPCMDescriptor", 0x51: "MPEG2VideoDescriptor", 0x27: "GenericPictureDescriptor",
    0x2e: "TapeDescriptor", 0x32: "ImportDescriptor", 0x60: "PackageMarkerObject", 0x3f: "TaggedValue",
    0x5c: "AuxDescriptor", 0x5b: "VBIDescriptor",
}
TAGS = {
    0x3c0a: "InstanceUID", 0x0102: "GenerationUID", 0x3b02: "LastModifiedDate", 0x3b05: "Version", 0x3b07: "ObjectModelVersion",
    0x3b08: "PrimaryPackage", 0x3b06: "Identifications", 0x3b03: "ContentStorage", 0x3b09: "OperationalPattern",
    0x3b0a: "EssenceContainers", 0x3b0b: "DMSchemes", 0x3c09: "ThisGenerationUID", 0x3c01: "CompanyName",
    0x3c02: "ProductName", 0x3c03: "ProductVersion", 0x3c04: "VersionString", 0x3c05: "ProductUID", 0x3c06: "ModificationDate",
    0x3c07: "ToolkitVersion", 0x3c08: "Platform", 0x1901: "Packages", 0x1902: "EssenceContainerData",
    0x2701: "LinkedPackageUID", 0x3f06: "IndexSID", 0x3f07: "BodySID", 0x4401: "PackageUID", 0x4402: "Name",
    0x4405: "PackageCreationDate", 0x4404: "PackageModifiedDate", 0x4403: "Tracks", 0x4406: "UserComments",
    0x4409: "Attributes", 0x4701: "Descriptor", 0x4801: "TrackID", 0x4804: "TrackNumber", 0x4802: "TrackName",
    0x4b01: "EditRate", 0x4b02: "Origin", 0x4803: "Sequence", 0x0201: "DataDefinition", 0x0202: "Duration",
    0x1001: "StructuralComponents", 0x1101: "SourcePackageID", 0x1102: "SourceTrackID", 0x1201: "StartPosition",
    0x1501: "StartTimecode", 0x1502: "RoundedTimecodeBase", 0x1503: "DropFrame", 0x2f01: "Locators",
    0x3001: "SampleRate", 0x3002: "ContainerDuration", 0x3004: "EssenceContainer", 0x3005: "Codec",
    0x3006: "LinkedTrackID", 0x3f01: "SubDescriptors", 0x3201: "PictureEssenceCoding", 0x3202: "StoredHeight",
    0x3203: "StoredWidth", 0x3204: "SampledHeight", 0x3205: "SampledWidth", 0x3206: "SampledXOffset",
    0x3207: "SampledYOffset", 0x3208: "DisplayHeight", 0x3209: "DisplayWidth", 0x320a: "DisplayXOffset",
    0x320b: "DisplayYOffset", 0x320c: "FrameLayout", 0x320d: "VideoLineMap", 0x320e: "AspectRatio",
    0x3211: "ImageAlignmentOffset", 0x3212: "FieldDominance", 0x3213: "ImageStartOffset", 0x3214: "ImageEndOffset",
    0x3215: "SignalStandard", 0x3216: "StoredF2Offset", 0x3217: "DisplayF2Offset", 0x3218: "ActiveFormatDescriptor",
    0x3219: "ColorPrimaries", 0x321a: "CodingEquations", 0x3210: "TransferCharacteristic", 0x3301: "ComponentDepth",
    0x3302: "HorizontalSubsampling", 0x3303: "ColorSiting", 0x3304: "BlackRefLevel", 0x3305: "WhiteRefLevel",
    0x3306: "ColorRange", 0x3307: "PaddingBits", 0x3308: "VerticalSubsampling", 0x3309: "AlphaSampleDepth",
    0x330b: "ReversedByteOrder", 0x3d03: "AudioSamplingRate", 0x3d02: "Locked", 0x3d04: "AudioRefLevel",
    0x3d05: "ElectroSpatialFormulation", 0x3d07: "ChannelCount", 0x3d01: "QuantizationBits", 0x3d0c: "DialNorm",
    0x3d06: "SoundEssenceCompression", 0x3d0a: "BlockAlign", 0x3d0b: "SequenceOffset", 0x3d09: "AverageBytesPerSecond",
    0x3d32: "ChannelAssignment", 0x3d29: "PeakEnvelopeVersion", 0x2f02: "LocatorURL",
}
# ULs de propriedades DINÂMICAS que sabemos nomear (o resto sai em hexa)
DINAMICAS = {
    "060e2b34010101020401060100000000": "PictureEssenceCoding? (dyn)",
    "060e2b34010101080601010401000000": "SubDescriptors? (dyn)",
}


def _uid(b: bytes) -> str:
    return b.hex()


def _ber(dados: bytes, i: int) -> tuple[int, int]:
    n = dados[i]
    if n < 0x80:
        return n, i + 1
    k = n & 0x7f
    return int.from_bytes(dados[i + 1:i + 1 + k], "big"), i + 1 + k


def _valor(tag: int, v: bytes):
    if tag in (0x4402, 0x4802, 0x3c01, 0x3c02, 0x3c04, 0x3c08, 0x2f02):
        try:
            return v.decode("utf-16-be").rstrip("\x00")
        except UnicodeDecodeError:
            return v.hex()
    if tag in (0x4b01, 0x3001, 0x3d03, 0x320e):
        if len(v) == 8:
            a, b = struct.unpack(">ii", v)
            return f"{a}/{b}"
    if tag in (0x4801, 0x1102, 0x3006, 0x3203, 0x3202, 0x3209, 0x3208, 0x3205, 0x3204, 0x3d07, 0x3d01, 0x3d0a,
               0x3d09, 0x3301, 0x3302, 0x3308, 0x1502, 0x3f06, 0x3f07, 0x3211, 0x3213, 0x3214) and len(v) <= 4:
        return int.from_bytes(v, "big")
    if tag in (0x0202, 0x3002, 0x1201, 0x1501, 0x4b02) and len(v) == 8:
        return int.from_bytes(v, "big", signed=True)
    if tag in (0x1503, 0x320c, 0x3d02, 0x3212, 0x3215) and len(v) == 1:
        return v[0]
    if len(v) >= 8 and len(v) % 16 == 8 and int.from_bytes(v[:4], "big") * int.from_bytes(v[4:8], "big") == len(v) - 8:
        n, k = int.from_bytes(v[:4], "big"), int.from_bytes(v[4:8], "big")     # lote/array de UIDs ou ULs
        return [v[8 + j * k:8 + (j + 1) * k].hex() for j in range(n)]
    if len(v) in (16, 32):
        return v.hex()
    return v.hex() if len(v) <= 48 else f"<{len(v)} bytes>"


def sets(caminho: str, limite: int = 8 * 1024 * 1024) -> list[dict]:
    with open(caminho, "rb") as fh:
        dados = fh.read(limite)
    i, primer, saida = 0, {}, []
    while i + 17 <= len(dados):
        chave = dados[i:i + 16]
        n, j = _ber(dados, i + 16)
        corpo = dados[j:j + n]
        if chave[:4] != b"\x06\x0e\x2b\x34":
            # o "Root" do dicionário AAF que o Avid/Resolve gravam (chave fora do SMPTE, ex.: 8053080036210804…)
            saida.append({"set": "nao-SMPTE:" + chave.hex(), "bytes": n})
            i = j + n
            continue
        if chave[4:6] == b"\x01\x02" and chave[12] in (0x15, 0x16, 0x17, 0x18):   # essência: fim do cabeçalho
            break
        if chave[:13] == bytes.fromhex("060e2b34020501010d01020101"):              # partição
            saida.append({"set": "Partition", "tipo": chave[13:15].hex()})
        elif chave == bytes.fromhex("060e2b34020501010d01020101050100"):
            pass
        elif chave[:14] == bytes.fromhex("060e2b34020501010d0102010105"):          # primer pack
            cont, tam = struct.unpack(">II", corpo[:8])
            for k in range(cont):
                e = corpo[8 + k * 18:8 + (k + 1) * 18]
                primer[int.from_bytes(e[:2], "big")] = e[2:].hex()
        elif chave[4:6] == b"\x02\x53":                                              # set com local tags
            if chave[12] == 0x02:      # 0d 01 01 01 02 XX: o DICIONÁRIO (definições de classe/propriedade/tipo)
                nome = "MetaDicionario:%02x" % chave[13]
            else:                      # 0d 01 01 01 01 01 XX: os sets estruturais
                nome = SETS.get(chave[14], "?" + chave.hex())
            props, p = {}, 0
            while p + 4 <= len(corpo):
                tag, tam = struct.unpack(">HH", corpo[p:p + 4])
                v = corpo[p + 4:p + 4 + tam]
                rotulo = TAGS.get(tag) if tag < 0x8000 else DINAMICAS.get(primer.get(tag, ""), "dyn:" + primer.get(tag, hex(tag)))
                props[rotulo or hex(tag)] = _valor(tag, v)
                p += 4 + tam
            saida.append({"set": nome, "props": props})
        elif chave[4:6] == b"\x02\x53" or chave[4] == 0x02:
            saida.append({"set": "outro:" + chave.hex(), "bytes": n})
        i = j + n
    return saida


def resumo(caminho: str) -> dict:
    s = [x for x in sets(caminho) if "props" in x]
    contagem: dict[str, int] = {}
    for x in s:
        contagem[x["set"]] = contagem.get(x["set"], 0) + 1
    return {"arquivo": caminho, "sets": contagem, "detalhe": s}


if __name__ == "__main__":
    if len(sys.argv) == 2:
        print(json.dumps(resumo(sys.argv[1]), ensure_ascii=False, indent=1))
    else:
        a, b = resumo(sys.argv[1]), resumo(sys.argv[2])
        print("SETS:", json.dumps({k: [a["sets"].get(k, 0), b["sets"].get(k, 0)]
                                   for k in sorted(set(a["sets"]) | set(b["sets"]))}, ensure_ascii=False))
        for nome in sorted(set(a["sets"]) | set(b["sets"])):
            pa = set().union(*[x["props"] for x in a["detalhe"] if x["set"] == nome]) if nome in a["sets"] else set()
            pb = set().union(*[x["props"] for x in b["detalhe"] if x["set"] == nome]) if nome in b["sets"] else set()
            if pa != pb:
                print(f"{nome}: só no 1º {sorted(pa - pb)} | só no 2º {sorted(pb - pa)}")
