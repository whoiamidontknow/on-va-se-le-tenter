from sim_signator_g4 import *
import collections
D_=all_data(True); A=collections.defaultdict(lambda:[0,0,0]); B=collections.defaultdict(lambda:[0,0,0])
for d in D_:
    for i in range(100,len(d['c'])):
        r=v8(d,i); tA=d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i]; tF=d['LF'][i] or d['SF'][i]
        pA=r is not None; pF=pA and r[1]=='F'
        for key in ((d['inst'],d['tf']),(d['inst'],'*'),('*',d['tf']),('*','*')):
            a=A[key];b=B[key]
            a[0]+=bool(pA and tA);a[1]+=bool(pA and not tA);a[2]+=bool(tA and not pA)
            b[0]+=bool(pF and tF);b[1]+=bool(pF and not tF);b[2]+=bool(tF and not pF)
print('cle | arrow(any) exact/trop/manque | Fort exact/trop/manque')
for k in sorted(A,key=lambda k:(k[0]!='*',k)): print(k,A[k],B[k])
