import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/tv3ans")
from base import *
a=load(); m=a[(a.sym=='MNQ')]
pd.set_option('display.width',250); pd.set_option('display.max_columns',40); pd.set_option('display.float_format','{:.2f}'.format); pd.set_option('display.max_rows',200)
def tab(p,col):
    x=m[m.pre==p]
    r=x.groupby(col).pnl.agg(n='size',net='sum')
    r['PF']=x.groupby(col).pnl.apply(pf)
    for y in ['2023-24','2024-25','2025-26']:
        r['net_'+y[2:4]+y[-2:]]=x[x.annee==y].groupby(col).pnl.sum()
    r['PF_a1']=x[x.annee=='2023-24'].groupby(col).pnl.apply(pf);r['PF_a2']=x[x.annee=='2024-25'].groupby(col).pnl.apply(pf);r['PF_a3']=x[x.annee=='2025-26'].groupby(col).pnl.apply(pf)
    return r.fillna(0)
for p in ['40']:
    print('HEURE',p);print(tab(p,'heure'))
    print('JOUR',p);print(tab(p,'jour'))
    print('RAISON',p);print(tab(p,'raison'))
# heure : tranches regroupees confirmees par 38 et 42
for p in ['38','42']:
    print('HEURE',p); print(tab(p,'heure')[['n','net','PF','PF_a1','PF_a2','PF_a3']])
    print('JOUR',p); print(tab(p,'jour')[['n','net','PF','PF_a1','PF_a2','PF_a3']])
