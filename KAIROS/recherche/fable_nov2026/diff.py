import pickle, numpy as np, pandas as pd, warnings, yfinance as yf; warnings.filterwarnings("ignore")
S=pickle.load(open("diff.pkl","rb")); bot=[v for k,v in S.items() if k.startswith("Lucid")][0][1].copy(); st=[v for k,v in S.items() if k.startswith("Strat")][0][1].copy()
d=yf.download("MNQ=F", interval="5m", period="60d", progress=False, auto_adjust=False)
if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
d.index=d.index.tz_convert("Europe/Paris").tz_localize(None); c=d.Close
tr=pd.concat([d.High-d.Low,(d.High-c.shift()).abs(),(d.Low-c.shift()).abs()],axis=1).max(axis=1); atr=tr.ewm(alpha=1/14,adjust=False).mean()
def dist(b):
    ex=b.exit.astype(str); dl=(b.p_out-b.p_in).abs()
    x=pd.Series(np.where(ex.str.startswith("Obj"),dl*1.5,np.where(ex.str.startswith("Stop"),dl,np.nan)),index=b.index)
    # ATR à la clôture de la bougie signal (= ouverture de la bougie d'entrée − 5 min)
    a=atr.reindex(b.t_in-pd.Timedelta(minutes=5)).values*3
    return x.fillna(pd.Series(a,index=b.index))
for b in (bot,st): b["dist"]=dist(b); b["risk1"]=b.dist*2; b["pm"]=b.pnl/b.qty; b["day"]=b.t_in.dt.date
kb=set(zip(bot.t_in,bot["dir"])); ks=set(zip(st.t_in,st["dir"]))
st["dans_bot"]=[k in kb for k in zip(st.t_in,st["dir"])]; bot["dans_strat"]=[k in ks for k in zip(bot.t_in,bot["dir"])]
lim=bot.t_in.max()
print(f"Bot : {len(bot)} trades, dernier le {lim}. Strat5669 : {len(st)} trades, dont {(st.t_in>lim).sum()} après le dernier trade du bot.")
print(f"Communs : {st.dans_bot.sum()} | seulement Strat5669 : {(~st.dans_bot).sum()} | seulement bot : {(~bot.dans_strat).sum()}")
def busy(t,other): return ((other.t_in<t)&(other.t_out>t)).any()
rows=[]
for r in st[~st.dans_bot].itertuples():
    day=bot[bot.day==r.day]; av=day[day.t_out<=r.t_in]
    pertes=0
    for p in av.sort_values("t_out").pnl: pertes = pertes+1 if p<0 else 0
    cause = "56 seul" if not r.god else "bot déjà en position" if busy(r.t_in,bot) else "stop trop loin (> 300 $ pour 1 micro)" if (not np.isnan(r.risk1) and r.risk1>300) else "coupe-circuit (2 pertes ou −400 $)" if (pertes>=2 or av.pnl.sum()<=-400) else "après 15:40 Chicago" if (r.t_in.hour*60+r.t_in.minute)>=22*60+35 else "inexpliqué"
    rows.append(dict(t=r.t_in,sens="L" if r.dir>0 else "S",god=r.god,cause=cause,risque_1_micro=None if np.isnan(r.risk1) else round(r.risk1),pnl_par_micro=round(r.pm),sortie=r.exit))
R=pd.DataFrame(rows)
print("\nTRADES PRIS PAR LA STRAT5669 ET PAS PAR LE BOT, par cause :")
print(R.groupby("cause").agg(n=("t","size"),gagnants=("pnl_par_micro",lambda x:(x>0).sum()),pnl_par_micro=("pnl_par_micro","sum")).to_string())
pd.set_option("display.width",220)
print("\nDétail hors « 56 seul » :"); print(R[R.cause!="56 seul"].to_string(index=False))
rows=[]
for r in bot[~bot.dans_strat].itertuples():
    o=st[(st.t_in<r.t_in)&(st.t_out>r.t_in)]
    rows.append(dict(t=r.t_in,sens="L" if r.dir>0 else "S",qty=r.qty,pnl=round(r.pnl),sortie=r.exit,cause=("Strat5669 déjà en position ("+("56 seul" if not o.god.iloc[0] else "GODLIKE")+f" du {o.t_in.iloc[0]:%d/%m %H:%M})") if len(o) else "inexpliqué"))
Rb=pd.DataFrame(rows)
print("\nTRADES PRIS PAR LE BOT ET PAS PAR LA STRAT5669 :"); print(Rb.to_string(index=False) if len(Rb) else "aucun")
print(f"\nBilan par micro sur les 90 jours : communs → Strat {st[st.dans_bot].pm.sum():+.0f} $ ; seulement Strat {st[~st.dans_bot].pm.sum():+.0f} $ (dont 56 seul {st[~st.dans_bot & ~st.god].pm.sum():+.0f} $) ; seulement bot {bot[~bot.dans_strat].pm.sum():+.0f} $")
print("Taille du bot :",bot.qty.value_counts().to_dict(),"| risque 1 micro médian des trades du bot :",round(bot.risk1.median()),"$ | max :",round(bot.risk1.max()))
