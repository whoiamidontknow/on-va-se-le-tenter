import glob, sys, warnings, importlib.util, openpyxl, numpy as np, pandas as pd; warnings.filterwarnings("ignore")
spec=importlib.util.spec_from_file_location("rl","rl.py"); rl=importlib.util.module_from_spec(spec); spec.loader.exec_module(rl)
def pf(x): g=x[x>0].sum(); l=-x[x<0].sum(); return g/l if l>0 else np.nan
def dd(x): e=x.cumsum(); return (e.cummax().clip(lower=0)-e).max()
rows=[]
for f in sorted(glob.glob(sys.argv[1]+"/*.xlsx")):
    p,b=rl.load(f); pr=next((str(v) for k,v in p.items() if k.startswith("Préréglage")),"?"); x=b.pnl
    day=b.groupby(b.t_out.dt.date).pnl.sum()
    wb=openpyxl.load_workbook(f,read_only=True); perf={str(r[0]):r[1] for r in wb["Performance"].iter_rows(values_only=True) if r and r[0]}
    ddtv=next((v for k,v in perf.items() if "aisse max" in k or "rawdown max" in k),None)
    b["y"]=b.t_in.dt.year
    rows.append(dict(f=f[-10:-5],sym=p["Symbole"].split(":")[1],tf=p["Plage temporelle"],pre=pr[:42],mode=str(p.get("Données multi-unités"))[:18],plage=str(p.get("Plage de trading"))[:13],n=len(b),qty=sorted(b.qty.unique())[-1],win=round(100*(x>0).mean(),1),pf=round(pf(x),2),pnl=round(x.sum()),dd_cloture=round(dd(x)),dd_tv=ddtv,pire_jour=round(day.min()),meilleur_jour=round(day.max()),part_meilleur_jour=round(100*day.max()/x.sum(),1),jours_sous_1200=int((day<-1200).sum()),
        par_an=" ".join(f"{y}:{v.sum():+.0f}" for y,v in b.groupby("y").pnl), sorties=" ".join(f"{k[:5]}:{len(v)}/{v.sum():+.0f}" for k,v in b.groupby(b.exit.str.replace(' [LS]$','',regex=True)).pnl)))
pd.set_option("display.width",330); pd.set_option("display.max_colwidth",80)
R=pd.DataFrame(rows); print(R.drop(columns=["par_an","sorties"]).to_string(index=False)); print(); print(R[["f","pre","par_an"]].to_string(index=False)); print(); print(R[["f","pre","sorties"]].to_string(index=False))
