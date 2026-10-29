import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from feat import *
d=prep(); dv=d[d.dev]
print(len(dv),len(d)-len(dv)); print(stats(dv)); 
for c in ['s15','s60','s240','s1D','nT','nD','Fa','Ia','cA','diA','zz','eA','v','adx','nTrig']:
    print('\n',c); 
    x=dv[c]; 
    if x.nunique()>12: x=pd.qcut(x,8,duplicates='drop')
    g=dv.groupby(x,observed=True).apply(lambda q: pd.Series(stats(q)))
    print(g.round(2).to_string())
for c in ['h','dow','trig','sens']:
    print('\n',c); print(dv.groupby(c).apply(lambda q: pd.Series(stats(q))).round(2).to_string())
