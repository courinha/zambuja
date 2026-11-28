import sys,math,json,hashlib,numpy as np,cv2
sys.path.insert(0,sys.argv[1]); S=sys.argv[1]
exec(open(S+'/geo.py').read())
from scipy import ndimage as nd
from PIL import Image
from pyproj import Transformer
REPO='/home/claude/zambuja'
EXT=2200.0                      # metros a mais para norte
OFF=-1.206                      # relevo atual = LiDAR - 1,206 m (medido)
box=Z['box']; res=Z['res']; hmin=Z['hmin']; hk=Z['hk']
NR=int(EXT/res)                 # 550 linhas novas no relevo (4 m)
z0n=box[1]-EXT
# --- chão (2 m): 9 campos de distância com sinal
sb=Z['sdf']['box']; CR=2.0; NC=int(EXT/CR); Wc=1545
olds={}
for n,hh in zip('abc',['4f159fb2','defd30e4','8a485dfa']):
    olds[n]=np.asarray(Image.open(f'{REPO}/img/zambujeira-chao-{n}.{hh}.webp').convert('RGB'))
PAD=40; Hc=NC+PAD
cz0=sb[1]-EXT
jj,ii=np.mgrid[0:Hc,0:Wc]; cx=sb[0]+ii*CR; cz=cz0+jj*CR
Hfull=np.load(S+'/out/Hfull.npy')
def hrel(x,z):
    u=((x-box[0])/res).astype(np.float32); w=((z-z0n)/res).astype(np.float32)
    return cv2.remap(Hfull.astype(np.float32),u,w,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
Hc2=hrel(cx,cz); landc=Hc2>0
def topx(p): return np.round(np.array([((x-sb[0])/CR,(z-cz0)/CR) for x,z in p])*16).astype(np.int32)
def fillmask(pred):
    m=np.zeros((Hc,Wc),np.uint8)
    for p,tg in polys(pred):
        if len(p)>2: cv2.fillPoly(m,[topx(p)],1,shift=4)
    return m>0
def linemask(pred,w):
    m=np.zeros((Hc,Wc),np.uint8)
    for p,tg in lines(pred):
        if len(p)>1: cv2.polylines(m,[topx(p)],False,1,max(1,int(round(w/CR))),shift=4)
    return m>0
cls=lambda keys:(lambda t:any(t.get(k)==v for k,v in keys))
beach=fillmask(cls([('natural','beach')]))
erva=fillmask(cls([('landuse',x) for x in ('farmland','grass','meadow','vineyard','industrial','construction','farmyard','orchard')]+[('natural','grassland'),('leisure','garden'),('leisure','pitch'),('leisure','park')]))
mato=fillmask(cls([('natural','scrub'),('natural','heath'),('landuse','allotments')]))
mata=fillmask(cls([('natural','wood'),('landuse','forest')]))
bld=np.zeros((Hc,Wc),np.uint8)
for p,tg in polys(lambda t:'building' in t and t['building']!='greenhouse'): cv2.fillPoly(bld,[topx(p)],1,shift=4)
vila=cv2.dilate(bld,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)))>0
vila|=fillmask(cls([('amenity','parking'),('leisure','swimming_pool'),('landuse','residential')]))&~erva
dland=nd.distance_transform_edt(~landc)*CR; dsea=nd.distance_transform_edt(landc)*CR
# areia: praias e o fundo junto a elas até 80 m
near_beach=nd.distance_transform_edt(~beach)*CR<80
areia=(beach|((~landc)&near_beach&(dland<80)))
rocha=((~landc)&~areia)|(landc&(dsea<10)&(Hc2<8)&~beach)
for m in (erva,mato,mata,vila): m&=landc
empty=np.zeros((Hc,Wc),bool)
def sdf(m):
    if not m.any(): return np.full(m.shape,-4.0)
    din=nd.distance_transform_edt(m); dout=nd.distance_transform_edt(~m)
    return np.where(m,din*CR-1,-(dout*CR-1))
def enc(d): return np.clip(np.round(np.clip(d,-4,3.97)*32+128),0,255).astype(np.uint8)
chans={'a':(areia,rocha,vila),'b':(erva,mato,mata),'c':(empty,empty,empty)}
for n,(r_,g_,b_) in chans.items():
    img=np.dstack([enc(sdf(r_)),enc(sdf(g_)),enc(sdf(b_))])[:NC]
    full=np.vstack([img,olds[n]])
    Image.fromarray(full).save(S+f'/out/chao-{n}.webp',lossless=True,method=6)
    print('chão',n,full.shape)
# vista rápida do troço novo
prev=np.zeros((NC,Wc,3),np.uint8); prev[...]= (205,192,137)
for m,c in [(erva[:NC],(160,193,120)),(mato[:NC],(112,153,87)),(mata[:NC],(82,125,77)),(vila[:NC],(229,219,199)),(areia[:NC],(235,215,160)),(rocha[:NC]&landc[:NC],(130,120,110)),((~landc[:NC])&rocha[:NC],(44,111,134))]: prev[m]=c
Image.fromarray(prev).save(S+'/out/prev_chao.png')
json.dump({'z0n':z0n,'cz0':cz0},open(S+'/out/meta.json','w'))
