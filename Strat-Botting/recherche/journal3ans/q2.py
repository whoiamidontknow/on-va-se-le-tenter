import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/journal3ans")
from charge import *; from filtres import *
import glob
df=pd.read_pickle('/private/tmp/claude-501/-Users-jeremk-Ephore/5255c912-f232-4044-9510-5af2888db584/scratchpad/j.pkl')
r40=trades(D+'Stratégie_V1_CME_MINI_MNQ1!_2026-10-17_a413e.xlsx')
r40['sens']=np.where(r40.raison.str.endswith('L'),1,-1) if False else np.nan
r40['h']=r40.entree_t.dt.hour
print('vrai 40',stats(r40)); r44=r40[~r40.h.isin([8,9])]; print('vrai 44 (40 sans 8-10h, 4 micros)',stats(r44), 'net/2',stats(r44)['net']/2)
j40=f40(df); j44=f44(df); print('journal 40',stats(j40)); print('journal 44',stats(j44))
# appariement par heure d'entrée (+ sens via raison ... on utilise pnl signe seulement) 
k_r=set(r40.entree_t); k_j=set(j40.entree_t)
print('instants vrai40',len(k_r),'journal40',len(k_j),'communs',len(k_r&k_j))
m=j40.merge(r40[['entree_t','pnl','raison']],on='entree_t',suffixes=('','_r'))
print('communs: même issue win',((m.pnl>0)==(m.pnl_r>0)).mean(), 'raison id',(m.raison==m.raison_r).mean(), len(m))
print('communs stats journal',stats(m),'; vrai',stats(m.assign(pnl=m.pnl_r)))
only_r=r40[~r40.entree_t.isin(k_j)]; only_j=j40[~j40.entree_t.isin(k_r)]
print('seulement vrai40',stats(only_r)); print('seulement journal',stats(only_j))
# chevauchement : seuls-journal tombent dans un trade du vrai 40 ?
