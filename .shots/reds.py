import sys,re,colorsys,os
pat=re.compile(r'#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)')
def isred(v0):
    try:
        if v0.startswith('#'):
            h=v0[1:]
            if len(h) in (3,4): h=''.join(x*2 for x in h)
            r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
        elif v0.startswith('rgb'):
            n=re.findall(r'[\d.]+',v0)
            if len(n)<3: return False
            r,g,b=[float(x) for x in n[:3]]
        else:
            n=re.findall(r'[\d.]+',v0); hh,ss,ll=float(n[0])/360,float(n[1])/100,float(n[2])/100
            r,g,b=[x*255 for x in colorsys.hls_to_rgb(hh,ll,ss)]
        h,l_,s=colorsys.rgb_to_hls(r/255,g/255,b/255)
        return s>.25 and (h<.06 or h>.88) and .08<l_<.97
    except Exception: return False
for root,_,files in os.walk('src'):
    for f in files:
        if not f.endswith(('.css','.jsx','.js')): continue
        p=os.path.join(root,f).replace(chr(92),'/')
        for i,line in enumerate(open(p,encoding='utf8',errors='ignore'),1):
            for m in pat.finditer(line):
                if isred(m.group(0).lower()): print(f'{p}:{i}:{m.group(0).lower()}')
