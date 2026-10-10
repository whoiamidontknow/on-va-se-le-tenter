from sim_climax_feat import *
import random
def rows(tf,keys):
    B,T,ev,F=feats(tf);X=[];Y=[];I=[]
    for i in range(300,len(B)):
        f=F[i]
        if f['nw']==0: continue
        s=f['nw'];sg='buy' if s==1 else 'sell'
        g=dict(f)
        for k in('body_atr','body_rg','rsi','rsir','d50','d20','posr','retr','body1','ret3','ret5','ret10','bull'): g[k]=f[k]*s
        g['lvol']=math.log(max(f['vol_r'],1e-3));g['lvol1']=math.log(max(f['vol_r1'],1e-3))
        g['sell']=1 if s==-1 else 0
        e=ev.get(T[i]);X.append([g[k] for k in keys]);Y.append(1 if e and e[0]==sg else 0);I.append(i)
    return X,Y,I
def fit(X,Y,it=4000,lr=0.1):
    m=len(X[0]);mu=[sum(x[j] for x in X)/len(X) for j in range(m)];sd=[(sum((x[j]-mu[j])**2 for x in X)/len(X))**.5 or 1 for j in range(m)]
    Z=[[(x[j]-mu[j])/sd[j] for j in range(m)] for x in X];w=[0]*m;b=0
    for _ in range(it):
        gw=[0]*m;gb=0
        for z,y in zip(Z,Y):
            p=1/(1+math.exp(-max(-30,min(30,b+sum(a*c for a,c in zip(w,z))))));e=p-y
            for j in range(m):gw[j]+=e*z[j]
            gb+=e
        w=[a-lr*g/len(Z) for a,g in zip(w,gw)];b-=lr*gb/len(Z)
    return w,b,mu,sd
def pred(model,X):
    w,b,mu,sd=model
    return [b+sum(a*(x[j]-mu[j])/sd[j] for j,a in enumerate(w))>0 for x in X]
def ev_(p,Y,ntot):
    tp=sum(1 for a,y in zip(p,Y) if a and y);fp=sum(1 for a,y in zip(p,Y) if a and not y);fn=sum(Y)-tp
    return tp,fp,fn
if __name__=='__main__':
    keys=['lvol','body_rg','body_atr','rg_atr','rsi','d20','body1','ret3','lvol1']
    A=rows('15m',keys);Bb=rows('2m',keys)
    for name,tr,te in(('15->2',A,Bb),('2->15',Bb,A)):
        m=fit(tr[0],tr[1]);print(name,'train',ev_(pred(m,tr[0]),tr[1],0),'test',ev_(pred(m,te[0]),te[1],0),[round(x,2) for x in m[0]])
