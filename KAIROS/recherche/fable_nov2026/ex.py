import glob, pickle, warnings, importlib.util, numpy as np, pandas as pd; warnings.filterwarnings("ignore")
spec=importlib.util.spec_from_file_location("rl","rl.py"); rl=importlib.util.module_from_spec(spec); spec.loader.exec_module(rl)
PV={"MNQ1!":2.0,"MES1!":5.0}; R=pickle.load(open("rech.pkl","rb"))
out={}
for f in sorted(glob.glob("/Users/jeremk/ERGON/KAIROS-data/SansFuite/*.xlsx")):
    p,b=rl.load(f); sym=p["Symbole"].split(":")[1]
    if not str(p.get("Données multi-unités")).startswith("b"): continue
    pv=PV[sym]; b["god"]=b.com.astype(str).str.contains("GODLIKE"); b["ex"]=b.exit.astype(str)
    d=(b.p_out-b.p_in).abs()
    b["atr"]=np.where(b.ex.str.startswith("Obj"),d/2,np.where(b.ex.str.startswith("Stop"),d/3,np.nan))
    # ATR exact des relevés R16 quand l'heure d'entrée coïncide
    r=R[(sym,"15 minutes","R16")].set_index("t_in").sl/3
    b["atr_r16"]=b.t_in.map(r)
    chk=b.dropna(subset=["atr","atr_r16"]); print(sym,"contrôle ATR (sorties exactes vs R16) : n=",len(chk),"écart médian %",round(100*((chk.atr-chk.atr_r16).abs()/chk.atr_r16).median(),1))
    b["atr"]=b.atr.fillna(b.atr_r16)
    s=b.set_index("t_in").atr.interpolate(method="time").ffill().bfill(); b["atr"]=b.atr.fillna(pd.Series(s.values,index=b.index))
    b["h"]=b.t_in.dt.hour+b.t_in.dt.minute/60
    b["pA"]=b.pnl/b.qty/pv/b.atr      # résultat en ATR (commission comprise)
    b["mfeA"]=b.mfe/b.qty/pv/b.atr; b["maeA"]=b.mae.abs()/b.qty/pv/b.atr; b["comA"]=2.5/pv/b.atr
    out[sym]=b
pickle.dump(out,open("ex.pkl","wb"))
def res(g,k,T):   # stop k ATR, objectif T ATR ; un seul des deux change à la fois (ordre exact)
    r=g.pA.copy()
    if T<2: r=np.where(g.mfeA>=T, T-g.comA, r)
    if k<3: r=np.where(g.maeA>=k, -k-g.comA, r)
    return pd.Series(r,index=g.index)/k     # en R (risque = k ATR)
for sym,b in out.items():
    g=b[b.god&(b.h<20)]
    print(f"\n{sym} GODLIKE mode b, entrées < 20h, n={len(g)}  (R = gain par unité de risque ; $450 = R × 450)")
    for k,T in ((3,2),(3,1.5),(3,1),(2.5,2),(2,2),(1.5,2),(1,2)):
        r=res(g,k,T); yr=" ".join(f"{y}:{v.sum():+.1f}" for y,v in r.groupby(g.t_in.dt.year))
        print(f"  stop {k} ATR / objectif {T} ATR : réussite {100*(r>0).mean():4.1f}% | R moyen {r.mean():+.3f} ±{1.96*r.std()/np.sqrt(len(r)):.3f} | total {r.sum():+6.1f} R | par an {yr}")
