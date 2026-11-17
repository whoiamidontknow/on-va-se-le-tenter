import glob, pickle, warnings, importlib.util, numpy as np, pandas as pd; warnings.filterwarnings("ignore")
spec=importlib.util.spec_from_file_location("rl","rl.py"); rl=importlib.util.module_from_spec(spec); spec.loader.exec_module(rl)
PV={"MNQ1!":2.0,"MES1!":5.0}; R16=pickle.load(open("rech.pkl","rb")); rng=np.random.default_rng(11)
D={}
for f in sorted(glob.glob("/Users/jeremk/ERGON/KAIROS-data/SansFuite/*.xlsx")):
    p,b=rl.load(f); sym=p["Symbole"].split(":")[1]; mode=str(p.get("Données multi-unités"))[:1].lower()
    pv=PV[sym]; b["god"]=b.com.astype(str).str.contains("GODLIKE"); ex=b.exit.astype(str); d=(b.p_out-b.p_in).abs()
    b["atr"]=np.where(ex.str.startswith("Obj"),d/2,np.where(ex.str.startswith("Stop"),d/3,np.nan))
    b["atr"]=b.atr.fillna(b.t_in.map(R16[(sym,"15 minutes","R16")].set_index("t_in").sl/3))
    s=b.set_index("t_in").atr.interpolate(method="time").ffill().bfill(); b["atr"]=b.atr.fillna(pd.Series(s.values,index=b.index))
    b["R"]=b.pnl/b.qty/pv/b.atr/3; b["h"]=b.t_in.dt.hour+b.t_in.dt.minute/60; D[(sym,mode)]=b
def sim(R,risk,n=20000,target=3000,dd=2000,maxtr=400):
    ok=0; nt=[]
    for _ in range(n):
        eq=np.cumsum(rng.choice(R,maxtr)*risk); floor=np.minimum(np.maximum.accumulate(np.maximum(eq,0))-dd,0)
        hit=np.argmax(eq>=target) if (eq>=target).any() else 10**9; bust=np.argmax(eq<=floor) if (eq<=floor).any() else 10**9
        if hit<bust: ok+=1; nt.append(hit+1)
    return ok/n,(np.median(nt) if nt else np.nan)
for mode,lab in (("a","ANCIEN CALCUL = ce que montre le graphique Strat5669"),("b","COMME EN DIRECT = ce que les alertes envoient")):
    print(lab)
    for god in (True,False):
        R=np.concatenate([D[(s,mode)][D[(s,mode)].god | (not god)].R.values for s in ("MNQ1!","MES1!")])
        n=len(R); mois=n/37
        for risk in (300,450):
            p,nt=sim(R,risk); print(f"   {'GODLIKE seulement' if god else 'tous les trades  '} MNQ+MES | {n} trades ({mois:.0f}/mois) réussite {100*(R>0).mean():.0f}% R moyen {R.mean():+.3f} | risque {risk} $ : éval validée {100*p:.0f} % en {nt:.0f} trades (≈ {nt/mois:.1f} mois)")
