"""Hors famille, verification de l'observation annexe : conviction continue
dBand + k*vol_ratio >= seuil, au lieu du OU booleen. Balayage k x seuil + controle sur l'API."""
import impl_lab_core as C, json
base=[C.feats(d) for d in C.DATA]
def score_c(ds,k,th,warm=100):
    tp=fp=fn=0
    for d in ds:
        for i in range(warm,len(d['c'])):
            u=False
            if (d['adx'][i] is not None and d['vma'][i] is not None and d['dband'][i] is not None
                and d['sc'][i] is not None and d['run'][i]==2 and d['adx'][i]>=18
                and ((d['cc'][i]>d['e50'][i]) if d['bull'][i] else (d['cc'][i]<d['e50'][i]))):
                vr=(d['v'][i]/d['vma'][i]) if d['vma'][i] else 1.0
                u = d['dband'][i]+k*vr >= th
            t=bool(d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i])
            tp+=u and t; fp+=u and not t; fn+=t and not u
    return tp,fp,fn
best=[];nb=0
for k in [0.3,0.5,0.75,1.0,1.25,1.5,1.75,2.0,2.5,3.0]:
    for th in [x/20 for x in range(10,61)]:
        nb+=1; tp,fp,fn=score_c(base,k,th); best.append((fp+fn,-tp,k,round(th,2),f"{tp}/{fp}/{fn}"))
best.sort()
print(f"=== conviction continue : {nb} combinaisons (k x seuil) ===")
for b in best[:8]: print("  ",b)
