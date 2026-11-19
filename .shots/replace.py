import re,os
M={}
def add(names,rep):
    for n in names.split(): M[n.lower()]=rep
add('c8102e d11a2a d62839 d94343 ee3a2a e53935 d63a3a e11d1d e8231a ed2b18 ff4b60 ff5969 ff6575 ff1115 ff1015 ff090b ff0000 f21730 cf001c ef6070 f11e00 ff1017 d90f0a e90000 f00003 f00808 ff0205 ea4335x','var(--brand-red)')
add('ff6f7c ff4a3c ff5962 ff7e84 ff4b51','var(--brand-red-hi)')
add('a3160c 8f1d1d 681625 642335 7b1c31 5e2730 7b2140 8d1730 8a1630 b50f0f 640808 612418 8e4c34 7a3828','var(--brand-red-dark)')
add('fff0ee ffe3e0 fde4e4 ffe5e8 ffe0e5 ffe8ea ffe8e8 fff1ef fff8fa ffdce3','var(--brand-red-tint)')
add('f3a9a1 e9a3a3 f4a7b1 f5a3b0 f1b6b0','var(--brand-red-border)')
add('4c1a1120','#0000001a')
add('c8403960 d4434a66 fa343659','rgb(var(--brand-red-rgb) / .35)')
rgbmap={'217 15 10':'var(--brand-red-rgb)','200 20 10':'var(--brand-red-rgb)','175 0 31':'var(--brand-red-rgb)','240 24 44':'var(--brand-red-rgb)','117 42 58':'var(--brand-red-rgb)','120 0 0':'0 0 0'}
hexre=re.compile(r'#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
rgbre=re.compile(r'rgb\((\d+) (\d+) (\d+)( / [\d.]+)\)')
count=0
def fix(text,ctx):
    global count
    def h(m):
        global count
        k=m.group(1).lower()
        if k in M and not (ctx=='comment'):
            count+=1; return M[k]
        return m.group(0)
    def r(m):
        global count
        key=f'{m.group(1)} {m.group(2)} {m.group(3)}'
        if key in rgbmap: count+=1; return f'rgb({rgbmap[key]}{m.group(4)})'
        return m.group(0)
    return rgbre.sub(r,hexre.sub(h,text))
skip={'GoogleSignIn.jsx'}
for root,_,files in os.walk('src'):
    for f in files:
        if not f.endswith('.css'): continue
        p=os.path.join(root,f); s=open(p,encoding='utf8').read()
        n=fix(s,'css')
        if n!=s: open(p,'w',encoding='utf8',newline='').write(n)
print('css replacements',count)
