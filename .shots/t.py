import re,colorsys
exec(open('../.shots/scan.py',encoding='utf8').read().split('hits=[]')[0])
v='#EA4335'; print(pat.findall('<path fill="#EA4335" d'), rgb_of(v))
c=rgb_of(v); r,g,b=[x/255 for x in c]; h,l,s=colorsys.rgb_to_hls(r,g,b); print(h*360,s)
