def rv(b,i):
    r=s=0
    while True:
        x=b[i]; i+=1; r|=(x&0x7f)<<s; s+=7
        if x<0x80: return r,i
def wv(n):
    o=bytearray()
    while True:
        x=n&0x7f; n>>=7
        if n: o.append(x|0x80)
        else: o.append(x); return bytes(o)
def campos(b):
    """lista de (campo, tipo, bruto_valor) ou None se não for mensagem válida"""
    i=0; out=[]
    try:
        while i<len(b):
            k,i=rv(b,i); f,t=k>>3,k&7
            if f==0: return None
            if t==0: j=i; _,i=rv(b,i); out.append((f,t,b[j:i]))
            elif t==1: out.append((f,t,b[i:i+8])); i+=8
            elif t==5: out.append((f,t,b[i:i+4])); i+=4
            elif t==2: n,i=rv(b,i); out.append((f,t,b[i:i+n])); i+=n
            else: return None
        return out if i==len(b) else None
    except IndexError: return None
def tirar(b, campo, tipo=0):
    """remove recursivamente todo campo `campo` de tipo varint; devolve (novo, quantos)"""
    cs=campos(b)
    if cs is None: return b,0
    o=bytearray(); tot=0
    for f,t,v in cs:
        if f==campo and t==tipo: tot+=1; continue
        if t==2:
            nv,k=tirar(v,campo,tipo)
            if k: tot+=k; v=nv
            o+=wv(f<<3|t)+wv(len(v))+v
        elif t==0: o+=wv(f<<3|t)+v
        else: o+=wv(f<<3|t)+v
    return bytes(o),tot
