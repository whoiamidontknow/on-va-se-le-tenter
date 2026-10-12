"""H4 - Heishinator : source (ohlc4/hlc3/hl2/close) et periodes (rapide 2..6, lente 26..40).
Un flip decale d'une barre deplace la '2e bougie', donc la fleche entiere."""
import impl_lab_core as C
base=[C.feats(d) for d in C.DATA]
print("=== A. sources, periodes 4/32 : accord d'etat + fleches ===")
print(f"{'source':8} {'etats != ref':>12} {'exactes/trop/manq':>20}")
for s in ('ohlc4','hlc3','hl2','close','open'):
    ds=[C.feats(d,heishi_src=s) for d in C.DATA]
    diff=sum(1 for a,b in zip(ds,base) for i in range(100,len(a['c'])) if a['bull'][i]!=b['bull'][i])
    tp,fp,fn,_,_=C.run_variant(dict(heishi_src=s))
    print(f"{s:8} {diff:12} {tp:12}/{fp}/{fn}")

print("\n=== B. grille rapide x lente sur ohlc4 (exactes/trop/manquees) ===")
F=[2,3,4,5,6]; S=[26,28,30,31,32,33,34,36,40]
print("  rap\\lent " + " ".join(f"{a:>12}" for a in S))
res=[]
for hf in F:
    row=[]
    for hs in S:
        tp,fp,fn,_,_=C.run_variant(dict(hf=hf,hs=hs))
        row.append(f"{tp}/{fp}/{fn}"); res.append((fp+fn,-tp,hf,hs))
    print(f"  {hf:>8} " + " ".join(f"{x:>12}" for x in row))
res.sort(); print("  meilleures :",res[:6])

print("\n=== C. grille source x periodes, seulement les combos qui font <=8 erreurs ===")
tot=0; good=[]
for s in ('ohlc4','hlc3','hl2','close'):
    for hf in (3,4,5):
        for hs in (28,30,32,34,36):
            tot+=1
            tp,fp,fn,_,_=C.run_variant(dict(heishi_src=s,hf=hf,hs=hs))
            if fp+fn<=8: good.append((fp+fn,-tp,s,hf,hs,f"{tp}/{fp}/{fn}"))
good.sort()
print(f"  {tot} combinaisons testees ; {len(good)} a <=8 erreurs :")
for g in good: print("   ",g)

print("\n=== D. ancienne formule SHA (0.42/0.44 vs EMA33) ===")
# SHA = a*ohlc4 + (1-a)*SHA[1] ; haussier si SHA > EMA(close,33)
def feats_sha(d0,**kw):
    d=C.feats(d0,**kw); n=len(d['c'])
    o4=[(d['oo'][i]+d['hh'][i]+d['ll'][i]+d['cc'][i])/4 for i in range(n)]
    a=0.42 if d['tf'] in ('1','2','5','15') else 0.44
    sha=[o4[0]]
    for i in range(1,n): sha.append(a*o4[i]+(1-a)*sha[-1])
    e33=C.ema(d['cc'],33,'first')
    bull=[sha[i]>e33[i] for i in range(n)]
    run=[1]*n
    for i in range(1,n): run[i]=run[i-1]+1 if bull[i]==bull[i-1] else 1
    db=[None]*n
    for i in range(n):
        if d['atr'][i] and d['e50'][i] is not None:
            db[i]=(d['cc'][i]-max(d['e50'][i],d['e60'][i]))/d['atr'][i] if bull[i] else (min(d['e50'][i],d['e60'][i])-d['cc'][i])/d['atr'][i]
    d.update(bull=bull,run=run,dband=db); return d
ds=[feats_sha(d) for d in C.DATA]
tp,fp,fn,errs=C.score(ds)
diff=sum(1 for a,b in zip(ds,base) for i in range(100,len(a['c'])) if a['bull'][i]!=b['bull'][i])
print(f"  SHA 0.42/0.44 vs EMA33 : {tp}/{fp}/{fn}   etats != ref : {diff}")
