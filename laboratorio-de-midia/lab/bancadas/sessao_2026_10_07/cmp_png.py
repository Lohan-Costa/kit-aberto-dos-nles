"""Compara dois PNGs (mesmo tamanho): % de pixels com diferença > tolerância e onde fica a área visível (alfa > 0)."""
import struct, sys, zlib


def png(p):
    d = open(p, "rb").read(); i = 8; idat = b""
    while i < len(d):
        n = struct.unpack(">I", d[i:i + 4])[0]; t = d[i + 4:i + 8]; c = d[i + 8:i + 8 + n]
        if t == b"IHDR": w, h, bd, ct = struct.unpack(">IIBB", c[:10])
        if t == b"IDAT": idat += c
        i += 12 + n
    raw = zlib.decompress(idat); bpp = {2: 3, 6: 4}[ct]; st = w * bpp; out = []; prev = bytearray(st); q = 0
    for y in range(h):
        f = raw[q]; line = bytearray(raw[q + 1:q + 1 + st]); q += 1 + st
        for x in range(st):
            a = line[x - bpp] if x >= bpp else 0; b = prev[x]; c = prev[x - bpp] if x >= bpp else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pa = abs(b - c); pb = abs(a - c); pc = abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        out.append(bytes(line)); prev = line
    return w, h, bpp, out


def caixa(w, h, bpp, px, passo=4):
    xs = []; ys = []
    for y in range(0, h, passo):
        for x in range(0, w, passo):
            vis = px[y][x * bpp + 3] > 0 if bpp == 4 else any(px[y][x * bpp:x * bpp + 3])
            if vis: xs.append(x); ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def comparar(a, b, tol=12, passo=4):
    w, h, bpp, A = png(a); w2, h2, bpp2, Bp = png(b)
    if (w, h) != (w2, h2): return {"erro": f"tamanhos {w}x{h} x {w2}x{h2}"}
    dif = tot = 0
    for y in range(0, h, passo):
        for x in range(0, w, passo):
            pa = A[y][x * bpp:x * bpp + bpp]; pb = Bp[y][x * bpp2:x * bpp2 + bpp2]
            va = pa[3] > 0 if bpp == 4 else True; vb = pb[3] > 0 if bpp2 == 4 else True
            tot += 1
            if va != vb or (va and max(abs(pa[k] - pb[k]) for k in range(3)) > tol): dif += 1
    return {"diferentes_%": round(100 * dif / tot, 2), "visivel_ref": caixa(w, h, bpp, A), "visivel_win": caixa(w2, h2, bpp2, Bp)}


if __name__ == "__main__":
    print(comparar(sys.argv[1], sys.argv[2]))
