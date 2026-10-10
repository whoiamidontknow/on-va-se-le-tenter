from sim_climax_base import *
import datetime
def feats(tf):
    B,T,ev=load(tf);N=len(B)
    O=[b['o'] for b in B];H=[b['h'] for b in B];L=[b['l'] for b in B];C=[b['c'] for b in B];V=[b['v'] for b in B]
    CR=[b['cr'] for b in B];HR=[b['hr'] for b in B];LR=[b['lr'] for b in B]
    tr=[H[0]-L[0]]+[max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1])) for i in range(1,N)]
    atr=rma(tr,14)
    trr=[HR[0]-LR[0]]+[max(HR[i]-LR[i],abs(HR[i]-CR[i-1]),abs(LR[i]-CR[i-1])) for i in range(1,N)]
    atrr=rma(trr,14)
    vs=[sum(V[i-19:i+1])/20 if i>=19 else None for i in range(N)]
    # rsi
    def rsi(x,p):
        up=[0]+[max(x[i]-x[i-1],0) for i in range(1,N)];dn=[0]+[max(x[i-1]-x[i],0) for i in range(1,N)]
        a=rma(up,p);b=rma(dn,p);return [None if a[i] is None else (100 if b[i]==0 else 100-100/(1+a[i]/b[i])) for i in range(N)]
    rs=rsi(C,14);rsr=rsi(CR,14)
    e50=ema(C,50);e20=ema(C,20)
    o4=[(O[i]+H[i]+L[i]+C[i])/4 for i in range(N)]; bull=[a>b for a,b in zip(ema(o4,4),ema(o4,32))]
    F=[]
    for i in range(N):
        f={}
        if i<30: F.append(None);continue
        rg=H[i]-L[i] or 1e-9
        f['body_atr']=(C[i]-O[i])/atr[i]
        f['body_rg']=(C[i]-O[i])/rg
        f['rg_atr']=rg/atr[i]
        f['vol_r']=V[i]/vs[i] if vs[i] else 0
        f['vol_r1']=V[i-1]/vs[i] if vs[i] else 0
        f['rsi']=rs[i]-50; f['rsir']=rsr[i]-50
        f['d50']=(C[i]-e50[i])/atr[i]; f['d20']=(C[i]-e20[i])/atr[i]
        f['bull']=1 if bull[i] else -1
        f['posr']=(CR[i]-LR[i])/((HR[i]-LR[i]) or 1e-9)*2-1
        f['retr']=(CR[i]-CR[i-1])/atrr[i]
        f['rgr']=(HR[i]-LR[i])/atrr[i]
        f['body1']=(C[i-1]-O[i-1])/atr[i]
        f['ret3']=(CR[i]-CR[i-3])/atrr[i]
        f['ret5']=(CR[i]-CR[i-5])/atrr[i]
        f['ret10']=(CR[i]-CR[i-10])/atrr[i]
        nwb=abs(O[i]-L[i])<1e-9; nws=abs(O[i]-H[i])<1e-9
        f['nw']=1 if nwb else (-1 if nws else 0)
        # streak of same HA color
        k=1
        while i-k>=0 and (C[i-k]>O[i-k])==(C[i]>O[i]): k+=1
        f['streak']=k
        F.append(f)
    return B,T,ev,F
