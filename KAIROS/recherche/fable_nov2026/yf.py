import yfinance as yf, pandas as pd, pickle
out={}
for s in ("MES=F","MNQ=F"):
    for iv,per in (("60m","90d"),("15m","59d")):
        d=yf.download(s, interval=iv, period=per, progress=False, auto_adjust=False)
        if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
        out[(s[:3],iv)]=d; print(s,iv,len(d),d.index.min(),d.index.max())
pickle.dump(out,open("yf.pkl","wb"))
