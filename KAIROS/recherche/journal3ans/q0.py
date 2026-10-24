import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/journal3ans")
from charge import *
import math
df=charge(); print(len(df)); print(df.head(3).T); print(df.isna().sum()[lambda x:x>0]); print(df.raison.value_counts()); print(df.qte.unique())
print(df.sig.iloc[0]); print(stats(df)); print(df.entree_t.min(),df.entree_t.max())
df.to_pickle('/private/tmp/claude-501/-Users-jeremk-Ephore/5255c912-f232-4044-9510-5af2888db584/scratchpad/j.pkl')
