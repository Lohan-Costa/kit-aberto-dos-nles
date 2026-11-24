# uso: montar_cache.py <nome do projeto> <proj_id> <item_id> <timeline_id> [pecas:dir com 256/ KeyframeBlob/ StateBlob/]
import sys,os,shutil,sqlite3,glob,numpy as np
from dvcc import escrever_dvcc
nome,proj,item,tlid=sys.argv[1:5]; pecas=sys.argv[5] if len(sys.argv)>5 else None
D=os.path.expanduser(f"~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Resolve Project Library/Resolve Projects/Users/guest/Projects/{nome}/Project.db")
shutil.copy(D,"tmp_proj.db")
con=sqlite3.connect("file:tmp_proj.db?mode=ro",uri=True)
seq=con.execute('select Sequence from Sm2Timeline where Sm2Timeline_id=?',(tlid,)).fetchone()[0]
ver=con.execute('select pActive from "ListMgt::LmVersionTable" where Sm2TiItem_id=?',(item,)).fetchone()[0]
base=os.path.expanduser(f"~/Movies/CacheClip/{proj}/AlgoCache/1000/{seq}/{item}/{ver}/1/")
os.makedirs(base+"0",exist_ok=True)
modelo=glob.glob("backup_I/*/AlgoCache/1000/*/*/*/1/0/0000000000.dvcc")[0]
m=np.load("masks_premiere.npy")
for n in range(300): escrever_dvcc(modelo,m[n],base+f"0/{n:010d}.dvcc")
if pecas:
    for s in ("256","KeyframeBlob","StateBlob"):
        if os.path.isdir(pecas+s): shutil.copytree(pecas+s,base+s,dirs_exist_ok=True)
print(base, {s:len(os.listdir(base+s)) for s in os.listdir(base)})
