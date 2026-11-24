import numpy as np
def ler_rawi(caminho, mascara_ctrl=0xFF):
    f=open(caminho,"rb").read()
    assert f[:4]==b"RAWI"
    u=np.frombuffer(f[:64],'<u4'); hdr=int(u[3]); size=int(u[4]); W=int(u[5]); H=int(u[6])
    w=np.frombuffer(f[hdr:hdr+size],'<u2'); out=np.empty(W*H,np.uint16); o=0; i=0; n=len(w)
    while i<n and o<W*H:
        c=int(w[i])&mascara_ctrl; i+=1
        if c<0x80:
            k=c+1; out[o:o+k]=w[i:i+k]; i+=k
        else:
            k=c-127; out[o:o+k]=w[i]; i+=1
        o+=k
    return out[:W*H].reshape(H,W).view(np.float16), o, i, n
if __name__=="__main__":
    import sys
    for p in sys.argv[1:]:
        img,o,i,n=ler_rawi(p); print(p.split('/')[-1],"valores",o,"de",1920*1080,"| palavras usadas",i,"de",n,"| min/max",float(img.min()),float(img.max()))
