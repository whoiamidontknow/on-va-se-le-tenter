from sim_climax_feat import *
import itertools
S={}
for tf in('15m','2m'):
    B,T,ev,F=feats(tf)
    S[tf]=[(F[i],ev[T[i]][1]=='PREMIUM') for i in range(300,len(B)) if T[i] in ev and ev[T[i]][0]=='buy']
    print(tf,len(S[tf]),sum(p for _,p in S[tf]))
keys=['vol_r','vol_r1','body_rg','body_atr','rg_atr','rsi','d20','d50','body1','ret3','ret5','streak','posr','rgr','retr']
def best1(tf,k):
    xs=sorted(set(round(f[k],3) for f,_ in S[tf]));res=[]
    return xs
import math
for k in keys:
    out=[]
    for tf in S:
        vals=[(f[k],p) for f,p in S[tf]]
        # best threshold errors, oriented >=
        best=None
        for th,_ in vals:
            e=sum(1 for v,p in vals if (v>=th)!=p)
            if best is None or e<best[0]:best=(e,th)
        out.append(best)
    print(k,out)
