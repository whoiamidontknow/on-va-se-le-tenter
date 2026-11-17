import pickle, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
S=pickle.load(open("rech.pkl","rb")); PV={"MNQ1!":2.0,"MES1!":5.0}
def out(b,T,sym):
    com=2.5/(b.sl*PV[sym]); return np.where(b.mfeR>=T, T-com, b.R)
K=[("MNQ1!","15 minutes","R16"),("MES1!","15 minutes","R16"),("MNQ1!","5 minutes","R16"),("MNQ1!","2 minutes","R16")]
N={K[0]:"MNQ15",K[1]:"MES15",K[2]:"MNQ5",K[3]:"MNQ2"}
for k in K:
    b=S[k]; b["r67"]=out(b,2/3,k[0]); b["r4"]=b.R
    b["ntr"]=b.tr.astype(str).map(lambda s:s.count("1")); b["nd"]=b.d.str.len()
    b["wd"]=b.t_in.dt.dayofweek
    b["hb"]=pd.cut(b.h,[0,8,13,15.5,18,20,24],right=False,labels=["00-08","08-13","13-15h30","15h30-18","18-20","20+"])
pd.set_option("display.width",250)
def tab(col,bins=None,q=5,val="r67"):
    rows={}
    for k in K:
        b=S[k].dropna(subset=[col]) if col in S[k] else S[k]
        g=pd.qcut(b[col],q,duplicates="drop") if bins is None and b[col].dtype.kind in "fi" and b[col].nunique()>8 else (pd.cut(b[col],bins) if bins is not None else b[col])
        if bins is None and b[col].dtype.kind in "fi" and b[col].nunique()>8:
            g=pd.qcut(b[col],q,labels=[f"q{i+1}" for i in range(q)],duplicates="drop")
        rows[N[k]]=b.groupby(g)[val].agg(lambda x:f"{x.mean():+.3f}({len(x)})")
    print(f"\n--- {col} [{val}]"); print(pd.DataFrame(rows).T.to_string())
B=[-9,-0.3,-0.1,-0.025,0,0.025,0.1,0.3,9]
for c in ("b1","b4","a1","a4"): tab(c,B)
tab("e",[-99,-2,-1,-0.3,0.3,0.6,1,2,99]); tab("ha"); tab("v"); tab("adx"); tab("hb"); tab("ntr"); tab("nd"); tab("dir"); tab("wd"); tab("y")
for L in "FMHTNCD":
    print(L," ".join(f"{N[k]}: avec {S[k][S[k].d.str.contains(L)].r67.mean():+.3f}({S[k].d.str.contains(L).sum()}) sans {S[k][~S[k].d.str.contains(L)].r67.mean():+.3f}" for k in K))
pickle.dump(S,open("rech2.pkl","wb"))
