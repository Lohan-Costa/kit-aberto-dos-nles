import struct,zlib,numpy as np
from exrhdr import ler as ler_hdr
def exr_uint(b):
    ver,at,p=ler_hdr(b); x0,y0,x1,y1=at["dataWindow"][1]; W=x1-x0+1; H=y1-y0+1
    comp=at["compression"][1]; lpb={"NONE":1,"RLE":1,"ZIPS":1,"ZIP":16,"PIZ":32}[comp]
    n=(H+lpb-1)//lpb; offs=struct.unpack(f"<{n}Q",b[p:p+8*n]); out=bytearray()
    for o in offs:
        y,sz=struct.unpack("<iI",b[o:o+8]); d=b[o+8:o+8+sz]; linhas=min(lpb,H-(y-y0)); bruto=W*4*linhas
        if sz<bruto:
            t=bytearray(zlib.decompress(d))
            for k in range(1,len(t)): t[k]=(t[k-1]+t[k]-128)&0xff        # preditor do EXR
            h=(len(t)+1)//2; r=bytearray(len(t)); r[0::2]=t[:h]; r[1::2]=t[h:]  # desentrelaça
            d=bytes(r)
        out+=d
    return np.frombuffer(bytes(out),'<u4').reshape(H,W), at
def ler_dvcc(caminho):
    raw=open(caminho,"rb").read(); i=raw.find(b"v/1\x01")
    return exr_uint(raw[i:])

def _zip_exr(raw):
    h=len(raw); t=bytearray(h)
    t[:(h+1)//2]=raw[0::2]; t[(h+1)//2:]=raw[1::2]            # entrelaça como o EXR
    p=bytearray(t)
    for k in range(h-1,0,-1): p[k]=(t[k]-t[k-1]+128)&0xff        # preditor do EXR
    return zlib.compress(bytes(p),6)
def escrever_dvcc(modelo, mascara_u8, destino, comprimir=False):
    """modelo: um .dvcc da MESMA pasta 0/ (cabeçalho DVCC + EXR); mascara_u8: 1080x1920 0/255."""
    raw=open(modelo,"rb").read(); i=raw.find(b"v/1\x01"); exr=raw[i:]
    ver,at,p=ler_hdr(exr); x0,y0,x1,y1=at["dataWindow"][1]; W=x1-x0+1; H=y1-y0+1
    n=(H+15)//16; dados=np.ascontiguousarray(mascara_u8,np.uint8).tobytes(); linha=W*4
    blocos=[]; pos=p+8*n
    for k in range(n):
        ini=k*16; lin=min(16,H-ini); bruto=dados[ini*linha:(ini+lin)*linha]; z=_zip_exr(bruto) if comprimir else bruto
        corpo=z if (comprimir and len(z)<len(bruto)) else bruto
        blocos.append(struct.pack("<iI",y0+ini,len(corpo))+corpo)
    offs=[]; o=pos
    for b in blocos: offs.append(o); o+=len(b)
    novo_exr=exr[:p]+struct.pack(f"<{n}Q",*offs)+b"".join(blocos)
    cab=bytearray(raw[:i]); cab[i-4:i]=struct.pack("<I",len(novo_exr))   # etiqueta 'g' = tamanho do EXR
    tudo=bytes(cab)+novo_exr; tudo+=b"\0"*((-len(tudo))%8192)
    open(destino,"wb").write(tudo)
