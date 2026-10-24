import pandas as pd,numpy as np
a=pd.read_pickle('/private/tmp/claude-501/-Users-jeremk-Ephore/5255c912-f232-4044-9510-5af2888db584/scratchpad/t.pkl')
m=a[a.sym=='MNQ']
print(m[m.pre=='40'].entree_t.dt.hour.value_counts().sort_index().to_dict())
print(m[m.pre=='40'].sortie_t.dt.hour.value_counts().sort_index().to_dict())
print(m[m.pre=='40'].groupby('raison').pnl.agg(['size','mean','sum']))
m=m.copy(); m['Rp']=(m.px_s-m.px_e).abs()
tp={'25':1,'38':1,'39':1.5,'40':1,'42':1,'43':None,'36':None}
st=m[m.raison.isin(['Stop L','Stop S'])&m.pre.isin(['25','38','39','40','42'])]
print(st.groupby('pre').Rp.describe())
g=st.groupby('entree_t').Rp.agg(['min','max','count']); g2=g[g['count']>1]; print(len(g2),(g2['max']-g2['min']).describe())
