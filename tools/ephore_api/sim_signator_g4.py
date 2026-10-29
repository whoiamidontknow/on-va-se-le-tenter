"""Simulateur V8 Signator vs groupe 4 des exports 'Base 10:10/Ajustements'. Reutilise ema/rma de sig_api (copie, sig_api charge le JSON a l'import)."""
import csv,glob,os,math,datetime
D="/Users/jeremk/ERGON/Base 10:10/Ajustements/"
def ema(x,p):
    a=2/(p+1); out=[x[0]]
    for v in x[1:]: out.append(a*v+(1-a)*out[-1])
    return out
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
def sma(x,p): return [None if i<p-1 else sum(x[i-p+1:i+1])/p for i in range(len(x))]
def fl(s): return float(s) if s not in('',None) else None
def load(f):
    r=list(csv.reader(open(f))); rows=r[1:]
    name=os.path.basename(f); inst='MES' if 'MES' in name else 'NQ'
    tf=name.split(', ')[1].split('_')[0]
    c=lambda i:[fl(x[i]) for x in rows]
    d=dict(inst=inst,tf=tf,t=[x[0] for x in rows],o=c(1),h=c(2),l=c(3),c=c(4),v=c(5),m1=c(34),m2=c(35))
    for k,i in (('LF',30),('SF',31),('LM',32),('SM',33)): d[k]=[1 if (x[i] not in('','0')) else 0 for x in rows]
    for k,i in (('g2LF',14),('g2SF',15)): d[k]=[1 if (x[i] not in('','0')) else 0 for x in rows]
    return d
def feats(d,use_truth_ma=False):
    o,h,l,c,v=d['o'],d['h'],d['l'],d['c'],d['v']; n=len(c)
    o4=[(o[i]+h[i]+l[i]+c[i])/4 for i in range(n)]
    bull=[a>b for a,b in zip(ema(o4,4),ema(o4,32))]
    run=[1]*n
    for i in range(1,n): run[i]=run[i-1]+1 if bull[i]==bull[i-1] else 1
    e50=ema(c,50); e60=ema(c,60)
    if use_truth_ma: e50=[a if a is not None else b for a,b in zip(d['m1'],e50)]; e60=[a if a is not None else b for a,b in zip(d['m2'],e60)]
    tr=[None]+[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,n)]
    tr[0]=h[0]-l[0]  # ta.atr: tr de la 1ere barre = h-l
    atr=rma(tr,14)
    up=[0]+[h[i]-h[i-1] for i in range(1,n)]; dn=[0]+[l[i-1]-l[i] for i in range(1,n)]
    pdm=[u if u>dd and u>0 else 0 for u,dd in zip(up,dn)]; mdm=[dd if dd>u and dd>0 else 0 for u,dd in zip(up,dn)]
    # ta.dmi : nan sur 1ere barre
    trs=rma(tr,14); ps=rma(pdm,14); ms=rma(mdm,14)
    dip=[100*a/b if a is not None and b else None for a,b in zip(ps,trs)]
    dim=[100*a/b if a is not None and b else None for a,b in zip(ms,trs)]
    dx=[abs(a-b)/(a+b)*100 if a is not None and (a+b)>0 else None for a,b in zip(dip,dim)]
    adx=rma(dx,14)
    vma=sma(v,20)
    # CQF
    sc=[None]*n
    for i in range(1,n):
        if atr[i] is None or vma[i] is None: continue
        rng=h[i]-l[i]; mt=0.01 if d['inst']=='x' else 0.25
        rs=max(rng,mt); br=min(abs(c[i]-o[i])/rs/0.5,1.0)
        cpos=(c[i]-l[i])/rs if bull[i] else (h[i]-c[i])/rs
        aw=(h[i]-c[i])/rs if bull[i] else (c[i]-l[i])/rs
        sS=(br+(1-min(aw/0.35,1))+min(cpos/0.67,1))/3
        sM=min(rng/max(0.5*atr[i],mt),1.0)
        sV=min(v[i]/vma[i],1.0) if vma[i]>0 else 0
        sG=min(abs(o[i]-c[i-1])/max(0.3*atr[i],mt),1.0)
        eng=((c[i]>o[i-1] and o[i]<c[i-1]) if bull[i] else (o[i]>c[i-1] and c[i]<o[i-1])) and h[i]>h[i-1] and l[i]<l[i-1]
        sc[i]=(sS+sM+sV+sG+(1 if eng else 0))/5*100
    dband=[None]*n
    for i in range(n):
        if atr[i]:
            dband[i]=(c[i]-max(e50[i],e60[i]))/atr[i] if bull[i] else (min(e50[i],e60[i])-c[i])/atr[i]
    # news : bougie contient 14:30 ou 16:00 Paris
    news=[False]*n
    if d['tf'] not in('1D',):
        tfm={'2':2,'5':5,'15':15,'30':30,'60':60,'240':240}[d['tf']]
        for i,ts in enumerate(d['t']):
            dt=datetime.datetime.fromisoformat(ts)  # heure locale +02:00 / +01:00 -> convertir en Paris = on suppose offset = Paris
            m=dt.hour*60+dt.minute
            for tgt in (14*60+30,16*60):
                if m<=tgt<m+tfm: news[i]=True
    d.update(bull=bull,run=run,e50=e50,e60=e60,atr=atr,adx=adx,vma=vma,sc=sc,dband=dband,news=news)
    return d
def v8(d,i,adx_th=18,db_th=0.3,vol_k=1.0,use_news=False,run_n=2,scmin=50,conv=True):
    if d['adx'][i] is None or d['vma'][i] is None or d['dband'][i] is None or d['sc'][i] is None: return None
    b=d['bull'][i]; c=d['c'][i]
    ok=d['run'][i]==run_n and d['adx'][i]>=adx_th and (c>d['e50'][i] if b else c<d['e50'][i])
    if conv: ok=ok and (d['dband'][i]>=db_th or d['v'][i]>=vol_k*d['vma'][i])
    if use_news: ok=ok and not d['news'][i]
    if not ok: return None
    return ('L' if b else 'S','F' if d['sc'][i]>=scmin else ('M' if d['sc'][i]>=adx_th else 'f'))
def all_data(truth=False):
    return [feats(load(f),truth) for f in sorted(glob.glob(D+'*.csv'))]
