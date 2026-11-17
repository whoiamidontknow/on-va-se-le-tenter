import pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
Y=pickle.load(open("pub.pkl","rb")); S=pickle.load(open("rech2.pkl","rb")); SF=pickle.load(open("sf.pkl","rb"))
src=open("dash.py").read(); exec("def ha"+src.split("def ha",1)[1].split("res=[]")[0])
PV={"MNQ1!":2.0,"MES1!":5.0}
def pf(x): g=x[x>0].sum(); l=-x[x<0].sum(); return g/l if l>0 else np.nan
def dd(x): e=x.cumsum(); return (e.cummax().clip(lower=0)-e).max()
def prep(sym,tf,pr,yk,mins):
    h1=Y[yk].copy(); h1.index=h1.index.tz_convert("UTC"); H1=ha(h1); h4=agg4(h1); h4.index=pd.DatetimeIndex(h4.index).tz_convert("UTC"); H4=ha(h4)
    b=S[(sym,tf,pr)].copy(); b=b[b.t_in>="2024-07-10"].copy()
    ti=pd.DatetimeIndex(b.t_in).tz_localize("Europe/Paris",ambiguous="NaT",nonexistent="NaT").tz_convert("UTC"); b=b[~ti.isna()]; ti=ti[~ti.isna()]
    sb=ti-pd.Timedelta(minutes=mins)
    i1=H1.index.searchsorted(sb,side="right")-1; i4=H4.index.searchsorted(sb,side="right")-1
    b["f1"]=b["dir"].values*H1.r.values[i1]; b["f4"]=b["dir"].values*H4.r.values[i4]     # valeur FINALE de la bougie 1 h / 4 h du signal (lecture du graphique d'origine)
    ok=(sb-H1.index[i1]<=pd.Timedelta(hours=1)); b=b[ok]
    b["e1"]=b.e.round(1); b["usd"]=b.sl*PV[sym]*2      # $ par R à 2 contrats
    return b
def res(b,T): 
    com=2.5/(b.sl*PV[b.attrs["sym"]]); return np.where(b.mfeR>=T,T-com,b.R)*b.usd
def line(lab,b,m,T=2/3):
    u=b[m]; x=pd.Series(np.asarray(res(u,T),float),index=u.t_in.values) if len(u) else pd.Series(dtype=float)
    yrs=(u.t_in.max()-u.t_in.min()).days/365.25 if len(u)>1 else 1
    print(f"   {lab:46s} n={len(x):4d} réussite {100*(x>0).mean():4.1f}% PF {pf(x):5.2f} P&L {x.sum():+8.0f} ({x.sum()/yrs:+7.0f}/an) baisse max {dd(x):5.0f}")
for nm,(sym,tf,pr,yk,mins) in {"MNQ 15 min":("MNQ1!","15 minutes","R16","NQ",15),"MES 15 min":("MES1!","15 minutes","R16","ES",15),"MNQ 5 min":("MNQ1!","5 minutes","R16","NQ",5)}.items():
    b=prep(sym,tf,pr,yk,mins); b.attrs["sym"]=sym
    G=(b.f1>0)&(b.f4>0)            # filtre Dashator 1 h + 4 h, lecture du graphique d'origine
    print(f"\n=========== {nm} — lecture du graphique d'origine, 2 contrats, depuis juillet 2024 (échantillon : signaux pris quand le relevé était à plat)")
    line("56 : 1 h + 4 h, e ≤ 0,6, objectif 2 ATR",b,G&(b.e1<=0.6))
    for em in (0.8,1.0,1.5,99): line(f"   e ≤ {em if em<99 else 'sans limite'}",b,G&(b.e1<=em))
    line("   sans filtre 4 h (1 h seul), e ≤ 0,6",b,(b.f1>0)&(b.e1<=0.6)); line("   sans filtre 1 h (4 h seul), e ≤ 0,6",b,(b.f4>0)&(b.e1<=0.6))
    for T,l in ((0.5,"1,5 ATR"),(0.8333,"2,5 ATR"),(1.0,"3 ATR"),(1.3333,"4 ATR")): line(f"   objectif {l}, e ≤ 0,6",b,G&(b.e1<=0.6),T)
    for T,l in ((0.8333,"2,5 ATR"),(1.0,"3 ATR")): line(f"   objectif {l}, e ≤ 1,0",b,G&(b.e1<=1.0),T)
    line("   sans entrée après 19h, e ≤ 1,0",b,G&(b.e1<=1.0)&(b.h<19)); line("   sans entrée après 19h, e sans limite",b,G&(b.h<19))
    print("   -- contrôle privé, lecture en cours (b1, b4) :")
    Gb=(b.b1>0)&(b.b4>0)
    line("   56 en cours",b,Gb&(b.e1<=0.6)); line("   e ≤ 1,0 en cours",b,Gb&(b.e1<=1.0)); line("   e sans limite en cours",b,Gb); line("   objectif 3 ATR, e ≤ 0,6 en cours",b,Gb&(b.e1<=0.6),1.0)
