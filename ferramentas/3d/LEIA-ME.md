# Zambuja · ferramentas do 3D (nov. 2026)

Scripts usados a 28 nov 2026 para alargar o mapa 3D até à Entrada da Barca. Correm em Python 3 com numpy, scipy, opencv, pillow, pyproj, rasterio e matplotlib. Entradas: quadrículas MDT da DGT (GeoTIFF, EPSG:3763) e um export .osm do OpenStreetMap. Ordem: osmload.py -> (mosaico do LiDAR, ver nota) -> relevo2.py -> chao.py -> gen_final.py -> patch3d.py.

Notas: o relevo do site = LiDAR - 1,206 m; conversão local: x=(lon-lon0)*cos(lat0)*K, z=-(lat-lat0)*K com K=pi/180*6371008.8 e origem ZDATA.origin; altura codificada R*256+G=(h-hmin)*hk, B=fundo junto à costa; chão: 9 campos de distância com sinal (byte-128)/32 m, a 2 m/px; mosaico LiDAR a 1 m guardado como mdt1m.npy (X0=-59000, Y1=-233000).

## osmload.py

```python
import xml.etree.ElementTree as ET, json, math, re, sys
U='/root/.claude/uploads/3d71be18-9c67-58e0-96d9-badc62bb6136/c1eb56af-map.osm'
t=ET.parse(U).getroot()
nodes={};ways={};rels=[]
for e in t:
    if e.tag=='node': nodes[e.get('id')]=(float(e.get('lat')),float(e.get('lon')),{k.get('k'):k.get('v') for k in e.findall('tag')})
    elif e.tag=='way': ways[e.get('id')]=([n.get('ref') for n in e.findall('nd')],{k.get('k'):k.get('v') for k in e.findall('tag')})
    elif e.tag=='relation': rels.append(([(m.get('type'),m.get('ref'),m.get('role')) for m in e.findall('member')],{k.get('k'):k.get('v') for k in e.findall('tag')}))
b=t.find('bounds'); print('bounds',b.attrib if b is not None else None)
print(len(nodes),'nodes',len(ways),'ways',len(rels),'rels')
from collections import Counter
c=Counter()
for nd,tg in ways.values():
    for k in ['building','highway','landuse','natural','leisure','amenity','man_made','waterway','barrier','surface']:
        if k in tg: c[k+'='+(tg[k] if k!='building' else 'x')]+=1
for k,v in sorted(c.items(),key=lambda x:-x[1])[:70]: print(v,k)
cr=Counter(tg.get('type','')+':'+next((k+'='+tg[k] for k in ['building','landuse','natural','leisure','place'] if k in tg),'?') for _,tg in rels)
print(cr.most_common(20))
import pickle; pickle.dump((nodes,ways,rels),open(sys.argv[1],'wb'))
```

## geo.py

```python
import pickle,json,math,numpy as np
S='/tmp/claude-0/-home-claude-zambuja/3d71be18-9c67-58e0-96d9-badc62bb6136/scratchpad'
nodes,ways,rels=pickle.load(open(S+'/osm/osm.pkl','rb'))
Z=json.load(open(S+'/zdata.json')); lat0,lon0=Z['origin']
R=6371008.8;K=math.pi/180*R;CL=math.cos(math.radians(lat0))
def loc(la,lo): return ((lo-lon0)*CL*K, -(la-lat0)*K)
def wpts(nd): return [loc(nodes[n][0],nodes[n][1]) for n in nd if n in nodes]
def polys(pred):
    out=[]
    for wid,(nd,tg) in ways.items():
        if pred(tg) and len(nd)>3 and nd[0]==nd[-1]: out.append((wpts(nd),tg))
    for mem,tg in rels:
        if tg.get('type')=='multipolygon' and pred(tg):
            # stitch outer rings
            segs=[ways[r][0] for t,r,role in mem if t=='way' and r in ways and role in('outer','')]
            rings=[];segs=[list(s) for s in segs]
            while segs:
                cur=segs.pop(0)
                while cur[0]!=cur[-1]:
                    for i,s in enumerate(segs):
                        if s[0]==cur[-1]: cur+=s[1:];segs.pop(i);break
                        if s[-1]==cur[-1]: cur+=s[::-1][1:];segs.pop(i);break
                    else: break
                if cur[0]==cur[-1]: rings.append(cur)
            for rg in rings: out.append((wpts(rg),tg))
    return out
def lines(pred):
    return [(wpts(nd),tg) for wid,(nd,tg) in ways.items() if pred(tg)]
```

## relevo2.py

```python
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
```

## chao.py

```python
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
```

## gen_final.py

