import sys,zlib
b=open(sys.argv[1],'rb').read()
i=b.find(b'Compressed = true')
print('fim do texto em',i,'tam',len(b))
for off in range(i, len(b)-2):
    if b[off]==0x78 and b[off+1] in (0x01,0x5e,0x9c,0xda):
        try:
            d=zlib.decompressobj(); c=d.decompress(b[off:]); 
            print('zlib em',off,'->',len(c)); open(sys.argv[1]+'.tools.txt','wb').write(c); break
        except Exception as e: pass
print(b[i:i+60])
