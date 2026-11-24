import struct,sys
def ler(b):
    assert b[:4]==b"v/1\x01"; ver=struct.unpack("<I",b[4:8])[0]; i=8; at={}
    while b[i]!=0:
        j=b.index(0,i); nome=b[i:j].decode(); k=b.index(0,j+1); tipo=b[j+1:k].decode(); n=struct.unpack("<I",b[k+1:k+5])[0]; val=b[k+5:k+5+n]; i=k+5+n
        if tipo=="chlist":
            chs=[];p=0
            while val[p]!=0:
                q=val.index(0,p); nm=val[p:q].decode(); pt,pl,xs,ys=struct.unpack("<iB3xii",val[q+1:q+17]); chs.append((nm,{0:"UINT",1:"HALF",2:"FLOAT"}[pt],xs,ys)); p=q+17
            val=chs
        elif tipo=="box2i": val=struct.unpack("<4i",val)
        elif tipo=="compression": val={0:"NONE",1:"RLE",2:"ZIPS",3:"ZIP",4:"PIZ"}.get(val[0],val[0])
        elif tipo=="lineOrder": val=val[0]
        elif tipo=="rational": val=struct.unpack("<iI",val)
        elif tipo=="string": val=val.decode(errors="replace")
        at[nome]=(tipo,val)
    return ver,at,i+1
if __name__=="__main__":
    for f in sys.argv[1:]:
        ver,at,fim=ler(open(f,"rb").read()); print(f.split('/')[-1],"versao",hex(ver),"fim cabecalho",fim)
        for k,v in at.items(): print("   ",k,v)
