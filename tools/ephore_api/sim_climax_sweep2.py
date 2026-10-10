from sim_climax_feat import *
import itertools
D={}
for tf in('15m','2m'):
    B,T,ev,F=feats(tf);N=len(B)
    V=[b['v'] for b in B]
    O=[b['o'] for b in B];H=[b['h'] for b in B];L=[b['l'] for b in B];C=[b['c'] for b in B]
    vr={}
    for n in (10,14,20,30,50):
        for kind in('sma','ema','smaprev'):
            if kind=='sma': r=[V[i]/(sum(V[i-n+1:i+1])/n) if i>=n else 0 for i in range(N)]
            elif kind=='ema':
                e=ema(V,n);r=[V[i]/e[i] for i in range(N)]
            else: r=[V[i]/(sum(V[i-n:i])/n) if i>=n else 0 for i in range(N)]
            vr[(n,kind)]=r
    D[tf]=(B,T,ev,F,vr)
def score(tf,vk,k,br):
    B,T,ev,F,vr=D[tf];tp=fp=fn=0;v=vr[vk]
    for i in range(300,len(B)):
        f=F[i];e=ev.get(T[i]);o=e[0] if e else None
        r=None
        if f['nw']!=0 and v[i]>=k and abs(f['body_rg'])>=br: r='buy' if f['nw']==1 else 'sell'
        if r and r==o: tp+=1
        elif r: fp+=1
        elif o: fn+=1
    return tp,fp,fn
if __name__=='__main__':
    res=[];n=0
    for vk in D['15m'][4]:
        for k in [1.2+0.1*j for j in range(0,12)]:
            for br in [0.4+0.025*j for j in range(0,10)]:
                a=score('15m',vk,k,br);b=score('2m',vk,k,br);n+=1
                res.append((a[1]+a[2]+b[1]+b[2],vk,round(k,2),round(br,3),a,b))
    res.sort(key=lambda x:x[0]);print(n,'combos')
    for r in res[:12]:print(r)
