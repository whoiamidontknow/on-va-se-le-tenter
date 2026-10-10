import sim_climax as s, itertools
def tot(P):
    r=[s.score(tf,P)[:4] for tf in('15m','2m')];return r
res=[];n=0
for bg,bv,sg,sv,pg,pv in itertools.product((.5,.525,.55,.575,.6),(1.4,1.5,1.6,1.7),(.6,.625,.65,.675,.7),(1.8,2.0,2.2,2.4),(.65,.675,.7,.725),(1.8,2.0,2.2,2.4,2.6)):
    P=dict(bg=bg,bv=bv,sg=sg,sv=sv,pg=pg,pv=pv);n+=1
    a,b=tot(P)
    e=a[1]+a[2]+b[1]+b[2]; lvl=(a[0]-a[3])+(b[0]-b[3])
    res.append((e,lvl,P,a[:3],b[:3]))
res.sort(key=lambda r:(r[0]+r[1]))
print(n,'combos')
for r in res[:6]:print(r)
# robustesse: combien de combos <= 30 erreurs
print('combos avec <=28 erreurs de declenchement:',sum(1 for r in res if r[0]<=28))
print('defaut:',[r for r in res if r[2]==s.P][0])
