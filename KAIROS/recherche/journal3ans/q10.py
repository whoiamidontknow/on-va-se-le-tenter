import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from feat import *; from filtres import *; from regles_figees import *
d=prep()
def ddmax(p):
    e=np.concatenate([[0],np.cumsum(p)]); return float((np.maximum.accumulate(e)-e).max())
def line(nm,q,scale=1.0):
    s=stats(q); return '%-34s n%5d  gagn %5.1f%%  PF %5.2f  net %8.0f  DD %6.0f'%(nm,s['n'],s['win'],s['pf'],s['net']*scale,ddmax(q.pnl.values)*scale)
r40=trades(D+'Stratégie_V1_CME_MINI_MNQ1!_2026-10-17_a413e.xlsx'); r40['h']=r40.entree_t.dt.hour
r44=r40[~r40.h.isin([8,9])]
sets={'journal tout':d, 'journal filtre 44':d.loc[f44(d).index], 'journal filtre 40':d.loc[f40(d).index],
      'journal R*':d[R_star(d)],'journal Alt (eA<=1.5)':d[R_alt(d)],'journal R2 (dA240&eA<=0.6)':d[R_simple(d)]}
real={'VRAI 40 (4 micros ->2)':(r40,0.5),'VRAI 44 = 40 sans 8-10h (4->2)':(r44,0.5)}
periods={'DEV 24/10/23-23/10/25':lambda x:x.entree_t<CUT,'TEST 24/10/25-16/10/26':lambda x:x.entree_t>=CUT,'An1 23-24':lambda x:x.entree_t<pd.Timestamp('2024-10-24'),
 'An2 24-25':lambda x:(x.entree_t>=pd.Timestamp('2024-10-24'))&(x.entree_t<CUT),'An3 25-26 (TEST)':lambda x:x.entree_t>=CUT,'TOTAL 3 ans':lambda x:x.entree_t>=pd.Timestamp('2000-01-01')}
for pn,pf in periods.items():
    print('\n##',pn)
    for k,q in sets.items(): print(line(k,q[pf(q)]))
    for k,(q,sc) in real.items(): print(line(k,q[pf(q)],sc))
