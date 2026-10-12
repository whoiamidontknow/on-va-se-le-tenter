"""H1/H3 variante lourde : ADX, ATR (et dBand) calcules sur les bougies REELLES au lieu des HA.
Seule source possible : la copie de l'API vitrine, qui porte a la fois o/h/l/c (HA) et cr/hr/lr (reel).
Verite terrain = marqueurs sig_lf / sig_sf de l'API (independante des CSV du groupe 4)."""
import json, collections
import impl_lab_core as C

A=json.load(open('/Users/jeremk/Ephore/on-va-se-le-tenter/tools/ephore_api/api_vitrine_instantane.json'))

def build(tf, src_ind='ha'):
    U=A['unites'][tf]; B=U['bougies']; n=len(B)
    T=[b['t']//1000 for b in B]
    O=[b['o'] for b in B]; H=[b['h'] for b in B]; L=[b['l'] for b in B]; Cc=[b['c'] for b in B]
    HR=[b['hr'] for b in B]; LR=[b['lr'] for b in B]; CR=[b['cr'] for b in B]
    V=[b['v'] for b in B]
    # Heishinator et EMA50/60 : TOUJOURS sur HA (valide a 100% par l'API)
    o4=[(O[i]+H[i]+L[i]+Cc[i])/4 for i in range(n)]
    bull=[a>b for a,b in zip(C.ema(o4,4),C.ema(o4,32))]
    run=[1]*n
    for i in range(1,n): run[i]=run[i-1]+1 if bull[i]==bull[i-1] else 1
    e50=C.ema(Cc,50); e60=C.ema(Cc,60)
    h,l,c = (H,L,Cc) if src_ind=='ha' else (HR,LR,CR)
    tr=[None]*n; tr[0]=h[0]-l[0]
    for i in range(1,n): tr[i]=max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1]))
    atr=C.rma(tr,14)
    up=[0.0]+[h[i]-h[i-1] for i in range(1,n)]; dn=[0.0]+[l[i-1]-l[i] for i in range(1,n)]
    pdm=[u if (u>dn[i] and u>0) else 0.0 for i,u in enumerate(up)]
    mdm=[x if (x>up[i] and x>0) else 0.0 for i,x in enumerate(dn)]
    trs=C.rma(tr,14); ps=C.rma(pdm,14); ms=C.rma(mdm,14)
    dip=[100*a/b if (a is not None and b) else None for a,b in zip(ps,trs)]
    dim=[100*a/b if (a is not None and b) else None for a,b in zip(ms,trs)]
    dx=[None if (a is None) else abs(a-b)/((a+b) if a+b else 1)*100 for a,b in zip(dip,dim)]
    adx=C.rma(dx,14)
    vma=C.sma(V,20)
    sig={}
    for x in U['indicateurs']:
        if x.get('type')=='marqueur_prix' and str(x.get('id','')).startswith(('sig_lf','sig_sf')):
            sig[x['t']]=1
    return dict(T=T,bull=bull,run=run,e50=e50,e60=e60,atr=atr,adx=adx,vma=vma,V=V,Cc=Cc,sig=sig,n=n)

def score(d,warm=300,adx_th=18.0,db_th=0.3):
    tp=fp=fn=0
    for i in range(warm,d['n']):
        u=False
        if d['run'][i]==2 and d['adx'][i] and d['adx'][i]>=adx_th and ((d['Cc'][i]>d['e50'][i]) if d['bull'][i] else (d['Cc'][i]<d['e50'][i])):
            db=((d['Cc'][i]-max(d['e50'][i],d['e60'][i])) if d['bull'][i] else (min(d['e50'][i],d['e60'][i])-d['Cc'][i]))/d['atr'][i]
            u = db>=db_th or d['V'][i]>=d['vma'][i]
        o=d['T'][i] in d['sig']
        tp+=u and o; fp+=u and not o; fn+=o and not u
    return tp,fp,fn

print("=== ADX/ATR sur bougies HA vs bougies reelles (verite = marqueurs API) ===")
print(f"{'unite':6} {'source ADX/ATR':16} {'exactes':>7} {'trop':>5} {'manq':>5}   ecart ADX p50/p95/max")
for tf in ('15m','2m'):
    ref=build(tf,'ha')
    for s in ('ha','reel'):
        d=build(tf,s); tp,fp,fn=score(d)
        err=[abs(d['adx'][i]-ref['adx'][i]) for i in range(300,d['n']) if d['adx'][i] and ref['adx'][i]]
        err.sort(); q=lambda f: err[int(f*(len(err)-1))] if err else 0
        print(f"{tf:6} {s:16} {tp:7} {fp:5} {fn:5}   {q(.5):.2f} / {q(.95):.2f} / {(err[-1] if err else 0):.2f}")

print("\n=== et sur l'ATR seul (ADX reste HA) / l'ADX seul (ATR reste HA) ===")
def mix(tf,adx_src,atr_src):
    a=build(tf,adx_src); b=build(tf,atr_src); d=dict(a); d['atr']=b['atr']; return d
for tf in ('15m','2m'):
    for lab,asrc,tsrc in (('ADX reel + ATR HA','reel','ha'),('ADX HA + ATR reel','ha','reel')):
        d=mix(tf,asrc,tsrc); tp,fp,fn=score(d)
        print(f"  {tf:4} {lab:20} {tp}/{fp}/{fn}")

print("\n=== Validation independante des variantes de bande sur l'API (verite = marqueurs sig_lf/sig_sf) ===")
def score_band(d,mode,warm=300,db_th=0.3):
    tp=fp=fn=0
    for i in range(warm,d['n']):
        u=False
        if d['run'][i]==2 and d['adx'][i] and d['adx'][i]>=18 and ((d['Cc'][i]>d['e50'][i]) if d['bull'][i] else (d['Cc'][i]<d['e50'][i])):
            a,b=d['e50'][i],d['e60'][i]
            ref={'far':(max(a,b) if d['bull'][i] else min(a,b)),'mid':(a+b)/2,'e60':b,
                 'near':(min(a,b) if d['bull'][i] else max(a,b)),'e50':a}[mode]
            db=((d['Cc'][i]-ref) if d['bull'][i] else (ref-d['Cc'][i]))/d['atr'][i]
            u = db>=db_th or d['V'][i]>=d['vma'][i]
        o=d['T'][i] in d['sig']
        tp+=u and o; fp+=u and not o; fn+=o and not u
    return tp,fp,fn
print(f"  {'unite':6} " + " ".join(f"{m:>12}" for m in ('far','mid','e60','e50','near')))
for tf in ('15m','2m'):
    d=build(tf,'ha')
    print(f"  {tf:6} " + " ".join(f"{'/'.join(map(str,score_band(d,m))):>12}" for m in ('far','mid','e60','e50','near')))
