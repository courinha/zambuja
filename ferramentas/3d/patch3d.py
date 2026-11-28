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