```python
import sys,math,json,hashlib,numpy as np,cv2
sys.path.insert(0,sys.argv[1]); S=sys.argv[1]
exec(open(S+'/geo.py').read())
from scipy import ndimage as nd
from PIL import Image
from matplotlib.path import Path
REPO='/home/claude/zambuja'
EXT=2200.0; OFF=-1.206
box=Z['box']; res=Z['res']; hmin=Z['hmin']; hk=Z['hk']; NR=int(EXT/res)
# ---------- 1) relevo já refeito (relevo2.py)
newrel=np.asarray(Image.open(S+'/out/relevo.webp').convert('RGB'))
oldrel=np.asarray(Image.open(REPO+'/img/zambujeira-relevo.24ed3c13.webp').convert('RGB'))
changed=np.zeros(newrel.shape[:2],bool); changed[:NR]=True; changed[NR:]=(newrel[NR:]!=oldrel).any(-1)
Hn=(newrel[...,0].astype(float)*256+newrel[...,1])/hk+hmin
z0n=box[1]-EXT
def hat(x,z):
    i=(x-box[0])/res; j=(z-z0n)/res; i=min(max(i,0),Hn.shape[1]-1.001); j=min(max(j,0),Hn.shape[0]-1.001); i0,j0=int(i),int(j); fx,fz=i-i0,j-j0
    return Hn[j0,i0]*(1-fx)*(1-fz)+Hn[j0,i0+1]*fx*(1-fz)+Hn[j0+1,i0]*(1-fx)*fz+Hn[j0+1,i0+1]*fx*fz
chg=changed
def touched(p):
    for x,z in p:
        i=int((x-box[0])/res); j=int((z-z0n)/res)
        if 0<=j<chg.shape[0] and 0<=i<chg.shape[1] and chg[max(0,j-1):j+2,max(0,i-1):i+2].any(): return True
    return False
# ---------- 2) correção a leste (o OSM está ~11 m a sul da realidade no campismo; medido contra a fotografia aérea)
SH=np.array([-2.7,-11.1])
def wsh(x,z): return float(np.clip((x-600)/250,0,1))*float(np.clip((z+800)/200,0,1))
def shp(p): return [[round(x+SH[0]*wsh(x,z),1),round(z+SH[1]*wsh(x,z),1)] for x,z in p]
Zn=json.loads(json.dumps(Z))
for b in Zn['buildings']: b['p']=shp(b['p'])
Zn['roads']=[[t,shp(r)] for t,r in Zn['roads']]
Zn['campRoads']=[shp(r) for r in Zn['campRoads']]
Zn['pools']=[shp(p) for p in Zn['pools']]
Zn['camp']=shp(Zn['camp'])
Zn['trees']=[[round(x+SH[0]*wsh(x,z),1),round(z+SH[1]*wsh(x,z),1),t] for x,z,t in Zn['trees']]
tx,tz=Zn['tower']; Zn['tower']=[round(tx+SH[0]*wsh(tx,tz),1),round(tz+SH[1]*wsh(tx,tz),1)]
# ---------- 3) campismo: casas e piscinas desenhadas a partir da fotografia
dig=json.load(open(S+'/camp_dig.json'))['dig']
camp=Path(Zn['camp'])
Zn['buildings']=[b for b in Zn['buildings'] if not camp.contains_point(np.mean(b['p'],0))]
for nm,p,h in dig: Zn['buildings'].append({'p':[[round(x,1),round(z,1)] for x,z in p],'h':h,'b':None,'k':'roof','_n':1})
glass=[[996,-269],[1020,-269],[1020,-250],[996,-250]]
rp=[[round(985.6+3.7*math.cos(a),1),round(-257+3.7*math.sin(a),1)] for a in np.linspace(0,2*math.pi,14)[:-1]]
Zn['pools']=[p for p in Zn['pools'] if not camp.contains_point(np.mean(p,0))]+[glass,rp]
# ---------- 4) troço norte: casas, estradas e árvores do OSM
ZOLD=box[1]
inside=lambda x,z: box[0]<x<box[2] and z0n<z<ZOLD
skipb={'greenhouse'}
for p,tg in polys(lambda t:'building' in t):
    if tg['building'] in skipb or len(p)<4: continue
    c=np.mean(p[:-1],0)
    if not inside(*c): continue
    lv=tg.get('building:levels'); k='flat' if tg['building'] in('garage','school','public','warehouse','shed','retail','office','industrial') else 'roof'
    hh=int(hashlib.md5(str(c).encode()).hexdigest(),16)%5
    h=(int(lv)*3+0.6) if lv and lv.isdigit() else ([5.8,6.2,6.6,7.0,7.4][hh] if k=='roof' else [3.6,4.2,4.8,5.4,6.2][hh])
    if tg['building'] in('shed',): h=3.0
    Zn['buildings'].append({'p':[[round(x,1),round(z,1)] for x,z in p[:-1]],'h':h,'b':None,'k':k,'_n':1})
RT={'secondary':0,'tertiary':1,'unclassified':2,'residential':3,'living_street':3,'service':5,'pedestrian':6,'track':7,'footway':8,'path':9,'steps':10,'cycleway':8,'bridleway':9}
old_r=[np.array(r) for t,r in Z['roads']]
def dup(P):
    for Q in old_r:
        if len(Q)<2: continue
        d=np.min(np.hypot(P[:,None,0]-Q[None,:,0],P[:,None,1]-Q[None,:,1]),axis=1)
        if np.mean(d<4)>0.6: return True
    return False
added=0
for p,tg in lines(lambda t:t.get('highway') in RT):
    P=np.array(p)
    if len(P)<2: continue
    m=(P[:,1]<ZOLD+20)&(P[:,1]>z0n-50)&(P[:,0]>box[0]-50)&(P[:,0]<box[2]+50)
    if not m.any() or (P[:,1]>ZOLD).all(): continue
    if dup(P): continue
    Zn['roads'].append([RT[tg['highway']],[[round(x,1),round(z,1)] for x,z in p]]); added+=1
print('estradas novas',added)
rng=np.random.default_rng(11); trees=[]
for p,tg in polys(lambda t:t.get('natural')=='wood' or t.get('landuse')=='forest' or t.get('natural')=='scrub'):
    pa=Path(p); P=np.array(p); x0,z0=P.min(0); x1,z1=P.max(0)
    if z1<z0n or z0>ZOLD: continue
    dens=30 if tg.get('natural')!='scrub' else 1.0
    n=int((x1-x0)*(z1-z0)/1e4*dens)
    for _ in range(n):
        x,z=rng.uniform(x0,x1),rng.uniform(z0,z1)
        if inside(x,z) and pa.contains_point((x,z)): trees.append([round(x,1),round(z,1),int(rng.integers(0,2)) if dens>2 else int(rng.choice([0,1,3]))])
for p,tg in lines(lambda t:t.get('natural')=='tree_row'):
    for (x1,z1),(x2,z2) in zip(p,p[1:]):
        L_=math.hypot(x2-x1,z2-z1)
        for s in np.arange(0,L_,7):
            x,z=x1+(x2-x1)*s/L_,z1+(z2-z1)*s/L_
            if inside(x,z): trees.append([round(x,1),round(z,1),2])
Zn['trees']+=trees; print('árvores novas',len(trees))
# limpar árvores mal postas no campismo: em cima de casas, piscinas e caminhos, e no prado aberto a leste
cb=[Path(b['p']) for b in Zn['buildings'] if camp.contains_point(np.mean(b['p'],0))]+[Path(p) for p in Zn['pools'][-2:]]
def nearline(x,z,L,d):
    for r in L:
        for (a,b_),(c,e) in zip(r,r[1:]):
            dx,dz=c-a,e-b_; t=max(0,min(1,((x-a)*dx+(z-b_)*dz)/max(dx*dx+dz*dz,1e-9)))
            if math.hypot(a+dx*t-x,b_+dz*t-z)<d: return True
    return False
keep=[]; rem=0
for x,z,t in Zn['trees']:
    if camp.contains_point((x,z)):
        if any(pp.contains_point((x,z),radius=6) or pp.contains_point((x,z),radius=-6) for pp in cb) or nearline(x,z,Zn['campRoads'],3) or (x>1058 and z<-185):
            rem+=1; continue
    keep.append([x,z,t])
Zn['trees']=keep; print('árvores retiradas no campismo',rem)
# ---------- 5) bases das casas: novas, do campismo e das zonas onde o relevo mudou
nb=0
for b in Zn['buildings']:
    if b.get('_n') or b['b'] is None or touched(b['p']):
        b['b']=round(min(hat(x,z) for x,z in b['p']),1); nb+=1
    b.pop('_n',None)
print('bases recalculadas',nb)
# ---------- 6) campo de jogos (polidesportivo)
Zn['courts']=[[ [round(x,1),round(z,1)] for x,z in p[:-1]] for p,tg in polys(lambda t:t.get('leisure')=='pitch' and t.get('sport')=='soccer')]
# ---------- 7) caixas
Zn['box'][1]=round(box[1]-EXT,1); Zn['sdf']['box'][1]=round(Z['sdf']['box'][1]-EXT,2)
json.dump(Zn,open(S+'/out/zdata_new.json','w'),ensure_ascii=False,separators=(',',':'))
print('caixa',Zn['box'],Zn['sdf']['box'],'casas',len(Zn['buildings']),'estradas',len(Zn['roads']),'árvores',len(Zn['trees']),'courts',Zn['courts'])
```

