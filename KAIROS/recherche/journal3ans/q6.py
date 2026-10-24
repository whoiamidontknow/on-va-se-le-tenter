import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from feat import *; from filtres import *
d=prep(); dv=d[d.dev].copy()
def row(nm,m):
    s=stats(dv[m]); y=[stats(dv[m&(dv.year==k)]) for k in (1,2)]
    print('%-46s n%4d win%5.1f pf%5.2f net%6d | a1 %5.1f/%4.2f a2 %5.1f/%4.2f'%(nm,s['n'],s['win'],s['pf'],s['net'],y[0]['win'],y[0]['pf'],y[1]['win'],y[1]['pf']))
b=(dv.dA60==1)&(dv.dA240==1)
row('tout',dv.F.notna()); row('f44',dv.index.isin(f44(dv).index)); row('f40',dv.index.isin(f40(dv).index))
row('dA60',dv.dA60==1); row('dA240',dv.dA240==1); row('dA60&dA240',b)
row('dA60&dA240&dA15',b&(dv.dA15==1)); row('dA60&dA240&dA1D',b&(dv.dA1D==1))
for x in [-1,-0.5,0,0.3,0.6,0.9,1.2,1.5,1.8,2.4,3]: row(f'b & eA<={x}',b&(dv.eA<=x))
for x in [0.3,1,1.5,2]: row(f'b & eA<=0.9 & zz>={x}',b&(dv.eA<=0.9)&(dv.zz>=x))
row('b&eA<=.9 sens L',b&(dv.eA<=.9)&(dv.sens==1)); row('b&eA<=.9 sens S',b&(dv.eA<=.9)&(dv.sens==-1))
row('b&eA<=.9&~D',b&(dv.eA<=.9)&(dv.g_D==0))
row('b&eA<=.9 & f44',b&(dv.eA<=.9)&dv.index.isin(f44(dv).index))
row('b&eA<=.9 & ~hour 8-9',b&(dv.eA<=.9)&~dv.h.isin([8,9]))
row('b&eA<=.9 & ~hour 10',b&(dv.eA<=.9)&~dv.h.isin([10]))
print(dv[b&(dv.eA<=.9)].groupby('raison').size())
