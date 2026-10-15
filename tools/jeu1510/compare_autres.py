from lib import *
from sim_ours import ema
order=['1','2','3','5','15','30','60','240','720','1D']
print('== Moyenator : écart max |notre(18,19) - original| par bloc, hors None')
mx={}
for b,s,t,f in files():
    R=load(f)
    for nm,(a,bb) in {'Vb':(38,39),'Vc':(46,47),'Vd':(54,55)}.items():
        for k in(0,1):
            d=[abs(r[18+k]-r[a+k]) for r in R if r[18+k] is not None and r[a+k] is not None]
            nn=sum(1 for r in R if (r[18+k] is None)!=(r[a+k] is None))
            m=max(d) if d else 0; key=(nm,k+1); mx[key]=max(mx.get(key,0),m)
            if m>1e-6: print('  ',s,t,b[-9:-4],nm,'M%d'%(k+1),'écart max %.4g'%m,'(lignes None asym.: %d)'%nn)
print('  écart max global :',{k:'%.3g'%v for k,v in mx.items()})
# colonnes 26/27 vides ?
print('  cols 26-27 non vides:',sum(1 for b,s,t,f in files() for r in load(f) if r[26] is not None or r[27] is not None))
print('== Rangeator colonnes 40,41,48,49 non nulles:',sum(1 for b,s,t,f in files() for r in load(f) for i in(40,41,48,49) if (r[i] or 0)!=0),'sur',sum(len(load(f))*4 for b,s,t,f in files()))
print('== colonnes 30-33, 42-45 (blocs signaux d\'instances mortes) non nulles:',sum(1 for b,s,t,f in files() for r in load(f) for i in(30,31,32,33,42,43,44,45) if (r[i] or 0)!=0))
print('== Ancres 20,21 non nulles:',sum(1 for b,s,t,f in files() for r in load(f) for i in(20,21) if (r[i] or 0)!=0))
print('== Heishi 28,29 non nulles:',sum(1 for b,s,t,f in files() for r in load(f) for i in(28,29) if (r[i] or 0)!=0))
# Heishinator
W=100;tot=[0,0,0];ba=0;n=0
print('== Heishinator : EMA(ohlc4,4)>EMA(ohlc4,32) recalculé ; changements d\'état vs flèches Fort/Moyen originales (Vb)')
ok=0;tt=0
for b,s,t,f in files():
    R=load(f);o=[r[1] for r in R];h=[r[2] for r in R];l=[r[3] for r in R];c=[r[4] for r in R]
    src=[(a+bb+cc+d)/4 for a,bb,cc,d in zip(o,h,l,c)];bull=[x>y for x,y in zip(ema(src,4),ema(src,32))]
    for i in range(W,len(R)):
        for k in range(4):
            if (R[i][34+k] or 0)!=0:
                tt+=1
                want=(k%2==0)
                # flèche => bull==want et changement d'état 1 barre avant (run==2)
                if bull[i]==want and bull[i-1]==want and bull[i-2]!=want: ok+=1
print('  flèches Vb dont le sens = Heishinator recalculé avec run==2 :',ok,'/',tt)
# bougies HA : close HA == (o+h+l+c reels)/4 pas testable. Couleur de bougie HA: close>open
