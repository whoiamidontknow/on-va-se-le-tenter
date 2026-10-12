"""Balayage des variables de CONTEXTE sur les 161 evenements V8 vs groupe 4.
Chaque hypothese est un filtre additionnel applique APRES la V8 : il ne peut que
tuer des faux positifs et perdre des vraies fleches. On compte TP gardes / FP tues /
TP perdus, separement MES / NQ et par unite de temps.
Sortie : classement + nombre de combinaisons testees.
"""
import sys, itertools
sys.path.insert(0,'/Users/jeremk/Ephore/on-va-se-le-tenter/tools/ephore_api')
import ctx_signator as C

ds=C.build(); ev=C.events(ds)
TP=[(d,i) for k,d,i in ev if k=='TP']; FP=[(d,i) for k,d,i in ev if k=='FP']
FN=[(d,i) for k,d,i in ev if k=='FN']
NTP,NFP=len(TP),len(FP)

def score(pred, name, out):
    lost=[(d,i) for d,i in TP if not pred(d,i)]
    kill=[(d,i) for d,i in FP if not pred(d,i)]
    err=len(lost)+(NFP-len(kill))+len(FN)
    lostMES=sum(1 for d,i in lost if d['inst']=='MES'); lostNQ=len(lost)-lostMES
    killMES=sum(1 for d,i in kill if d['inst']=='MES'); killNQ=len(kill)-killMES
    out.append((err,len(kill),len(lost),name,killMES,killNQ,lostMES,lostNQ))

out=[]; ncomb=0
vS=lambda d,i: (d['v'][i]/d['vma'][i]) if d['vma'][i] else None

# --- 1. fenetre de seance, heure de Paris et de New York, bornes 0..23
for tz in ('paris','ny'):
    for a in range(0,24):
        for b in range(a+1,25):
            ncomb+=1
            def p(d,i,a=a,b=b,tz=tz):
                if d['dayonly'][i]: return True
                hh=d['hr'][i] if tz=='paris' else d['nyh'][i]
                return a<=hh<b
            score(p,'seance %s %02dh-%02dh'%(tz,a,b),out)
# --- 1b. jours de la semaine exclus
for wset in itertools.chain.from_iterable(itertools.combinations(range(7),k) for k in (1,2)):
    ncomb+=1
    score(lambda d,i,w=wset: d['wd'][i] not in w, 'hors jours %s'%(wset,), out)
# --- 2. liquidite horaire
for k in [0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.2]:
    ncomb+=1
    score(lambda d,i,k=k: d['volh'][i] is None or d['volh'][i]>=k,'volHour>=%.1f'%k,out)
    ncomb+=1
    score(lambda d,i,k=k: (d['volh'][i] is None or d['volh'][i]>=k) or (vS(d,i) or 9)>=1,'volHour>=%.1f ou volSMA>=1'%k,out)
# --- 3. distance aux extremes / position dans le range
for N in (10,20,50,100):
    for lo in [0.0,0.1,0.2,0.3,0.4]:
        ncomb+=1
        score(lambda d,i,N=N,lo=lo: d['dext'][N][2][i] is None or not (lo<=d['dext'][N][2][i]<=1-lo),'pos%d hors [%.1f,%.1f]'%(N,lo,1-lo),out)
    for th in [0.5,1.0,1.5,2.0,2.5,3.0]:
        ncomb+=1
        score(lambda d,i,N=N,th=th: (d['dext'][N][0][i] is None) or (d['dext'][N][0][i]<=th if d['bull'][i] else d['dext'][N][1][i]<=th),'dist extreme%d <=%.1f ATR'%(N,th),out)
# --- 4. multi-barres : delai minimum entre deux fleches, direction precedente
for n in (2,3,4,5,6,8,10,15,20):
    ncomb+=1
    score(lambda d,i,n=n: d['sincepred'][i]>=n,'delai>=%d barres'%n,out)
ncomb+=1
score(lambda d,i: d['prevdir'][i]==(1 if d['bull'][i] else -1),'barre prec. meme sens',out)
ncomb+=1
score(lambda d,i: d['prevdir'][i]!=(1 if d['bull'][i] else -1),'barre prec. sens oppose',out)
# --- 5. regime de volatilite
for N in (20,50,100):
    for lo in [0.7,0.8,0.9,1.0]:
        ncomb+=1
        score(lambda d,i,N=N,lo=lo: d['volreg'][N][i] is None or d['volreg'][N][i]>=lo,'atr/atrMoy%d>=%.1f'%(N,lo),out)
for th in [0.3,0.35,0.4,0.45,0.5,0.55,0.6,0.65,0.7,0.75,0.8]:
    ncomb+=1
    score(lambda d,i,th=th: d['rngatr'][i] is None or d['rngatr'][i]>=th,'range>=%.2f ATR'%th,out)
    ncomb+=1
    score(lambda d,i,th=th: (d['rngatr'][i] or 9)>=th or (vS(d,i) or 9)>=1,'range>=%.2f ATR ou volSMA>=1'%th,out)
    ncomb+=1
    score(lambda d,i,th=th: (d['rngatr'][i] or 9)>=th and (d['volh'][i] is None or d['volh'][i]>=0.5),'range>=%.2f ATR et volHour>=0.5'%th,out)
# --- 6. position dans la journee : 1re barre de seance, barre d'ouverture
ncomb+=1
score(lambda d,i: d['dayonly'][i] or not (d['mop'][i] in (0,)),'pas la barre de 00:00',out)
ncomb+=1
score(lambda d,i: d['dayonly'][i] or d['mop'][i]!=23*60,'pas la barre de 23:00',out)
# corps de la bougie / ATR (variante de range)
for th in [0.1,0.2,0.3,0.4,0.5]:
    ncomb+=1
    score(lambda d,i,th=th: (abs(d['c'][i]-d['o'][i])/d['atr'][i])>=th if d['atr'][i] else True,'corps>=%.1f ATR'%th,out)

out.sort(key=lambda r:(r[0],-r[1]))
print('combinaisons testees :',ncomb)
print('reference V8 : 153 exactes / 6 en trop / 2 manquees -> 8 erreurs')
print('%-34s %4s %4s %4s  %-11s %-11s'%('regle','err','tues','perd','tues M/NQ','perdus M/NQ'))
seen=set()
for err,kill,lost,name,kM,kN,lM,lN in out[:25]:
    print('%-34s %4d %4d %4d  %-11s %-11s'%(name,err,kill,lost,'%d/%d'%(kM,kN),'%d/%d'%(lM,lN)))
