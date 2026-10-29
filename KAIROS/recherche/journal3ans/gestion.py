import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from feat import *
def commission(d):
    o=d[d.raison.str.startswith('Obj')]
    return 5.0
def borne_075(q,T=0.75):
    """Retourne (pnl_prudent, pnl_optimiste) par trade pour un objectif T<1 R. Stop = -1R."""
    c=commission(q); g=q.pnl+c; R=q.Rusd
    hit=(q.mfeR>=T-1e-9); stopt=(q.maeR<=-1+1e-9)|q.raison.str.startswith('Stop')
    ambiguous=hit&stopt
    orig=g
    new_ok=np.where(hit&~stopt,T*R,np.where(ambiguous,T*R,orig))   # optimiste
    new_pe=np.where(hit&~stopt,T*R,np.where(ambiguous,-R,orig))     # prudent
    return pd.Series(new_pe-c,index=q.index),pd.Series(new_ok-c,index=q.index),ambiguous
def st(x):
    g=x[x>0].sum();l=-x[x<0].sum(); return dict(n=len(x),win=100*(x>0).mean(),pf=g/l if l else np.inf,net=x.sum())
