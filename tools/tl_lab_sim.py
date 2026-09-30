import csv,glob,os
def load(f,cut=None):
    R=[r for r in csv.DictReader(open(f)) if cut is None or r['time'][:16]<=cut]
    return [r['time'][:16] for r in R],[float(r['high']) for r in R],[float(r['low']) for r in R]
def sim(T,H,L,side,mode='confirm',bars=10,buf=0.001,nT=3,newH=100,gate=True):
    Y=H if side=='R' else [-x for x in L]; n=len(Y)
    ancH=ancB=None; last=None; line=None
    def check(a,ya,b,yb,t):
        sl=(yb-ya)/(b-a); tc=0
        for k in range(a,t+1):
            p=ya+sl*(k-a)
            if Y[k]>p+abs(p)*buf: return False
            if Y[k]>=p-abs(p)*buf: tc+=1
        return tc>=nT
    for t in range(n):
        c=t-bars; ph=None
        if c-bars>=0 and all(Y[c]>Y[c-k] for k in range(1,bars+1)) and all(Y[c]>=Y[c+k] for k in range(1,bars+1)): ph=Y[c]
        if ph is not None and (ancH is None or ph>ancH or t-ancB>newH):
            ancH,ancB=ph,c; last=None
        elif ph is not None and c>ancB and ph<ancH:
            last=(c,ph)
            if mode=='confirm' and check(ancB,ancH,c,ph,t): line=(ancB,ancH,c,ph)
        if mode=='every' and last is not None and (not gate or Y[t]<ancH):
            if check(ancB,ancH,last[0],last[1],t): line=(ancB,ancH,last[0],last[1])
    if line is None: return None
    a,ya,b,yb=line; s=1 if side=='R' else -1
    return (T[a],s*ya,T[b],s*yb)
