"""H1 - ADX : amorcage, 1ere barre du TR, DM na vs 0, longueurs DI/lissage dissociees.
Mesure d'abord l'ecart numerique sur les 8 barres limites, puis l'effet sur les fleches."""
import impl_lab_core as C

LIM=[('MES','15','2026-10-02T21:00'),('MES','5','2026-10-08T07:05'),('MES','60','2026-10-09T07:00'),
     ('NQ','15','2026-09-30T11:45'),('NQ','15','2026-10-02T22:15'),('NQ','1D','2025-12-18'),
     ('NQ','240','2026-07-10T00:00'),('NQ','240','2026-07-31T08:00')]
def find(ds,inst,tf,ts):
    for d in ds:
        if d['inst']==inst and d['tf']==tf:
            for i,t in enumerate(d['t']):
                if t[:16]==ts or t[:10]==ts: return d,i
    return None,None

BASE=dict()
base_ds=[C.feats(d) for d in C.DATA]
ref={k:find(base_ds,*k)[0]['adx'][find(base_ds,*k)[1]] for k in LIM}

VAR=[
 ('reference  rma(SMA seed), tr[0]=h-l, dm[0]=0, 14/14', dict()),
 ('ta.dmi exact : tr[0]=na (ta.tr), dm[0]=na',           dict(adx_tr_first='na',dm_first='na')),
 ('tr[0]=na seulement',                                  dict(adx_tr_first='na')),
 ('dm[0]=na seulement',                                  dict(dm_first='na')),
 ('amorcage RMA = 1ere valeur (pas de SMA) sur DI',      dict(adx_rma='first')),
 ('amorcage RMA = 1ere valeur sur le DX',                dict(adx_dx_rma='first')),
 ('amorcage RMA = 1ere valeur partout',                  dict(adx_rma='first',adx_dx_rma='first')),
 ('DI 14 / lissage 7',                                   dict(adx_len=7)),
 ('DI 14 / lissage 10',                                  dict(adx_len=10)),
 ('DI 14 / lissage 20',                                  dict(adx_len=20)),
 ('DI 14 / lissage 28',                                  dict(adx_len=28)),
 ('DI 7  / lissage 14',                                  dict(di_len=7)),
 ('DI 10 / lissage 14',                                  dict(di_len=10)),
 ('DI 20 / lissage 14',                                  dict(di_len=20)),
 ('DI 28 / lissage 14',                                  dict(di_len=28)),
 ('prix arrondis au tick 0.25 avant calcul',             dict(round_tick=True)),
]
print("=== A. ADX des 8 barres limites, par variante (ecart max vs reference) ===")
print(f"{'variante':52} " + " ".join(f"{t[1]+t[0][:1]:>8}" for t in LIM) + "   ecartMax")
print(f"{'(seuil 18)':52} " + " ".join(f"{ref[k]:8.2f}" for k in LIM))
for name,kw in VAR:
    ds=[C.feats(d,**kw) for d in C.DATA]
    vals=[]
    for k in LIM:
        d,i=find(ds,*k); vals.append(d['adx'][i])
    emax=max(abs(a-b) for a,b in zip(vals,[ref[k] for k in LIM]))
    print(f"{name:52} " + " ".join(f"{x:8.2f}" for x in vals) + f"   {emax:8.3f}")

print("\n=== B. ecart numerique global de l'ADX (toutes barres, chauffe 100) ===")
print(f"{'variante':52} {'p50':>9} {'p95':>9} {'max':>9}  {'n barres franchissant 18':>8}")
for name,kw in VAR:
    ds=[C.feats(d,**kw) for d in C.DATA]
    err=[]; flip=0
    for a,b in zip(ds,base_ds):
        for i in range(100,len(a['c'])):
            if a['adx'][i] is None or b['adx'][i] is None: continue
            err.append(abs(a['adx'][i]-b['adx'][i]))
            if (a['adx'][i]>=18)!=(b['adx'][i]>=18): flip+=1
    err.sort(); q=lambda f: err[int(f*(len(err)-1))]
    print(f"{name:52} {q(.5):9.4f} {q(.95):9.4f} {err[-1]:9.4f}  {flip:8}")

print("\n=== C. effet sur les fleches (groupe 4, chauffe 100, tout niveau) ===")
print(f"{'variante':52} {'exactes':>7} {'trop':>5} {'manq':>5}")
for name,kw in VAR:
    tp,fp,fn,errs,_=C.run_variant(kw)
    flag='  <<<' if (fp+fn)<8 else ''
    print(f"{name:52} {tp:7} {fp:5} {fn:5}{flag}")

print("\n=== D. grille DI x lissage (exactes/trop/manquees) ===")
L=[5,7,9,10,12,14,16,18,20,24,28]
print("  DI\\liss " + " ".join(f"{a:>12}" for a in L))
best=[]
for di in L:
    row=[]
    for al in L:
        tp,fp,fn,_,_=C.run_variant(dict(di_len=di,adx_len=al))
        row.append(f"{tp}/{fp}/{fn}")
        best.append((fp+fn,-tp,di,al))
    print(f"  {di:>7} " + " ".join(f"{x:>12}" for x in row))
best.sort()
print("  meilleures combinaisons :", best[:6])
