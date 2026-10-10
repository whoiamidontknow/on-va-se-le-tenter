# hypothese: regle sur bougies reelles (cr/hr/lr) au lieu de HA
from sim_climax_feat import *
best=None;n=0
for tf in('15m','2m'): pass
D={tf:feats(tf) for tf in('15m','2m')}
def err(pg,k,sg):
    e=0
    for tf in D:
        B,T,ev,F=D[tf]
        for i in range(300,len(B)):
            f=F[i];p=(f['posr']+1)/2;r=None
            if f['vol_r']>=k:
                if p>=pg:r='buy'
                elif p<=1-pg:r='sell'
            o=ev.get(T[i]);o=o[0] if o else None
            e+= (r!=o)
    return e
for pg in (.6,.7,.8,.9,.95):
    for k in (1.5,2,2.5):
        n+=1;e=err(pg,k,0)
        if best is None or e<best[0]:best=(e,pg,k)
print(n,'combos, meilleure regle reelle (erreurs totales sur 155 evts):',best)
