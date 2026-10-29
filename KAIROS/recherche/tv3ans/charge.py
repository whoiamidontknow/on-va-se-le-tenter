"""Charge les exports TradingView 3 ans -> un DataFrame de trades (1 ligne par trade)."""
import pandas as pd, glob, re, numpy as np
D='/Users/jeremk/ERGON/KAIROS-data/'
def charge():
    out=[]
    for f in sorted(glob.glob(D+'*.xlsx')):
        x=pd.ExcelFile(f)
        p=x.parse('Propriétés',header=None); d=dict(zip(p[0].astype(str),p[1].astype(str)))
        pre=d['Préréglage'][:2]; sym='MNQ' if 'MNQ' in d['Symbole'] else 'MES'
        t=x.parse('Trades')
        e=t[t['Type'].str.startswith('Entrer')].set_index('Numéro de trade')
        s=t[t['Type'].str.startswith('Sortir')].set_index('Numéro de trade')
        df=pd.DataFrame({'sens':np.where(e['Type'].str.contains('long'),'L','S'),
          'entree_t':pd.to_datetime(e['Date et heure']),'sortie_t':pd.to_datetime(s['Date et heure']),
          'px_e':e['Prix USD'],'px_s':s['Prix USD'],'qte':e['Taille (qté)'],'raison':s['Signal'],
          'pnl':s['P&L net USD'],'mfe':s['Excursion favorable USD'],'mae':s['Excursion adverse USD'],
          'barres':s['Durée (barres)'],'sig_e':e['Signal'],'comm':s['Commission USD']+e['Commission USD']})
        df['pre']=pre; df['sym']=sym; df['file']=f[-9:-5]
        out.append(df.reset_index())
    return pd.concat(out,ignore_index=True)
if __name__=='__main__':
    a=charge(); a.to_pickle('/private/tmp/claude-501/-Users-jeremk-Ephore/5255c912-f232-4044-9510-5af2888db584/scratchpad/t.pkl')
    print(a.groupby(['sym','pre']).agg(n=('pnl','size'),net=('pnl','sum')))
    m=a[(a.sym=='MNQ')&(a.pre=='40')]; print(m.head(8).T); print(m.raison.value_counts()); print(m.sig_e.value_counts().head(8))
