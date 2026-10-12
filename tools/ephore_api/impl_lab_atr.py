"""H3 - ATR : lissage (RMA/SMA/EMA), 1ere barre du TR, periode. L'ATR est le denominateur de dBand :
son erreur se transmet directement au seuil de conviction 0.3."""
import impl_lab_core as C
LIM=[('MES','15','2026-10-02T21:00','FP'),('MES','5','2026-10-08T07:05','FN'),('MES','60','2026-10-09T07:00','FP'),
     ('NQ','15','2026-09-30T11:45','FP'),('NQ','15','2026-10-02T22:15','FP'),('NQ','1D','2025-12-18','FP'),
     ('NQ','240','2026-07-10T00:00','FP'),('NQ','240','2026-07-31T08:00','FN')]
def find(ds,inst,tf,ts):
    for d in ds:
        if d['inst']==inst and d['tf']==tf:
            for i,t in enumerate(d['t']):
                if t[:16]==ts or t[:10]==ts: return d,i
base=[C.feats(d) for d in C.DATA]
VAR=[('reference  RMA(TR,14), tr[0]=h-l',dict()),
     ('RMA, tr[0]=na (ta.tr sans handle_na)',dict(tr_first='na')),
     ('SMA(TR,14)',dict(atr_mode='sma')),
     ('EMA(TR,14)',dict(atr_mode='ema')),
     ('RMA amorcee a la 1ere valeur',dict(atr_mode='rma_nosma')),
     ('RMA(TR,10)',dict(atr_len=10)),('RMA(TR,20)',dict(atr_len=20)),('RMA(TR,21)',dict(atr_len=21)),
     ('RMA(TR,7)',dict(atr_len=7)),('RMA(TR,28)',dict(atr_len=28)),
     ('SMA(TR,14) + arrondi tick',dict(atr_mode='sma',round_tick=True)),
     ('arrondi tick 0.25',dict(round_tick=True)),
     ]
print("=== A. dBand des 8 barres limites (seuil 0.30) ; FP doit tomber <0.30, FN monter >=0.30 ===")
print(f"{'variante':40} " + " ".join(f"{t[3]}{t[1]}{t[0][:1]:>4}" for t in LIM))
for name,kw in VAR:
    ds=[C.feats(d,**kw) for d in C.DATA]
    row=[]
    for k in LIM:
        d,i=find(ds,*k[:3]); row.append(d['dband'][i])
    print(f"{name:40} " + " ".join(f"{x:8.3f}" for x in row))
print("\n=== B. ecart relatif de l'ATR vs reference (chauffe 100) et effet sur les fleches ===")
print(f"{'variante':40} {'p50%':>8} {'p95%':>8} {'max%':>8}  {'exactes/trop/manq':>18}")
for name,kw in VAR:
    ds=[C.feats(d,**kw) for d in C.DATA]
    err=[]
    for a,b in zip(ds,base):
        for i in range(100,len(a['c'])):
            if a['atr'][i] and b['atr'][i]: err.append(abs(a['atr'][i]/b['atr'][i]-1)*100)
    err.sort(); q=lambda f: err[int(f*(len(err)-1))]
    tp,fp,fn,_,_=C.run_variant(kw)
    print(f"{name:40} {q(.5):8.3f} {q(.95):8.3f} {err[-1]:8.3f}  {tp:7}/{fp}/{fn}")
print("\n=== C. combien faut-il changer l'ATR pour corriger chaque cas ? (facteur sur l'ATR) ===")
for k in LIM:
    d,i=find(base,*k[:3])
    db=d['dband'][i]
    fac=db/0.3   # atr_nouveau = fac*atr_ref donnerait dBand=0.30
    sens='doit descendre <0.30 -> ATR x >%.3f'%fac if k[3]=='FP' else 'doit monter >=0.30 -> ATR x <%.3f'%fac
    print(f"  {k[3]} {k[0]:3} {k[1]:3} {k[2]:16} dBand={db:6.3f}  {sens}")
