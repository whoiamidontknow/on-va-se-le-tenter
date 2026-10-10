from sim_climax_logit import *
keys=['vol_r','body_rg','body_atr','rg_atr','sell']
R={tf:rows(tf,keys) for tf in('15m','2m')}
def sc(tf,sell,g,p,c):
    X,Y,_=R[tf];tp=fp=fn=0
    for x,y in zip(X,Y):
        if x[4]!=sell: continue
        if x[1]>=g and x[0]*x[1]**p>=c:
            if y:tp+=1
            else:fp+=1
        elif y: fn+=1
    return tp,fp,fn
if __name__=='__main__':
    n=0
    for sell in(0,1):
        res=[]
        for g in [.4+.025*j for j in range(0,16)]:
            for p in (0,.5,1,2):
                for c in [0.8+0.1*j for j in range(0,40)]:
                    a=sc('15m',sell,g,p,c);b=sc('2m',sell,g,p,c);n+=1
                    res.append((a[1]+a[2]+b[1]+b[2],round(g,3),p,round(c,2),a,b))
        res.sort(key=lambda r:r[0]);print('sell' if sell else 'buy')
        for r in res[:8]:print(r)
    print(n)
