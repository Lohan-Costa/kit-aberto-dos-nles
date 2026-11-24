# uso: editar_banco.py <Project.db> <item_id>  -> tira os campos 12 da versão de cor ativa do clipe (zstd como o Resolve)
import sqlite3,sys
from pb import tirar
from zst import comprimir,abrir
db,item=sys.argv[1:3]; con=sqlite3.connect(db)
ver=con.execute('select pActive from "ListMgt::LmVersionTable" where Sm2TiItem_id=?',(item,)).fetchone()[0]
b=con.execute('select Body from "ListMgt::LmVersion" where "ListMgt::LmVersion_id"=?',(ver,)).fetchone()[0]
i=b.find(b'\x28\xb5\x2f\xfd'); novo,k=tirar(abrir(b[i:]),12)
con.execute('update "ListMgt::LmVersion" set Body=? where "ListMgt::LmVersion_id"=?',(b[:i]+comprimir(novo),ver)); con.commit(); con.close()
print("campos 12 tirados:",k)
