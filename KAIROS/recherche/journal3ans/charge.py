"""Parse le journal 3 ans (preset 99) -> DataFrame, 1 ligne par trade."""
import pandas as pd, numpy as np, glob
J='/Users/jeremk/ERGON/KAIROS-data/dataset/Stratégie_V1_CME_MINI_MNQ1!_2026-10-17_ad887.xlsx'
D='/Users/jeremk/ERGON/KAIROS-data/'
def _f(x):
    try: return float(x)
    except: return np.nan
def parse(sig):
    p=sig.split('|'); r={}
    r['sens']=p[0]; r['trig']=p[1]
    for k in 'FIfEtdsaz':pass
    for q in p[2:]:
        if q.startswith('F'): r['F']=_f(q[1:])
        elif q.startswith('I'): r['I']=_f(q[1:])
        elif q.startswith('f'):
            a,b=q[1:].split('/'); r['feuL']=_f(a); r['feuS']=_f(b)
        elif q.startswith('t'):
            for i,u in enumerate(['3','5','15','60','240','1D']): r['t'+u]=int(q[1+i]) if q[1+i] in '01' else np.nan
        elif q.startswith('d'):
            for i,u in enumerate(['1','5','15','60','240','1D']): r['d'+u]=int(q[1+i]) if q[1+i] in '01' else np.nan
        elif q.startswith('s'):
            for i,u in enumerate(['15','60','240','1D']): r['s'+u]=_f(q[1+i])
        elif q.startswith('a'):
            r['adx']=_f(q[1:-1]); r['di']=1 if q[-1]=='+' else -1
        elif q.startswith('z'): r['z']=_f(q[1:])
        elif q.startswith('e'): r['e']=_f(q[1:])
        elif q.startswith('v'): r['v']=_f(q[1:])
        elif q.startswith('c'): r['c']=_f(q[1:])
        elif q.startswith('R'): r['R']=_f(q[1:])
    return r
def trades(f):
    t=pd.read_excel(f,sheet_name='Trades')
    e=t[t['Type'].str.startswith('Entrer')].set_index('Numéro de trade')
    s=t[t['Type'].str.startswith('Sortir')].set_index('Numéro de trade')
    df=pd.DataFrame({'entree_t':pd.to_datetime(e['Date et heure']),'sortie_t':pd.to_datetime(s['Date et heure']),
      'raison':s['Signal'],'pnl':s['P&L net USD'],'mfe':s['Excursion favorable USD'],'mae':s['Excursion adverse USD'],
      'barres':s['Durée (barres)'],'sig':e['Signal'],'qte':e['Taille (qté)']})
    return df
def charge():
    df=trades(J)
    P=pd.DataFrame([parse(s) for s in df.sig],index=df.index)
    df=pd.concat([df,P],axis=1)
    df['sens']=np.where(df.sens=='L',1,-1)  # écrase
    df['win']=(df.pnl>0).astype(int)
    df['h']=df.entree_t.dt.hour; df['dow']=df.entree_t.dt.dayofweek
    df['Rusd']=df.R*2.0*df.qte  # MNQ 2$/pt/micro? vérifié ailleurs
    return df
def stats(d,col='pnl'):
    if len(d)==0: return dict(n=0,win=np.nan,pf=np.nan,net=0)
    g=d[col][d[col]>0].sum(); l=-d[col][d[col]<0].sum()
    return dict(n=len(d),win=100*(d[col]>0).mean(),pf=g/l if l>0 else np.inf,net=d[col].sum())
