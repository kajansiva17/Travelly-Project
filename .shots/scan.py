import re,os,colorsys
pat=re.compile(r'#[0-9a-fA-F]{8}(?![0-9a-fA-F])|#[0-9a-fA-F]{6}(?![0-9a-fA-F])|#[0-9a-fA-F]{4}(?![0-9a-fA-F])|#[0-9a-fA-F]{3}(?![0-9a-fA-F])|rgba?\([^)]*\)|hsla?\([^)]*\)|:\s*(?:red|crimson|tomato|firebrick|maroon|darkred|indianred|salmon|coral)\s*[;}!]')
def rgb_of(v):
    v=v.lower()
    if v.startswith('#'):
        h=v[1:]
        if len(h) in (3,4): h=''.join(x*2 for x in h)
        return int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    if v.startswith('rgb'):
        n=re.findall(r'[\d.]+',v)
        if len(n)<3: return None
        return float(n[0]),float(n[1]),float(n[2])
    if v.startswith('hsl'):
        n=re.findall(r'[\d.]+',v)
        if len(n)<3: return None
        return tuple(x*255 for x in colorsys.hls_to_rgb(float(n[0])/360,float(n[2])/100,float(n[1])/100))
    return (255,0,0)
hits=[]; files=0
for base in ('src','public','index.html'):
    paths=[]
    if os.path.isfile(base): paths=[base]
    else:
        for root,_,fs in os.walk(base):
            for f in fs:
                if f.endswith(('.css','.jsx','.js','.svg','.html')): paths.append(os.path.join(root,f))
    for p in paths:
        files+=1
        for i,line in enumerate(open(p,encoding='utf8',errors='ignore'),1):
            for m in pat.finditer(line):
                v=m.group(0); c=rgb_of(v)
                if not c: continue
                if tuple(round(x) for x in c)==(242,13,24): continue
                r,g,b=[x/255 for x in c]
                h,l,s=colorsys.rgb_to_hls(r,g,b); h*=360
                if (h>=345 or h<=15) and s>.40: hits.append((p.replace(chr(92),'/'),i,v))
for h in hits[:80]: print(*h)
print('FILES',files,'COUNT',len(hits))
