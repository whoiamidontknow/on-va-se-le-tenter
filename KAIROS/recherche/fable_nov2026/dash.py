import pandas as pd, numpy as np, pickle, warnings; warnings.filterwarnings("ignore")
Y=pickle.load(open("yf.pkl","rb"))
exec(open("al.py").read().split("pd.set_option")[0])   # m = alertes d'entrée 15 min
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
res=[]
for sym in ("MES","MNQ"):
    h1=Y[(sym,"60m")].copy(); h1.index=h1.index.tz_convert("UTC")
    H1=ha(h1); h4=agg4(h1); h4.index=pd.DatetimeIndex(h4.index).tz_convert("UTC"); H4=ha(h4)
    for r in m[m.sym==sym].itertuples():
        T=pd.Timestamp(r.t).tz_localize("Europe/Paris").tz_convert("UTC")   # clôture de la bougie signal
        sb=T-pd.Timedelta(minutes=15)                                        # ouverture de la bougie signal
        i1=H1.index.searchsorted(sb,side="right")-1; i4=H4.index.searchsorted(sb,side="right")-1
        f=lambda H,i,k: round(float(H.r.iloc[i-k]),3) if i-k>=0 else np.nan
        res.append(dict(t=r.t,sym=sym,dir=r.dir,cas=r.cas,god=r.god, live_1h=float(r.h1), h1_k1=f(H1,i1,1), h1_k2=f(H1,i1,2), h1_k0=f(H1,i1,0),
                        live_4h=float(r.h4), h4_k1=f(H4,i4,1), h4_k2=f(H4,i4,2), h4_k0=f(H4,i4,0), bar1h=H1.index[i1].tz_convert("Europe/Paris").strftime("%H:%M"), bar4h=H4.index[i4].tz_convert("Europe/Paris").strftime("%d %H:%M")))
R=pd.DataFrame(res).sort_values("t"); pd.set_option("display.width",260)
print("k1 = dernière bougie clôturée (ce que le script doit lire) ; k2 = celle d'avant ; k0 = bougie en cours, valeur finale")
print(R.to_string(index=False))
for c,ks in (("live_1h",("h1_k1","h1_k2","h1_k0")),("live_4h",("h4_k1","h4_k2","h4_k0"))):
    d=pd.DataFrame({k:(R[c]-R[k]).abs() for k in ks}); best=d.idxmin(axis=1)
    print(c,"→ colonne la plus proche :",best.value_counts().to_dict(),"| écart médian à k1 :",round(d[ks[0]].median(),3))
