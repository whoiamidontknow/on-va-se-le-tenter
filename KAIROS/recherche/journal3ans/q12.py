import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from feat import *; from filtres import *; from regles_figees import *
d=prep(); q=d[R_star(d)].copy()
rng=np.random.default_rng(1)
t=q[~q.dev]; w=(t.pnl>0).values
bs=[rng.choice(w,len(w)).mean()*100 for _ in range(5000)]; print('test win IC95',np.percentile(bs,[2.5,97.5]).round(1))
pf=lambda x:(x[x>0].sum()/-x[x<0].sum())
p=t.pnl.values; bp=[pf(rng.choice(p,len(p))) for _ in range(5000)]; print('test PF IC95',np.percentile(bp,[2.5,97.5]).round(2))
q['trim']=q.entree_t.dt.to_period('Q'); print(q.groupby('trim').apply(lambda x: pd.Series(stats(x))).round(1).to_string())
print('sens (test)',t.groupby('sens').apply(lambda x: pd.Series(stats(x))).round(1).to_string())
print('R pts moy %.1f med %.1f max %.1f ; Rusd moy %.0f max %.0f ; pire MAE$ %.0f ; pire perte %.0f'%(q.R.mean(),q.R.median(),q.R.max(),q.Rusd.mean(),q.Rusd.max(),q.mae.min(),q.pnl.min()))
print('trades/semaine',len(q)/ (3*52))
print('heures',q.groupby('h').size().to_dict()); print('raisons',q.raison.value_counts().to_dict())
print('jour',q.groupby('dow').apply(lambda x: pd.Series(stats(x))).round(1)[['n','win','pf']].to_string())
dv=d[d.dev]; te=d[~d.dev]
for nm,f in [('dA240',lambda x:x.dA240==1),('dA60&dA240',lambda x:(x.dA60==1)&(x.dA240==1)),('dA240&e<=0.6',R_simple),('R*',R_star)]:
    print(nm,'dev',{k:round(v,2) for k,v in stats(dv[f(dv)]).items()},'test',{k:round(v,2) for k,v in stats(te[f(te)]).items()})
# R* trades chevauchant 44 ?
f=set(f44(d).index); print('part de R* dans filtre44',np.mean([i in f for i in q.index]))
# ratio blocage : R* journal vs réel : nombre de signaux R* masqués (pendant un trade du journal)
