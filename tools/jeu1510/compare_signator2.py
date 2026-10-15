from lib import *
import sys,json
CUT=int(sys.argv[1]) if len(sys.argv)>1 else 0
order=['1','2','3','5','15','30','60','240','720','1D']
# dedupe par (sym,tf,time): fichier primaire = le plus long; doublons complètent
data={}
for b,s,t,f in sorted(files(),key=lambda x:-len(open(x[3]).read())):
    R=load(f)
    for i,r in enumerate(R):
        data.setdefault((s,t),{}).setdefault(r[0],(r,i,b))
ref={'Vb':34,'Vd':50}
res={};diffs=[]
for (s,t),d in data.items():
    ts=sorted(d)
    for rn,base in ref.items():
        for grp,ks in (('Fort',(0,1)),('Moyen',(2,3))):
            a=res.setdefault((rn,s,t,grp),[0,0,0])
            for tm in ts:
                r,i,b=d[tm]
                if i<CUT: continue
                for k in ks:
                    o=(r[base+k] or 0)!=0;n=(r[22+k] or 0)!=0
                    nm=('Long','Short')[k%2]
                    if o and n:a[0]+=1
                    elif n:a[1]+=1;diffs.append((rn,s,t,grp+' '+nm,tm[:16],i,'EN TROP'))
                    elif o:a[2]+=1;diffs.append((rn,s,t,grp+' '+nm,tm[:16],i,'MANQUÉ'))
for rn in ref:
  for grp in('Fort','Moyen'):
    print('###',rn,grp,'(exact/trop/manqué) NQ | MES')
    for t in order:
        x=res.get((rn,'NQZ',t,grp));y=res.get((rn,'MES',t,grp))
        print(' ',t.rjust(4),'/'.join(map(str,x)).ljust(9),'|','/'.join(map(str,y)))
    T=[sum(v[i] for k,v in res.items() if k[0]==rn and k[3]==grp) for i in range(3)]
    print('  TOTAL',T)
json.dump(diffs,open('diffs_signator_cut%d.json'%CUT,'w'))
