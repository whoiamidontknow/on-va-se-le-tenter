import sys, itertools
from amph_sim import load, CASES
def ispiv(Y,c,G,D,mode):
    if c-G<0 or c+D>=len(Y): return False
    v=Y[c]; l=Y[c-G:c]; r=Y[c+1:c+D+1]
    if mode=='pine': return v>max(l) and v>=max(r)
    if mode=='strict': return v>max(l) and v>max(r)
    if mode=='eqleft': return v>=max(l) and v>=max(r)
def sim(Y,G,D,G2,D2,buf=0.001,nt=3,newH=100,p2='pivot',vrange='now',pm='pine',upd='before',tsrc=None,anch_line=True):
    """Y: mirrored series (resistance on high, support on -low). Anchor: pivot(G,D) per Amphibian rule.
    p2='pivot': 2nd point = pivot(G2,D2) confirmed at this bar; 'bar': current bar.
    vrange: validation over anchor..now or anchor..pivot"""
    n=len(Y); ah=None; ab=None; cur=None; out=[]
    for bi in range(n):
        newanch=False
        def anch():
            nonlocal ah,ab
            c=bi-D
            if ispiv(Y,c,G,D,pm) and (ah is None or Y[c]>ah or bi-ab>newH):
                ah=Y[c]; ab=c; return True
            return False
        if upd=='before': anch()
        cand=None
        if ah is not None:
            if p2=='bar':
                if Y[bi]<ah: cand=bi
            else:
                c2=bi-D2
                if c2>ab and ispiv(Y,c2,G2,D2,pm) and Y[c2]<ah: cand=c2
        if cand is not None:
            sl=(Y[cand]-ah)/(cand-ab); t=0; ok=True
            end=bi if vrange=='now' else cand
            for k in range(ab,end+1):
                p=ah+sl*(k-ab); a=abs(p)*buf
                if Y[k]>p+a: ok=False;break
                if Y[k]>=p-a: t+=1
            if ok and t>=nt: cur=(ab,cand)
        if upd=='after': anch()
        out.append(cur)
    return out
DATA={}
def get(f,cut):
    if (f,cut) not in DATA: DATA[(f,cut)]=load(f,cut)
    return DATA[(f,cut)]
def score(par,cases=CASES,verbose=False):
    sc=0; det=''
    for f,side,ref,cut in cases:
        T,H,L,C=get(f,cut); X=H if side=='R' else L; s=1 if side=='R' else -1
        Y=[s*x for x in X]
        kw=dict(par); 
        for k in ('G','D','G2','D2'):
            if k+side in kw: kw[k]=kw.pop(k+side)
        kw={k:v for k,v in kw.items() if not k[-1] in 'RS' or k in('upd',)}
        l=sim(Y,**kw)[-1]
        got=(X[l[0]],X[l[1]]) if l else None
        ok=got==ref; sc+=ok; det+='✓' if ok else '✗'
        if verbose: print(f[9:24],side,ref,'got',got,T[l[0]][5:] if l else '',T[l[1]][5:] if l else '','OK' if ok else '')
    return sc,det
if __name__=='__main__':
    res=[]
    for G in (5,8,10,12,15):
     for G2 in (2,3,4,5,6,8,10):
      for D2 in (1,2,3,4,5,6,8,10):
       for vr in ('now','piv'):
        for nt in (2,3):
         par=dict(G=G,D=G,G2=G2,D2=D2,vrange=vr,nt=nt)
         sc,det=score(par); res.append((sc,det,par))
    res.sort(key=lambda r:-r[0])
    for r in res[:25]: print(r)
