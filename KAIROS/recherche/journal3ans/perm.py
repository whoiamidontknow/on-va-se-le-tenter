import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from moteur import *
import multiprocessing as mp, time
d=prep(); dv=d[d.dev].reset_index(drop=True)
C=conditions(dv)
pnl0=dv.pnl.values.astype(float)
NMIN=340
def run(seed):
    rng=np.random.default_rng(seed)
    if seed==0: p=pnl0
    else:
        # permutation par blocs de 5 jours pour garder l'autocorrélation : on permute les pnl entre trades (global)
        p=rng.permutation(pnl0)
    best,tried=beam(C,p,p>0,nmin=NMIN,score='wilson',pfmin=1.0)
    k,s=best[0]
    m=np.ones(len(p),bool)
    for i in k: m&=C[i][1]
    return seed,s,100*(p[m]>0).mean(),int(m.sum()),tried
if __name__=='__main__':
    t=time.time()
    with mp.Pool(8) as pool:
        res=pool.map(run,range(0,501))
    r0=res[0]; nul=np.array([r[1] for r in res[1:]]); wn=np.array([r[2] for r in res[1:]])
    print('réel: wilson %.3f win %.1f n %d essais %d'%(r0[1],r0[2],r0[3],r0[4]))
    print('nul (500 perm): wilson max moy %.3f max %.3f ; win%% moyen du meilleur %.1f max %.1f'%(nul.mean(),nul.max(),wn.mean(),wn.max()))
    print('p-valeur', (np.sum(nul>=r0[1])+1)/(len(nul)+1), 'temps',time.time()-t)
