"""H2 - EMA : amorcage. Compare nos EMA50/60 aux colonnes Moyenator 1/2 (EMA exactes d'Ephore),
mesure l'ecart en fonction du nombre de barres de chauffe, et verifie l'amorcage de ta.ema."""
import impl_lab_core as C

print("=== A. ou commencent les colonnes Moyenator (na de tete) ? ===")
for d in C.DATA:
    n1=sum(1 for x in d['m1'] if x is None); n2=sum(1 for x in d['m2'] if x is None)
    i1=next((i for i,x in enumerate(d['m1']) if x is not None),None)
    i2=next((i for i,x in enumerate(d['m2']) if x is not None),None)
    if n1 or n2: print(f"  {d['inst']:3} {d['tf']:3} n={len(d['c']):4}  na(M1)={n1:3} 1er idx={i1}   na(M2)={n2:3} 1er idx={i2}   ecart={n2-n1}")
print("  (les autres fichiers : Moyenator rempli des la 1ere barre -> l'export commence apres la chauffe)")

print("\n=== B. amorcage ta.ema teste sur les fichiers ou l'export contient la 1ere barre ===")
for d in C.DATA:
    i1=next((i for i,x in enumerate(d['m1']) if x is not None),None)
    if i1 is None or i1==0: continue
    c=d['c']
    for p,col,lab in ((50,'m1','EMA50'),(60,'m2','EMA60')):
        ref=d[col]
        j=next(i for i,x in enumerate(ref) if x is not None)
        # hypothese : graine = SMA(p) sur les p premieres barres de l'export
        g=sum(c[:p])/p
        print(f"  {d['inst']} {d['tf']} {lab}: 1ere valeur a idx {j} (p-1={p-1}) ; "
              f"ref={ref[j]:.4f}  SMA({p})={g:.4f}  ecart={ref[j]-g:+.4f}  close[{j}]={c[j]:.4f}")

print("\n=== C. ecart |notre EMA - Moyenator| selon la chauffe (en ticks de 0.25) ===")
print("  seed      barres_chauffe   p50        p95        max      (sur 14 fichiers)")
for seed in ('first','sma'):
    for warm in (0,20,50,100,150,200,300):
        err=[]
        for d in C.DATA:
            n=len(d['c'])
            for p,col in ((50,'m1'),(60,'m2')):
                mine=C.ema(d['c'],p,seed)
                for i in range(warm,n):
                    if d[col][i] is None or mine[i] is None: continue
                    err.append(abs(mine[i]-d[col][i]))
        err.sort()
        q=lambda f: err[int(f*(len(err)-1))]
        print(f"  {seed:6}    {warm:4}            {q(.5):9.5f}  {q(.95):9.5f}  {err[-1]:9.5f}")

print("\n=== D. ecart en points, par fichier, chauffe 100, seed='first' ===")
for d in C.DATA:
    e50=C.ema(d['c'],50,'first')
    err=[abs(e50[i]-d['m1'][i]) for i in range(100,len(d['c'])) if d['m1'][i] is not None]
    if err: print(f"  {d['inst']:3} {d['tf']:3}  max={max(err):10.6f}  moy={sum(err)/len(err):10.6f}  prix~{d['c'][-1]:.0f}  -> max en % du prix {100*max(err)/d['c'][-1]:.5f}%")

print("\n=== E. effet sur les fleches : notre EMA calculee VS colonnes Moyenator ===")
for seed in ('first','sma'):
    for truth in (True,False):
        tp,fp,fn,errs,_=C.run_variant(dict(ema_seed=seed,use_truth_ma=truth))
        print(f"  seed={seed:6} truth_ma={truth!s:5} -> {tp} exactes / {fp} en trop / {fn} manquees")

print("\n=== F. effet de l'amorcage sur les EMA du Heishinator (4 et 32) ===")
for hseed in ('first','sma'):
    tp,fp,fn,errs,_=C.run_variant(dict(heishi_seed=hseed))
    print(f"  heishi_seed={hseed:6} -> {tp}/{fp}/{fn}")
# ecart de l'etat bull entre les deux amorcages
diff=0; tot=0; firstdiff={}
for d in C.DATA:
    a=C.feats(d,heishi_seed='first'); b=C.feats(d,heishi_seed='sma')
    for i in range(100,len(d['c'])):
        if a['bull'][i] is None or b['bull'][i] is None: continue
        tot+=1
        if a['bull'][i]!=b['bull'][i]:
            diff+=1; firstdiff.setdefault((d['inst'],d['tf']),d['t'][i][:16])
print(f"  etats Heishinator differents apres chauffe 100 : {diff}/{tot}")
