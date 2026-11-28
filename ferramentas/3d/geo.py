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
