from sim_climax_feat import *
D={tf:feats(tf) for tf in('15m','2m')}
def score(tf,rule):
    B,T,ev,F=D[tf];tp=fp=fn=0
    for i in range(300,len(B)):
        e=ev.get(T[i]); o=e[0] if e else None
        r=rule(F[i],i,B)
        if r and r==o: tp+=1
        elif r: fp+=1
        elif o: fn+=1
    return tp,fp,fn
if __name__=='__main__':
    n=0
    for k in (1.3,1.4,1.5,1.6,1.8):
      for br in (0.5,0.6,0.7,0.8,0.9):
        r=lambda f,i,B:(('buy' if f['nw']==1 else 'sell') if f['nw']!=0 and f['vol_r']>=k and abs(f['body_rg'])>=br else None)
        n+=1;print(k,br,score('15m',r),score('2m',r))
