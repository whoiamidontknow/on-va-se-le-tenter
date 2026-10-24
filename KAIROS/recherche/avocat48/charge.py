import pandas as pd,glob,os
B=os.path.expanduser('~/Ephore/KAIROS-data/')
def files():
    return glob.glob(B+'slcourtoupas/*.xlsx')+glob.glob(B+'slcourtoupas/*/*.xlsx')
def preset(f):
    p=pd.read_excel(f,sheet_name='Propriétés');return str(p[p.iloc[:,0]=='Préréglage'].iloc[0,1])
def trades(f):
    d=pd.read_excel(f,sheet_name='Trades')
    d.columns=['n','type','dt','sig','px','qty','val','pnl','ret','com','mfe','mfep','mae','maep','cum','cump','bars']
    e=d[d.type.str.startswith('Entrer')].set_index('n');s=d[d.type.str.startswith('Sortir')].set_index('n')
    t=pd.DataFrame({'side':e.type.str.replace('Entrer ',''),'entry':pd.to_datetime(e.dt),'exit':pd.to_datetime(s.dt),'sig':e.sig,'reason':s.sig,'epx':e.px,'xpx':s.px,'pnl':e.pnl,'mfe':e.mfe,'mae':e.mae,'bars':s.bars,'qty':e.qty})
    return t.sort_index()
def load():
    out={}
    for f in files():
        k=preset(f).split()[0];out[k]=trades(f)
    return out
