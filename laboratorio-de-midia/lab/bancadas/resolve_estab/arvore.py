from comum import *
import re, sys, zstandard, struct
from tools.inspect_drp import pb_decode
def body_do_xml(arq):
    x = open(arq, encoding="utf-8").read()
    return [bytes.fromhex(b) for b in re.findall(r"<Body>([0-9a-f]+)</Body>", x)]
def dec(b):
    assert b[0] == 0x81
    return zstandard.ZstdDecompressor().decompress(b[1:], max_output_size=1 << 28)
def mostra(fs, ind=0, prof=0, lim=6):
    vistos = {}
    for f in fs:
        k = f["field"]; vistos[k] = vistos.get(k, 0) + 1
        if vistos[k] > lim: 
            if vistos[k] == lim + 1: print(" " * ind + f"{k}: …")
            continue
        v = f["value"]
        if isinstance(v, list):
            print(" " * ind + f"{k}:"); mostra(v, ind + 2, prof + 1, lim)
        elif f["wire"] == 5:
            print(" " * ind + f"{k}: f32 {struct.unpack('<f', v)[0]:.6g}")
        elif f["wire"] == 0:
            print(" " * ind + f"{k}: {v} (0x{v:x})")
        else:
            print(" " * ind + f"{k}: bytes[{len(v)}] {v[:48].hex()}")
if __name__ == "__main__":
    for b in body_do_xml(sys.argv[1]):
        d = dec(b)
        print("=== body", len(d), "contém 0x10300015:", (0x10300015).to_bytes(4,'little') in d)
        if len(sys.argv) > 2: mostra(pb_decode(d), lim=int(sys.argv[2]))
