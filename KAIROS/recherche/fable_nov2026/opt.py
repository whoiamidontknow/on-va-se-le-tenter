import glob, pickle, warnings, importlib.util, numpy as np, pandas as pd; warnings.filterwarnings("ignore")
spec=importlib.util.spec_from_file_location("rl","rl.py"); rl=importlib.util.module_from_spec(spec); spec.loader.exec_module(rl)
def pf(x): g=x[x>0].sum(); l=-x[x<0].sum(); return g/l if l>0 else np.nan
def st(x): return f"n={len(x):4d} réussite {100*(x>0).mean():4.1f}% PF {pf(x):4.2f} total {x.sum():+7.0f}"
print("=== A. Export V2 de Jeremy (MNQ 15 min, préréglage 57, comme en direct, 2 contrats)")
f=glob.glob("/Users/jeremk/ERGON/KAIROS-data/Strat de merde/*4ea0d.xlsx")[0]; p,b=rl.load(f)
b["god"]=b.com.astype(str).str.contains("GODLIKE"); b["h"]=b.t_in.dt.hour+b.t_in.dt.minute/60; b["y"]=b.t_in.dt.year; b["dow"]=b.t_in.dt.dayofweek
print("  tous            :",st(b.pnl)); print("  GODLIKE         :",st(b[b.god].pnl)); print("  56 seul         :",st(b[~b.god].pnl))
g=b[b.god]
for lo,hi in ((0,8),(8,13),(13,15.5),(15.5,18),(18,20),(13,20),(8,20),(0.33,13)):
    u=g[(g.h>=lo)&(g.h<hi)]; print(f"  GODLIKE {lo:>5}-{hi:<5}: {st(u.pnl)} | par an {dict((y,round(v.sum())) for y,v in u.pnl.groupby(u.y))}")
print("  GODLIKE par sens :",{("long" if d>0 else "short"):st(u.pnl) for d,u in g.groupby("dir")})
print("  GODLIKE par jour :",{d:(len(u),round(u.pnl.sum())) for d,u in g.groupby("dow")})
print("  GODLIKE sorties  :",{e:(len(u),round(u.pnl.sum())) for e,u in g.groupby(g.exit.str.replace(' [LS]$','',regex=True))})
print("\n=== B. Relevés R16, trades qui passent les filtres du 56 en lecture « en direct », GODLIKE, entrée < 20h")
S=pickle.load(open("rech2.pkl","rb")); PV={"MNQ1!":2.0,"MES1!":5.0}
def out(b,T,sym): com=2.5/(b.sl*PV[sym]); return np.where(b.mfeR>=T,T-com,b.R)
N={("MNQ1!","15 minutes","R16"):"MNQ15",("MES1!","15 minutes","R16"):"MES15",("MNQ1!","5 minutes","R16"):"MNQ5"}
G={}
for k,nm in N.items():
    d=S[k]; d=d[(d.b1>=0.025)&(d.b4>=0.025)&(d.e.round(1)<=0.6)&(d.h<20)].copy()
    for T in (0.5,2/3,1,1.5,2,4): d[f"T{T:.2f}"]=out(d,T,k[0])
    G[nm]=d
    print(f"  {nm} n={len(d)} | R moyen selon l'objectif : "+" ".join(f"{T:.2f}R:{d[f'T{T:.2f}'].mean():+.3f}({100*(d[f'T{T:.2f}']>0).mean():.0f}%)" for T in (0.5,2/3,1,1.5,2,4)))
def cut(name,fn):
    print(f"  -- {name}")
    for nm,d in G.items():
        parts=[]
        for lab,m in fn(d):
            u=d[m]["T0.67"]; parts.append(f"{lab}: {u.mean():+.2f}/{100*(u>0).mean():.0f}%({len(u)})")
        print(f"     {nm:6s} "+" | ".join(parts))
cut("e (distance à l'EMA50)",lambda d:[("e<-1",d.e<-1),("-1..0",(d.e>=-1)&(d.e<0)),("0..0,3",(d.e>=0)&(d.e<0.3)),("0,3..0,6",d.e>=0.3)])
cut("force b1 (1 h en cours)",lambda d:[("<0,1",d.b1<0.1),("0,1-0,3",(d.b1>=0.1)&(d.b1<0.3)),("0,3-0,6",(d.b1>=0.3)&(d.b1<0.6)),("≥0,6",d.b1>=0.6)])
cut("force b4 (4 h en cours)",lambda d:[("<0,1",d.b4<0.1),("0,1-0,3",(d.b4>=0.1)&(d.b4<0.3)),("≥0,3",d.b4>=0.3)])
cut("bougie 1 h clôturée (a1)",lambda d:[("contre",d.a1<0),("dans le sens",d.a1>=0)])
cut("bougie 4 h clôturée (a4)",lambda d:[("contre",d.a4<0),("dans le sens",d.a4>=0)])
cut("volume / moyenne",lambda d:[("<0,8",d.v<0.8),("0,8-1,3",(d.v>=0.8)&(d.v<1.3)),("≥1,3",d.v>=1.3)])
cut("ADX",lambda d:[("<20",d.adx<20),("20-30",(d.adx>=20)&(d.adx<30)),("≥30",d.adx>=30)])
cut("corps HA du signal",lambda d:[("<0,3",d.ha<0.3),("0,3-0,8",(d.ha>=0.3)&(d.ha<0.8)),("≥0,8",d.ha>=0.8)])
cut("TREND : unités dans le sens",lambda d:[("0-2",d.ntr<=2),("3-4",(d.ntr>=3)&(d.ntr<=4)),("5-6",d.ntr>=5)])
cut("heure",lambda d:[("0-8",d.h<8),("8-13",(d.h>=8)&(d.h<13)),("13-15h30",(d.h>=13)&(d.h<15.5)),("15h30-18",(d.h>=15.5)&(d.h<18)),("18-20",d.h>=18)])
cut("déclencheur",lambda d:[(L,d.d.str.contains(L)) for L in "FHTNCD"])
cut("sens",lambda d:[("long",d.dir>0),("short",d.dir<0)])
pickle.dump(G,open("optG.pkl","wb"))
