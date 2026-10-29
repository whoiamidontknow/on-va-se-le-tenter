import json,csv,math,collections
d=json.load(open('/Users/jeremk/ERGON/on-va-se-le-tenter/tools/ephore_api/api_vitrine_instantane.json'))
exec(open('/Users/jeremk/ERGON/on-va-se-le-tenter/tools/ephore_api/sig_api.py').read().split('def run')[0].split('d=json.load')[0])
def ema(x,p):
    a=2/(p+1); out=[x[0]]
    for v in x[1:]: out.append(a*v+(1-a)*out[-1])
    return out
def rma(x,p):
    out=[None]*len(x); s=None; buf=[]
    for i,v in enumerate(x):
        if v is None: continue
        if s is None:
            buf.append(v)
            if len(buf)==p: s=sum(buf)/p
        else: s=(s*(p-1)+v)/p
        out[i]=s
    return out
def load(tf):
    U=d['unites'][tf];B=U['bougies']
    T=[b['t']//1000 for b in B]
    ev={}
    for x in U['indicateurs']:
        if str(x.get('id','')).startswith('clx_'): ev[x['t']]=(x['sens'],x['niveau'])
    return B,T,ev
if __name__=='__main__':
    w=csv.writer(open('/Users/jeremk/ERGON/on-va-se-le-tenter/tools/ephore_api/oracle_climax.csv','w'))
    w.writerow(['tf','t','idx','sens','niveau','o','h','l','c','cr','hr','lr','v'])
    for tf in('15m','2m'):
        B,T,ev=load(tf); ix={t:i for i,t in enumerate(T)}
        for t,(s,n) in sorted(ev.items()):
            b=B[ix[t]]; w.writerow([tf,t,ix[t],s,n,b['o'],b['h'],b['l'],b['c'],b['cr'],b['hr'],b['lr'],b['v']])
        print(tf,len(ev),'bars',len(B))
