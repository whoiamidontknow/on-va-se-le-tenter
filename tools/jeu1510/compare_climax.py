from lib import *
order=['1','2','3','5','15','30','60','240','720','1D'];W=100
data={}
for b,s,t,f in sorted(files(),key=lambda x:-len(open(x[3]).read())):
    for i,r in enumerate(load(f)): data.setdefault((s,t),{}).setdefault(r[0],(r,i))
agg={}
for (s,t),d in data.items():
    for tm,(r,i) in d.items():
        if i<W:continue
        for side,mine,orig in(('BUY',((r[5] or 0)!=0 or (r[6] or 0)!=0),(r[56] or 0)!=0),('SELL',(r[7] or 0)!=0,(r[57] or 0)!=0)):
            a=agg.setdefault((t,side),[0,0,0])
            if mine and orig:a[0]+=1
            elif mine:a[1]+=1
            elif orig:a[2]+=1
print('Climator (cols 5-7) vs Climax original confirmed (56-57), NQ+MES dédoublonnés, chauffe 100 : exact/trop/manqué | rappel | précision')
T=[0,0,0]
for t in order:
    for side in('BUY','SELL'):
        a=agg[(t,side)]
        print(' ',t.rjust(4),side.ljust(4),a,'rappel %.0f%% préc %.0f%%'%(100*a[0]/max(1,a[0]+a[2]),100*a[0]/max(1,a[0]+a[1])))
        T=[x+y for x,y in zip(T,a)]
print('TOTAL',T,'rappel %.1f%% précision %.1f%%'%(100*T[0]/(T[0]+T[2]),100*T[0]/(T[0]+T[1])))
for t in order:
    tt=[sum(agg[(t,sd)][i] for sd in('BUY','SELL')) for i in range(3)]
    print(' ',t.rjust(4),tt,'rappel %.0f%% préc %.0f%%'%(100*tt[0]/max(1,tt[0]+tt[2]),100*tt[0]/max(1,tt[0]+tt[1])))
