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
