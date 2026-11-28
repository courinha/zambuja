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
