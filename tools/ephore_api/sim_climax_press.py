from sim_climax_feat import *
def pressures(B):
    N=len(B);V=[b['v'] for b in B]
    out={}
    for src in('ha','real'):
        if src=='ha': O=[b['o'] for b in B];H=[b['h'] for b in B];L=[b['l'] for b in B];C=[b['c'] for b in B]
        else: H=[b['hr'] for b in B];L=[b['lr'] for b in B];C=[b['cr'] for b in B];O=[None]*N
        pos=[(C[i]-L[i])/(H[i]-L[i]) if H[i]>L[i] else .5 for i in range(N)]
        for p in (5,14):
            for kind in('mfi','ratio'):
                for sm in('rma','ema','sma'):
                    def S(x):
                        if sm=='rma': return rma(x,p)
                        if sm=='ema': return ema(x,p)
                        return [None if i<p-1 else sum(x[i-p+1:i+1])/p for i in range(N)]
                    if kind=='mfi':
                        d=[(2*pos[i]-1)*V[i] for i in range(N)]
                        u=S([max(x,0) for x in d]);dn=S([max(-x,0) for x in d])
                        pr=[None if u[i] is None else (100*u[i]/(u[i]+dn[i]) if u[i]+dn[i]>0 else 50) for i in range(N)]
                    else:
                        u=S([pos[i]*V[i] for i in range(N)]);t=S(V)
                        pr=[None if u[i] is None else 100*u[i]/t[i] for i in range(N)]
                    out[(src,p,kind,sm)]=pr
    return out
if __name__=='__main__':
    def auc(pos,neg):
        pos=pos;neg=neg
        allv=sorted([(v,1) for v in pos]+[(v,0) for v in neg]);n=len(allv);s=0;i=0
        while i<n:
            j=i
            while j<n and allv[j][0]==allv[i][0]:j+=1
            for k in range(i,j):
                if allv[k][1]: s+=(i+j+1)/2
            i=j
        return (s-len(pos)*(len(pos)+1)/2)/(len(pos)*len(neg))
    for tf in('15m','2m'):
        B,T,ev=load(tf);P=pressures(B)
        for k,pr in P.items():
            res=[]
            for sg in('buy','sell'):
                ps=[];ns=[]
                for i in range(300,len(B)):
                    v=pr[i] if sg=='buy' else 100-pr[i]
                    e=ev.get(T[i]);(ps if e and e[0]==sg else ns).append(v)
                res.append(auc(ps,ns))
            print(tf,k,[round(x,3) for x in res])
