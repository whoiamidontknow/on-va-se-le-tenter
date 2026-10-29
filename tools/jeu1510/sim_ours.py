"""Réimplémentation Python de la chaîne Signator de COMPLETV2 (V5), calculée depuis les colonnes HA du CSV."""
import sys,math,datetime
sys.path.insert(0,'/Users/jeremk/ERGON/on-va-se-le-tenter/tools/ephore_api')
from impl_lab_core import ema_first as ema, rma
from lib import *
from zoneinfo import ZoneInfo
NY=ZoneInfo('America/New_York')
MT=0.25
def feats(R):
    n=len(R); o=[r[1] for r in R];h=[r[2] for r in R];l=[r[3] for r in R];c=[r[4] for r in R];v=[r[17] or 0 for r in R]
    src=[(o[i]+h[i]+l[i]+c[i])/4 for i in range(n)]
    ef=ema(src,4);es=ema(src,32);bull=[a>b for a,b in zip(ef,es)]
    run=[1]*n
    for i in range(1,n): run[i]=run[i-1]+1 if bull[i]==bull[i-1] else 1
    e50=[r[18] for r in R]; e60=[r[19] for r in R]
    if any(x is None for x in e50+e60): print('  (Moyenator manquant, repli EMA propre)',sum(x is None for x in e50)); a50=ema(c,50);a60=ema(c,60);e50=[x if x is not None else y for x,y in zip(e50,a50)];e60=[x if x is not None else y for x,y in zip(e60,a60)]   # Moyenator exporté = EMA50/60 exactes
    tr=[h[0]-l[0]]+[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,n)]
    atr=rma(tr,14)
    up=[0]+[h[i]-h[i-1] for i in range(1,n)];dn=[0]+[l[i-1]-l[i] for i in range(1,n)]
    pdm=[u if (u>d and u>0) else 0.0 for u,d in zip(up,dn)];mdm=[d if (d>u and d>0) else 0.0 for u,d in zip(up,dn)]
    trs=rma(tr,14);ps=rma(pdm,14);ms=rma(mdm,14)
    dip=[100*a/b if a is not None and b else None for a,b in zip(ps,trs)]
    dim=[100*a/b if a is not None and b else None for a,b in zip(ms,trs)]
    dx=[None if a is None else abs(a-b)/((a+b) or 1)*100 for a,b in zip(dip,dim)]
    adx=rma(dx,14)
    vma=[None]*n
    for i in range(19,n): vma[i]=sum(v[i-19:i+1])/20
    F=[]
    for i in range(n):
        f=dict(i=i,bull=bull[i],run=run[i],adx=adx[i],atr=atr[i],vma=vma[i])
        if atr[i] is None or vma[i] is None or e50[i] is None or i==0: F.append(f);continue
        rng=h[i]-l[i];rs=max(rng,MT);br=min(abs(c[i]-o[i])/rs/.5,1)
        cpos=(c[i]-l[i])/rs if bull[i] else (h[i]-c[i])/rs
        aw=(h[i]-c[i])/rs if bull[i] else (c[i]-l[i])/rs
        sS=(br+(1-min(aw/.35,1))+min(cpos/.67,1))/3
        sM=min(rng/max(.5*atr[i],MT),1);sV=min(v[i]/vma[i],1) if vma[i]>0 else 0
        sG=min(abs(o[i]-c[i-1])/max(.3*atr[i],MT),1)
        score=(sS+sM+sV+sG)/4*100
        dB=(c[i]-max(e50[i],e60[i]))/atr[i] if bull[i] else (min(e50[i],e60[i])-c[i])/atr[i]
        f.update(sS=sS,sM=sM,sV=sV,sG=sG,score=score,dB=dB,cpos=cpos,rng=rng,vol=v[i],c=c[i],e50=e50[i],rngatr=rng/atr[i],
                 volr=v[i]/vma[i] if vma[i] else None)
        F.append(f)
    return F
def news(tm, tf):
    if tf=='1D' or tf in('720',) and False: return False
    # tm 'YYYY-MM-DDTHH:MM:SS+02:00' heure de Paris
    if tf=='1D': return False
    dt=datetime.datetime.fromisoformat(tm).astimezone(NY)
    m=dt.hour*60+dt.minute
    return abs(m-(8*60+30))<=3 or abs(m-600)<=3
def arrows(R,tf,F=None,score_min=50,force=18,v9=True,black=True,adxth=18):
    F=F or feats(R);out=[]
    for i,f in enumerate(F):
        if 'score' not in f or f['adx'] is None: out.append(None);continue
        base=(f['run']==2 and f['adx']>=adxth and (f['c']>f['e50'] if f['bull'] else f['c']<f['e50'])
              and (f['dB']>=0.3 or f['vol']>=f['vma']) and (not v9 or f['rngatr']>=0.5 or f['cpos']>=0.67)
              and not (black and news(R[i][0],tf)))
        if not base: out.append(None);continue
        if f['score']>=score_min: out.append(('F','L' if f['bull'] else 'S'))
        elif f['score']>=force: out.append(('M','L' if f['bull'] else 'S'))
        else: out.append(None)
    return out
if __name__=='__main__':
    W=100;tot=[0,0,0]
    for b,s,t,f in files():
        R=load(f);A=arrows(R,t)
        ex=tr=mq=0;dl=[]
        for i in range(W,len(R)):
            for k in range(4):
                mine=A[i] is not None and A[i]==(('F','M')[k//2],('L','S')[k%2])
                ours=(R[i][22+k] or 0)!=0
                if mine and ours:ex+=1
                elif mine:tr+=1;dl.append((R[i][0][:16],k,'sim seul'))
                elif ours:mq+=1;dl.append((R[i][0][:16],k,'CSV seul'))
        print(s,t,b[-9:-4],'sim vs notre colonne: ',ex,tr,mq,dl[:4])
