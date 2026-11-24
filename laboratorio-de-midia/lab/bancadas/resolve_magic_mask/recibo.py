# uso: recibo.py <Project.db> <item_id> [serie]  -> grava o RenderCacheBA (o "recibo" do Magic Mask) no clipe
import sqlite3,sys,zlib,struct
db,item=sys.argv[1:3]; serie=int(sys.argv[3],0) if len(sys.argv)>3 else 0x7ffffff0
con=sqlite3.connect(db)
ver=con.execute('select pActive from "ListMgt::LmVersionTable" where Sm2TiItem_id=?',(item,)).fetchone()[0]
mod=zlib.decompress(sqlite3.connect("file:Z_depois.db?mode=ro",uri=True).execute('select RenderCacheBA from Sm2TiItem where Sm2TiItem_id=?',("57749910-892f-4e7d-a1ab-22f0bf222240",)).fetchone()[0][4:])
d=bytearray(mod); vz=b"0ec9344f-465e-4900-a36e-a8b5c1221794"; i=d.find(vz); d[i:i+36]=ver.encode()
d[0x4c:0x50]=struct.pack(">I",serie); d[0x96:0x9a]=struct.pack(">I",serie+3)
z=zlib.compress(bytes(d)); blob=struct.pack(">I",len(d))+z
con.execute('update Sm2TiItem set RenderCacheBA=? where Sm2TiItem_id=?',(blob,item)); con.commit(); con.close()
print("recibo gravado: versao",ver,"serie",hex(serie))
