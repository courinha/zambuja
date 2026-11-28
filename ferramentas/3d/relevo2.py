import sys,math,json,numpy as np,cv2
S=sys.argv[1]
from scipy import ndimage as nd
from PIL import Image
from pyproj import Transformer
Z=json.load(open(S+'/zdata.json')); lat0,lon0=Z['origin']; box=Z['box']; res=Z['res']; hmin=Z['hmin']; hk=Z['hk']
R=6371008.8;K=math.pi/180*R;CL=math.cos(math.radians(lat0)); tr=Transformer.from_crs('EPSG:4326','EPSG:3763',always_xy=True)
EXT=2200.0; NR=int(EXT/res); OFF=-1.206
old=np.asarray(Image.open('/home/claude/zambuja/img/zambujeira-relevo.24ed3c13.webp').convert('RGB'))
Hold=(old[...,0].astype(float)*256+old[...,1])/hk+hmin; Wd=Hold.shape[1]
M=np.load(S+'/mdt1m.npy'); valid=(~np.isnan(M)).astype(np.float32); Mf=np.nan_to_num(M).astype(np.float32)
bM=cv2.blur(Mf,(4,4)); bV=cv2.blur(valid,(4,4))
z0n=box[1]-EXT
jj,ii=np.mgrid[0:NR+Hold.shape[0],0:Wd]; xs=box[0]+ii*res; zs=z0n+jj*res
E,N=tr.transform(lon0+xs/(CL*K),lat0-zs/K)
mx=(E+59000-.5).astype(np.float32); my=(-233000-N-.5).astype(np.float32)
s=cv2.remap(bM,mx,my,cv2.INTER_LINEAR,borderValue=0); v=cv2.remap(bV,mx,my,cv2.INTER_LINEAR,borderValue=0)
L=np.where(v>.5,s/np.maximum(v,1e-6),np.nan)+OFF          # LiDAR na grelha toda
H=np.full(L.shape,np.nan); H[NR:]=Hold
# zona a refazer: troço novo + retângulos antigos de fonte grosseira
redo=np.zeros(L.shape,bool); redo[:NR]=True; redo[NR:NR+80,120:480]=True; redo[NR+556:,120:480]=True
# mar = zona baixa (ou sem LiDAR) ligada à margem oeste
low=np.where(redo,np.isnan(L)|(L<1.0),Hold_full:=np.vstack([np.full((NR,Wd),-99.0),Hold])<=0)
lab,n=nd.label(low); westlabs=set(np.unique(lab[:,0]))-{0}
sea=np.isin(lab,list(westlabs))
land=~sea
# ilhas de "terra" falsas no mar (ondas no LiDAR): componentes pequenas
ll,nl=nd.label(land); sz=nd.sum(np.ones_like(ll),ll,range(1,nl+1)); small=np.isin(ll,np.where(sz<40)[0]+1); land&=~small; sea=~land
print('mar',sea.mean().round(3),'ilhas retiradas',int((sz<40).sum()))
# terra: LiDAR; buracos sem LiDAR em terra -> vizinho mais próximo
Lr=L.copy(); hole=redo&land&np.isnan(Lr)
if hole.any():
    idx=nd.distance_transform_edt(np.isnan(Lr),return_distances=False,return_indices=True); Lr=Lr[idx[0],idx[1]]
print('buracos preenchidos',int(hole.sum()))
dist=nd.distance_transform_edt(~land)*res
prof_d=[0,2,6,12,24,48,96,192,256,10000]; prof_h=[-0.2,-0.64,-1.34,-1.96,-2.76,-4.38,-8.6,-18.1,-20,-20]
rng=np.random.default_rng(3); noise=cv2.GaussianBlur(rng.random(L.shape).astype(np.float32),(0,0),6); noise=(noise-noise.mean())/noise.std()
seaH=np.clip(np.interp(dist,prof_d,prof_h)+noise*0.8*np.clip(dist/40,0,1),hmin,-0.05)
Hn=np.where(redo,np.where(land,np.maximum(Lr,0.05),seaH),H)
v=np.round((Hn-hmin)*hk).astype(np.int64)
B=np.where(Hn>0,255,np.clip(np.round((Hn+12)/18*255),0,255)).astype(np.uint8)
out=np.dstack([(v>>8).astype(np.uint8),(v&255).astype(np.uint8),B])
out[NR:][~redo[NR:]]=old[~redo[NR:]]           # o resto fica exatamente igual
Image.fromarray(out).save(S+'/out/relevo.webp',lossless=True,method=6)
assert (np.asarray(Image.open(S+'/out/relevo.webp').convert('RGB'))==out).all()
Hc=(out[...,0].astype(float)*256+out[...,1])/hk+hmin; np.save(S+'/out/Hfull.npy',Hc)
for r in [0,1,2,3]: print('linha',r,'primeira terra x=',box[0]+int(np.argmax(Hc[r]>-4))*res)
d=Hc[NR]-Hc[NR-1]; m=(Hc[NR]>0)&(Hc[NR-1]>0); print('emenda: med %.2f p5 %.2f p95 %.2f'%(np.median(d[m]),np.percentile(d[m],5),np.percentile(d[m],95)))
img=np.clip((Hc+5)*5,0,255).astype(np.uint8); Image.fromarray(cv2.cvtColor(cv2.applyColorMap(img,cv2.COLORMAP_JET),cv2.COLOR_BGR2RGB)).resize((386,579)).save(S+'/relevo_prev.png')
