"""Variantes de la 'conviction' pour expliquer les 7 manqués / 10 en trop vs Vb. Présence de flèche (Fort∪Moyen), W=100."""
from sim_ours import *
import itertools
W=100
DS=[]
for b,s,t,f in files():
    R=load(f);F=feats(R)
    DS.append((s,t,b,R,F))
def vol_series(R): return [r[17] or 0 for r in R]
def ev(variant):
    ex=tr=mq=0;err=[]
    for s,t,b,R,F in DS:
        v=vol_series(R)
        for i in range(W,len(R)):
            f=F[i]
            if 'score' not in f or f['adx'] is None: continue
            pred=False
            if f['run']==2 and (f['c']>f['e50'] if f['bull'] else f['c']<f['e50']) and not news(R[i][0],t):
                pred=variant(f,F,R,v,i)
            for k in(0,1):
                truth=any((R[i][34+k+2*m] or 0)!=0 for m in(0,1))
                mine=pred and (f['bull']==(k==0))
                if mine and truth:ex+=1
                elif mine:tr+=1;err.append((s,t,R[i][0][:16],'T'))
                elif truth:mq+=1;err.append((s,t,R[i][0][:16],'M'))
    return ex,tr,mq,err
def base(f,extra):
    return f['adx']>=18 and (f['rngatr']>=.5 or f['cpos']>=.67) and extra
V={}
V['actuel']=lambda f,F,R,v,i: base(f,(f['dB']>=.3 or f['vol']>=f['vma']))
n=0
for th in(0.1,0.2,0.3,0.4,0.5):
  for vk in(0.5,0.6,0.7,0.8,0.9,1.0,1.2):
    V['dB>=%s ou vol>=%s*vma'%(th,vk)]=(lambda th,vk:lambda f,F,R,v,i: base(f,(f['dB']>=th or f['vol']>=vk*f['vma'])))(th,vk)
V['dB>=0.3 ou vol[1]>=vma[1]']=lambda f,F,R,v,i: base(f,(f['dB']>=.3 or (F[i-1]['vma'] and v[i-1]>=F[i-1]['vma'])))
V['dB>=0.3 (seul)']=lambda f,F,R,v,i: base(f,f['dB']>=.3)
V['sans conviction']=lambda f,F,R,v,i: base(f,True)
V['dB>=0.3 ou vol>=vma[1]']=lambda f,F,R,v,i: base(f,(f['dB']>=.3 or (F[i-1]['vma'] and v[i]>=F[i-1]['vma'])))
V['dB>=0.3 ou vol>vma']=lambda f,F,R,v,i: base(f,(f['dB']>=.3 or f['vol']>f['vma']))
res=[]
for k,fn in V.items():
    ex,tr,mq,err=ev(fn);res.append((tr+mq,k,ex,tr,mq))
res.sort()
print(len(V),'variantes')
for r in res[:12]:print(r)
print([r for r in res if r[1]=='actuel'])
