import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from gestion import *; from filtres import *
d=prep(); dv=d[d.dev]
print('commission mediane',commission(d))
rules={'R*: dA60&dA240&eA<=0.6':(dv.dA60==1)&(dv.dA240==1)&(dv.eA<=0.6),'Alt eA<=0.9':(dv.dA60==1)&(dv.dA240==1)&(dv.eA<=0.9),
 'f44':dv.index.isin(f44(dv).index)}
for k,m in rules.items():
    q=dv[m]; pe,ok,amb=borne_075(q)
    print(k,'actuel',{a:round(b,1) for a,b in st(q.pnl).items()},'\n   0.75R prudent',{a:round(b,1) for a,b in st(pe).items()},'\n   0.75R optimiste',{a:round(b,1) for a,b in st(ok).items()},'ambigus',amb.sum())
