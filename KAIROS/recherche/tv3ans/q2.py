import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/tv3ans")
from base import *
a=load(); m=a[(a.sym=='MNQ')&a.pre.isin(['38','39','40','42'])]
def s(d): 
    return pd.Series({'n':len(d),'%gag':100*(d.pnl>0).mean(),'PF':pf(d.pnl),'net':d.pnl.sum(),'$/trade':d.pnl.mean(),'R_moy':d.pnl_R.mean(),
      'MAE_moy_R':d.mae_R.mean(),'MAE>=.8':(d.mae_R>=.8).mean()*100,'MAE>=.5':(d.mae_R>=.5).mean()*100,'R_pts_med':d.R.median(),'stop%':100*d.raison.str.startswith('Stop').mean(),'obj%':100*d.raison.str.startswith('Obj').mean(),'tps%':100*d.raison.str.startswith('Temps').mean()})
pd.set_option('display.width',250); pd.set_option('display.max_columns',30); pd.set_option('display.float_format','{:.2f}'.format)
print(m.groupby(['pre','sens']).apply(s))
# MAE des gagnants seulement (a quel point frolent-ils le stop)
w=m[m.pnl>0]; print(w.groupby(['pre','sens']).apply(lambda d:pd.Series({'n':len(d),'MAE_moy_R':d.mae_R.mean(),'MAE>=.8':(d.mae_R>=.8).mean()*100})))
print(m[m.pre=='40'].groupby(['annee','sens'],observed=True).apply(s)[['n','%gag','PF','net','R_moy']])
print(m[m.pre=='42'].groupby(['annee','sens'],observed=True).apply(s)[['n','%gag','PF','net','R_moy']])
print(m[m.pre=='38'].groupby(['annee','sens'],observed=True).apply(s)[['n','%gag','PF','net','R_moy']])
# shorts par heure / vol
x=m[m.pre=='40']; print(x.groupby('sens').R.describe())
