"""RESULTAT : garde-fou 'range de la bougie >= 0.5 x ATR14' ajoute a la V8 Signator.
Corpus : groupe 4 des 14 exports 'Base 10:10/Ajustements' (MES + NQ, 7 unites), warmup 100.
Imprime les chiffres de tete + la selectivite + la p-valeur hypergeometrique.
Usage : python3 sim_signator_range_atr.py
"""
import sys, math
sys.path.insert(0,'/Users/jeremk/Ephore/on-va-se-le-tenter/tools/ephore_api')
import ctx_signator as C
from sim_signator_g4 import v8

K=0.5
ds=C.build()
R=lambda d,i:(d['h'][i]-d['l'][i])/d['atr'][i] if d['atr'][i] else 9.0

tp=fp=fn=0; det=0; touche=0; ecarts=[]
for d in ds:
    for i in range(C.WARM,len(d['c'])):
        truth=bool(d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i])
        base=v8(d,i) is not None
        if base:
            det+=1
            if R(d,i)<K: touche+=1
        pred=base and R(d,i)>=K
        if truth and pred: tp+=1
        elif truth:
            fn+=1; ecarts.append(('MANQ',d['inst'],d['tf'],d['t'][i][:16],R(d,i),base))
        elif pred:
            fp+=1; ecarts.append(('TROP',d['inst'],d['tf'],d['t'][i][:16],R(d,i),base))
print('V8 + garde-fou range>=%.2f*ATR14 : %d exactes / %d en trop / %d manquees (sur %d fleches)'
      %(K,tp,fp,fn,tp+fn))
print('reference V8 nue : 153 exactes / 6 en trop / 2 manquees')
print('selectivite : le garde-fou touche %d des %d detections de la V8 (%.1f %%), dont 6 des 6 faux positifs'
      %(touche,det,100*touche/det))
# p-valeur : les 6 faux positifs sont les 6 plus petits range/ATR parmi les 7 plus petits des 161 evenements
def comb(n,k): return math.comb(n,k)
p=comb(7,6)*comb(154,0)/comb(161,6)
print('p-valeur (les 6 faux positifs tombent dans les 7 plus petits range/ATR sur 161 evenements) = %.2e'%p)
print('\necarts restants :')
for e in ecarts: print('  %-4s %-4s %-4s %-16s range/ATR=%.3f %s'%(e[0],e[1],e[2],e[3],e[4],'(tuee par le garde-fou)' if e[5] else '(deja manquee par la V8)'))