## patch3d.py

```python
import re,os,glob,hashlib,json,shutil,sys
S=sys.argv[1]
h8=lambda b:hashlib.sha256(b).hexdigest()[:8]
rd=lambda f:open(f,encoding='utf8').read()
def wr(f,s): open(f,'w',encoding='utf8').write(s)
def rep(n,s,o,w,c=None):
    k=s.count(o); assert k>0 and (c is None or k==c),(n,k,o[:80]); return s.replace(o,w)
ren={}
# imagens
for old,src in [('img/zambujeira-relevo.24ed3c13.webp','relevo.webp'),('img/zambujeira-chao-a.4f159fb2.webp','chao-a.webp'),('img/zambujeira-chao-b.defd30e4.webp','chao-b.webp'),('img/zambujeira-chao-c.8a485dfa.webp','chao-c.webp')]:
    b=open(S+'/out/'+src,'rb').read(); base=old.split('/')[1].rsplit('.',2)[0]; new=f'img/{base}.{h8(b)}.webp'
    open(new,'wb').write(b); os.remove(old); ren[old]=new
# dados
Zn=json.load(open(S+'/out/zdata_new.json'))
js_ix='const ZDATA='+json.dumps(Zn,ensure_ascii=False,separators=(',',':'))+';\n'
js_ar='/* Zambujeira do Mar · dados © contribuidores do OpenStreetMap (ODbL) */\n'+js_ix
for old,txt in [('js/zambujeira-dados.a1b282dd.js',js_ix),('js/zambujeira-dados.c002c2b0.js',js_ar)]:
    new=f'js/zambujeira-dados.{h8(txt.encode())}.js'; wr(new,txt); os.remove(old); ren[old]=new
# código do cabeçalho: limites do arrasto e campo de jogos
APP=glob.glob('js/app.*.js')[0]; app=rd(APP)
app=rep('zB',app,'const zB=[-700,-1150,2000,1150];','const zB=[-700,-3250,2000,1150];',1)
court='(d.courts||[]).forEach(l=>{let B=0,f=0;l.forEach(([k,G])=>{B+=k,f+=G}),B/=l.length,f/=l.length;const E=lt(B,f)+.15,sq=(s,y,col)=>{const g=new e.ShapeGeometry(new e.Shape(l.map(([k,G])=>new e.Vector2(B+(k-B)*s,-(f+(G-f)*s)))));g.rotateX(-Math.PI/2),g.translate(0,E+y,0),i.push(ct(g,re(col)))};sq(1.06,0,"#F2F1EC"),sq(.97,.03,"#5A86BE"),sq(.9,.05,"#6E96C9")}),'
app=rep('court',app,'c.push(ct(b,re("#3FB6D8")))}),i.length&&(','c.push(ct(b,re("#3FB6D8")))}),'+court+'i.length&&(',1)
SC='js/scene3d.4fb74ef4.js'; sc=rd(SC)
for o,n in ren.items():
    k=o.split('/',1)[1]; v=n.split('/',1)[1]
    app=app.replace(k,v); sc=sc.replace(k,v)
newSC=f'js/scene3d.{h8(sc.encode())}.js'; wr(newSC,sc); os.remove(SC); ren[SC]=newSC
newAPP=f'js/app.{h8(app.encode())}.js'; wr(newAPP,app); os.remove(APP); ren[APP]=newAPP
for f in ['index.html','ar.html','sw.js']:
    s=rd(f)
    for o,n in ren.items(): s=s.replace(o.split('/',1)[1],n.split('/',1)[1])
    if f=='index.html':
        s=rep('nv',s,'<div class="nv-list"><section><h3>Versão 2.8','<div class="nv-list"><section><h3>Versão 2.9<span>28 de novembro de 2026</span></h3><ul><li>🗺️ Mapa 3D até à Entrada da Barca: mais dois quilómetros de costa para norte, com o relevo LiDAR de 2024 da DGT, casas, caminhos e árvores</li><li>⛺ Parque de campismo redesenhado a partir da fotografia aérea: edifícios, piscinas e árvores nos sítios certos</li><li>⚽ O polidesportivo da vila passa a aparecer no 3D</li><li>⛰️ Relevo mais rigoroso a norte e a sul da vila</li></ul></section><section><h3>Versão 2.8',1)
    wr(f,s)
sw=rd('sw.js'); v=hashlib.sha256((rd('index.html')+sw).encode()).hexdigest()[:10]
sw,n=re.subn(r'const V="zambuja-[0-9a-f]+"',f'const V="zambuja-{v}"',sw); assert n==1; wr('sw.js',sw)
for o,n in ren.items(): print(o,'->',n)
```
