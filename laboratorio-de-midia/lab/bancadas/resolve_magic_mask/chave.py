# ⚠️ REGISTRO HISTÓRICO — script de UMA rodada, na máquina do autor: os caminhos abaixo são os do SSD de trabalho
# dele e não existem noutra máquina. O que se mediu está registrado no banco (bancodedadosnles). Para repetir,
# peça ao Claude para adaptar: achar o laboratório SUBINDO de pasta e gerar a mídia por uma receita
# (skill ciclo-laboratorio) — nunca com o material de uma produção.
# uso: chave.py render.mov -> por faixa de quadros, a chave do render bate com a máscara ORIGINAL ou com a INJETADA (+400 px)?
import sys,subprocess,numpy as np,glob
from dvcc import ler_dvcc
W,H=1920,1080
SRC="/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia/saida/base/B10_ROTO/B10_ROTO_MOV-PRORES.mov"
BK=glob.glob("backup_I/cb7eb85d-cbdd-490e-96a5-ebfd0d0e0b69/AlgoCache/1000/*/*/*/1/0/")[0]
def ler(p):
    b=subprocess.run(["ffmpeg","-v","error","-i",p,"-vf","format=gray","-f","rawvideo","-"],capture_output=True,check=True).stdout
    return np.frombuffer(b,np.uint8).reshape(-1,H,W)
src=ler(SRC); out=ler(sys.argv[1])
def iou(a,b,ok):
    a=a&ok; b=b&ok; u=(a|b).sum(); return (a&b).sum()/u if u else 1.0
res={}
for q in list(range(60,100,8))+list(range(100,200,8))+list(range(200,240,8)):
    a,_=ler_dvcc(BK+f"{q:010d}.dvcc"); orig=a.view(np.uint8).reshape(H,W)>127; inj=np.roll(orig,400,axis=1)
    k=out[q]<15; ok=src[q]>40
    res[q]=(round(iou(k,orig,ok),3),round(iou(k,inj,ok),3))
for faixa,(i0,i1) in (("60-99",(60,100)),("100-199 (injetados)",(100,200)),("200-239",(200,240))):
    v=[res[q] for q in res if i0<=q<i1]
    print(faixa,"IoU com ORIGINAL %.3f | com INJETADA %.3f"%(np.mean([x[0] for x in v]),np.mean([x[1] for x in v])))
