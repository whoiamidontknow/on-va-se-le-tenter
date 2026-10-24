import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from moteur import *
from sklearn.tree import DecisionTreeClassifier, export_text
d=prep(); dv=d[d.dev].reset_index(drop=True)
dv['sem']=(dv.entree_t>=pd.Timestamp('2024-04-24')).astype(int)+(dv.entree_t>=pd.Timestamp('2024-10-24')).astype(int)+(dv.entree_t>=pd.Timestamp('2025-04-24')).astype(int)
C=conditions(dv); pnl=dv.pnl.values.astype(float)
def show(k):
    m=np.ones(len(dv),bool)
    for i in k: m&=C[i][1]
    st=stats(dv[m]); hs=[stats(dv[m&(dv['sem']==s).values]) for s in range(4)]
    return ' & '.join(C[i][0] for i in sorted(k,key=lambda i:C[i][0])),st,hs
for depth in (2,3,4):
    best,tried=beam(C,pnl,pnl>0,nmin=340,depth=depth,width=300,score='wilson',pfmin=1.0)
    print('\n## profondeur<=%d essais %d'%(depth,tried))
    seen=set();c=0
    for k,s in best:
        nm,st,hs=show(k)
        if nm in seen: continue
        seen.add(nm); c+=1
        print('%s | n%d win%.1f pf%.2f net%d | semestres win: %s pf: %s'%(nm,st['n'],st['win'],st['pf'],st['net'],'/'.join('%.0f'%h['win'] for h in hs),'/'.join('%.1f'%h['pf'] for h in hs)))
        if c>=10: break
# arbre
X=dv[FEATS].fillna(-99); y=(dv.pnl>0).astype(int)
for dp in (2,3):
    t=DecisionTreeClassifier(max_depth=dp,min_samples_leaf=300,random_state=0).fit(X,y)
    print(export_text(t,feature_names=FEATS,show_weights=True))
