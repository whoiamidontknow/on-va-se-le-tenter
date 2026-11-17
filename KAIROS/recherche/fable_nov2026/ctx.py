import pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
Y=pickle.load(open("pub.pkl","rb")); S=pickle.load(open("rech2.pkl","rb")); PV={"MNQ1!":2.0,"MES1!":5.0}
def out(b,T,sym): com=2.5/(b.sl*PV[sym]); return np.where(b.mfeR>=T,T-com,b.R)
K={"MNQ15":("MNQ1!","15 minutes","R16","NQ"),"MES15":("MES1!","15 minutes","R16","ES"),"MNQ5":("MNQ1!","5 minutes","R16","NQ")}
def ctx(h1):
    h=h1.copy(); h.index=h.index.tz_convert("UTC"); ny=h.index.tz_convert("America/New_York")
    sess=(ny-pd.Timedelta(hours=18)).normalize()          # jour de session (début 18:00 New York)
    h["sess"]=sess; g=h.groupby("sess")
    day=pd.DataFrame({"o":g.Open.first(),"h":g.High.max(),"l":g.Low.min(),"c":g.Close.last()})
    day["pc"]=day.c.shift(); day["ph"]=day.h.shift(); day["pl"]=day.l.shift(); day["pdir"]=np.sign(day.c.shift()-day.o.shift()); day["ema20"]=day.c.ewm(span=20,adjust=False).mean().shift()
    cash=h[(ny.hour==9)&(ny.minute==0)|((ny.hour==10)&(ny.minute==0))]   # bougie 09:00-10:00 NY ≈ ouverture cash (09:30)
    co=h[(ny.hour==9)].groupby("sess").Close.last()       # prix à 10:00 NY
    day["co"]=co
    return h,day
C={k:ctx(Y[v[3]]) for k,v in K.items()}
def st(x): return f"{x.mean():+.3f}/{100*(x>0).mean():.0f}%({len(x)})"
res={}
for nm,(sym,tf,pr,yk) in K.items():
    h,day=C[nm]; b=S[(sym,tf,pr)].copy(); b=b[b.t_in>="2024-07-10"].copy(); b["r"]=out(b,2/3,sym)
    ti=pd.DatetimeIndex(b.t_in).tz_localize("Europe/Paris",ambiguous="NaT",nonexistent="NaT").tz_convert("UTC"); b=b[~ti.isna()]; ti=ti[~ti.isna()]
    ny=ti.tz_convert("America/New_York"); ss=(ny-pd.Timedelta(hours=18)).normalize(); d=day.reindex(ss)
    px=b.p_in.values; dr=b["dir"].values
    ok=(np.abs(px-d.c.values)/px<0.06)                    # alignement grossier des prix
    b["so"]=dr*np.sign(px-d.o.values)                     # dans le sens du mouvement depuis l'ouverture de séance (00h Paris)
    b["pcl"]=dr*np.sign(px-d.pc.values)                   # au-dessus / en dessous de la clôture de la veille
    b["pd"]=dr*d.pdir.values                              # dans le sens de la veille
    b["e20"]=dr*np.sign(px-d.ema20.values)                # du bon côté de la moyenne 20 jours
    b["brk"]=np.where(dr>0,px>d.ph.values,px<d.pl.values) # au-delà du plus haut / plus bas de la veille
    cash=(ny.hour*60+ny.minute)>=10*60; b["cashdir"]=np.where(cash,dr*np.sign(px-d.co.values),np.nan)   # après 16h Paris : sens depuis 16h
    b=b[ok]; res[nm]=b
    print(f"\n{nm} — tous les signaux (aucun filtre), objectif 0,667 R, depuis juillet 2024 : {st(b.r)}")
    for c,lab in (("so","sens depuis l'ouverture de séance"),("pcl","côté de la clôture de la veille"),("pd","sens de la veille"),("e20","côté de la moyenne 20 jours"),("cashdir","sens depuis 16h (entrées après 16h)")):
        print(f"   {lab:36s} avec : {st(b[b[c]>0].r)} | contre : {st(b[b[c]<0].r)}")
    print(f"   {'cassure du haut/bas de la veille':36s} oui  : {st(b[b.brk].r)} | non    : {st(b[~b.brk].r)}")
    g=b[(b.b1>=0.025)&(b.b4>=0.025)&(b.e.round(1)<=0.6)]
    print(f"   -- parmi les trades GODLIKE (filtres du 56, en direct) : {st(g.r)}")
    for c,lab in (("so","sens depuis l'ouverture de séance"),("pcl","côté de la clôture de la veille"),("pd","sens de la veille"),("e20","côté de la moyenne 20 jours")):
        print(f"      {lab:33s} avec : {st(g[g[c]>0].r)} | contre : {st(g[g[c]<0].r)}")
pickle.dump(res,open("ctx.pkl","wb"))
