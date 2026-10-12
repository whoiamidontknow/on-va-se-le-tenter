"""H1 (fin) : arrondis intermediaires de l'ADX et lissage du DX par SMA/EMA au lieu du RMA de Wilder."""
import impl_lab_core as C
base=[C.feats(d) for d in C.DATA]

def smooth_dx(ds,mode,p=14):
    """Recalcule l'ADX en lissant le DX autrement (le DX lui-meme reste identique)."""
    out=[]
    for d in ds:
        e=dict(d); n=len(d['c'])
        dx=[None]*n
        for i in range(n):
            a,b=d['dip'][i],d['dim'][i]
            if a is None or b is None: continue
            s=a+b; dx[i]=abs(a-b)/(s if s else 1)*100
        if mode=='sma': e['adx']=C.sma(dx,p)
        elif mode=='ema': e['adx']=C.ema_series(dx,p)
        elif mode=='rma': e['adx']=C.rma(dx,p)
        out.append(e)
    return out

print("=== A. lissage du DX ===")
for m in ('rma','sma','ema'):
    ds=smooth_dx(base,m); tp,fp,fn,_=C.score(ds)
    err=[abs(a['adx'][i]-b['adx'][i]) for a,b in zip(ds,base) for i in range(100,len(a['c'])) if a['adx'][i] and b['adx'][i]]
    err.sort(); q=lambda f: err[int(f*(len(err)-1))]
    lab={'rma':'RMA de Wilder (reference)','sma':'SMA(DX,14)','ema':'EMA(DX,14)'}[m]
    print(f"  {lab:28} {tp:4}/{fp}/{fn}   ecart ADX p50={q(.5):.2f} p95={q(.95):.2f} max={err[-1]:.2f}")

print("\n=== B. arrondis intermediaires de l'ADX avant comparaison au seuil 18 ===")
def rnd(ds,nd):
    out=[]
    for d in ds:
        e=dict(d)
        e['adx']=[None if x is None else (round(x,nd) if nd is not None else float(int(x))) for x in d['adx']]
        out.append(e)
    return out
for nd,lab in ((None,'troncature a l entier'),(0,'arrondi a l entier'),(1,'arrondi a 0.1'),(2,'arrondi a 0.01'),(4,'arrondi a 1e-4')):
    ds=rnd(base,nd); tp,fp,fn,_=C.score(ds)
    print(f"  {lab:24} {tp:4}/{fp}/{fn}")

print("\n=== C. arrondi du dBand et de l'ATR ===")
def rnd_db(ds,nd):
    out=[]
    for d in ds:
        e=dict(d); e['dband']=[None if x is None else round(x,nd) for x in d['dband']]; out.append(e)
    return out
for nd in (1,2,3):
    ds=rnd_db(base,nd); tp,fp,fn,_=C.score(ds)
    print(f"  dBand arrondi a 1e-{nd}      {tp:4}/{fp}/{fn}")

print("\n=== D. seuil ADX fin autour de 18 (les deux FP sont a 18.37 et 18.69) ===")
for th in (18.0,18.2,18.4,18.5,18.7,18.8,19.0):
    tp,fp,fn,_=C.score(base,adx_th=th)
    print(f"  ADX >= {th:4.1f}   {tp:4}/{fp}/{fn}   ({fp+fn} erreurs)")
