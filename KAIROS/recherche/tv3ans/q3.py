import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/tv3ans")
from base import *
a=load(); m=a[(a.sym=='MNQ')&a.pre.isin(['38','39','40','42','43'])]
pd.set_option('display.width',250); pd.set_option('display.max_columns',30); pd.set_option('display.float_format','{:.2f}'.format)
def s(d): return pd.Series({'n':len(d),'%gag':100*(d.pnl>0).mean(),'PF':pf(d.pnl),'net':d.pnl.sum()})
y=m.groupby(['pre','annee'],observed=True).apply(s); print(y)
q=m[m.pre.isin(['38','39','40','42'])].groupby(['trim','pre']).apply(s)
print(q.PF.unstack().round(2)); print(q.net.unstack().round(0)); print(q.n.unstack())
