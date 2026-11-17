import yfinance as yf, pandas as pd, numpy as np, pickle, warnings, os; warnings.filterwarnings("ignore")
if not os.path.exists("pub.pkl"):
    Y={}
    for s in ("NQ=F","ES=F"):
        d=yf.download(s, interval="60m", period="729d", progress=False, auto_adjust=False)
        if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
        Y[s[:2]]=d
    pickle.dump(Y,open("pub.pkl","wb"))
Y=pickle.load(open("pub.pkl","rb"))
def ha(df):
    o,h,l,c=[df[k].values.astype(float) for k in ("Open","High","Low","Close")]
    hc=(o+h+l+c)/4; ho=np.empty(len(df)); ho[0]=(o[0]+c[0])/2
    for i in range(1,len(df)): ho[i]=(ho[i-1]+hc[i-1])/2
    hh=np.maximum(h,np.maximum(ho,hc)); hl=np.minimum(l,np.minimum(ho,hc))
    tr=np.empty(len(df)); tr[0]=hh[0]-hl[0]
    for i in range(1,len(df)): tr[i]=max(hh[i]-hl[i],abs(hh[i]-hc[i-1]),abs(hl[i]-hc[i-1]))
    atr=np.empty(len(df)); atr[:]=np.nan; atr[13]=tr[:14].mean()
    for i in range(14,len(df)): atr[i]=(atr[i-1]*13+tr[i])/14
    return pd.DataFrame({"body":hc-ho,"atr":atr,"r":(hc-ho)/atr,"ho":ho,"hc":hc},index=df.index)
def agg4(h1):
    ct=h1.index.tz_convert("America/Chicago")
    sess=(ct - pd.Timedelta(hours=17)).normalize()      # jour de session (début 17:00 Chicago)
    blk=((ct - pd.Timedelta(hours=17)).hour//4)
    g=h1.groupby([sess,blk]); d=g.agg(Open=("Open","first"),High=("High","max"),Low=("Low","min"),Close=("Close","last")); d.index=g.apply(lambda x:x.index[0]).values
    d.index=pd.DatetimeIndex(d.index).tz_localize("UTC") if d.index.tz is None else d.index
    return d.sort_index()

def tstat(x): x=x.dropna(); return x.mean()/x.std()*np.sqrt(len(x)) if len(x)>5 else np.nan
for sym,h1 in Y.items():
    h1=h1.copy(); h1.index=h1.index.tz_convert("UTC"); h1=h1[h1.Volume>0] if "Volume" in h1 else h1
    print(f"\n================ {sym} : {len(h1)} bougies 1 h, {h1.index.min().date()} → {h1.index.max().date()}")
    H1=ha(h1); h4=agg4(h1); h4.index=pd.DatetimeIndex(h4.index).tz_convert("UTC"); H4=ha(h4)
    # ATR standard 1 h
    c=h1.Close; tr=pd.concat([h1.High-h1.Low,(h1.High-c.shift()).abs(),(h1.Low-c.shift()).abs()],axis=1).max(axis=1); atr=tr.ewm(alpha=1/14,adjust=False).mean()
    d=pd.DataFrame({"o":h1.Open,"c":c,"atr":atr,"r1":H1.r})
    # dernière bougie 4 h CLÔTURÉE à la clôture de chaque bougie 1 h
    end4=H4.index+pd.Timedelta(hours=4); r4=pd.Series(H4.r.values,index=end4)
    d["r4"]=r4.reindex(d.index+pd.Timedelta(hours=1),method="ffill").values
    d["ema"]=c.ewm(span=50,adjust=False).mean(); d["e"]=(c-d.ema)/atr
    par=d.index.tz_convert("Europe/Paris"); d["h"]=par.hour; d["half"]=np.where(d.index<d.index[len(d)//2],"1re moitié","2e moitié")
    for n in (1,2,4): d[f"f{n}"]=(d.o.shift(-n-1)-d.o.shift(-1))/d.atr      # entrée à l'ouverture suivante, sortie n heures après
    d["ret1"]=(d.c-d.o)/d.atr
    # A. effet de l'heure
    g=d.groupby("h").ret1; t=pd.DataFrame({"moy":g.mean().round(3),"t":g.apply(tstat).round(1),"t_1":d[d.half=="1re moitié"].groupby("h").ret1.apply(tstat).round(1),"t_2":d[d.half=="2e moitié"].groupby("h").ret1.apply(tstat).round(1)})
    print("A. Rendement moyen de la bougie 1 h par heure de Paris (en ATR), t global / 1re moitié / 2e moitié — lignes avec |t|>2 :")
    print(t[(t.t.abs()>2)].T.to_string())
    # B. tendance Dashator sur bougies clôturées
    print("B. Suivre le Dashator 1 h + 4 h clôturés (rendement dans le sens, en ATR, sur 1 / 2 / 4 h) :")
    for k in (0.0,0.025,0.1,0.3):
        for lab,cond_e in (("tous",None),("repli e≤0,6",0.6)):
            L=(d.r1>=k)&(d.r4>=k); S=(d.r1<=-k)&(d.r4<=-k)
            if cond_e is not None: L&=(d.e<=cond_e); S&=(d.e>=-cond_e)
            sg=pd.Series(np.where(L,1,np.where(S,-1,0)),index=d.index); m=sg!=0
            txt=" | ".join(f"{n}h {(sg[m]*d[f'f{n}'][m]).mean():+.3f} (t {tstat(sg[m]*d[f'f{n}'][m]):+.1f}; moitiés {tstat((sg*d[f'f{n}'])[m&(d.half=='1re moitié')]):+.1f}/{tstat((sg*d[f'f{n}'])[m&(d.half=='2e moitié')]):+.1f})" for n in (1,2,4))
            print(f"   seuil {k:<5} {lab:12s} n={m.sum():5d} : {txt}")
    pickle.dump(d,open(f"pub_{sym}.pkl","wb"))
