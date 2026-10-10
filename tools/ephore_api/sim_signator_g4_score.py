"""Fort vs Moyen : balayage du seuil et variantes du score CQF, niveau Fort uniquement, warm=100 (et 80)."""
from sim_signator_g4 import *
D_=all_data(True)
def comps(d,i):
    o,h,l,c,v=d['o'],d['h'],d['l'],d['c'],d['v']; b=d['bull'][i]; atr=d['atr'][i]; vma=d['vma'][i]; mt=0.25
    rng=h[i]-l[i]; rs=max(rng,mt); br=min(abs(c[i]-o[i])/rs/0.5,1.0)
    cpos=(c[i]-l[i])/rs if b else (h[i]-c[i])/rs; aw=(h[i]-c[i])/rs if b else (c[i]-l[i])/rs
    sS=(br+(1-min(aw/0.35,1))+min(cpos/0.67,1))/3
    sM=min(rng/max(0.5*atr,mt),1.0); sV=min(v[i]/vma,1.0) if vma>0 else 0.0
    sG=min(abs(o[i]-c[i-1])/max(0.3*atr,mt),1.0)
    eng=((c[i]>o[i-1] and o[i]<c[i-1]) if b else (o[i]>c[i-1] and c[i]<o[i-1])) and h[i]>h[i-1] and l[i]<l[i-1]
    return [sS,sM,sV,sG,1.0 if eng else 0.0]
rows=[]
for d in D_:
    for i in range(80,len(d['c'])):
        r=v8(d,i)
        tF=bool(d['LF'][i] or d['SF'][i]); 
        rows.append((i>=100,d['inst'],d['tf'],tF,r is not None,comps(d,i) if r else None))
def ev(fn,warm100=True):
    tp=fp=fn_=0
    for w,ins,tf,tF,trig,cp in rows:
        if warm100 and not w: continue
        p= trig and fn(cp)
        tp+=p and tF; fp+=p and not tF; fn_+=tF and not p
    return tp,fp,fn_
W=[1,1,1,1,1]
def mk(w,th,tr=lambda c:c): 
    return lambda cp: sum(a*b for a,b in zip(tr(cp),w))/sum(w)*100>=th
n=0
print('tout trigger = Fort',ev(lambda cp:True))
for th in range(30,62,4): n+=1; print('seuil',th,ev(mk(W,th)),ev(mk(W,th),False))
# retirer chaque composant
for k,nm in enumerate(['str','mom','vol','gap','eng']):
    w=W[:]; w[k]=0
    for th in (40,45,50): n+=1; print('sans',nm,th,ev(mk(w,th)))
for k,nm in enumerate(['str','mom','vol','gap','eng']):
    w=W[:]; w[k]=2
    for th in (50,55): n+=1; print('x2',nm,th,ev(mk(w,th)))
print('combos',n)
