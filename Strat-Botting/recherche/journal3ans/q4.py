import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/journal3ans")
from moteur import *
d=prep(); dv=d[d.dev].reset_index(drop=True)
C=conditions(dv); print(len(C),'conditions')
pnl=dv.pnl.values.astype(float); win=(pnl>0)
for sc in ['wilson','pf','net']:
  best,tried=beam(C,pnl,win,nmin=400,score=sc,pfmin=1.15 if sc!='pf' else 1.0)
  print('\n==',sc,'essais',tried)
  seen=0
  for k,s in best[:12]:
    m=np.ones(len(dv),bool)
    for i in k: m&=C[i][1]
    st=stats(dv[m]); ys=[stats(dv[m&(dv.year==y).values]) for y in (1,2)]
    print(' & '.join(C[i][0] for i in k),'| n%d win%.1f pf%.2f net%d'%(st['n'],st['win'],st['pf'],st['net']),'| y1 %.1f/%.2f y2 %.1f/%.2f'%(ys[0]['win'],ys[0]['pf'],ys[1]['win'],ys[1]['pf']))
