from sim_climax_logit import *
keys=['vol_r','body_rg','body_atr','rg_atr']
R={tf:rows(tf,keys) for tf in('15m','2m')}
def sc(tf,g,p,c):
    X,Y,_=R[tf];tp=fp=0
    for x,y in zip(X,Y):
        if x[1]>=g and x[0]*x[1]**p>=c:
            if y:tp+=1
            else:fp+=1
    return tp,fp,sum(Y)-tp   # note: manqués hors nw ajoutés plus bas
if __name__=='__main__':
    res=[];n=0
    for g in [.5+.01*j for j in range(0,11)]:
        for p in (0,.5,1,1.5,2,3,4):
            for c in [0.6+0.05*j for j in range(0,70)]:
                a=sc('15m',g,p,c);b=sc('2m',g,p,c);n+=1
                res.append((a[1]+a[2]+b[1]+b[2],round(g,2),p,round(c,2),a,b))
    res.sort(key=lambda r:r[0]);print(n)
    for r in res[:15]:print(r)
