import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/KAIROS/recherche/tv3ans")
from base import *
a=load(); m=a[(a.sym=='MNQ')]
pd.set_option('display.width',250); pd.set_option('display.float_format','{:.2f}'.format)
rows=[]
for p in ['38','39','40','42','43']:
    for lab,msk in [('toutes',m.heure>=0),('sans 8-10h',~m.heure.isin([8,9])),('sans 8-10h et 15h',~m.heure.isin([8,9,15]))]:
        for y in ['2023-24','2024-25','2025-26','tout']:
            x=m[(m.pre==p)&msk&((m.annee==y)|(y=='tout'))]
            rows.append((p,lab,y,len(x),pf(x.pnl),x.pnl.sum()))
r=pd.DataFrame(rows,columns=['pre','filtre','periode','n','PF','net'])
print(r.pivot_table(index=['pre','filtre'],columns='periode',values=['PF','net','n']))
# MES check same hours
x=a[(a.sym=='MES')&a.heure.isin([8,9])].groupby('pre').pnl.agg(['size','sum']); print('MES 8-10h',x)
# 8-10h par sens pour 40
x=m[(m.pre=='40')&m.heure.isin([8,9])]; print(x.groupby('sens').pnl.agg(['size','sum']), x.groupby('raison').pnl.agg(['size','sum']))
