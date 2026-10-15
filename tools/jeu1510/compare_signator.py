from lib import *
import sys
CUT=int(sys.argv[1]) if len(sys.argv)>1 else 0
names=['Fort Long','Fort Short','Moyen Long','Moyen Short']
tot={}
diffs=[]
for ref,base in (('Vb',34),('Vd',50)):
  print('=== référence original',ref,'cols',base,'-',base+3,'| chauffe coupée:',CUT)
  agg={}
  for b,s,t,f in files():
    R=load(f)[CUT:]
    for k in range(4):
        for r in R:
            o=(r[base+k] or 0)!=0; n=(r[22+k] or 0)!=0
            key=(s,t,names[k]); a=agg.setdefault(key,[0,0,0])
            if o and n:a[0]+=1
            elif n and not o:a[1]+=1; diffs.append((ref,s,t,b[-9:-4],names[k],r[0][:16],'EN TROP'))
            elif o and not n:a[2]+=1; diffs.append((ref,s,t,b[-9:-4],names[k],r[0][:16],'MANQUE'))
  order=['1','2','3','5','15','30','60','240','720','1D']
  for sym in('NQZ','MES'):
    print(sym)
    for tf in order:
        row=[]
        for nm in names:
            a=agg.get((sym,tf,nm))
            if a: row.append('%d/%d/%d'%tuple(a))
        # sums over duplicates
        print(' ',tf.rjust(4),'  '.join(nm+' '+x for nm,x in zip(names,row)))
  T=[sum(v[i] for v in agg.values()) for i in range(3)]
  print('TOTAL exact/trop/manqué',T)
  for nm in names:
    T=[sum(v[i] for k,v in agg.items() if k[2]==nm) for i in range(3)];print('  ',nm,T)
import json
json.dump(diffs,open('diffs_signator.json','w'))
