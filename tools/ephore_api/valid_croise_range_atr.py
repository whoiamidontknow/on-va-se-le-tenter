"""Validation croisee du garde-fou 'range >= k*ATR' (k balaye sur 0.30..0.80 par 0.01).
On cale k sur une partie du corpus (un instrument, ou une liste d'unites de temps) et
on mesure sur l'autre. Corpus : groupe 4 de 'Base 10:10/Ajustements'.
"""
import sys
sys.path.insert(0,'/Users/jeremk/Ephore/on-va-se-le-tenter/tools/ephore_api')
import ctx_signator as C
ds=C.build(); ev=C.events(ds)
R=lambda d,i:(d['h'][i]-d['l'][i])/d['atr'][i] if d['atr'][i] else 9
KS=[0.30+0.01*j for j in range(51)]

def ERR(sub,k):
    """erreurs = TP perdus + FP survivants + FN d origine, sur le sous-ensemble sub"""
    lost=sum(1 for kk,d,i in sub if kk=='TP' and R(d,i)<k)
    surv=sum(1 for kk,d,i in sub if kk=='FP' and R(d,i)>=k)
    fn  =sum(1 for kk,d,i in sub if kk=='FN')
    return lost+surv+fn, lost, surv

def fit(sub):
    best=min(KS,key=lambda k:(ERR(sub,k)[0],abs(k-0.5)))
    e=ERR(sub,best)[0]
    plateau=[k for k in KS if ERR(sub,k)[0]==e]
    return best,plateau[0],plateau[-1]

def tell(name,train,test):
    k,lo,hi=fit(train)
    e0=ERR(test,0.0); e1=ERR(test,k)
    print('%-28s k cale=%.2f (plateau %.2f-%.2f) | test: V8 nue %d err -> %d err (perdus %d, FP survivants %d)'
          %(name,k,lo,hi,e0[0],e1[0],e1[1],e1[2]))

for inst in ('MES','NQ'):
    tell('cale %s -> teste %s'%(inst,'NQ' if inst=='MES' else 'MES'),
         [e for e in ev if e[1]['inst']==inst],[e for e in ev if e[1]['inst']!=inst])
for tfs in (('2','5','15'),('30','60'),('240','1D')):
    tell('cale TF %s -> teste reste'%('+'.join(tfs)),
         [e for e in ev if e[1]['tf'] in tfs],[e for e in ev if e[1]['tf'] not in tfs])
tell('cale tout -> teste tout (in-sample)',ev,ev)
print()
print('detail par unite de temps avec k=0.50 :')
print('%-5s %8s %6s %6s %8s %6s %6s'%('tf','ex.V8','trop','manq','ex.0.5','trop','manq'))
for tf in ('2','5','15','30','60','240','1D'):
    s=[e for e in ev if e[1]['tf']==tf]
    tp=sum(1 for k,_,_ in s if k=='TP'); fp=sum(1 for k,_,_ in s if k=='FP'); fn=sum(1 for k,_,_ in s if k=='FN')
    lost=sum(1 for kk,d,i in s if kk=='TP' and R(d,i)<0.5)
    surv=sum(1 for kk,d,i in s if kk=='FP' and R(d,i)>=0.5)
    print('%-5s %8d %6d %6d %8d %6d %6d'%(tf,tp,fp,fn,tp-lost,surv,fn+lost))
