import re,sys,zlib,binascii
for fn in sys.argv[1:]:
    s=open(fn,encoding='utf-8').read()
    for i,h in enumerate(re.findall(r'<CompositionBA>([0-9a-f]+)</CompositionBA>',s)):
        raw=binascii.unhexlify(h); n=int.from_bytes(raw[:4],'big')
        c=zlib.decompress(raw[4:]); print(fn, 'BA', len(raw), 'declarado', n, 'aberto', len(c))
        open(fn.replace('/','_')+f'.{i}.comp','wb').write(c)
