"""Climax (clx_) : regle candidate. Usage: python3 sim_climax.py"""
from sim_climax_feat import *
D={tf:feats(tf) for tf in('15m','2m')}
P=dict(bg=.55,bv=1.5,sg=.65,sv=2.0,pg=.70,pv=2.0)
def detect(f,P):
    if f['nw']==1 and f['body_rg']>=P['bg'] and f['vol_r']>=P['bv']:
        return ('buy','PREMIUM' if f['vol_r']>=P['pv'] and f['body_rg']>=P['pg'] else 'HIGH')
    if f['nw']==-1 and -f['body_rg']>=P['sg'] and f['vol_r']>=P['sv']: return ('sell','HIGH')
def score(tf,P,verbose=False):
    B,T,ev,F=D[tf];tp=fp=fn=0;lv=0;ex=[]
    for i in range(300,len(B)):
        o=ev.get(T[i]);r=detect(F[i],P)
        if r and o and r[0]==o[0]:
            tp+=1;lv+= r[1]==o[1]
            if r[1]!=o[1]: ex.append(('NIV',T[i],r,o))
        elif r: fp+=1;ex.append(('TROP',T[i],i,r))
        elif o: fn+=1;ex.append(('MANQ',T[i],i,o))
    return tp,fp,fn,lv,ex
if __name__=='__main__':
    for tf in D:
        tp,fp,fn,lv,ex=score(tf,P);print(tf,'exactes',tp,'trop',fp,'manq',fn,'niveau ok',lv,'/',tp)
        for e in ex:
            if e[0]!='NIV':print('  ',e)
