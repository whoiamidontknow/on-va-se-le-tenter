import pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
Y=pickle.load(open("pub.pkl","rb"))
COST={"NQ":1.75,"ES":0.45}     # aller-retour en points : commission + 1 tick de glissement par côté (micro)
def t(x): x=pd.Series(x).dropna(); return x.mean()/x.std()*np.sqrt(len(x)) if len(x)>5 and x.std()>0 else np.nan
def pf(x): x=pd.Series(x).dropna(); g=x[x>0].sum(); l=-x[x<0].sum(); return g/l if l>0 else np.nan
def rep(lab,x,dates):
    x=pd.Series(np.asarray(x,float),index=pd.DatetimeIndex(dates)).dropna(); x=x[x!=0] if (x==0).mean()>0.3 else x
    if len(x)<30: print(f"   {lab:58s} n={len(x)}"); return
    h=x.index<x.index[len(x)//2]
    print(f"   {lab:58s} n={len(x):4d} réussite {100*(x>0).mean():4.1f}% PF {pf(x):4.2f} moy {x.mean():+6.2f} pts t {t(x):+5.2f} | moitiés t {t(x[h]):+5.2f} / {t(x[~h]):+5.2f} | par an "+" ".join(f"{y}:{v.sum():+.0f}" for y,v in x.groupby(x.index.year)))
for sym,h1 in Y.items():
    h=h1.copy(); h.index=h.index.tz_convert("America/New_York"); c=COST[sym]
    h["d"]=h.index.normalize(); h["hh"]=h.index.hour
    P=h.pivot_table(index="d",columns="hh",values="Open",aggfunc="first")      # prix à hh:00 New York
    C=h.pivot_table(index="d",columns="hh",values="Close",aggfunc="last"); Hi=h.pivot_table(index="d",columns="hh",values="High",aggfunc="max"); Lo=h.pivot_table(index="d",columns="hh",values="Low",aggfunc="min")
    P=P[P.index.dayofweek<5].dropna(subset=[9,10,15,16]); C=C.reindex(P.index); Hi=Hi.reindex(P.index); Lo=Lo.reindex(P.index)
    pc=P[16].shift()                          # prix à 16:00 la veille
    print(f"\n================ {sym} : {len(P)} jours, {P.index.min().date()} → {P.index.max().date()} (coût {c} pt par trade)")
    # 1. Momentum intrajournalier : sens (veille 16:00 → 10:00) joué de 15:00 à 16:00 puis de 10:00 à 16:00
    s=np.sign(P[10]-pc)
    rep("veille→10h, joué 15h→16h (dernière heure)", s*(P[16]-P[15])-c, P.index)
    rep("veille→10h, joué 10h→16h", s*(P[16]-P[10])-c, P.index)
    s2=np.sign(P[10]-P[9]); rep("9h→10h, joué 10h→16h", s2*(P[16]-P[10])-c, P.index)
    s3=np.sign(P[15]-P[10]); rep("10h→15h, joué 15h→16h", s3*(P[16]-P[15])-c, P.index)
    # 2. Zone de bruit (Zarattini, Aziz, Barbon) en heures : référence = prix de 9h ; bande = moyenne 14 j de |prix(h)/ref − 1|
    ref=P[9]; res=pd.Series(0.0,index=P.index); 
    for k in (1.0,1.5):
        res=pd.Series(0.0,index=P.index); pos=pd.Series(0,index=P.index); ent=pd.Series(np.nan,index=P.index)
        for hh in (10,11,12,13,14,15):
            mv=(P[hh]/ref-1).abs(); band=mv.rolling(14).mean().shift()*k
            up=ref*(1+band); dn=ref*(1-band)
            new=(pos==0)&(P[hh]>up); newS=(pos==0)&(P[hh]<dn)
            pos=pos.where(~new,1).where(~newS,-1); ent=ent.where(~(new|newS),P[hh])
        res=pos*(P[16]-ent)-c*(pos!=0)
        rep(f"zone de bruit ×{k} (entrée à l'heure, sortie 16h)", res.where(pos!=0), P.index)
        # variante : sortie si le prix repasse la référence à une heure pleine
    # 3. Cassure de la première heure (9h-10h) : entrée au prix de cassure approché à l'heure suivante, stop de l'autre côté, sortie 16h
    rh=Hi[9]; rl=Lo[9]; pos=pd.Series(0,index=P.index); ent=pd.Series(np.nan,index=P.index); out=pd.Series(np.nan,index=P.index)
    for hh in (10,11,12,13,14,15):
        bu=(pos==0)&(Hi[hh]>rh); bd=(pos==0)&(Lo[hh]<rl)&~bu
        ent=ent.where(~bu,rh).where(~bd,rl); pos=pos.where(~bu,1).where(~bd,-1)
        stopL=(pos==1)&out.isna()&(Lo[hh]<rl)&~bu; stopS=(pos==-1)&out.isna()&(Hi[hh]>rh)&~bd
        out=out.where(~stopL,rl-rh+0).where(~stopS,rl-rh+0)        # perte = largeur de la zone
    r=np.where(out.notna(),out,pos*(P[16]-ent))-c*(pos!=0)
    rep("cassure de la zone 9h-10h, stop opposé, sortie 16h", pd.Series(r,index=P.index).where(pos!=0), P.index)
    # 4. Nuit : achat 18h → 9h30 approché (16h veille → 9h) ; et 2h → 3h du matin
    rep("nuit : achat veille 16h → 9h", (P[9]-pc)-c, P.index)
    if 2 in P and 3 in P: rep("achat 2h → 3h du matin (dérive nocturne)", (P[3]-P[2])-c, P.index)
    if 18 in P: rep("achat 18h → 9h (séance de nuit)", (P[9]-P[18].shift())-c, P.index)
    # 5. Retour à la moyenne : grosse baisse veille→10h (> 1 écart-type 20 j) achetée 10h→16h, et inverse
    g=(P[10]/pc-1); z=g/g.rolling(20).std().shift()
    rep("contre un écart > 1σ à 10h, joué 10h→16h", np.where(z.abs()>1,-np.sign(z)*(P[16]-P[10])-c,np.nan), P.index)
    rep("avec un écart > 1σ à 10h, joué 10h→16h", np.where(z.abs()>1,np.sign(z)*(P[16]-P[10])-c,np.nan), P.index)
