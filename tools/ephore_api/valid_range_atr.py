"""Validation INDEPENDANTE du garde-fou 'range >= k*ATR' sur les lots de CSV autres
que 'Base 10:10/Ajustements' : ~/Ephore/Singal (filtre OFF), ~/Ephore/Filtres (filtre ON).
Reimplemente la detection V8 a partir des primitives de tools/signator_sim.py
(ema/rma/load) pour pouvoir inserer le garde-fou avant comptage.
Usage : python3 valid_range_atr.py
"""
import sys, os, glob, math
sys.path.insert(0,'/Users/jeremk/ERGON/on-va-se-le-tenter/tools')
import signator_sim as S

def detect(d, use_filter, k):
    N=len(d['c']); O,H,L,C,V,T=d['o'],d['h'],d['l'],d['c'],d['v'],d['t']
    tf=S.tf_seconds(T)
    o4=[(O[i]+H[i]+L[i]+C[i])/4 for i in range(N)]
    bull=[a>b for a,b in zip(S.ema(o4,4),S.ema(o4,32))]
    run=[1]*N
    for i in range(1,N): run[i]=run[i-1]+1 if bull[i]==bull[i-1] else 1
    tr=[H[0]-L[0]]+[max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1])) for i in range(1,N)]
    up=[0]+[max(H[i]-H[i-1],0) if H[i]-H[i-1]>L[i-1]-L[i] else 0 for i in range(1,N)]
    dn=[0]+[max(L[i-1]-L[i],0) if L[i-1]-L[i]>H[i]-H[i-1] else 0 for i in range(1,N)]
    atr,pu,pd=S.rma(tr,14),S.rma(up,14),S.rma(dn,14)
    dx=[None if pu[i] is None else (abs(pu[i]-pd[i])/(pu[i]+pd[i])*100 if pu[i]+pd[i]>0 else 0) for i in range(N)]
    adx=S.rma(dx,14)
    m1,m2=d.get('m1') or [],d.get('m2') or []
    ok=(len(m1)==N and sum(1 for v in m1 if v and not math.isnan(v))>N*0.9)
    if ok:
        e50=[v if v and not math.isnan(v) else None for v in m1]
        e60=[v if v and not math.isnan(v) else None for v in m2]
    else: e50,e60=S.ema(C,50),S.ema(C,60)
    vma=S.sma_n(V,20)
    def news(i):
        if not use_filter: return False
        for hh,mm in S.NEWS_HHMM:
            tn=T[i].replace(hour=int(hh),minute=int(mm),second=0,microsecond=0)
            if 0<=(tn-T[i]).total_seconds()<tf: return True
        return False
    res=[]
    for i in range(S.WARMUP,N):
        b=bull[i]; ours=False
        if (run[i]==2 and adx[i] is not None and adx[i]>=S.ADX_MIN and e50[i] and e60[i]
                and ((C[i]>e50[i]) if b else (C[i]<e50[i])) and not news(i)):
            db=((C[i]-max(e50[i],e60[i])) if b else (min(e50[i],e60[i])-C[i]))/atr[i]
            if db>=0.3 or (vma[i] is not None and V[i]>=vma[i]):
                ours = (k is None) or (atr[i] and (H[i]-L[i])>=k*atr[i])
        orig = d['oL'][i] or d['oS'][i] or d['oLM'][i] or d['oSM'][i]
        res.append((i,ours,orig,T[i],(H[i]-L[i])/atr[i] if atr[i] else None))
    return res

def lot(root,use_filter):
    print('\n=== %s  (filtre %s) ==='%(root,'ON' if use_filter else 'OFF'))
    files=sorted(glob.glob(os.path.join(os.path.expanduser(root),'*.csv')))
    cache={}
    for f in files:
        d=S.load(f)
        if d: cache[f]=d
    print('%-6s %8s %6s %6s'%('k','exactes','trop','manq'))
    for k in (None,0.40,0.45,0.50,0.55,0.60):
        TP=FP=FN=0; perdus=[]
        for f,d in cache.items():
            base=detect(d,use_filter,None); test=detect(d,use_filter,k)
            for (i,ob,orig,t,r),(i2,ot,_,_,_) in zip(base,test):
                if ot and orig: TP+=1
                elif ot: FP+=1
                elif orig: FN+=1
                if ob and orig and not ot: perdus.append((os.path.basename(f)[:24],str(t)[:16],r))
        print('%-6s %8d %6d %6d   (%d vraies fleches perdues par le garde-fou)'%(str(k),TP,FP,FN,len(perdus)))
        if k==0.50 and perdus:
            for p in perdus[:6]: print('      perdue:',p[0],p[1],'range/ATR=%.2f'%p[2])

if __name__=='__main__':
    lot('~/Ephore/Singal',False)
    lot('~/Ephore/Filtres',True)
