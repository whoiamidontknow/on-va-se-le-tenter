import pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
Y=pickle.load(open("pub.pkl","rb")); S=pickle.load(open("rech2.pkl","rb")); PV={"MNQ1!":2.0,"MES1!":5.0}
def out(b,T,sym): com=2.5/(b.sl*PV[sym]); return np.where(b.mfeR>=T,T-com,b.R)
K={"MNQ15":("MNQ1!","15 minutes","R16","NQ"),"MES15":("MES1!","15 minutes","R16","ES"),"MNQ5":("MNQ1!","5 minutes","R16","NQ"),"MNQ15-48":("MNQ1!","15 minutes","R48","NQ"),"MNQ5-48":("MNQ1!","5 minutes","R48","NQ")}
def pf(x): g=x[x>0].sum(); l=-x[x<0].sum(); return g/l if l>0 else np.nan
def st(x): return f"{x.mean():+.3f}R {100*(x>0).mean():.0f}% PF{pf(x):.2f} (n={len(x)})" if len(x) else "n=0"
def refs(h1):
    h=h1.copy(); h.index=h.index.tz_convert("UTC"); ny=h.index.tz_convert("America/New_York"); h["sess"]=(ny-pd.Timedelta(hours=18)).normalize()
    r={}
    for hh in (8,9,10,11): r[hh]=h[ny.hour==hh].groupby("sess").Open.first()      # prix à hh:00 New York
    r["o930"]=h[ny.hour==9].groupby("sess").Open.first()
    return r
D={}
for nm,(sym,tf,pr,yk) in K.items():
    R=refs(Y[yk]); b=S[(sym,tf,pr)].copy(); b=b[b.t_in>="2024-07-10"].copy()
    ti=pd.DatetimeIndex(b.t_in).tz_localize("Europe/Paris",ambiguous="NaT",nonexistent="NaT").tz_convert("UTC"); b=b[~ti.isna()]; ti=ti[~ti.isna()]
    ny=ti.tz_convert("America/New_York"); ss=(ny-pd.Timedelta(hours=18)).normalize(); b["nym"]=ny.hour*60+ny.minute; b["yr"]=ny.year
    for T in (0.5,2/3,1,1.5,2,4): b[f"T{T:.2f}"]=out(b,T,sym)
    for k,v in R.items(): b[f"ref{k}"]=v.reindex(ss).values
    b["atr"]=b.sl/3
    D[nm]=b
print("A. Signaux à CONTRE-SENS du mouvement depuis 10:00 New York (16:00 Paris), entrées de 10:00 à 16:00 NY, aucun autre filtre")
for nm,b in D.items():
    u=b[(b.nym>=600)&(b.ref10.notna())&(np.abs(b.p_in-b.ref10)/b.p_in<0.05)].copy()
    u["mv"]=u["dir"]*(u.p_in-u.ref10)/u.atr          # >0 : le trade va dans le sens du mouvement ; <0 : contre
    c=u[u.mv<0]; w=u[u.mv>0]
    print(f"\n{nm}: contre {st(c['T0.67'])} | avec {st(w['T0.67'])}")
    print("   par année (contre) :"," | ".join(f"{y}: {st(v['T0.67'])}" for y,v in c.groupby("yr")))
    print("   par heure NY (contre) :"," | ".join(f"{lo//60}h-{hi//60}h: {st(c[(c.nym>=lo)&(c.nym<hi)]['T0.67'])}" for lo,hi in ((600,720),(720,840),(840,975))))
    print("   selon l'ampleur du mouvement (contre, en ATR) :"," | ".join(f"{lab}: {st(c[(c.mv<=-lo)&(c.mv>-hi)]['T0.67'])}" for lab,lo,hi in (("<2",0,2),("2-5",2,5),("5-10",5,10),(">10",10,999))))
    print("   long / short (contre) :",st(c[c['dir']>0]['T0.67']),"/",st(c[c['dir']<0]['T0.67']))
    print("   selon l'objectif (contre) :"," ".join(f"{T:.2f}R:{c[f'T{T:.2f}'].mean():+.3f}" for T in (0.5,2/3,1,1.5,2,4)))
    print("   autre repère (contre / avec) :"," | ".join(f"depuis {k}h NY: {u2[u2.m<0]['T0.67'].mean():+.3f} / {u2[u2.m>0]['T0.67'].mean():+.3f}" for k in (8,9,11) for u2 in [b[(b.nym>=max(600,k*60))&b[f'ref{k}'].notna()].assign(m=lambda z:z['dir']*(z.p_in-z[f'ref{k}']))]))
pickle.dump(D,open("fade.pkl","wb"))
