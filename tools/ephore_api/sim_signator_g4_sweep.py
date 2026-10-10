from sim_signator_g4 import *
import itertools,sys
D_=all_data(True)
def ev(warm,**kw):
    tp=fp=fn=0
    for d in D_:
        for i in range(warm,len(d['c'])):
            r=v8(d,i,**kw); p=r is not None
            t=d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i]
            tp+=bool(p and t); fp+=bool(p and not t); fn+=bool(t and not p)
    return tp,fp,fn
n=0
print('base',ev(100),ev(80))
res=[]
for db,vk in itertools.product([0.1,0.15,0.2,0.25,0.3,0.35,0.4,0.5,0.6,9],[0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.25,1.5,99]):
    n+=1; a=ev(100,db_th=db,vol_k=vk); b=ev(80,db_th=db,vol_k=vk); res.append((a[1]+a[2]+b[1]+b[2],db,vk,a,b))
res.sort(); 
for r in res[:8]: print(r)
for adx in (16,17,18,19,20,22):
    n+=1; print('adx',adx,ev(100,adx_th=adx),ev(80,adx_th=adx))
n+=1; print('news',ev(100,use_news=True),ev(80,use_news=True))
for rn in (1,2,3): n+=1; print('run',rn,ev(100,run_n=rn))
n+=1; print('noconv',ev(100,conv=False),ev(80,conv=False))
print('combos',n)
