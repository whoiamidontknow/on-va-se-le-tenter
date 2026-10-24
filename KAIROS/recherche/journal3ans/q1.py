import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/journal3ans")
from charge import *
import glob, pandas as pd, math
for f in sorted(glob.glob(D+'*MNQ1!*.xlsx'))+[J]:
    p=pd.read_excel(f,sheet_name='Propriétés',header=None); d=dict(zip(p[0].astype(str),p[1].astype(str)))
    t=trades(f); print(f[-9:-5], d['Préréglage'][:60], len(t), t.qte.unique(), t.entree_t.min(), stats(t))
