import pickle, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
E=pickle.load(open("ex.pkl","rb")); rng=np.random.default_rng(7)
def Rs(sym,lim=20):
    b=E[sym]; g=b[b.god&(b.h<lim)]; return (g.pA/3).values
def sim(R,risk,n=20000,target=3000,dd=2000,maxtr=400):
    ok=0; nt=[]
    for _ in range(n):
        x=rng.choice(R,maxtr)*risk; eq=np.cumsum(x); peak=np.maximum.accumulate(np.maximum(eq,0)); floor=np.minimum(peak-dd,0)   # plancher suiveur, bloqué au solde de départ
        hit=np.argmax(eq>=target) if (eq>=target).any() else 10**9; bust=np.argmax(eq<=floor) if (eq<=floor).any() else 10**9
        if hit<bust: ok+=1; nt.append(hit+1)
    return ok/n, (np.median(nt) if nt else np.nan)
mnq=Rs("MNQ1!"); mes=Rs("MES1!"); mnq_all=Rs("MNQ1!",24)
print(f"R moyen : MNQ <20h {mnq.mean():+.3f} (n={len(mnq)}) | MNQ toutes heures {mnq_all.mean():+.3f} | MES <20h {mes.mean():+.3f}")
for lab,R in (("MNQ seul, sans entrée après 20h",mnq),("MNQ seul, toutes heures",mnq_all),("MNQ + MES, sans entrée après 20h",np.concatenate([mnq,mes])),("pile ou face (référence, 56 % à 0,667 R → 0)",np.where(rng.random(5000)<0.6,2/3,-1.0))):
    print(lab)
    for risk in (225,300,450,600):
        p,nt=sim(R,risk); print(f"   risque {risk} $ : éval validée {100*p:.0f} %  (médiane {nt:.0f} trades)")
