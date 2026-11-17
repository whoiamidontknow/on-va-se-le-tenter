import pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
Y=pickle.load(open("pub.pkl","rb")); SF=pickle.load(open("sf.pkl","rb"))
src=open("dash.py").read(); exec("def ha"+src.split("def ha",1)[1].split("res=[]")[0])
PV={"MNQ1!":2.0,"MES1!":5.0}; YK={"MNQ1!":"NQ","MES1!":"ES"}
def pf(x): g=x[x>0].sum(); l=-x[x<0].sum(); return g/l if l>0 else np.nan
def st(x): return f"n={len(x):3d} réussite {100*(x>0).mean():4.1f}% PF {pf(x):4.2f} total {x.sum():+7.0f}$"
for sym in ("MNQ1!","MES1!"):
    h1=Y[YK[sym]].copy(); h1.index=h1.index.tz_convert("UTC"); H1=ha(h1); h4=agg4(h1); h4.index=pd.DatetimeIndex(h4.index).tz_convert("UTC"); H4=ha(h4)
    b=SF[(sym,"15 minutes","b")].copy(); b=b[b.t_in>="2024-07-05"].copy()
    b["d"]=np.where(b["dir"]=="L",1,-1); pv=PV[sym]
    tin=pd.DatetimeIndex(b.t_in).tz_localize("Europe/Paris",ambiguous="NaT",nonexistent="NaT").tz_convert("UTC"); tout=pd.DatetimeIndex(b.t_out).tz_localize("Europe/Paris",ambiguous="NaT",nonexistent="NaT").tz_convert("UTC")
    rows=[]
    for i,(ti,to) in enumerate(zip(tin,tout)):
        r=b.iloc[i]
        if pd.isna(ti) or pd.isna(to): continue
        sb=ti-pd.Timedelta(minutes=15)
        i1=H1.index.searchsorted(sb,side="right")-1; i4=H4.index.searchsorted(sb,side="right")-1
        if i1<20 or i4<20: continue
        t1=H1.index[i1]; e1=t1+pd.Timedelta(hours=1); t4=H4.index[i4]; e4=t4+pd.Timedelta(hours=4)
        if sb-t1>pd.Timedelta(hours=1): continue                      # trou de données
        # contrôle d'alignement des prix (roulement de contrat) : prix d'entrée dans la bougie 1 h qui contient l'entrée
        ie=h1.index.searchsorted(ti,side="right")-1; hb=h1.iloc[ie]
        if not (hb.Low-15*(pv==2)-4 <= r.p_in <= hb.High+15*(pv==2)+4): continue
        ok1=r.d*H1.r.iloc[i1]>=0.025; ok4=r.d*H4.r.iloc[i4]>=0.025
        c1=float(h1.Close.iloc[i1]); 
        i4last=h1.index.searchsorted(e4,side="left")-1; c4=float(h1.Close.iloc[i4last])
        rows.append(dict(t=r.t_in,god=r.god,pnl=r.pm*2,d=r.d,p_in=r.p_in,ok1=ok1,ok4=ok4,open1=to>e1,open4=to>e4,
                         x1=r.d*(c1-r.p_in)*pv*2-5, x4=r.d*(c4-r.p_in)*pv*2-5, ex=r.ex, h=r.t_in.hour+r.t_in.minute/60))
    T=pd.DataFrame(rows)
    print(f"\n================ {sym} 15 min, alertes telles qu'en direct, depuis juillet 2024, 2 contrats — {len(T)} trades alignés sur {len(b)}")
    print("  aujourd'hui (aucune sortie ajoutée)                 :",st(T.pnl))
    f1=(~T.ok1)&T.open1; f4=(~T.ok4)&T.open4
    print(f"  trades dont la bougie 1 h finit CONTRE (encore ouverts) : {f1.sum()} | résultat final {T[f1].pnl.sum():+.0f}$ ({100*(T[f1].pnl>0).mean():.0f}% gagnants) | si on sort à la clôture 1 h : {T[f1].x1.sum():+.0f}$")
    print(f"  trades dont la bougie 4 h finit CONTRE (encore ouverts) : {f4.sum()} | résultat final {T[f4].pnl.sum():+.0f}$ | si on sort à la clôture 4 h : {T[f4].x4.sum():+.0f}$")
    n1=np.where(f1,T.x1,T.pnl); print("  RÈGLE 1 : sortir à la clôture 1 h si elle finit contre :",st(pd.Series(n1)))
    n2=np.where(f1,T.x1,np.where(f4,T.x4,T.pnl)); print("  RÈGLE 2 : règle 1 + sortir à la clôture 4 h si contre  :",st(pd.Series(n2)))
    g=T.god&(T.h<20); print("  — GODLIKE, entrées < 20h : aujourd'hui",st(T[g].pnl),"| règle 1",st(pd.Series(n1)[g.values]))
    for y,u in T.groupby(T.t.dt.year): print(f"     {y}: aujourd'hui {u.pnl.sum():+.0f} | règle 1 {pd.Series(n1,index=T.index)[u.index].sum():+.0f} | règle 2 {pd.Series(n2,index=T.index)[u.index].sum():+.0f}")
    print("  contrôle : part des trades dont la bougie 1 h finale est dans le sens :",f"{100*T.ok1.mean():.0f}% ; 4 h : {100*T.ok4.mean():.0f}% ; résultat final si les deux dans le sens : {st(T[T.ok1&T.ok4].pnl)} ; sinon : {st(T[~(T.ok1&T.ok4)].pnl)}")
    pickle.dump(T,open(f"sol_{sym[:3]}.pkl","wb"))
