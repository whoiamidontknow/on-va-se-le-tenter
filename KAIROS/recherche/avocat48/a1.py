import sys;sys.path.insert(0,'.')
import charge as c, pandas as pd, numpy as np, glob
fs={}
for f in c.files():
    p=c.preset(f);k=p.split()[0]
    if k=='45' and '4eb81' not in f: 
        T=c.trades(f);continue
    fs[k]=c.trades(f)
D={k:fs[k] for k in ['45','47','48','49','50']}
# is the other 45 identical
t45b=T
print('45 dup identical',t45b.pnl.equals(D['45'].pnl) if len(t45b)==len(D['45']) else ('diff len',len(t45b)))
def pf(x): return x[x>0].sum()/-x[x<0].sum()
def key(t): return t.entry.astype(str)+t.side
for k,t in D.items(): t['key']=key(t)
rng=np.random.default_rng(1)
print('== Q1')
rows=[];diffs={}
base=D['45'].set_index('key')
for k in ['47','48','49','50']:
    o=D[k].set_index('key');common=base.index.intersection(o.index)
    d=(o.loc[common,'pnl']-base.loc[common,'pnl']).values;diffs[k]=(common,d)
    n=len(d);bs=np.array([d[rng.integers(0,n,n)].sum() for _ in range(5000)])
    # total difference incl unmatched
    tot=o.pnl.sum()-base.pnl.sum()
    ch=(d!=0).sum()
    print(k,'common',n,'only45',len(base.index.difference(o.index)),'onlyk',len(o.index.difference(base.index)),'sum diff common',d.sum(),'nb diff trades',ch,'CI95',np.percentile(bs,[2.5,97.5]).round(0),'p(<=0)',(bs<=0).mean(),'total diff',tot)
# selection: max over 4 of centered bootstrap, common to all
com=base.index
for k in ['47','48','49','50']: com=com.intersection(D[k].set_index('key').index)
M=np.array([ (D[k].set_index('key').loc[com,'pnl']-base.loc[com,'pnl']).values for k in ['47','48','49','50']])
n=M.shape[1];obs=M.sum(1);cen=M-M.mean(1,keepdims=True)
mx=[]
for _ in range(5000):
    i=rng.integers(0,n,n);mx.append(cen[:,i].sum(1).max())
print('common to all',n,'obs sums',obs,'p max under H0',(np.array(mx)>=obs.max()).mean())
# 48 vs 50, 48 vs 47 
for a,b in [('48','50'),('48','47'),('48','49')]:
    A=D[a].set_index('key');B=D[b].set_index('key');cm=A.index.intersection(B.index)
    d=(A.loc[cm,'pnl']-B.loc[cm,'pnl']).values;bs=np.array([d[rng.integers(0,len(d),len(d))].sum() for _ in range(5000)])
    print(a,'vs',b,d.sum(),np.percentile(bs,[2.5,97.5]).round(0),(bs<=0).mean())
# stats table
print('table')
for k,t in D.items():
    print(k,len(t),round((t.pnl>0).mean()*100,1),round(pf(t.pnl),2),t.pnl.sum(),t.pnl.mean().round(1))
# by year / quarter / side, 48 minus 45 on common
common=diffs['48'][0];d=pd.Series(diffs['48'][1],index=common)
e=base.loc[common];e['d']=d.values
e['yr']=np.where(e.entry<'2024-10-25','Y1 oct23-oct24',np.where(e.entry<'2025-10-25','Y2 oct24-oct25','Y3 oct25-oct26'))
e['q']=e.entry.dt.to_period('Q')
print(e.groupby('yr').d.agg(['sum','count']))
print(e.groupby('side').d.agg(['sum','count']))
qs=e.groupby('q').d.agg(['sum','count']);print(qs.T.to_string());print('quarters positive',(qs['sum']>0).sum(),'of',len(qs),'neg',(qs['sum']<0).sum())
# sums of totals per year for 45, 48 full sets
for k in ['45','48']:
    t=D[k];t['yr']=np.where(t.entry<'2024-10-25','Y1',np.where(t.entry<'2025-10-25','Y2','Y3'))
    print(k,t.groupby('yr').pnl.agg(['sum','count',lambda x:(x>0).mean(),pf]).round(2).to_string())
# changed trades detail
ch=e[e.d!=0]; print('changed trades by 45 reason',ch.reason.value_counts().to_dict(),'sum',ch.d.sum()); 
print('48 outcome of trades that 45 stopped', D['48'].set_index('key').loc[e[e.reason.str.startswith('Stop')].index,'reason'].value_counts().to_dict())
print('d for those',e[e.reason.str.startswith('Stop')].d.sum(), 'd others',e[~e.reason.str.startswith('Stop')].d.sum())
