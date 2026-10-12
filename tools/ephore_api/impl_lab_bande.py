"""Detail d'implementation de la 'bande' du Moyenator dans dBand : bord eloigne max(e50,e60),
bord proche min(e50,e60), EMA50 seule, EMA60 seule, milieu de bande. Plus la grille des seuils."""
import impl_lab_core as C
base=[C.feats(d) for d in C.DATA]

def reband(ds,mode):
    out=[]
    for d in ds:
        e=dict(d); n=len(d['c']); db=[None]*n
        for i in range(n):
            if not d['atr'][i] or d['e50'][i] is None or d['e60'][i] is None: continue
            a,b=d['e50'][i],d['e60'][i]
            if mode=='far':   ref=max(a,b) if d['bull'][i] else min(a,b)
            elif mode=='near':ref=min(a,b) if d['bull'][i] else max(a,b)
            elif mode=='e50': ref=a
            elif mode=='e60': ref=b
            elif mode=='mid': ref=(a+b)/2
            db[i]=(d['cc'][i]-ref)/d['atr'][i] if d['bull'][i] else (ref-d['cc'][i])/d['atr'][i]
        e['dband']=db; out.append(e)
    return out

print("=== A. definition de la bande ===")
for m in ('far','near','e50','e60','mid'):
    ds=reband(base,m); tp,fp,fn,errs=C.score(ds)
    lab={'far':'max/min (reference)','near':'bord proche','e50':'EMA50 seule','e60':'EMA60 seule','mid':'milieu (e50+e60)/2'}[m]
    print(f"  {lab:24} {tp:4}/{fp}/{fn}" + ('   <<< MIEUX' if fp+fn<8 else ''))

print("\n=== B. grille seuil dBand x seuil volume, pour chaque definition de bande ===")
TH=[0.20,0.25,0.28,0.30,0.32,0.35,0.40,0.50]
VK=[0.8,0.9,1.0,1.1,1.25]
nb=0; best=[]
for m in ('far','e50','mid','near','e60'):
    ds=reband(base,m)
    for t in TH:
        for k in VK:
            nb+=1
            tp,fp,fn,_=C.score(ds,db_th=t,vol_k=k)
            best.append((fp+fn,-tp,m,t,k,f"{tp}/{fp}/{fn}"))
best.sort()
print(f"  {nb} combinaisons testees. Top 10 :")
for b in best[:10]: print("   ",b)

print("\n=== C. erreurs restantes avec la meilleure definition de bande ===")
_,_,m,t,k,_=best[0][:6]
ds=reband(base,m); tp,fp,fn,errs=C.score(ds,db_th=t,vol_k=k)
print(f"  bande={m} dBand>={t} vol>={k}xSMA20 -> {tp}/{fp}/{fn}")
for e in errs: print("   ",e)
