from lib import *
import sys,json
CUT=int(sys.argv[1]);order=['1','2','3','5','15','30','60','240','720','1D']
data={}
for b,s,t,f in sorted(files(),key=lambda x:-len(open(x[3]).read())):
    for i,r in enumerate(load(f)): data.setdefault((s,t),{}).setdefault(r[0],(r,i,b))
for rn,base in (('Vb',34),('Vd',50)):
  print('###',rn,'flèche (Fort∪Moyen) présente ?  NQ ex/trop/mq | MES ex/trop/mq   (chauffe',CUT,')')
  tot=[0,0,0];lst=[]
  for t in order:
    line=[]
    for s in('NQZ','MES'):
        a=[0,0,0]
        for tm,(r,i,b) in sorted(data[(s,t)].items()):
            if i<CUT:continue
            for k in(0,1):
                o=((r[base+k] or 0)!=0)or((r[base+2+k] or 0)!=0);n=((r[22+k] or 0)!=0)or((r[24+k] or 0)!=0)
                if o and n:a[0]+=1
                elif n:a[1]+=1;lst.append((s,t,tm[:16],'Long' if k==0 else 'Short','trop'))
                elif o:a[2]+=1;lst.append((s,t,tm[:16],'Long' if k==0 else 'Short','manqué'))
        line.append('/'.join(map(str,a)));tot=[x+y for x,y in zip(tot,a)]
    print(' ',t.rjust(4),line[0].ljust(8),'|',line[1])
  print('  TOTAL',tot)
  if rn=='Vb':
    for x in lst:print('   ',x)
