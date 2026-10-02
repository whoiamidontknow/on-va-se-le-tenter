import json,math,collections
d=json.load(open('api_vitrine_instantane.json'))
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
def run(tf,opt):
    U=d['unites'][tf]; B=U['bougies']; N=len(B)
    T=[b['t']//1000 for b in B]; O=[b['o'] for b in B];H=[b['h'] for b in B];L=[b['l'] for b in B];C=[b['c'] for b in B];V=[b['v'] for b in B]
    o4=[(O[i]+H[i]+L[i]+C[i])/4 for i in range(N)]; bull=[a>b for a,b in zip(ema(o4,4),ema(o4,32))]
    run_=[1]*N
    for i in range(1,N): run_[i]=run_[i-1]+1 if bull[i]==bull[i-1] else 1
    tr=[H[0]-L[0]]+[max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1])) for i in range(1,N)]
    up=[0]+[max(H[i]-H[i-1],0) if H[i]-H[i-1]>L[i-1]-L[i] else 0 for i in range(1,N)]
    dn=[0]+[max(L[i-1]-L[i],0) if L[i-1]-L[i]>H[i]-H[i-1] else 0 for i in range(1,N)]
    atr=rma(tr,14); pu=rma(up,14); pd=rma(dn,14)
    dx=[None if atr[i] is None or pu[i] is None else (abs(pu[i]-pd[i])/(pu[i]+pd[i])*100 if pu[i]+pd[i]>0 else 0) for i in range(N)]
    adx=rma(dx,14); e50=ema(C,50); e60=ema(C,60)
    vs=[sum(V[i-19:i+1])/20 if i>=19 else None for i in range(N)]
    sig={}
    for x in U['indicateurs']:
        if x.get('type')=='marqueur_prix' and str(x.get('id','')).startswith(('sig_lf','sig_sf','v7a','v7c')):
            sig[x['t']]=(x['id'].split('_')[0]+'_'+x['id'].split('_')[1], x.get('sens'), x.get('niveau'))
    tp=fp=fn=0; det=[]
    for i in range(300,N):
        b=bull[i]; u=False
        if run_[i]==2 and adx[i] and adx[i]>=18 and ((C[i]>e50[i]) if b else (C[i]<e50[i])):
            db=((C[i]-max(e50[i],e60[i])) if b else (min(e50[i],e60[i])-C[i]))/atr[i]
            u = (db>=0.3 or V[i]>=vs[i]) if opt.get('conv',True) else True
        o=sig.get(T[i]); o_ok= o is not None and o[0] in ('sig_lf','sig_sf')
        if u and o_ok: tp+=1
        elif u: fp+=1; det.append(('TROP',T[i]))
        elif o_ok: fn+=1; det.append(('MANQ',T[i],o))
    other=collections.Counter(v[0]+':'+str(v[2]) for v in sig.values())
    return tp,fp,fn,other,det
for tf in ('15m','2m'):
    for opt in ({'conv':False},{'conv':True}):
        tp,fp,fn,other,det=run(tf,opt)
        print(tf,opt,'exactes',tp,'trop',fp,'manq',fn,'| types de signaux:',dict(other))
