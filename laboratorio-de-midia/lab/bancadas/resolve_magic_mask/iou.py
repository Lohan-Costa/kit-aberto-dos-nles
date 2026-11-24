# uso: iou.py render.mov  -> IoU do alfa do render x mascara perfeita do B10, por quadro
import sys, subprocess, numpy as np, json
W,H=1920,1080
VERD="/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia/saida/base/B10_ROTO/B10_ROTO_MASCARA_MOV-PRORES.mov"
def ler(p, alfa):
    vf = "alphaextract,format=gray" if alfa else "format=gray"
    b = subprocess.run(["ffmpeg","-v","error","-i",p,"-vf",vf,"-f","rawvideo","-"],capture_output=True,check=True).stdout
    return np.frombuffer(b,np.uint8).reshape(-1,H,W)
r=ler(sys.argv[1],True); v=ler(VERD,False)
n=min(len(r),len(v)); ious=[]; cob=[]
for i in range(n):
    a=r[i]>127; b=v[i]>127
    u=(a|b).sum(); ious.append(float((a&b).sum()/u) if u else 1.0); cob.append(float(a.mean()))
ious=np.array(ious)
vazios=int(sum(1 for c in cob if c<0.0005))
print(json.dumps({"arquivo":sys.argv[1].split('/')[-1],"quadros":n,"iou_medio":round(float(ious.mean()),4),"iou_min":round(float(ious.min()),4),
 "quadro_pior":int(ious.argmin()),"iou_q80":round(ious[80],4) if n>80 else None,"quadros_sem_mascara":vazios,
 "alfa_medio_%":round(100*float(np.mean(cob)),2), "amostra_iou_q0_50_150_250_299":[round(float(ious[i]),3) for i in (0,50,150,250,min(299,n-1))]}))
