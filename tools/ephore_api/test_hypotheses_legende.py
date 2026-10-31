#!/usr/bin/env python3
"""Teste les hypotheses issues du decodage de la legende TradingView (10/10).
Cible : groupe 4 des exports Base 10:10/Ajustements. Warmup 100."""
import csv, glob, collections, itertools, os
D=os.path.expanduser('~/ERGON/Base 10:10/Ajustements')
def ema(x,p):
    a=2/(p+1); o=[x[0]]
    for v in x[1:]: o.append(a*v+(1-a)*o[-1])
    return o
def rma(x,p):
    out=[None]*len(x); s=None; buf=[]
    for i,v in enumerate(x):
        if v is None: continue
        if s is None:
            buf.append(v)
            if len(buf)==p: s=sum(buf)/p
        else: s=(s*(p-1)+v)/p
        out[i]=s
    return out
FILES=[]
for f in sorted(glob.glob(f'{D}/*.csv')):
    rows=list(csv.reader(open(f,newline=''))); hdr,data=rows[0],[r for r in rows[1:] if r and r[0]]
    occ=collections.Counter(); g4=[]; vol=None
    for i,n in enumerate(hdr):
        n=n.strip()
        if n.startswith('Signal L') or n.startswith('Signal S'):
            occ[n]+=1
            if occ[n]==4: g4.append((n,i))
        if n=='Volume': vol=i
    if not g4 or vol is None or len(data)<140: continue
    def num(r,i,d=0.0):
        try: return float(r[i])
        except: return d
    N=len(data)
    O=[num(r,1) for r in data];H=[num(r,2) for r in data];L=[num(r,3) for r in data]
    C=[num(r,4) for r in data];V=[num(r,vol) for r in data]
    fort={i for i in range(N) if any(num(data[i],j)!=0 for n,j in g4 if 'Fort' in n)}
    moyen={i for i in range(N) if any(num(data[i],j)!=0 for n,j in g4 if 'Moyen' in n)}
    o4=[(O[i]+H[i]+L[i]+C[i])/4 for i in range(N)]
    bull=[a>b for a,b in zip(ema(o4,4),ema(o4,32))]
    tr=[H[0]-L[0]]+[max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1])) for i in range(1,N)]
    up=[0]+[max(H[i]-H[i-1],0) if H[i]-H[i-1]>L[i-1]-L[i] else 0 for i in range(1,N)]
    dn=[0]+[max(L[i-1]-L[i],0) if L[i-1]-L[i]>H[i]-H[i-1] else 0 for i in range(1,N)]
    atr=rma(tr,14);pu=rma(up,14);pd=rma(dn,14)
    dx=[None if pu[i] is None else (abs(pu[i]-pd[i])/(pu[i]+pd[i])*100 if pu[i]+pd[i]>0 else 0) for i in range(N)]
    adx=rma(dx,14); e50=ema(C,50); e60=ema(C,60)
    vma=[sum(V[i-19:i+1])/20 if i>=19 else None for i in range(N)]
    run=[1]*N
    for i in range(1,N): run[i]=run[i-1]+1 if bull[i]==bull[i-1] else 1
    FILES.append(dict(N=N,O=O,H=H,L=L,C=C,V=V,bull=bull,atr=atr,adx=adx,e50=e50,e60=e60,
                      vma=vma,run=run,fort=fort,moyen=moyen))

def run_test(adx_min, db_min, cpos_div, ncomp):
    tp=fp=fn=0
    for d in FILES:
        for i in range(100,d['N']):
            O,H,L,C,V=d['O'],d['H'],d['L'],d['C'],d['V']
            b=d['bull'][i]; a=d['adx'][i]; vm=d['vma'][i]
            trig=False
            if d['run'][i]==2 and a and a>=adx_min and vm and ((C[i]>d['e50'][i]) if b else (C[i]<d['e50'][i])):
                dbv=((C[i]-max(d['e50'][i],d['e60'][i])) if b else (min(d['e50'][i],d['e60'][i])-C[i]))/d['atr'][i]
                trig = dbv>=db_min or V[i]>=vm
            sim_fort=False
            if trig:
                rg=max(H[i]-L[i],1e-12)
                br=min(abs(C[i]-O[i])/rg/0.5,1.0)
                cp=(C[i]-L[i])/rg if b else (H[i]-C[i])/rg
                aw=(H[i]-C[i])/rg if b else (C[i]-L[i])/rg
                s1=(br+(1-min(aw/0.35,1))+min(cp/cpos_div,1))/3
                s2=min(rg/max(0.5*d['atr'][i],1e-12),1)
                s3=min(V[i]/vm,1) if vm else 0
                s4=min(abs(O[i]-C[i-1])/max(0.3*d['atr'][i],1e-12),1)
                sc=((s1+s2+s3+s4)/4 if ncomp==4 else (s1+s2+s3+s4+0)/5)*100
                sim_fort = sc>=50
            truth = i in d['fort']
            if sim_fort and truth: tp+=1
            elif sim_fort: fp+=1
            elif truth: fn+=1
    return tp,fp,fn

print(f"{'ADX':>4}{'dBand':>7}{'cpos/':>7}{'comp':>6}{'exact':>7}{'trop':>6}{'manq':>6}{'erreurs':>9}")
print("-"*52)
res=[]
for adx_min,db in ((18,0.30),(22,0.34),(18,0.34),(22,0.30)):
    for cd in (0.67,0.33):
        for nc in (5,4):
            tp,fp,fn=run_test(adx_min,db,cd,nc)
            res.append((fp+fn,adx_min,db,cd,nc,tp,fp,fn))
            flag='  <- V8 actuelle' if (adx_min,db,cd,nc)==(18,0.30,0.67,5) else ''
            print(f"{adx_min:>4}{db:>7.2f}{cd:>7.2f}{nc:>6}{tp:>7}{fp:>6}{fn:>6}{fp+fn:>9}{flag}")
print()
best=min(res)
print(f"MEILLEUR : ADX {best[1]}, dBand {best[2]}, cpos/{best[3]}, {best[4]} composantes "
      f"-> {best[5]} exactes, {best[6]} trop, {best[7]} manq ({best[0]} erreurs)")
